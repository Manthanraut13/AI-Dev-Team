"""Documentation agent — updates README/API docs/CHANGELOG from project context.

Triggered by git commit (via post-commit hook). Per Agent.md §8: never rewrites
README from scratch — diff-patches changed sections only. Writes to project
root (README.md, docs/API.md, CHANGELOG.md). Returns DocsOutput.
"""
from pathlib import Path

from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import DocsOutput
from plugin.config import settings
from plugin.memory.context import load_context
from plugin.memory.long_term import qdrant_upsert
from plugin.utils.llm import get_llm, invoke_with_retry
from plugin.utils.files import parse_files, safe_join
from plugin.tools.output import log_activity
import logging

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Project: {project_name}
Requirements:
{requirements}

API Endpoints:
{endpoints}

Changed files in this commit: {changed_files}

{readme_section}

Generate documentation. For each file, use this EXACT format:

### FILE: <relative/path>
<complete markdown content>

Generate:
1. README.md — overview, features, tech stack, quickstart
2. docs/API.md — endpoint reference with request/response examples
3. CHANGELOG.md — new entry summarizing this change

Rules:
- Never rewrite README from scratch. If existing content is provided,
  diff-patch only the changed sections.
- Changelog format: `## [date] - <summary>\\n### Changed\\n- ...`
- Write complete, professional markdown. No placeholders."""


def _existing_readme_section() -> str:
    """If README.md exists, include it so the LLM patches rather than rewrites."""
    readme_path = Path("README.md")
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8", errors="replace")[:4000]
        return f"Existing README.md (patch this, do not rewrite):\n```\n{content}\n```"
    return "No existing README.md — generate a new one."


async def documentation_agent(changed_files: list[str]) -> DocsOutput:
    """Update README, API docs, and changelog based on changed files."""
    log_activity("documentation", "start", {"changed_files_count": len(changed_files)})

    context = load_context()
    project_name = context.get("project_name", "project")
    requirements = context.get("requirements", [])
    architecture = context.get("architecture", {})

    endpoints = architecture.get("api_endpoints", [])
    ep_text = "\n".join(
        f"{e.get('method', 'GET')} {e.get('path', '/')} — {e.get('description', '')}"
        for e in endpoints[:8]
    )
    req_text = "\n".join(f"- {r}" for r in requirements[:8])
    files_text = ", ".join(changed_files[:20]) or "none specified"

    prompt = PROMPT_TEMPLATE.format(
        project_name=project_name,
        requirements=req_text,
        endpoints=ep_text,
        changed_files=files_text,
        readme_section=_existing_readme_section(),
    )

    llm = get_llm(model=settings.DOCS_MODEL, temperature=0.3, max_tokens=4000)

    try:
        response = await invoke_with_retry(llm, [HumanMessage(content=prompt)])
        parsed = parse_files(response.content)
    except Exception as e:
        log_activity("documentation", "error", {"error": str(e)})
        logger.error(f"Documentation Agent failed: {e}")
        raise RuntimeError(f"Documentation Agent failed: {e}") from e

    readme_written = False
    api_written = False
    changelog_entry = ""
    files_written = []

    import datetime
    for rel_path, content in parsed.items():
        # Normalise paths: README.md, docs/API.md, CHANGELOG.md
        if rel_path.lower().endswith("readme.md"):
            dest = Path("README.md")
            readme_written = True
        elif "api" in rel_path.lower() and rel_path.lower().endswith(".md"):
            dest = Path("docs/API.md")
            dest.parent.mkdir(parents=True, exist_ok=True)
            api_written = True
        elif "changelog" in rel_path.lower():
            dest = Path("CHANGELOG.md")
            changelog_entry = content
        else:
            # Untrusted LLM output — never let it escape the project root.
            dest = Path(safe_join(str(Path.cwd()), rel_path))
            dest.parent.mkdir(parents=True, exist_ok=True)

        dest.write_text(content, encoding="utf-8")
        files_written.append(str(dest))
        logger.info(f"Wrote docs: {dest}")

    log_activity(
        "documentation",
        "end",
        {"files_written": files_written, "readme": readme_written, "api_docs": api_written},
    )

    # Persist changelog entry to long-term memory (graceful if Qdrant is down).
    qdrant_upsert(
        "references",
        content=changelog_entry or f"Doc update covering {len(files_written)} file(s)",
        metadata={
            "agent": "documentation",
            "project": project_name,
            "files": files_written[:8],
        },
    )

    return DocsOutput(
        readme_updated=readme_written,
        api_docs_updated=api_written,
        changelog_entry=changelog_entry,
        files_written=files_written,
    )