from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, List
from app.config import settings
from app.utils.llm import get_llm, invoke_with_retry
from app.utils.files import parse_files
import logging

logger = logging.getLogger(__name__)


def documentation_node(state) -> dict:
    project_name = state.get("project_name", "project")
    requirements = state.get("requirements", [])
    architecture = state.get("architecture", {})
    files = state.get("files", {})
    review_feedback = state.get("review_feedback", [])

    logger.info(f"Documentation Agent starting for {project_name}")

    req_text = "\n".join(f"- {r}" for r in requirements[:8])
    endpoints = architecture.get("api_endpoints", [])
    ep_text = "\n".join(
        f"{e.get('method','GET')} {e.get('path','/')} — {e.get('description','')}"
        for e in endpoints[:8]
    )
    feedback_text = "\n".join(f"- {f}" for f in review_feedback[:5])

    file_summary = ", ".join(sorted(set(k.split("/")[1] for k in files if "/" in k))) or "none"

    prompt = f"""Project: {project_name}
Requirements:
{req_text}

API Endpoints:
{ep_text}

Generated code files: {file_summary}
Code review feedback: {feedback_text or "None"}

Generate documentation. For each file, use this EXACT format:

### FILE: docs/<filename>
<complete markdown content>

Generate:
1. README.md — overview, features, tech stack, quickstart
2. API.md — endpoint reference with request/response examples
3. SETUP.md — setup and running instructions (Docker + local)
4. CHANGELOG.md — initial release entry

Write complete, professional markdown. No placeholders."""

    llm = get_llm(model=settings.DOCS_MODEL, temperature=0.3, max_tokens=4000)

    try:
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        parsed = parse_files(response.content)
        logger.info(f"Generated {len(parsed)} documentation files")
    except Exception as e:
        logger.error(f"Documentation Agent failed: {e}")
        return {
            "current_task": "error",
            "messages": [AIMessage(content=f"Documentation Agent error: {str(e)[:200]}")]
        }

    doc_files = {f"docs/{k.split('/',1)[-1]}": v for k, v in parsed.items()}
    documentation = {k.split('/',1)[-1]: v for k, v in parsed.items()}

    return {
        "files": doc_files,
        "documentation": documentation,
        "current_task": "human_checkpoint_final",
        "messages": [AIMessage(content=f"Documentation generated: {len(doc_files)} files")]
    }
