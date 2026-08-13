"""Pydantic schemas for the Codex-style session API.

A session holds a workspace path, chat history, and all generated artifacts. The
endpoint surface is intentionally small in Phase 1 — just session CRUD, workspace
setup, chat, and the workspace tree/file/write views used by the file panel.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class WorkspaceSpec(BaseModel):
    """How to resolve a workspace directory when creating a session."""
    mode: Literal["existing", "create"] = "create"
    path: Optional[str] = None        # required when mode=existing
    name: Optional[str] = None        # used when mode=create (slug → ~/ai-dev-team-projects/<slug>)


class SessionCreate(BaseModel):
    name: Optional[str] = None
    workspace: WorkspaceSpec = WorkspaceSpec()


class SessionSummary(BaseModel):
    id: str
    name: str
    workspace_path: Optional[str] = None
    has_files: bool = False
    created_at: float


class SessionResponse(BaseModel):
    id: str
    name: str
    workspace_path: Optional[str] = None
    idea: str = ""
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    requirements: List[str] = Field(default_factory=list)
    architecture: Dict[str, Any] = Field(default_factory=dict)
    files: Dict[str, str] = Field(default_factory=dict)
    test_results: Dict[str, Any] = Field(default_factory=dict)
    review_feedback: List[str] = Field(default_factory=list)
    documentation: Dict[str, str] = Field(default_factory=dict)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    fixes: List[str] = Field(default_factory=list)
    created_at: float


class ChatRequest(BaseModel):
    message: str
    block: bool = False  # REST fallback — if true, return final assistant text


class ChatResponse(BaseModel):
    message_id: str
    status: str = "started"


class WorkspaceSetRequest(BaseModel):
    """Manually (re)set the session's workspace path. Use only after a session exists."""
    path: str


class WorkspaceNode(BaseModel):
    path: str           # relative to workspace root, forward slashes
    type: Literal["file", "dir"]
    size: Optional[int] = None


class WorkspaceTreeResponse(BaseModel):
    workspace_path: str
    tree: List[WorkspaceNode]


class WorkspaceFileResponse(BaseModel):
    path: str
    content: str


class WriteRequest(BaseModel):
    overwrite: bool = False


class WriteResponse(BaseModel):
    written: List[str] = Field(default_factory=list)
    skipped: List[str] = Field(default_factory=list)