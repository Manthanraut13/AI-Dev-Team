"""REST API for session management.

Phase 1 endpoints:
  - POST /sessions — create session (optionally with workspace)
  - GET /sessions — list all sessions
  - GET /sessions/{id} — get session details
  - DELETE /sessions/{id} — delete session
  - POST /sessions/{id}/workspace — set workspace path
  - GET /sessions/{id}/workspace/tree — list files
  - GET /sessions/{id}/workspace/file — read file content
  - POST /sessions/{id}/write — write generated files to disk
  - POST /sessions/{id}/chat — REST fallback (starts chat, returns message_id)
  - POST /sessions/{id}/run — start the generated app (preview)
  - POST /sessions/{id}/stop — stop the running app
  - GET /sessions/{id}/run/status — current preview status
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.schemas.session import (
    ChatRequest,
    ChatResponse,
    SessionCreate,
    SessionResponse,
    SessionSummary,
    WorkspaceFileResponse,
    WorkspaceSetRequest,
    WorkspaceTreeResponse,
    WriteRequest,
    WriteResponse,
)
from app.services import workspace as ws
from app.services.session_store import Session, session_store

logger = logging.getLogger(__name__)

router = APIRouter()


# Marker used to attach the broadcast closure to a Session instance so the
# REST endpoints can drive the runner without re-creating it.
_BROADCAST_ATTR = "_broadcast_closure"


# --- Session CRUD ---


@router.post("/sessions", response_model=SessionResponse)
def create_session(body: SessionCreate) -> SessionResponse:
    """Create a new session, optionally resolving a workspace."""
    # Create session in store.
    session = session_store.create(name=body.name or "Untitled")

    # Resolve workspace if requested.
    if body.workspace:
        try:
            if body.workspace.mode == "existing" and body.workspace.path:
                session.workspace_path = ws.resolve("existing", path=body.workspace.path)
            elif body.workspace.mode == "create" and body.workspace.name:
                session.workspace_path = ws.resolve("create", name=body.workspace.name)
        except ws.WorkspaceError as e:
            # Session created but workspace failed — user can retry via POST /{id}/workspace.
            logger.warning(f"Workspace resolution failed: {e}")

    session_store.save(session)
    return _session_to_response(session)


@router.get("/sessions", response_model=list[SessionSummary])
def list_sessions() -> list[SessionSummary]:
    """List all sessions (summary only, no messages)."""
    return [
        SessionSummary(
            id=s.id,
            name=s.name,
            workspace_path=s.workspace_path,
            has_files=bool(s.files),
            created_at=s.created_at,
        )
        for s in session_store.list()
    ]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    """Get full session state including messages and artifacts."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return _session_to_response(session)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """Delete a session. Stops any running preview first."""
    if not session_store.delete(session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    # Stop the preview runner (kills uvicorn/next dev process trees).
    from app.services.project_runner import pop_runner

    runner = pop_runner(session_id)
    if runner is not None:
        await runner.stop()

    return {"status": "deleted", "session_id": session_id}


# --- Workspace ---


@router.post("/sessions/{session_id}/workspace", response_model=SessionResponse)
def set_workspace(session_id: str, body: WorkspaceSetRequest) -> SessionResponse:
    """Set or change the workspace path for a session."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        session.workspace_path = ws.resolve("existing", path=body.path)
    except ws.WorkspaceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    session_store.save(session)
    return _session_to_response(session)


@router.get("/sessions/{session_id}/workspace/tree", response_model=WorkspaceTreeResponse)
def get_workspace_tree(session_id: str) -> WorkspaceTreeResponse:
    """List files in the workspace directory."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.workspace_path:
        raise HTTPException(status_code=400, detail="No workspace set for this session")

    try:
        nodes = ws.list_files(session.workspace_path)
    except ws.WorkspaceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from app.schemas.session import WorkspaceNode
    return WorkspaceTreeResponse(
        workspace_path=session.workspace_path,
        tree=[WorkspaceNode(path=n.path, type=n.type, size=n.size) for n in nodes],
    )


@router.get("/sessions/{session_id}/workspace/file", response_model=WorkspaceFileResponse)
def read_workspace_file(session_id: str, path: str) -> WorkspaceFileResponse:
    """Read a file from the workspace."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.workspace_path:
        raise HTTPException(status_code=400, detail="No workspace set for this session")

    try:
        rel_path, content = ws.read_file(session.workspace_path, path)
    except ws.WorkspaceError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return WorkspaceFileResponse(path=rel_path, content=content)


