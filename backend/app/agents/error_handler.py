"""Error Handler agent — reads failure logs from QA / Code Review, then
auto-fixes the generated code up to ``MAX_FIX_ROUNDS`` rounds and re-runs
the tests to confirm the fix.

This agent is the "auto-heal" loop. It sits between QA / Code Reviewer
and Documentation in both the pipeline graph and the supervisor tool
chain.  When there are no errors it short-circuits immediately and
passes the files through unchanged.

The agent does NOT write files to disk — it only mutates the in-memory
``files`` dict so the next agent (Documentation) sees the corrected code.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage

from app.config import settings
from app.utils.files import parse_files
from app.utils.llm import get_llm, invoke_with_retry
from app.utils.test_runner import materialize_and_run

logger = logging.getLogger(__name__)

MAX_FIX_ROUNDS = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_error_context(state: Dict[str, Any]) -> str:
    """Turn ``test_results`` and ``review_feedback`` into a human-readable
    error summary suitable for an LLM prompt."""
    test_results = state.get("test_results", {})
    lines: List[str] = []

    failed = test_results.get("failed", 0)
    if failed:
        logs = test_results.get("logs", "")[-1500:]
        lines.append(f"{failed} test(s) failed. Pytest output:\n{logs}")

    for item in state.get("review_feedback", []):
        lines.append(f"Code review finding: {item}")

    return "\n\n".join(lines)


def _relevant_file_text(files: Dict[str, str], max_chars: int = 10000) -> str:
    """Return a compact text representation of the backend Python files,
    suitable for inclusion in an LLM prompt."""
    parts: List[str] = []
    total = 0
    for path in sorted(files):
        if not path.startswith("backend/"):
            continue
        if not path.endswith(".py"):
            continue
        content = files[path]
        chunk = f"\n===== {path} =====\n{content[:1500]}\n"
        if total + len(chunk) > max_chars:
            break
        parts.append(chunk)
        total += len(chunk)
    return "".join(parts)


def _current_test_failures(state: Dict[str, Any]) -> List[Dict[str, str]]:
    """Turn the final ``test_results`` into a list of structured error dicts
    that we return in the output so downstream agents / the UI can show them."""
    test_results = state.get("test_results", {})
    errors: List[Dict[str, str]] = []
    failed = test_results.get("failed", 0)
    if failed:
        errors.append({
            "type": "test_failure",
            "file": "",
            "message": f"{failed} test(s) still failing after fix attempts",
        })
    return errors


# ---------------------------------------------------------------------------
# Main node
# ---------------------------------------------------------------------------


def error_handler_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """Run the Error Handler agent.

    If there are test failures or code-review issues, attempt up to
    ``MAX_FIX_ROUNDS`` rounds of LLM-driven fixes and re-test.

    Returns a dict with keys:
      ``files``       — possibly corrected file map
      ``test_results`` — re-run results after fixes
      ``errors``      — remaining errors (empty = all clear)
      ``fixes``       — human-readable list of applied fixes
      ``current_task`` — always ``"documentation"``
      ``messages``    — summary message(s)
    """
    project_name = state.get("project_name", "project")
    files = dict(state.get("files", {}))

    error_context = _build_error_context(state)
    no_errors = not error_context.strip()

    if no_errors:
        logger.info(f"Error Handler [{project_name}]: no errors detected — passing through")
        return {
            "current_task": "documentation",
            "errors": [],
            "fixes": [],
            "messages": [
                AIMessage(
                    content=(
                        "Error Check: all clear — no failing tests and "
                        "no code-review issues flagged."
                    )
                )
            ],
        }

    logger.info(
        f"Error Handler [{project_name}]: errors detected, "
        f"attempting up to {MAX_FIX_ROUNDS} fix round(s)"
    )

    fixes: List[str] = []
    test_results: Dict[str, Any] = state.get("test_results", {})

    for round_no in range(1, MAX_FIX_ROUNDS + 1):
        file_text = _relevant_file_text(files)

        prompt = (
            f"You are the Error Handler on an AI software development team.\n"
            f"Your job is to fix the errors below in the generated FastAPI project \"{project_name}\".\n\n"
            f"--- ERRORS (round {round_no}) ---\n{error_context}\n\n"
            f"--- RELEVANT SOURCE FILES ---\n{file_text}\n\n"
            f"Output ONLY the corrected files using this EXACT format:\n"
            f"### FILE: backend/app/<path>\n<complete corrected file content>\n\n"
            f"Do NOT include files that do not need changes.\n"
            f"Write complete, runnable code — no placeholders."
        )

        llm = get_llm(model=settings.REVIEW_MODEL, temperature=0.2, max_tokens=3000)

        try:
            response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
            fixed = parse_files(response.content)
        except Exception as e:
            logger.error(f"Error Handler round {round_no} LLM call failed: {e}")
            break

        if not fixed:
            logger.warning(f"Error Handler round {round_no}: LLM returned no fixes")
            break

        changed = False
        for raw_path, content in fixed.items():
            path = raw_path if raw_path.startswith("backend/") else f"backend/{raw_path}"
            old = files.get(path)
            if old == content:
                continue
            files[path] = content
            fixes.append(f"round {round_no}: rewrote {path}")
            changed = True

        if not changed:
            logger.info(f"Error Handler round {round_no}: no changes applied by LLM")
            break

        # Re-run tests with the updated files.
        test_results = materialize_and_run(files, timeout=60)
        error_context = _build_error_context({"test_results": test_results, "review_feedback": state.get("review_feedback", [])})
        logger.info(
            f"Error Handler round {round_no}: "
            f"{test_results.get('passed', 0)} passed, "
            f"{test_results.get('failed', 0)} failed"
        )
        if test_results.get("failed", 0) == 0:
            break

    remaining_errors = _current_test_failures({"test_results": test_results})

    summary_parts: List[str] = []
    if fixes:
        summary_parts.append(f"Error handling: {len(fixes)} fix(es) applied")
    else:
        summary_parts.append("Error handling: no auto-fixes applied")
    if remaining_errors:
        summary_parts.append(
            f"{len(remaining_errors)} error(s) still remain after "
            f"{MAX_FIX_ROUNDS} round(s)"
        )
    summary = ". ".join(summary_parts) + "."

    return {
        "files": files,
        "test_results": test_results,
        "errors": remaining_errors,
        "fixes": fixes,
        "current_task": "documentation",
        "messages": [AIMessage(content=summary)],
    }
