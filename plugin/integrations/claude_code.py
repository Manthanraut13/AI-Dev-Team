"""Claude Code integration.

Writes:
- `<project_root>/CLAUDE.md` — rules file instructing Claude Code when to call
  each MCP tool (auto-loaded by Claude Code at session start).
- Registers the `ai-dev-team` MCP server. Preferred method is `claude mcp add
  --scope user` (writes to `~/.claude.json` on every OS, correct on Windows).
  Falls back to editing the user config JSON directly if the CLI is missing.

Verify: `claude mcp list` should show `ai-dev-team`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from plugin.integrations._common import (
    RULES_FRONT_MATTER,
    SERVER_NAME,
    merge_json_config,
    mcp_server_entry,
    write_text,
)


CLAUDE_MD_HEADER = RULES_FRONT_MATTER + """
## Claude Code specifics

Use the Bash + Read tools for filesystem work. All MCP tools appear in the
tool palette under the `mcp__ai-dev-team__` namespace.
"""


def claude_config_path() -> Path:
    """Claude Code user config: `~/.claude.json` on every OS (not %APPDATA%)."""
    return Path.home() / ".claude.json"


def _register_via_cli(server_command: list[str]) -> bool:
    """Try `claude mcp add --scope user`. Returns True on success."""
    if shutil.which("claude") is None:
        return False
    cmd = [
        "claude", "mcp", "add", "--scope", "user",
        SERVER_NAME, *server_command,
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
        )
        return result.returncode == 0
    except Exception:
        return False


def install(project_root: Path, server_command: list[str]) -> dict:
    """Write CLAUDE.md and register the MCP server. Idempotent."""
    # 1. Rules file at project root.
    rules_path = project_root / "CLAUDE.md"
    write_text(rules_path, CLAUDE_MD_HEADER)

    # 2. Register the MCP server — CLI first, JSON fallback.
    if _register_via_cli(server_command):
        cfg_path = claude_config_path()
        return {
            "written": [str(rules_path)],
            "registered": True,
            "message": (
                f"Claude Code: CLAUDE.md + {SERVER_NAME} MCP server registered "
                f"via `claude mcp add --scope user`"
            ),
        }

    # Fallback: merge into ~/.claude.json directly.
    cfg_path = claude_config_path()
    new_payload = {"mcpServers": mcp_server_entry(server_command)}
    merge_json_config(cfg_path, new_payload)

    return {
        "written": [str(rules_path), str(cfg_path)],
        "registered": True,
        "message": f"Claude Code: CLAUDE.md + {SERVER_NAME} MCP server registered at {cfg_path}",
    }


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    cmd = ["python", "-m", "plugin.server"]
    print(json.dumps(install(root, cmd), indent=2))
