"""Platform integration generators.

Each generator exposes `install(project_root: Path, server_command: list[str]) -> dict`.
The registry below maps the platform name used by `install.py --platform <name>`
to the matching generator module.
"""
from __future__ import annotations

from pathlib import Path

from plugin.integrations import claude_code, cline, codex, opencode, roocode

__all__ = ["GENERATORS", "run_install", "list_platforms"]


GENERATORS = {
    "claude-code": claude_code,
    "cline": cline,
    "roocode": roocode,
    "opencode": opencode,
    "codex": codex,
}


def list_platforms() -> list[str]:
    return sorted(GENERATORS.keys())


def run_install(platform: str, project_root: Path, server_command: list[str]) -> dict:
    """Dispatch to the right generator. Raises KeyError on unknown platform."""
    module = GENERATORS[platform]
    return module.install(project_root, server_command)
