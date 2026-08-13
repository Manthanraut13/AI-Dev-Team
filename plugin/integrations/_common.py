"""Shared helpers for platform integration generators.

Each platform generator module exposes a single `install(project_root, server_command)`
function. They all need to:
- Resolve platform-specific config paths (Windows-aware).
- JSON-load existing config (or start from `{}` / `[]`), merge in the plugin's
  MCP server entry, and JSON-write back atomically.
- Write a rules/markdown file at the project root.
- Return a status dict so `install.py` can summarise the work.

This module keeps those helpers DRY.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any


SERVER_NAME = "ai-dev-team"


def platform_config_dir() -> Path:
    """Platform-specific user config directory (Claude/Cline/Roo/OpenCode/Codex).

    Windows: %APPDATA%\\<vendor>
    macOS:   ~/Library/Application Support/<vendor>
    Linux:   $XDG_CONFIG_HOME/<vendor> or ~/.config/<vendor>
    """
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base


def merge_json_config(path: Path, new_payload: Any) -> dict:
    """Load JSON from `path` (or {} / []), deep-merge `new_payload`, write back.

    For dicts: keys in `new_payload` overwrite / extend existing keys. Recursive
    merge is shallow — only the top-level is deep-merged for now (sufficient for
    MCP server blocks). For lists: replaced wholesale if `new_payload` is a list,
    because each platform's MCP server list is a registry, not user data.

    Returns the dict {written: bool, before: <parsed-or-empty>, after: <written>}.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        try:
            before = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            before = {} if isinstance(new_payload, dict) else []
    else:
        before = {} if isinstance(new_payload, dict) else []

    after = _merge(before, new_payload)

    # Atomic write: temp file in same dir, then replace.
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(after, f, indent=2)
            f.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        if Path(tmp_name).exists():
            Path(tmp_name).unlink()
        raise
    return {"written": True, "before": before, "after": after}


def _merge(before: Any, new: Any) -> Any:
    """Merge `new` into `before`. Dicts merge recursively; lists replaced wholesale."""
    if isinstance(before, dict) and isinstance(new, dict):
        merged = dict(before)
        for k, v in new.items():
            if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
                merged[k] = _merge(merged[k], v)
            else:
                merged[k] = v
        return merged
    return new


def write_text(path: Path, content: str) -> None:
    """Write a text file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# Shared rule-file front-matter reused by Claude Code, Cline, Roo Code.
# Each platform's rules file just adds its own header + slash-command map.
RULES_FRONT_MATTER = """# AI Dev Team — Agent Tool Guide

You have access to the `ai-dev-team` MCP server. The 11 tools below turn a
rough idea into a working scaffold (PM → Architect → Backend+Frontend → QA →
Review → Docs). Auto-call them based on the user's request and the slash
commands listed under each role.

## Slash commands

| Slash | Tool to call |
|-------|--------------|
| `/pm <idea>`         | `run_product_manager(idea)` |
| `/architect`         | `run_architect()` (uses context) |
| `/research <topic>`  | `run_research(topic)` |
| `/backend <spec>`    | `run_backend_dev(spec)` |
| `/frontend <spec>`   | `run_frontend_dev(spec)` |
| `/devteam <idea>`    | `run_devteam(idea)` — full pipeline |
| `/docs <files>`      | `run_documentation(changed_files)` |

## Trigger rules

- On any new project idea: call `run_product_manager`.
- After PM, call `run_architect` before any code is written.
- Scaffold files require user confirmation (`requires_confirmation: true`).
  Surface the proposed files to the user; write only after explicit OK.
- All outputs land in `.ai-devteam/` — read but do not modify user source.
"""


def mcp_server_entry(server_command: list[str]) -> dict:
    """The standard MCP server block inserted into every platform's config."""
    return {
        SERVER_NAME: {
            "command": server_command[0] if server_command else "python",
            "args": server_command[1:] if len(server_command) > 1 else ["-m", "plugin.server"],
            "type": "local",
        }
    }
