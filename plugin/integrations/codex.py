"""Codex CLI integration.

Writes to `~/.codex/config.json` under the `mcpServers` array (Codex uses an
array of server objects, each with `name` / `command` / optional `args`).

Verify: `codex mcp list` should show `ai-dev-team`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from plugin.integrations._common import (
    SERVER_NAME,
    merge_json_config,
)


def codex_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("USERPROFILE", Path.home()))
    else:
        base = Path.home()
    return base / ".codex" / "config.json"


def _codex_server_entry(server_command: list[str]) -> dict:
    """Codex's MCP server entry shape is `{name, command, args?}` — command is
    a single string, args is an array."""
    cmd_str = server_command[0] if server_command else "python"
    args = server_command[1:] if len(server_command) > 1 else ["-m", "plugin.server"]
    return {
        "name": SERVER_NAME,
        "command": cmd_str,
        "args": args,
    }


def install(project_root: Path, server_command: list[str]) -> dict:
    """Register the MCP server in Codex's config.json. No rules file."""
    cfg_path = codex_config_path()
    new_entry = _codex_server_entry(server_command)

    # Codex uses an array of server objects — replace if same `name` exists,
    # otherwise append.
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if cfg_path.exists():
        try:
            existing = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}
    else:
        existing = {}

    servers = list(existing.get("mcpServers", []))
    servers = [s for s in servers if s.get("name") != SERVER_NAME]
    servers.append(new_entry)

    merge_json_config(cfg_path, {"mcpServers": servers})

    return {
        "written": [str(cfg_path)],
        "registered": True,
        "message": f"Codex: {SERVER_NAME} MCP server registered at {cfg_path}",
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    cmd = ["python", "-m", "plugin.server"]
    print(json.dumps(install(root, cmd), indent=2))
