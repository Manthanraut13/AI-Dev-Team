"""QA Engineer agent — generates tests for a saved file.

Triggered by file-save events (watchdog) or explicit `/test` invocation. Per
Agent.md §6: writes a test file mirroring the saved file's path under
`.ai-devteam/tests/`. Returns QAOutput.
"""
from pathlib import Path
import re

from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import QAOutput
from plugin.memory.context import load_context
from plugin.memory.long_term import qdrant_upsert
from plugin.utils.llm import get_llm, invoke_with_retry
from plugin.utils.files import parse_files
from plugin.tools.output import log_activity
import logging

logger = logging.getLogger(__name__)


def _build_prompt(file_path: str, file_content: str) -> str:
    p = Path(file_path)
    ext = p.suffix
    if ext in (".ts", ".tsx"):
        kind = "Jest unit tests for a React component" if "components" in str(p) else "Playwright e2e tests"
    else:
        kind = "Pytest tests with pytest-asyncio for an async FastAPI route or Python module"
    return f"""Generate tests for the following file: {file_path}

File content:
{file_content[:6000]}

Generate {kind}. Use this EXACT format:

### FILE: <test_file_name>
<complete test file content>

Mock all external dependencies. Test the happy path and at least 2 edge cases per function.
Use the appropriate async testing pattern for the file type."""


def _default_test_name(file_path: str) -> str:
    p = Path(file_path)
    if p.suffix == ".py":
        return f"test_{p.stem}.py"
    return f"{p.stem}.test.ts" if p.suffix == ".tsx" else f"{p.stem}.spec.ts"


async def qa_engineer_agent(file_path: str) -> QAOutput:
    """Generate tests for the given file path. Writes to `.ai-devteam/tests/`."""
    log_activity("qa_engineer", "start", {"file": file_path})

    p = Path(file_path)
    if not p.exists():
        log_activity("qa_engineer", "error", {"error": f"file not found: {file_path}"})
        raise FileNotFoundError(f"File not found: {file_path}")

    file_content = p.read_text(encoding="utf-8", errors="replace")
    context = load_context()

    prompt = _build_prompt(str(p), file_content)
    llm = get_llm(temperature=0.3, max_tokens=3000)

    try:
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        parsed = parse_files(response.content, trim_prose=True)
    except Exception as e:
        log_activity("qa_engineer", "error", {"error": str(e)})
        logger.error(f"QA Engineer failed: {e}")
        raise RuntimeError(f"QA Engineer failed: {e}") from e

    if parsed and any(parsed.values()):
        test_filename, test_content = next(iter(parsed.items()))
    else:
        test_filename = _default_test_name(file_path)
        test_content = f"# Auto-generated test stub for {file_path}\n# Re-run /test to regenerate.\n"

    # Write under `.ai-devteam/tests/<source_dir>/<test_filename>` mirroring the source path.
    out_dir = Path(context["project_name"]) if context.get("project_name") else Path(".")
    from plugin.paths import ai_devteam_dir
    mirror_dir = ai_devteam_dir() / "tests"
    if p.parent and str(p.parent) != ".":
        # Mirror the source file's sub-path (flattened to the stem) for traceability.
        mirror_dir = mirror_dir / p.stem
    mirror_dir.mkdir(parents=True, exist_ok=True)
    final_path = mirror_dir / test_filename
    final_path.write_text(test_content, encoding="utf-8")

    test_count = len(
        re.findall(r"^\s*(?:async\s+def\s+test_|def\s+test_|it\(|test\()", test_content, re.MULTILINE)
    )

    log_activity("qa_engineer", "end", {"test_count": test_count, "test_file": str(final_path)})

    # Persist the test path + count to long-term memory (graceful if Qdrant is down).
    qdrant_upsert(
        "patterns",
        content=f"QA tests for {p.name}: {test_count} tests at {final_path.name}",
        metadata={
            "agent": "qa_engineer",
            "source": str(p),
            "test_file": str(final_path),
            "test_count": test_count,
        },
    )

    return QAOutput(
        file_tested=str(p),
        test_file_path=str(final_path),
        test_file_content=test_content,
        test_count=test_count,
        coverage_notes=f"Generated {test_count} tests for {file_path}",
    )