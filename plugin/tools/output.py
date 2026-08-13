"""Agent output writer + activity logger.

Agents write results to `.ai-devteam/` — never to the user's source (scaffold
agents are the exception and require confirmation). This module is the single
place that decides where each agent's output goes.
"""
import json
import logging
import datetime
from pathlib import Path

from plugin.paths import ai_devteam_dir, log_file

logger = logging.getLogger(__name__)

# agent_name -> subdirectory under .ai-devteam/. Empty string = .ai-devteam root.
AGENT_DIRS = {
    "product_manager": "",   # requirements.md
    "architect": "",         # architecture.md
    "research": "research",
    "code_reviewer": "reviews",
    "qa_engineer": "tests",
    "documentation": "docs",
}


def write_agent_output(agent_name: str, filename: str, content: str) -> Path:
    """Write an agent's output to `.ai-devteam/<dir>/<filename>` and return the path.

    `dir` is derived from the agent name (see AGENT_DIRS); unknown agents get a
    subdirectory named after them. Parent directories are created as needed.
    """
    subdir = AGENT_DIRS.get(agent_name, agent_name)
    base = ai_devteam_dir()
    if subdir:
        base = base / subdir
    base.mkdir(parents=True, exist_ok=True)

    path = base / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    logger.info(f"Wrote agent output: {path}")
    return path


def log_activity(agent_name: str, event: str = "run", details: dict | None = None) -> None:
    """Append one JSON line to `.ai-devteam/logs/agent_activity.log`."""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "agent": agent_name,
        "event": event,
        **(details or {}),
    }
    path = log_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