@router.post("/sessions/{session_id}/write", response_model=WriteResponse)
def write_files_to_workspace(session_id: str, body: WriteRequest) -> WriteResponse:
    """Write generated files to the workspace disk."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.workspace_path:
        raise HTTPException(status_code=400, detail="No workspace set for this session")
    if not session.files:
        raise HTTPException(status_code=400, detail="No files generated. Run build_project first.")

    try:
        written, skipped = ws.write_files(session.workspace_path, session.files, overwrite=body.overwrite)
    except ws.WorkspaceError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Auto-run hint: if a broadcast closure is attached, emit preview.auto so
    # connected clients (websocket) can fire off POST /run themselves.
    _broadcast = getattr(session, _BROADCAST_ATTR, None)
    if _broadcast is not None:
        try:
            _broadcast("preview.auto", {
                "session_id": session.id,
                "workspace_path": session.workspace_path,
            })
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(f"preview.auto broadcast failed: {exc}")

    return WriteResponse(written=written, skipped=skipped)


# --- Preview (auto-run) -----------------------------------------------------


async def _run_runner(session: "Session", action: str) -> Dict[str, Any]:
    """Drive the ProjectRunner for this session.

    Looks up the broadcast closure attached by the WS handler; falls back to a
    no-op broadcaster when called via REST without a connected WS.
    """
    if not session.workspace_path:
        raise HTTPException(status_code=400, detail="No workspace set for this session")

    from app.services.project_runner import get_runner

    broadcast = getattr(session, _BROADCAST_ATTR, None)
    if broadcast is None:
        # REST-only path: no WS attached. Use a no-op broadcaster so the
        # runner still emits status internally (returned via the response).
        broadcast = lambda *_args, **_kw: None  # noqa: E731

    runner = get_runner(session.id, session.workspace_path, broadcast)

    if action == "start":
        return await runner.start()
    if action == "stop":
        return await runner.stop()
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@router.post("/sessions/{session_id}/run")
async def run_session(session_id: str) -> Dict[str, Any]:
    """Start the generated app (install deps + run backend/frontend).

    Returns the runner status snapshot. Streaming logs and URL updates are
    broadcast over WebSocket as ``preview.log`` / ``preview.status`` /
    ``preview.ready`` events.
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await _run_runner(session, "start")


@router.post("/sessions/{session_id}/stop")
async def stop_session(session_id: str) -> Dict[str, Any]:
    """Stop the running app (kills the uvicorn + next dev process trees)."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await _run_runner(session, "stop")


@router.get("/sessions/{session_id}/run/status")
async def run_status(session_id: str) -> Dict[str, Any]:
    """Return the current preview status snapshot."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.services.project_runner import get_runner

    broadcast = getattr(session, _BROADCAST_ATTR, None) or (lambda *_a, **_kw: None)
    runner = get_runner(session.id, session.workspace_path or "", broadcast)
    return runner.status_snapshot()


# --- Chat (REST fallback) ---


@router.post("/sessions/{session_id}/chat", response_model=ChatResponse)
def send_chat(session_id: str, body: ChatRequest) -> ChatResponse:
    """Start a chat turn. Tokens stream over WebSocket; this returns immediately.

    If `block=True`, waits for completion and returns final assistant content.
    """
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # For now, REST chat is a stub that returns a message_id.
    # The real streaming happens over WS in ws_sessions.py.
    # If we wanted blocking mode, we'd need to import the runner and await it.
    if body.block:
        raise HTTPException(status_code=501, detail="Blocking chat not implemented in Phase 1")

    import uuid
    message_id = uuid.uuid4().hex[:8]

    # Note: actual chat processing happens via WebSocket, not REST.
    # This endpoint is a placeholder for clients that can't use WS.
    return ChatResponse(message_id=message_id, status="started")


# --- Helpers ---


def _session_to_response(s: Session) -> SessionResponse:
    """Convert Session dataclass to Pydantic response."""
    return SessionResponse(
        id=s.id,
        name=s.name,
        workspace_path=s.workspace_path,
        idea=s.idea,
        messages=s.messages,
        requirements=s.requirements,
        architecture=s.architecture,
        files=s.files,
        test_results=s.test_results,
        review_feedback=s.review_feedback,
        documentation=s.documentation,
        errors=s.errors,
        fixes=s.fixes,
        created_at=s.created_at,
    )
