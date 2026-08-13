"""OpenCode integration.

Writes to `~/.config/opencode/config.json` under the `mcp` key. OpenCode uses
a single config file; no per-project rules file is required — the MCP tools
appear in the tool palette directly.

Verify: `opencode mcp list` should show `ai-dev-team`.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from plugin.integrations._common import (
    SERVER_NAME,
    merge_json_config,
    mcp_server_entry,
)


def opencode_config_path() -> Path:
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "opencode" / "config.json"


def install(project_root: Path, server_command: list[str]) -> dict:
    """Register the MCP server in OpenCode's config. No rules file (not needed)."""
    cfg_path = opencode_config_path()
    new_payload = {"mcp": mcp_server_entry(server_command)}
    merge_json_config(cfg_path, new_payload)

    return {
        "written": [str(cfg_path)],
        "registered": True,
        "message": f"OpenCode: {SERVER_NAME} MCP server registered at {cfg_path}",
    }


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    cmd = ["python", "-m", "plugin.server"]
    print(json.dumps(install(root, cmd), indent=2))
