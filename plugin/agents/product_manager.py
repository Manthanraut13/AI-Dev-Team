"""Product Manager agent — turns a software idea into structured requirements.

Ported from v1 backend `product_manager.py`. Interface changed from a LangGraph
node to a standalone async function returning a validated `PMOutput`.
"""
from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import PMOutput
from plugin.memory.context import load_context, update_context
from plugin.memory.long_term import qdrant_upsert
from plugin.tools.output import write_agent_output, log_activity
from plugin.utils.llm import get_llm, invoke_with_retry
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior product manager with extensive experience in software development.
Given a software idea, produce a structured list of:
1. Functional requirements - what the system must do
2. Non-functional requirements - quality attributes (performance, security, scalability, etc.)
3. Prioritized tasks - ordered list of implementation tasks

Always respond with valid JSON matching the schema provided.
Be specific and actionable in your requirements.
Each requirement should be clear, testable, and unambiguous."""

USER_PROMPT_TEMPLATE = """Software Idea: {idea}

Please analyze this idea and produce:
1. A comprehensive list of functional requirements
2. Non-functional requirements (security, performance, usability, etc.)
3. A prioritized breakdown of tasks

Format your response as valid JSON."""


async def product_manager_agent(idea: str) -> PMOutput:
    """Generate requirements from a software idea or feature description."""
    log_activity("product_manager", "start", {"idea": idea[:120]})
    context = load_context()

    llm = get_llm(temperature=0.7)
    structured_llm = llm.with_structured_output(PMOutput, method="json_schema")

    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(idea=idea)),
    ]

    try:
        result = invoke_with_retry(structured_llm, messages)
    except Exception as e:
        if "validation" in str(e).lower() or "parse" in str(e).lower():
            logger.warning(f"PM output validation failed, retrying: {e}")
            try:
                result = invoke_with_retry(structured_llm, messages)
            except Exception as e2:
                log_activity("product_manager", "error", {"error": str(e2)})
                raise RuntimeError(f"Product Manager agent failed after retry: {e2}") from e2
        else:
            log_activity("product_manager", "error", {"error": str(e)})
            raise RuntimeError(f"Product Manager agent failed: {e}") from e

    # Persist project context so downstream agents (architect, devs) see it.
    update_context(
        project_name=result.project_name,
        summary=result.summary,
        requirements=result.functional_requirements,
        decisions=result.prioritized_tasks,
    )

    # Write .ai-devteam/requirements.md
    md = _format_requirements_md(result, context)
    write_agent_output("product_manager", "requirements.md", md)

    # Persist to long-term memory so future projects can reference this one
    # (graceful if Qdrant is down).
    qdrant_upsert(
        "projects",
        content=result.summary,
        metadata={
            "agent": "product_manager",
            "project": result.project_name,
            "functional_requirements": len(result.functional_requirements),
            "tasks": len(result.prioritized_tasks),
        },
    )

    log_activity(
        "product_manager",
        "end",
        {"functional": len(result.functional_requirements), "tasks": len(result.prioritized_tasks)},
    )
    return result


def _format_requirements_md(result: PMOutput, context: dict) -> str:
    lines = [
        f"# Requirements — {result.project_name}",
        "",
        f"> {result.summary}",
        "",
        "## Functional Requirements",
        "",
    ]
    lines += [f"- [ ] {r}" for r in result.functional_requirements]
    lines += ["", "## Non-Functional Requirements", ""]
    lines += [f"- [ ] {r}" for r in result.non_functional_requirements]
    lines += ["", "## Prioritized Tasks", ""]
    lines += [f"{i}. {t}" for i, t in enumerate(result.prioritized_tasks, 1)]
    lines.append("")
    if context.get("project_name"):
        lines.append(f"_Generated for existing project: {context['project_name']}_")
        lines.append("")
    return "\n".join(lines)
