"""Trigger → agent routing map (mirrors Workflow §4).

The watcher and git hooks look up which agents to run for a given event type.
Each route lists agent function references in dependency order.
"""
from plugin.agents.product_manager import product_manager_agent
from plugin.agents.architect import architect_agent
from plugin.agents.research import research_agent
from plugin.agents.backend_dev import backend_dev_agent
from plugin.agents.frontend_dev import frontend_dev_agent
from plugin.agents.qa_engineer import qa_engineer_agent
from plugin.agents.code_reviewer import code_reviewer_agent
from plugin.agents.documentation import documentation_agent

# event name -> (agent_fn, args-builder)
# args-builder receives the event payload dict and returns positional args.
TRIGGER_ROUTES = {
    "file_saved": {
        "qa_engineer": (qa_engineer_agent, lambda e: (e["file_path"],)),
        "code_reviewer": (code_reviewer_agent, lambda e: (e["file_path"],)),
    },
    "git_commit": {
        "documentation": (documentation_agent, lambda e: (e["changed_files"],)),
    },
    "unknown_import": {
        "research": (research_agent, lambda e: (e["topic"],)),
    },
    "new_project": {
        "product_manager": (product_manager_agent, lambda e: (e["idea"],)),
    },
}

# Full /devteam order (pipeline.py mirrors this — keep in sync).
DEVTEAM_ORDER = [
    product_manager_agent,
    architect_agent,
    backend_dev_agent,
    frontend_dev_agent,
    qa_engineer_agent,
    code_reviewer_agent,
    documentation_agent,
]


def agents_for_event(event_type: str, payload: dict) -> list[dict]:
    """Return [{name, fn, args}] for the given event, or [] if unhandled."""
    route = TRIGGER_ROUTES.get(event_type)
    if not route:
        return []
    calls = []
    for name, (fn, args_builder) in route.items():
        try:
            calls.append({"name": name, "fn": fn, "args": args_builder(payload)})
        except KeyError:
            continue
    return calls
