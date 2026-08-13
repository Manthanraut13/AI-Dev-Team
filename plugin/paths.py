"""Filesystem conventions for the plugin.

The plugin treats the directory it is launched in (the user's coding project)
as the project root. All agent output lands under `.ai-devteam/` — never in
the user's source (except scaffold agents, which ask for confirmation).
"""
from pathlib import Path


def project_root() -> Path:
    """The user's coding project = CWD when the platform spawns the server."""
    return Path.cwd()


def ai_devteam_dir() -> Path:
    return project_root() / ".ai-devteam"


def ensure_dirs() -> dict:
    """Create the `.ai-devteam/` tree. Returns a {name: Path} map."""
    root = ai_devteam_dir()
    subdirs = {
        "root": root,
        "logs": root / "logs",
        "reviews": root / "reviews",
        "tests": root / "tests",
        "research": root / "research",
        "docs": root / "docs",
    }
    for d in subdirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return subdirs


def context_file() -> Path:
    return ai_devteam_dir() / "project_context.json"


def config_file() -> Path:
    return ai_devteam_dir() / "config.toml"


def log_file() -> Path:
    return ai_devteam_dir() / "logs" / "agent_activity.log"
