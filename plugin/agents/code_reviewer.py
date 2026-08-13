"""Code Reviewer agent — reviews a file for issues, security, and performance.

Ported from v1. Rewritten as a standalone async function. Uses the
deepseek-r1 / gpt-oss review model with delimited output (proven on this
machine). Writes `.ai-devteam/reviews/<basename>.md`.
"""
from pathlib import Path
import re

from langchain_core.messages import HumanMessage

from plugin.schemas.outputs import ReviewOutput
from plugin.config import settings
from plugin.memory.long_term import qdrant_upsert
from plugin.utils.llm import get_llm, invoke_with_retry
from plugin.tools.output import write_agent_output, log_activity
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior code reviewer. Review the code provided and
write your review in EXACTLY the following delimiter format:

### ISSUES
- <specific issue with file reference>

### SUGGESTIONS
- <improvement suggestion>

### SECURITY
- <security concern>

### PERFORMANCE
- <performance note>

If a category has nothing, write 'None' under it. Be concise — one line per item."""


def _parse_review(text: str) -> dict:
    """Parse the delimited review into structured fields."""
    text = re.sub(r"<hthink>.*?</hthink>", "", text, flags=re.DOTALL).strip()

    def section(marker: str) -> list[str]:
        match = re.search(rf"###\s*{marker}\s*\n(.*?)(?=###\s|\Z)", text, re.DOTALL)
        if not match:
            return []
        lines = [l.strip().lstrip("- ") for l in match.group(1).strip().splitlines() if l.strip()]
        return [l for l in lines if not l.startswith("###") and l.lower() != "none"]

    issues = section("ISSUES")
    suggestions = section("SUGGESTIONS")
    security = section("SECURITY")
    performance = section("PERFORMANCE")

    severity = "clean"
    if security:
        severity = "critical"
    elif len(issues) > 2:
        severity = "major"
    elif issues or suggestions:
        severity = "minor"

    return {
        "issues": issues,
        "suggestions": suggestions,
        "security_flags": security,
        "performance_notes": performance,
        "severity": severity,
    }


async def code_reviewer_agent(file_path: str) -> ReviewOutput:
    """Review the given file. Writes `.ai-devteam/reviews/<basename>.md`."""
    log_activity("code_reviewer", "start", {"file": file_path})

    p = Path(file_path)
    if not p.exists():
        log_activity("code_reviewer", "error", {"error": f"file not found: {file_path}"})
        raise FileNotFoundError(f"File not found: {file_path}")

    code_content = p.read_text(encoding="utf-8", errors="replace")
    code_content = code_content[:12000]

    prompt = (
        f"{SYSTEM_PROMPT}\n\n"
        f"File: {p.name}\n"
        f"```\n{code_content}\n```"
    )

    llm = get_llm(model=settings.REVIEW_MODEL, temperature=0.3, max_tokens=3000)

    try:
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        parsed = _parse_review(response.content)
    except Exception as e:
        log_activity("code_reviewer", "error", {"error": str(e)})
        logger.error(f"Code Reviewer failed: {e}")
        parsed = {"issues": [f"Review failed: {e}"], "suggestions": [], "security_flags": [],
                  "performance_notes": [], "severity": "major"}

    review = ReviewOutput(
        file_reviewed=str(p),
        issues=parsed["issues"],
        security_flags=parsed["security_flags"],
        performance_notes=parsed["performance_notes"],
        suggestions=parsed["suggestions"],
        severity=parsed["severity"],
    )

    # Build the markdown report
    lines = [f"# Review — {p.name}", f"\nSeverity: **{review.severity}**", ""]
    if review.issues:
        lines += ["## Issues", ""] + [f"- {i}" for i in review.issues] + [""]
    if review.security_flags:
        lines += ["## Security", ""] + [f"- {s}" for s in review.security_flags] + [""]
    if review.performance_notes:
        lines += ["## Performance", ""] + [f"- {n}" for n in review.performance_notes] + [""]
    if review.suggestions:
        lines += ["## Suggestions", ""] + [f"- {s}" for s in review.suggestions] + [""]
    if review.severity == "clean":
        lines.append("No issues found. ✅\n")

    write_agent_output("code_reviewer", f"{p.stem}.md", "\n".join(lines))

    log_activity("code_reviewer", "end", {"severity": review.severity, "issues": len(review.issues)})

    # Persist review summary to long-term memory (graceful if Qdrant is down).
    findings_blob = "\n".join(
        (review.issues or []) + (review.security_flags or []) + (review.performance_notes or [])
    )[:1500]
    qdrant_upsert(
        "patterns",
        content=findings_blob or f"Clean review for {p.name}",
        metadata={
            "agent": "code_reviewer",
            "file": str(p),
            "severity": review.severity,
            "issues": len(review.issues),
            "security_flags": len(review.security_flags),
        },
    )

    return review