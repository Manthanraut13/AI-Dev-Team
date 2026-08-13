from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, List
from app.utils.llm import get_llm, invoke_with_retry
from app.utils.files import parse_files
import logging

logger = logging.getLogger(__name__)


def backend_dev_node(state) -> dict:
    project_name = state.get("project_name", "project")
    architecture = state.get("architecture", {})
    requirements = state.get("requirements", [])

    logger.info(f"Backend Dev starting for {project_name}")

    if not architecture:
        return {"current_task": "error", "messages": [AIMessage(content="No architecture")]}

    endpoints = [f"{e.get('method','GET')} {e.get('path','/')}" for e in architecture.get("api_endpoints", [])[:6]]
    tables = []
    for t in architecture.get("db_schema", []):
        cols = []
        for c in t.get("columns", [])[:6]:
            if isinstance(c, dict):
                cols.append(f"{c.get('name','?')}:{c.get('type','?')}")
            else:
                cols.append(str(c))
        tables.append(f"TABLE {t.get('table')}: {', '.join(cols)}")

    req_text = "\n".join(f"- {r[:60]}" for r in requirements[:5])
    ep_text = "\n".join(endpoints)
    tbl_text = "\n".join(tables)

    prompt = f"""Generate a complete FastAPI backend for project "{project_name}".

Requirements:
{req_text}

API Endpoints:
{ep_text}

DB Schema:
{tbl_text}

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

    llm = get_llm(temperature=0.3, max_tokens=4000)
    response = invoke_with_retry(llm, [HumanMessage(content=prompt)])

    files = parse_files(response.content)

    backend_files = {f"backend/{k}": v for k, v in files.items()}

    logger.info(f"Generated {len(backend_files)} backend files: {list(backend_files.keys())}")

    return {
        "files": backend_files,
        "current_task": "human_checkpoint_final",
        "messages": [AIMessage(content=f"Backend: {len(backend_files)} files generated")]
    }
