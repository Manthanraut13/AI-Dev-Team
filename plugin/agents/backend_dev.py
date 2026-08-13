"""Backend Developer agent — scaffolds a FastAPI backend from project context.

Ported from v1. Key changes: (1) standalone `backend_dev_agent(spec)` instead of
a LangGraph node, (2) returns `BackendDevOutput` with `requires_confirmation=True`
rather than writing files directly, (3) reads architecture/requirements from
project_context.json rather than graph state.
"""
from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import BackendDevOutput
from plugin.memory.context import load_context
from plugin.memory.long_term import qdrant_search, qdrant_upsert
from plugin.utils.llm import get_llm, invoke_with_retry
from plugin.utils.files import parse_files
from plugin.tools.output import log_activity
import logging

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Generate a complete FastAPI backend for project "{project_name}".

Spec / requirements:
{spec}

API Endpoints:
{endpoints}

DB Schema:
{tables}

Prior similar code patterns (from long-term memory, may be empty):
{patterns}

Generate ALL of the following files. For each file, use this EXACT format:

### FILE: <relative/path>
<complete file content>

Generate these files:
1. app/models.py — SQLAlchemy 2.0 models (Mapped[], mapped_column) for all tables
2. app/schemas.py — Pydantic v2 request/response schemas
3. app/api/routes.py — FastAPI APIRouter with async handlers for all endpoints
4. app/main.py — FastAPI app with CORS, includes router, startup log
5. requirements.txt — all dependencies
6. Dockerfile — python:3.12-slim, pip install, uvicorn CMD

Write complete, runnable code. No placeholders."""


async def backend_dev_agent(spec: str) -> BackendDevOutput:
    """Generate backend scaffolding (FastAPI + SQLAlchemy) from a spec."""
    log_activity("backend_dev", "start", {"spec": spec[:120]})
    context = load_context()
    project_name = context.get("project_name", "project")
    architecture = context.get("architecture", {})
    requirements = context.get("requirements", [])

    if not architecture:
        logger.warning("No architecture in project context — proceeding with spec only")

    endpoints = [
        f"{e.get('method', 'GET')} {e.get('path', '/')}"
        for e in architecture.get("api_endpoints", [])[:6]
    ]
    tables = []
    for t in architecture.get("db_schema", []):
        cols = []
        for c in t.get("columns", [])[:6]:
            if isinstance(c, dict):
                cols.append(f"{c.get('name', '?')}:{c.get('type', '?')}")
            else:
                cols.append(str(c))
        tables.append(f"TABLE {t.get('table')}: {', '.join(cols)}")

    # Supplement spec with context requirements when no explicit spec given.
    if not spec.strip() and requirements:
        spec = "\n".join(f"- {r[:80]}" for r in requirements[:10])

    # Retrieve similar past code patterns from long-term memory (graceful if down).
    patterns = qdrant_search("patterns", query=spec[:500], limit=3)
    patterns_text = "\n\n".join(f"--- pattern {i + 1} (score {p.get('score', 0):.2f}) ---\n{p.get('content', '')[:800]}" for i, p in enumerate(patterns))

    prompt = PROMPT_TEMPLATE.format(
        project_name=project_name,
        spec=spec,
        endpoints="\n".join(endpoints) if endpoints else "(none defined)",
        tables="\n".join(tables) if tables else "(none defined)",
        patterns=patterns_text or "(no prior patterns found)",
    )

    llm = get_llm(temperature=0.3, max_tokens=4000)
    try:
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        files = parse_files(response.content)
    except Exception as e:
        log_activity("backend_dev", "error", {"error": str(e)})
        logger.error(f"Backend Dev agent failed: {e}")
        raise RuntimeError(f"Backend Dev agent failed: {e}") from e

    # Prefix all paths under backend/ so they stay out of the plugin tree
    # when written to disk after user confirmation.
    backend_files = {f"backend/{k}": v for k, v in files.items()}

    # Store code patterns in long-term memory (graceful if Qdrant is down).
    qdrant_upsert(
        "patterns",
        content=f"Backend for {project_name}: {', '.join(list(backend_files.keys())[:8])}",
        metadata={"project_name": project_name, "type": "backend_scaffold"},
    )

    log_activity("backend_dev", "end", {"files": len(backend_files)})
    return BackendDevOutput(
        files=backend_files,
        summary=f"Generated {len(backend_files)} backend files for {project_name}",
        requires_confirmation=True,
    )
