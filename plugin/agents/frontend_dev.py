"""Frontend Developer agent — scaffolds a Next.js frontend from project context.

Same rewrites as backend_dev.py: standalone async function returning
`FrontendDevOutput` with `requires_confirmation=True`.
"""
from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import FrontendDevOutput
from plugin.memory.context import load_context
from plugin.memory.long_term import qdrant_search, qdrant_upsert
from plugin.utils.llm import get_llm, invoke_with_retry
from plugin.utils.files import parse_files
from plugin.tools.output import log_activity
import logging

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Generate a complete Next.js 14 frontend for project "{project_name}".

Spec / requirements:
{spec}

Backend API:
{endpoints}

Prior similar code patterns (from long-term memory, may be empty):
{patterns}

Generate ALL of the following files. For each file, use this EXACT format:

### FILE: <relative/path>
<complete file content>

Generate these files:
1. package.json — next@14, react@18, tailwindcss, typescript
2. tsconfig.json — standard Next.js config with @/* alias
3. tailwind.config.js — content globs for app/ and components/
4. postcss.config.js — tailwindcss + autoprefixer
5. app/globals.css — tailwind directives
6. app/layout.tsx — root layout with metadata
7. app/page.tsx — landing page with Tailwind styling
8. lib/api.ts — typed fetch wrappers for every API endpoint above
9. types/index.ts — TypeScript interfaces for API responses

Write complete, runnable code. No placeholders."""


async def frontend_dev_agent(spec: str) -> FrontendDevOutput:
    """Generate frontend scaffolding (Next.js + React) from a spec."""
    log_activity("frontend_dev", "start", {"spec": spec[:120]})
    context = load_context()
    project_name = context.get("project_name", "project")
    architecture = context.get("architecture", {})
    requirements = context.get("requirements", [])

    endpoints = [
        f"{e.get('method', 'GET')} {e.get('path', '/')}"
        for e in architecture.get("api_endpoints", [])[:6]
    ]

    if not spec.strip() and requirements:
        spec = "\n".join(f"- {r[:80]}" for r in requirements[:10])

    # Retrieve similar past code patterns from long-term memory (graceful if down).
    patterns = qdrant_search("patterns", query=spec[:500], limit=3)
    patterns_text = "\n\n".join(f"--- pattern {i + 1} (score {p.get('score', 0):.2f}) ---\n{p.get('content', '')[:800]}" for i, p in enumerate(patterns))

    prompt = PROMPT_TEMPLATE.format(
        project_name=project_name,
        spec=spec,
        endpoints="\n".join(endpoints) if endpoints else "(none defined)",
        patterns=patterns_text or "(no prior patterns found)",
    )

    llm = get_llm(temperature=0.3, max_tokens=4000)
    try:
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        files = parse_files(response.content)
    except Exception as e:
        log_activity("frontend_dev", "error", {"error": str(e)})
        logger.error(f"Frontend Dev agent failed: {e}")
        raise RuntimeError(f"Frontend Dev agent failed: {e}") from e

    frontend_files = {f"frontend/{k}": v for k, v in files.items()}

    qdrant_upsert(
        "patterns",
        content=f"Frontend for {project_name}: {', '.join(list(frontend_files.keys())[:8])}",
        metadata={"project_name": project_name, "type": "frontend_scaffold"},
    )

    log_activity("frontend_dev", "end", {"files": len(frontend_files)})
    return FrontendDevOutput(
        files=frontend_files,
        summary=f"Generated {len(frontend_files)} frontend files for {project_name}",
        requires_confirmation=True,
    )
