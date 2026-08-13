"""Shared file utilities: parse the `### FILE: <path>` LLM output format used by all
code-generation agents, and safe path joining for the workspace service.

Extracted from the duplicated `_parse_files` blocks in backend_dev / frontend_dev /
qa_engineer / documentation. The qa_engineer-specific trim_prose behavior is available
via the optional parameter.
"""
from __future__ import annotations

import os
import re
from typing import Dict


# Match a `### FILE: <path>` line followed by content until the next `### FILE:` or EOF.
_FILE_PATTERN = re.compile(r"###\s*FILE:\s*(.+?)\s*\n(.*?)(?=###\s*FILE:|\Z)", re.DOTALL)


def parse_files(text: str, *, trim_prose: bool = False) -> Dict[str, str]:
    """Extract a `{path: content}` map from an LLM response that uses the `### FILE: <path>` format.

    Strips thinking blocks, trims quotes around the path, and skips blank entries.

    Args:
        text: The LLM response text to parse.
        trim_prose: If True, applies additional cleanup (strip ``` fences, trim prose tail).
                   This is used by qa_engineer for cleaner test file output.
    """
    # Strip thinking blocks (various LLM formats)
    text = re.sub(r"<hthink>.*?</hthink>", "", text, flags=re.DOTALL).strip()

    if trim_prose:
        # Strip ``` fences from content
        def clean_content(content: str) -> str:
            lines = [l for l in content.splitlines() if not l.strip().startswith("```")]
            content = "\n".join(lines).strip()
            return _trim_prose_tail(content)
    else:
        clean_content = lambda c: c.strip()

    matches = _FILE_PATTERN.findall(text)
    out: Dict[str, str] = {}
    for raw_path, content in matches:
        path = raw_path.strip().strip('"').strip("'")
        content = clean_content(content)
        if path and content:
            out[path] = content
    return out


def _trim_prose_tail(content: str) -> str:
    """Trim trailing prose after the last code anchor line.

    Used by qa_engineer to avoid prose artifacts at the end of generated test files.
    """
    lines = content.splitlines()
    last_anchor = -1
    for i, l in enumerate(lines):
        if re.match(r"^\s*(def |class |import |from |async def |@)", l):
            last_anchor = i
    if last_anchor < 0:
        return content
    kept = lines[:last_anchor + 1]
    for l in lines[last_anchor + 1:]:
        if l.startswith((" ", "\t")) or not l.strip() or l.strip().startswith("#"):
            kept.append(l)
    return "\n".join(kept).strip()


def safe_join(root: str, rel_path: str) -> str:
    """Resolve `rel_path` against `root` and confirm it stays inside `root`.

    Rejects:
      - Absolute paths
      - `..` traversal (after normalization)
      - Windows drive-letter prefixes (e.g. `C:`)
      - Symlink escapes (resolved via realpath)

    Raises `PermissionError` on any escape attempt.
    """
    rel = str(rel_path or "").replace("\\", "/").lstrip("/")
    # Strip Windows drive letters like "C:" so they can't be re-anchored.
    rel = re.sub(r"^[A-Za-z]:", "", rel)
    if rel.startswith("/"):
        rel = rel.lstrip("/")
    root_r = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root_r, rel))
    if target != root_r and not target.startswith(root_r + os.sep):
        raise PermissionError(f"Path escapes workspace: {rel_path!r}")
    return target


def slugify(name: str) -> str:
    """Filesystem-safe slug: lowercase, alnum + dash, collapses repeats, trims dashes."""
    s = re.sub(r"[^a-zA-Z0-9\-_]+", "-", (name or "").strip().lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "project"
