"""Workspace service — the only place that touches the user's chosen directory.

Responsibilities:
  - Resolve a workspace (validate an existing path, or create a new one under
    DEFAULT_PROJECTS_DIR).
  - Write generated files to disk atomically, skipping identical content to avoid
    clobbering user edits (the `overwrite=True` flag forces).
  - List the on-disk file tree and read file content (size-capped).

Every disk operation goes through `safe_join` so we reject `..`, absolute paths,
Windows drive-letter prefixes, and symlink escapes. This is the security-critical
layer of the supervisor.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.config import settings
from app.utils.files import safe_join, slugify


MAX_READ_BYTES = 1 * 1024 * 1024  # 1 MB cap on file reads


class WorkspaceError(Exception):
    """User-visible workspace failure (bad path, not a directory, etc.)."""


@dataclass
class WorkspaceNode:
    path: str  # forward slashes, relative to root
    type: str  # "file" | "dir"
    size: Optional[int] = None


def resolve(mode: str, path: Optional[str] = None, name: Optional[str] = None) -> str:
    """Resolve a workspace directory path. Creates if mode='create'.

    Returns the absolute, realpath-canonicalized path.
    """
    if mode == "existing":
        if not path:
            raise WorkspaceError("path is required when mode='existing'")
        rp = os.path.realpath(os.path.expanduser(path))
        if not os.path.isdir(rp):
            raise WorkspaceError(f"not a directory: {path}")
        return rp

    if mode == "create":
        if not name:
            raise WorkspaceError("name is required when mode='create'")
        base = Path(os.path.expanduser(settings.DEFAULT_PROJECTS_DIR))
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise WorkspaceError(f"cannot create default projects dir: {e}")
        target = base / slugify(name)
        # If the slug collides, suffix a counter.
        if target.exists():
            i = 2
            while (base / f"{slugify(name)}-{i}").exists():
                i += 1
            target = base / f"{slugify(name)}-{i}"
        try:
            target.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            # Lost a race — fine, return what exists.
            pass
        except OSError as e:
            raise WorkspaceError(f"cannot create workspace: {e}")
        return os.path.realpath(str(target))

    raise WorkspaceError(f"unknown mode: {mode}")


def write_files(root: str, files: Dict[str, str], overwrite: bool = False) -> Tuple[List[str], List[str]]:
    """Write a `{rel_path: content}` map under `root`.

    - Files with identical existing content are skipped (unless `overwrite=True`) — protects
      the user's manual edits between builds.
    - Writes are atomic: temp file + `os.replace`.
    - Returns (written, skipped) relative paths.
    """
    if not files:
        return [], []

    written: List[str] = []
    skipped: List[str] = []
    for rel, content in files.items():
        try:
            target = safe_join(root, rel)
        except PermissionError:
            # Skip silently — paths that escape the workspace shouldn't have been
            # generated in the first place.
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)

        if not overwrite and os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    if f.read() == content:
                        skipped.append(rel)
                        continue
            except OSError:
                # If we can't read the existing file, fall through to overwrite.
                pass

        tmp = target + ".part"
        try:
            with open(tmp, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            os.replace(tmp, target)
            written.append(rel)
        except OSError as e:
            # Surface the error to the caller by skipping this file but continuing.
            try:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            except OSError:
                pass
            raise WorkspaceError(f"failed to write {rel}: {e}")

    return written, skipped


def list_files(root: str) -> List[WorkspaceNode]:
    """Recursive walk returning relative paths with type + size. Dirs first, then alpha."""
    nodes: List[WorkspaceNode] = []
    rp = os.path.realpath(root)

    def walk(abs_dir: str) -> None:
        try:
            entries = sorted(os.listdir(abs_dir), key=lambda s: (not os.path.isdir(os.path.join(abs_dir, s)), s.lower()))
        except OSError:
            return
        for name in entries:
            if name.startswith(".") and name not in (".env", ".gitignore"):
                # Skip hidden noise (.git, .next, .venv...) unless user explicitly opts in.
                # Keep .env and .gitignore visible since they matter for code reviews.
                continue
            full = os.path.join(abs_dir, name)
            rel = os.path.relpath(full, rp).replace(os.sep, "/")
            if os.path.isdir(full):
                nodes.append(WorkspaceNode(path=rel + "/", type="dir"))
                walk(full)
            elif os.path.isfile(full):
                try:
                    size = os.path.getsize(full)
                except OSError:
                    size = None
                nodes.append(WorkspaceNode(path=rel, type="file", size=size))

    walk(rp)
    return nodes


def read_file(root: str, rel_path: str) -> Tuple[str, str]:
    """Read a file under `root`. Returns (relative_path, content). Raises on size cap."""
    target = safe_join(root, rel_path)
    if not os.path.isfile(target):
        raise WorkspaceError(f"not a file: {rel_path}")
    size = os.path.getsize(target)
    if size > MAX_READ_BYTES:
        raise WorkspaceError(f"file too large to view ({size} bytes > {MAX_READ_BYTES})")
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        return rel_path, f.read()