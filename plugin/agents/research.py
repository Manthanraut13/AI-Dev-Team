"""Research agent — searches the web for docs/libraries and synthesizes findings.

Rewritten from v1 backend: the old version extracted search terms from graph
state; this version takes a topic string directly (per Agent.md §3), calls
Tavily/Exa/Firecrawl, and uses the LLM to synthesize a structured ResearchOutput.
Search keys degrade gracefully — when none are set, the agent returns a
LLM-only summary from general knowledge.
"""
from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import ResearchOutput
from plugin.memory.context import load_context
from plugin.memory.long_term import qdrant_upsert
from plugin.tools.search import web_search
from plugin.tools.crawl import firecrawl_scrape
from plugin.tools.output import write_agent_output, log_activity
from plugin.utils.llm import get_llm, invoke_with_retry
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a technical researcher embedded in a developer's workflow.
Given a topic, synthesize findings into:
1. A concise summary
2. Key findings (bullet list)
3. Useful links (URLs)
4. Code examples (if any found or if you can demonstrate the concept)

Be specific and actionable. Respond only in valid JSON matching the schema."""

USER_PROMPT_TEMPLATE = """Topic: {topic}

{web_context}

Synthesize the research into a structured JSON response.
If no web results were found, produce a summary from your general knowledge
and note that web search was unavailable."""


async def research_agent(topic: str) -> ResearchOutput:
    """Search and summarize documentation and libraries for a given topic."""
    log_activity("research", "start", {"topic": topic})

    context = load_context()
    stack = context.get("detected_stack", [])
    full_topic = f"{topic} ({', '.join(stack[:3])})" if stack else topic

    # --- Gather raw results ---------------------------------------------------
    results = web_search(full_topic, max_results=5)
    logger.info(f"Web search returned {len(results)} results")

    # Scrape the top 2 results via Firecrawl for deeper content.
    enriched = []
    for r in results[:2]:
        content = firecrawl_scrape(r.get("url", ""), max_length=3000)
        if content:
            r = {**r, "full_content": content}
        enriched.append(r)

    # --- Build context for the LLM -------------------------------------------
    web_context = ""
    if enriched:
        parts = []
        for i, r in enumerate(enriched, 1):
            title = r.get("title", "")
            url = r.get("url", "")
            text = r.get("full_content") or r.get("content", "")
            parts.append(f"Result {i}: {title}\nURL: {url}\n{text[:1500]}")
        web_context = "Web search results:\n\n" + "\n\n---\n\n".join(parts)
    else:
        web_context = (
            "No web results were found (search keys may be missing or "
            "the topic is too specific). Produce a summary from your general knowledge."
        )

    # --- LLM synthesis -------------------------------------------------------
    llm = get_llm(temperature=0.7)
    structured_llm = llm.with_structured_output(ResearchOutput, method="json_schema")

    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(topic=topic, web_context=web_context)),
    ]

    try:
        result = invoke_with_retry(structured_llm, messages)
    except Exception as e:
        if "validation" in str(e).lower() or "parse" in str(e).lower():
            logger.warning(f"Research output validation failed, retrying: {e}")
            try:
                result = invoke_with_retry(structured_llm, messages)
            except Exception as e2:
                log_activity("research", "error", {"error": str(e2)})
                raise RuntimeError(f"Research agent failed after retry: {e2}") from e2
        else:
            log_activity("research", "error", {"error": str(e)})
            raise RuntimeError(f"Research agent failed: {e}") from e

    # Store findings in Qdrant for future reference (graceful if down).
    qdrant_upsert(
        "references",
        content=f"Topic: {topic}\n\n{result.summary}",
        metadata={"project_name": context.get("project_name", ""), "topic": topic},
    )

    md = _format_research_md(result)
    filename = f"{topic.lower().replace(' ', '_')[:80]}.md"
    write_agent_output("research", filename, md)

    log_activity("research", "end", {"findings": len(result.key_findings), "links": len(result.useful_links)})
    return result


def _format_research_md(result: ResearchOutput) -> str:
    lines = [f"# Research — {result.topic}", "", result.summary, "", "## Key Findings", ""]
    lines += [f"- {f}" for f in result.key_findings]
    lines += ["", "## Useful Links", ""]
    lines += [f"- <{link}>" for link in result.useful_links]
    if result.code_examples:
        lines += ["", "## Code Examples", ""]
        for i, ex in enumerate(result.code_examples, 1):
            lines += [f"### Example {i}", "```", ex, "```", ""]
    lines.append("")
    return "\n".join(lines)
