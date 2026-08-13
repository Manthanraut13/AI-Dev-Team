"""Cline (VS Code) integration.

Writes:
- `<project_root>/.clinerules` — rules file instructing Cline when to call
  each MCP tool.
- VS Code `settings.json` (workspace or user) — registers the MCP server under
  `cline.mcpServers.ai-dev-team`.

Verify: VS Code → Cline panel → MCP Servers → `ai-dev-team` should appear connected.
"""
from __future__ import annotations

import json
from pathlib import Path

from plugin.integrations._common import (
    RULES_FRONT_MATTER,
    SERVER_NAME,
    merge_json_config,
    mcp_server_entry,
    platform_config_dir,
    write_text,
)


CLINERULES_HEADER = RULES_FRONT_MATTER + """
## Cline specifics

Workspace `.clinerules` files are loaded automatically by the Cline extension.
MCP tools are surfaced in the Cline UI as `mcp__ai-dev-team__*` actions.
"""


def cline_settings_path() -> Path:
    """VS Code user settings on Windows.

    Cline reads both workspace `.vscode/settings.json` (preferred for per-project
    isolation) and the global user `settings.json`. We target the user-level one
    so the plugin works across projects without per-project setup; `--verify`
    will surface a hint if a workspace-local settings.json would be more
    appropriate.
    """
    return platform_config_dir() / "Code" / "User" / "settings.json"


def install(project_root: Path, server_command: list[str]) -> dict:
    rules_path = project_root / ".clinerules"
    write_text(rules_path, CLINERULES_HEADER)

    cfg_path = cline_settings_path()
    new_payload = {"cline.mcpServers": mcp_server_entry(server_command)}
    merge_json_config(cfg_path, new_payload)

    return {
        "written": [str(rules_path), str(cfg_path)],
        "registered": True,
        "message": f"Cline: .clinerules + {SERVER_NAME} MCP server registered at {cfg_path}",
    }


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    cmd = ["python", "-m", "plugin.server"]
    print(json.dumps(install(root, cmd), indent=2))
