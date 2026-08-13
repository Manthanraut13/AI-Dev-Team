"""Architect agent — designs API, DB schema, and folder structure from requirements.

Ported from v1 backend `architect.py`. Uses Qdrant long-term memory for past
architectures when available (degrades gracefully). Returns a validated
`ArchitectOutput` and writes `.ai-devteam/architecture.md`.
"""
from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import ArchitectOutput
from plugin.memory.context import load_context, update_context
from plugin.memory.long_term import qdrant_search, qdrant_upsert
from plugin.tools.output import write_agent_output, log_activity
from plugin.utils.llm import get_llm, invoke_with_retry
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software architect with expertise in:
- FastAPI and Python backend development
- Next.js, React, and TypeScript frontend development
- PostgreSQL database design
- RESTful API design
- Scalable system architecture

Given a list of requirements, produce a comprehensive architecture design including:
1. API endpoints (method, path, description)
2. Database schema (tables and columns)
3. Folder structure for the project
4. Key technology decisions and rationale
5. The detected technology stack

Always respond with valid JSON matching the schema provided.
Focus on practical, implementable designs."""

USER_PROMPT_TEMPLATE = """Requirements:
{requirements}

{context}

Please design the architecture for a system meeting these requirements.
Consider:
- RESTful API best practices
- Proper database normalization
- Clear separation of concerns
- Scalability and maintainability

Format your response as valid JSON."""


async def architect_agent(requirements: Optional[List[str]] = None) -> ArchitectOutput:
    """Design API, DB schema, and folder structure for the current project."""
    log_activity("architect", "start")
    context = load_context()

    reqs = requirements or context.get("requirements", [])
    if not reqs:
        log_activity("architect", "error", {"error": "No requirements available"})
        raise ValueError("Architect agent needs requirements. Run the Product Manager first or pass requirements.")

    project_name = context.get("project_name", "project")

    # Pull past architectures from long-term memory when Qdrant is up.
    context_parts = []
    past = qdrant_search("architectures", query="\n".join(reqs[:5]), limit=3)
    if past:
        context_parts.append("Relevant patterns from past projects:")
        for i, arch in enumerate(past, 1):
            context_parts.append(f"\n{i}. {arch['content'][:500]}...")
        logger.info(f"Found {len(past)} relevant past architectures")

    llm = get_llm(temperature=0.7)
    structured_llm = llm.with_structured_output(ArchitectOutput)

    requirements_text = "\n".join(f"- {r}" for r in reqs)
    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(
            requirements=requirements_text,
            context="\n".join(context_parts) if context_parts else "",
        )),
    ]

    try:
        result = invoke_with_retry(structured_llm, messages)
    except Exception as e:
        log_activity("architect", "error", {"error": str(e)})
        logger.error(f"Architect agent failed: {e}")
        raise RuntimeError(f"Architect agent failed: {e}") from e

    architecture = {
        "api_endpoints": result.api_endpoints,
        "db_schema": result.db_schema,
        "folder_structure": result.folder_structure,
        "tech_decisions": result.tech_decisions,
    }

    update_context(architecture=architecture, detected_stack=result.detected_stack)

    # Store for future projects (graceful if Qdrant is down).
    qdrant_upsert(
        "architectures",
        content=(
            f"Project: {project_name}\n\n"
            f"Requirements: {requirements_text[:1000]}\n\n"
            f"Architecture: {str(architecture)[:2000]}"
        ),
        metadata={"project_name": project_name, "type": "architecture"},
    )

    md = _format_architecture_md(result, project_name)
    write_agent_output("architect", "architecture.md", md)

    log_activity(
        "architect",
        "end",
        {"endpoints": len(result.api_endpoints), "tables": len(result.db_schema)},
    )
    return result


def _format_architecture_md(result: ArchitectOutput, project_name: str) -> str:
    lines = [f"# Architecture — {project_name}", ""]
    if result.detected_stack:
        lines += ["## Detected Stack", ""]
        lines += [f"- {s}" for s in result.detected_stack]
        lines.append("")
    lines += ["## API Endpoints", ""]
    for ep in result.api_endpoints:
        method = ep.get("method", "GET")
        path = ep.get("path", "/")
        desc = ep.get("description", "")
        lines.append(f"- **{method}** `{path}` — {desc}")
    lines += ["", "## Database Schema", ""]
    for table in result.db_schema:
        lines.append(f"### {table.get('table', 'unknown')}")
        for col in table.get("columns", []):
            if isinstance(col, dict):
                name = col.get("name", "?")
                ctype = col.get("type", "?")
                constraints = col.get("constraints", "")
                line = f"- {name}: {ctype}"
                if constraints:
                    line += f" ({constraints})"
                lines.append(line)
            else:
                lines.append(f"- {col}")
        lines.append("")
    lines += ["## Folder Structure", "", "```", result.folder_structure, "```", ""]
    lines += ["## Technology Decisions", ""]
    lines += [f"{i}. {d}" for i, d in enumerate(result.tech_decisions, 1)]
    lines.append("")
    return "\n".join(lines)
