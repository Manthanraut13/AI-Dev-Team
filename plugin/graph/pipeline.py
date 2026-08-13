"""`/devteam` pipeline orchestrator.

Runs the full build loop as async steps, collecting every agent's output into
a single dict for the MCP tool to return. Scaffold agents (backend/frontend)
do NOT write files here — their `requires_confirmation=True` files are surfaced
under `pending_scaffold` so the calling platform/LLM can confirm before writing.

Flow: PM → Architect → (Backend + Frontend) → QA + Review → Docs
"""
import logging
from pathlib import Path

from plugin.agents.product_manager import product_manager_agent
from plugin.agents.architect import architect_agent
from plugin.agents.backend_dev import backend_dev_agent
from plugin.agents.frontend_dev import frontend_dev_agent
from plugin.agents.qa_engineer import qa_engineer_agent
from plugin.agents.code_reviewer import code_reviewer_agent
from plugin.agents.documentation import documentation_agent
from plugin.tools.output import log_activity
from plugin.utils.errors import error_response

logger = logging.getLogger(__name__)


PIPELINE_STAGES = [
    "product_manager",
    "architect",
    "backend_dev",
    "frontend_dev",
    "qa_engineer",
    "code_reviewer",
    "documentation",
]


async def run_devteam_pipeline(idea: str) -> dict:
    """Run the full agent pipeline and return a combined result dict.

    Returns a JSON-serialisable dict on every path — never raises. On any
    failure mid-pipeline, returns `{"status": "error", "stage": <which>,
    "error": ..., "partial_results": {...}}`.
    """
    log_activity("pipeline", "start", {"idea": idea[:120]})
    results: dict = {}
    last_stage = "start"
    try:
        # 1. Product Manager — idea → requirements
        last_stage = "product_manager"
        pm = await product_manager_agent(idea)
        results["product_manager"] = pm.model_dump()
        spec = "\n".join(pm.functional_requirements[:10]) or idea

        # 2. Architect — requirements → architecture
        last_stage = "architect"
        arch = await architect_agent(pm.functional_requirements)
        results["architect"] = arch.model_dump()

        # 3. Backend + Frontend scaffolds (returned, NOT written)
        last_stage = "backend_dev"
        backend = await backend_dev_agent(spec)
        results["backend_dev"] = backend.model_dump()

        last_stage = "frontend_dev"
        frontend = await frontend_dev_agent(spec)
        results["frontend_dev"] = frontend.model_dump()

        # 4. QA + Review in parallel over the generated backend files
        last_stage = "qa_engineer+code_reviewer"
        qa_results, review_results = await _qa_and_review(backend.files)
        results["qa_engineer"] = qa_results
        results["code_reviewer"] = review_results

        # 5. Documentation — summarize the change set
        last_stage = "documentation"
        changed = _all_generated_paths(backend.files) + _all_generated_paths(frontend.files)
        docs = await documentation_agent(changed)
        results["documentation"] = docs.model_dump()

        pending = {
            "backend": {
                "files": backend.files,
                "requires_confirmation": backend.requires_confirmation,
                "summary": backend.summary,
            },
            "frontend": {
                "files": frontend.files,
                "requires_confirmation": frontend.requires_confirmation,
                "summary": frontend.summary,
            },
        }

        summary = (
            f"Pipeline complete for \"{pm.project_name}\". "
            f"{len(pm.functional_requirements)} requirements, {len(arch.api_endpoints)} API "
            f"endpoints, {len(backend.files)} backend + {len(frontend.files)} frontend files "
            f"generated (pending confirmation), {len(review_results['reviews'])} code reviews. "
            f"Docs updated: README={docs.readme_updated}, API={docs.api_docs_updated}."
        )

        log_activity("pipeline", "end", {"summary": summary})
        return {
            "status": "ok",
            "project_name": pm.project_name,
            "summary": summary,
            "agents": results,
            "pending_scaffold": pending,
        }
    except Exception as e:
        logger.exception(f"Pipeline failed at stage '{last_stage}': {e}")
        log_activity("pipeline", "error", {"stage": last_stage, "error": str(e)[:200]})
        return error_response(stage=last_stage, error=e, partial_results=results)


async def _qa_and_review(backend_files: dict) -> tuple[list, dict]:
    """QA + code review over the generated backend files, both gracefully best-effort."""
    qa_results = []
    review_results = {"reviews": []}

    # Write backend files to a temp location so qa/review can read them,
    # then clean up. Scaffold files are otherwise only written after confirm.
    import tempfile
    from plugin.utils.files import safe_join

    with tempfile.TemporaryDirectory() as tmp:
        written = []
        for rel_path, content in backend_files.items():
            p = safe_join(Path(tmp), rel_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            written.append(p)

        for p in written[:4]:  # cap to keep the pipeline snappy
            try:
                qa = await qa_engineer_agent(str(p))
                qa_results.append({"file": qa.file_tested, "tests": qa.test_count})
            except Exception as e:
                logger.warning(f"QA step skipped for {p}: {e}")
            try:
                review = await code_reviewer_agent(str(p))
                review_results["reviews"].append(
                    {"file": review.file_reviewed, "severity": review.severity,
                     "issues": len(review.issues), "security": len(review.security_flags)}
                )
            except Exception as e:
                logger.warning(f"Review step skipped for {p}: {e}")

    return qa_results, review_results


def _all_generated_paths(files: dict) -> list[str]:
    return list(files.keys())[:20]


def confirm_scaffold(target: str, files: dict) -> list[str]:
    """Write confirmed scaffold files to `backend/` or `frontend/` under the project root.

    Called only after the user approves a `requires_confirmation` scaffold.
    """
    from plugin.utils.files import safe_join

    if target not in ("backend", "frontend"):
        raise ValueError(f"Unknown scaffold target: {target}")
    root = Path.cwd()
    written = []
    for rel_path, content in files.items():
        dest = safe_join(root / target, rel_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        written.append(str(dest))
    log_activity("pipeline", "confirm_scaffold", {"target": target, "files": len(written)})
    return written