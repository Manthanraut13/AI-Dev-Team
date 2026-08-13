"""Roo Code (VS Code) integration.

Writes:
- `<project_root>/.roorules` — rules file (mirrors `.clinerules`).
- VS Code `settings.json` — registers the MCP server under
  `roo.cline.mcpServers` (Roo uses the same settings surface as Cline, just
  with a different key prefix).
- Adds a Roo custom-mode block (`roo.customModes`) named `devteam` that
  pre-loads all plugin tools.

Verify: Roo Code panel → Settings → MCP → `ai-dev-team` listed.
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


ROORULES_HEADER = RULES_FRONT_MATTER + """
## Roo Code specifics

This project enables the `devteam` custom mode (registered in `settings.json`).
Switch into `devteam` mode to have all plugin tools pre-loaded and available
without manual invocation.
"""


def roo_settings_path() -> Path:
    return platform_config_dir() / "Code" / "User" / "settings.json"


DEVTEAM_MODE = {
    "slug": "devteam",
    "name": "DevTeam",
    "roleDefinition": (
        "You are the AI Dev Team orchestrator. Use the ai-dev-team MCP tools to "
        "turn a rough idea into a working scaffold: PM → Architect → Backend + "
        "Frontend → QA → Review → Docs. Always start with run_product_manager."
    ),
    "groups": ["read", "edit", "command", "mcp"],
    "customInstructions": (
        "Always load .ai-devteam/project_context.json before planning. Scaffold "
        "files require explicit user confirmation before they are written."
    ),
}


def install(project_root: Path, server_command: list[str]) -> dict:
    rules_path = project_root / ".roorules"
    write_text(rules_path, ROORULES_HEADER)

    cfg_path = roo_settings_path()
    # Merge both the MCP server entry and the devteam custom-mode block.
    new_payload = {
        "roo.cline.mcpServers": mcp_server_entry(server_command),
        "roo.customModes": [DEVTEAM_MODE],
    }
    merge_json_config(cfg_path, new_payload)

    return {
        "written": [str(rules_path), str(cfg_path)],
        "registered": True,
        "message": (
            f"Roo Code: .roorules + {SERVER_NAME} MCP server + devteam mode "
            f"registered at {cfg_path}"
        ),
    }


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    cmd = ["python", "-m", "plugin.server"]
    print(json.dumps(install(root, cmd), indent=2))
