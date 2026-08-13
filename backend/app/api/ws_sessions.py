"""WebSocket endpoint for session-based chat.

Protocol (Phase 1):
  Inbound:
    - {"type": "chat", "message": "...", "client_message_id": "..."} — start a chat turn
    - {"type": "chat.stop"} — cancel current generation
    - {"type": "workspace.read", "path": "..."} — read a file from workspace

  Outbound:
    - {"type": "chat.ack", "message_id": "...", "session_id": "..."}
    - {"type": "chat.token", "session_id": "...", "message_id": "...", "delta": "..."}
    - {"type": "chat.done", "session_id": "...", "message_id": "...", "content": "..."}
    - {"type": "chat.message", "session_id": "...", "role": "...", "content": "...", "ts": ...}
    - {"type": "agent_update", "session_id": "...", "node": "...", "label": "...", "status": "..."}
    - {"type": "workspace.updated", "written": [...], "skipped": [...], "timestamp": ...}
    - {"type": "file.content", "path": "...", "content": "..."}
    - {"type": "error", "session_id": "...", "message": "..."}
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.session_store import session_store
from app.services.runner import get_runner, remove_runner

logger = logging.getLogger(__name__)

ws_router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections per session."""

    def __init__(self):
        # session_id -> set of WebSocket connections
        self._connections: Dict[str, Set[WebSocket]] = {}

    def connect(self, session_id: str, websocket: WebSocket):
        if session_id not in self._connections:
            self._connections[session_id] = set()
        self._connections[session_id].add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket):
        conns = self._connections.get(session_id)
        if conns:
            conns.discard(websocket)
            if not conns:
                del self._connections[session_id]

    async def broadcast(self, session_id: str, msg_type: str, data: Dict[str, Any]):
        """Send a typed message to all connections for a session."""
        msg = {"type": msg_type, **data}
        text = json.dumps(msg)
        conns = self._connections.get(session_id, set())
        for ws in list(conns):
            try:
                await ws.send_text(text)
            except Exception:
                # Connection likely closed
                self.disconnect(session_id, ws)


manager = ConnectionManager()


@ws_router.websocket("/ws/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for session chat."""
    await websocket.accept()
    manager.connect(session_id, websocket)

    session = session_store.get(session_id)
    if not session:
        await websocket.send_text(json.dumps({"type": "error", "message": "Session not found"}))
        await websocket.close()
        manager.disconnect(session_id, websocket)
        return

    # Send session snapshot on connect (history sync).
    await websocket.send_text(json.dumps({
        "type": "session.snapshot",
        "session_id": session_id,
        "session": {
            "id": session.id,
            "name": session.name,
            "workspace_path": session.workspace_path,
            "idea": session.idea,
            "messages": session.messages,
            "requirements": session.requirements,
            "architecture": session.architecture,
            "files": session.files,
            "test_results": session.test_results,
            "review_feedback": session.review_feedback,
            "documentation": session.documentation,
            "errors": session.errors,
            "fixes": session.fixes,
            "created_at": session.created_at,
        },
    }))

    # Broadcast helper bound to this session — thread-safe via call_soon_threadsafe.
    loop = asyncio.get_running_loop()

    def broadcast(msg_type: str, data: Dict[str, Any]):
        # Schedule the coroutine on the running loop from any thread.
        loop.call_soon_threadsafe(
            lambda: asyncio.create_task(manager.broadcast(session_id, msg_type, data))
        )

    # Stash the broadcaster on the Session so REST endpoints (write/run) can
    # also emit WS events through the same loop.
    setattr(session, "_broadcast_closure", broadcast)

    runner = get_runner(session, broadcast)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))
                continue

            msg_type = msg.get("type")

            if msg_type == "chat":
                message = msg.get("message", "")
                if not message:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Empty message"}))
                    continue

                # Run the chat turn (non-blocking for us — runner handles async internally).
                runner._current_task = asyncio.create_task(runner.run_chat(message))

            elif msg_type == "chat.stop":
                runner.cancel()
                await websocket.send_text(json.dumps({"type": "chat.stopped", "session_id": session_id}))

            elif msg_type == "workspace.read":
                from app.services import workspace as ws
                path = msg.get("path", "")
                if not session.workspace_path:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "session_id": session_id,
                        "message": "No workspace set",
                    }))
                    continue
                try:
                    _, content = ws.read_file(session.workspace_path, path)
                    await websocket.send_text(json.dumps({
                        "type": "file.content",
                        "path": path,
                        "content": content,
                    }))
                except ws.WorkspaceError as e:
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "session_id": session_id,
                        "message": str(e),
                    }))

            else:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {msg_type}",
                }))

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(session_id, websocket)
        remove_runner(session_id)
        # Stop the preview app when the client goes away (fire-and-forget).
        from app.services import project_runner

        project_runner.remove_runner(session_id)
