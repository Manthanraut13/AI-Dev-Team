"""Short-term project context memory, backed by `.ai-devteam/project_context.json`.

Every agent reads this at start (to inject project context into its prompt) and
updates it at the end (to persist its output). Rewritten from the v1 state-helper
`short_term.py` to a file-based model, since v2 agents are standalone functions
that have no shared in-memory graph state.
"""
import json
import logging
import datetime

from plugin.paths import ai_devteam_dir, context_file

logger = logging.getLogger(__name__)

DEFAULT_CONTEXT = {
    "project_name": "",
    "detected_stack": [],
    "requirements": [],
    "architecture": {},
    "files": {},
    "decisions": [],
    "last_updated": "",
}


def load_context() -> dict:
    """Load project context, merging over defaults. Never raises."""
    path = context_file()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {**DEFAULT_CONTEXT, **data}
        except Exception as e:
            logger.warning(f"Could not load project_context.json: {e}")
    return dict(DEFAULT_CONTEXT)


def save_context(context: dict) -> dict:
    """Write context to disk. Returns the saved dict."""
    path = context_file()
    ai_devteam_dir().mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, indent=2, ensure_ascii=False), encoding="utf-8")
    return context


def update_context(**updates) -> dict:
    """Merge updates into the stored context and persist. Returns new context."""
    context = load_context()
    for key, value in updates.items():
        if value is not None:
            context[key] = value
    context["last_updated"] = datetime.datetime.now().isoformat(timespec="seconds")
    return save_context(context)


def reset_context() -> dict:
    """Clear context back to defaults and persist."""
    return save_context(dict(DEFAULT_CONTEXT))
