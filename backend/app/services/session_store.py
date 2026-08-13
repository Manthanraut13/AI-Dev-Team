"""In-memory session store with best-effort JSON snapshot persistence.

A Session is the unit of work: workspace path, chat history, and all generated
artifacts (requirements, architecture, files, test_results, review_feedback,
documentation). State is held in process memory so reads are cheap; a JSON
snapshot is written to ~/.ai-dev-team/sessions/<id>.json on every update so a
crash doesn't lose the workspace path and chat history. Generated artifacts
(requirements, files, etc.) are recomputed by the agents, so they're intentionally
excluded from the snapshot to keep snapshots small and avoid race-condition conflicts
on concurrent updates.
"""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import settings


@dataclass
class Session:
    id: str
    name: str
    workspace_path: Optional[str] = None
    idea: str = ""
    # Chat history — list of {"type": ..., "content": ...} dicts mirroring BaseMessage shape.
    messages: List[Dict[str, Any]] = field(default_factory=list)
    # Generated artifacts (populated by agent tools).
    requirements: List[str] = field(default_factory=list)
    architecture: Dict[str, Any] = field(default_factory=dict)
    files: Dict[str, str] = field(default_factory=dict)
    test_results: Dict[str, Any] = field(default_factory=dict)
    review_feedback: List[str] = field(default_factory=list)
    documentation: Dict[str, str] = field(default_factory=dict)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    fixes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    # --- serialization helpers -------------------------------------------------
    def to_snapshot(self) -> Dict[str, Any]:
        """Compact JSON-serializable shape for crash recovery (excludes generated artifacts)."""
        return {
            "id": self.id,
            "name": self.name,
            "workspace_path": self.workspace_path,
            "idea": self.idea,
            "messages": self.messages,
            "created_at": self.created_at,
        }

    def to_response(self) -> Dict[str, Any]:
        """Full shape returned by the REST API."""
        return {
            "id": self.id,
            "name": self.name,
            "workspace_path": self.workspace_path,
            "idea": self.idea,
            "messages": list(self.messages),
            "requirements": list(self.requirements),
            "architecture": dict(self.architecture),
            "files": dict(self.files),
            "test_results": dict(self.test_results),
            "review_feedback": list(self.review_feedback),
            "documentation": dict(self.documentation),
            "errors": list(self.errors),
            "fixes": list(self.fixes),
            "created_at": self.created_at,
        }

    def to_summary(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "workspace_path": self.workspace_path,
            "has_files": bool(self.files),
            "created_at": self.created_at,
        }


class SessionStore:
    """Thread-safe in-memory session registry with optional JSON snapshot persistence."""

    def __init__(self, data_dir: Optional[str] = None) -> None:
        self._sessions: Dict[str, Session] = {}
        self._lock = threading.RLock()
        self._data_dir = Path(os.path.expanduser(data_dir or settings.SESSION_DATA_DIR))
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            # Persistence is best-effort; keep going even if the dir can't be made.
            self._data_dir = None  # type: ignore[assignment]

    # --- lifecycle -------------------------------------------------------------
    def create(self, name: Optional[str] = None) -> Session:
        sid = uuid.uuid4().hex
        s = Session(id=sid, name=(name or "Untitled").strip() or "Untitled")
        with self._lock:
            self._sessions[sid] = s
            self._maybe_persist(s)
        return s

    def get(self, sid: str) -> Optional[Session]:
        with self._lock:
            return self._sessions.get(sid)

    def list(self) -> List[Session]:
        with self._lock:
            return list(self._sessions.values())

    def delete(self, sid: str) -> bool:
        with self._lock:
            s = self._sessions.pop(sid, None)
        if s and self._data_dir:
            p = self._snapshot_path(s)
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
        return s is not None

    # --- mutations -------------------------------------------------------------
    def save(self, session: Session) -> None:
        """Persist a snapshot. Call after any mutation that should survive a crash."""
        with self._lock:
            self._maybe_persist(session)

    # --- internals -------------------------------------------------------------
    def _snapshot_path(self, session: Session) -> Path:
        assert self._data_dir is not None
        return self._data_dir / f"{session.id}.json"

    def _maybe_persist(self, session: Session) -> None:
        if not self._data_dir:
            return
        try:
            tmp = self._snapshot_path(session).with_suffix(".json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(session.to_snapshot(), f, indent=2, default=str)
            os.replace(tmp, self._snapshot_path(session))
        except OSError:
            # Persistence failures must never break the request path.
            pass


# Module-level singleton — process-wide registry.
session_store = SessionStore()