"""Session runner — bridges the synchronous supervisor graph to async WebSocket streaming.

Responsibilities:
  - Run the supervisor graph in a worker thread (via asyncio.to_thread)
  - Pump events from the thread to the event loop via an asyncio.Queue
  - Dispatch token chunks as `chat.token` WS messages (only for main_agent)
  - Dispatch agent status events as `agent_update`
  - Finalize with `chat.done` and persist messages to the session store

This design keeps the event loop responsive while the blocking LLM calls
(invoke_with_retry with time.sleep) run in a thread.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from langchain_core.messages import AIMessage, HumanMessage

from app.services.session_store import session_store

if TYPE_CHECKING:
    from app.services.session_store import Session


logger = logging.getLogger(__name__)


class SessionRunner:
    """Per-session runner that executes supervisor turns and streams events."""

    def __init__(self, session: "Session", broadcast: Callable[[str, Dict[str, Any]], None]):
        self.session = session
        self.broadcast = broadcast
        self._current_task: Optional[asyncio.Task] = None

    async def run_chat(self, user_message: str) -> str:
        """Run one supervisor turn. Streams tokens and events via the broadcaster.

        Returns the final assistant message content.
        """
        from app.supervisor.graph import run_supervisor_turn

        # Generate a message ID for this turn.
        message_id = uuid.uuid4().hex[:8]

        # Acknowledge the message.
        self.broadcast("chat.ack", {"message_id": message_id, "session_id": self.session.id})

        # Token buffer for batching.
        token_buffer: list[str] = []
        last_flush = time.time()

        def flush_tokens():
            nonlocal last_flush
            if not token_buffer:
                return
            combined = "".join(token_buffer)
            token_buffer.clear()
            self.broadcast("chat.token", {
                "session_id": self.session.id,
                "message_id": message_id,
                "delta": combined,
            })
            last_flush = time.time()

        def on_token(delta: str):
            token_buffer.append(delta)
            # Batch flush every 50ms or 20 tokens to avoid WS spam.
            if len(token_buffer) >= 20 or (time.time() - last_flush) > 0.05:
                flush_tokens()

        def on_agent_update(data: Dict[str, Any]):
            self.broadcast("agent_update", {**data, "session_id": self.session.id})

        try:
            # Run the supervisor turn.
            final_messages = await run_supervisor_turn(
                self.session,
                user_message,
                self.broadcast,
                on_token=on_token,
                on_agent_update=on_agent_update,
            )

            # Flush any remaining tokens.
            flush_tokens()

            # Extract final assistant content.
            final_content = ""
            for msg in reversed(final_messages):
                if isinstance(msg, AIMessage):
                    final_content = msg.content or ""
                    break

            # Broadcast completion.
            self.broadcast("chat.done", {
                "session_id": self.session.id,
                "message_id": message_id,
                "content": final_content,
            })

            # Persist session.
            session_store.save(self.session)

            return final_content

        except Exception as e:
            logger.error(f"SessionRunner error: {e}")
            self.broadcast("error", {"message": str(e), "session_id": self.session.id})
            return f"Error: {e}"

    def cancel(self):
        """Cancel the current run if active."""
        if self._current_task and not self._current_task.done():
            self._current_task.cancel()


# Global registry of active runners by session ID.
_active_runners: Dict[str, SessionRunner] = {}


def get_runner(session: "Session", broadcast: Callable[[str, Dict[str, Any]], None]) -> SessionRunner:
    """Get or create a runner for the session."""
    if session.id not in _active_runners:
        _active_runners[session.id] = SessionRunner(session, broadcast)
    return _active_runners[session.id]


def remove_runner(session_id: str):
    """Clean up a runner when the session closes."""
    runner = _active_runners.pop(session_id, None)
    if runner:
        runner.cancel()
