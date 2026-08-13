from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, List
from app.config import settings
from app.utils.llm import get_llm, invoke_with_retry
import logging
import re

logger = logging.getLogger(__name__)


def _parse_review(text: str) -> Dict:
    """Parse the review delimited output into structured fields."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    def section(marker: str) -> List[str]:
        match = re.search(rf"###\s*{marker}\s*\n(.*?)(?=###\s|\Z)", text, re.DOTALL)
        if not match:
            return []
        lines = [l.strip().lstrip("- ") for l in match.group(1).strip().splitlines() if l.strip()]
        return [l for l in lines if not l.startswith("###")]

    issues = section("ISSUES")
    suggestions = section("SUGGESTIONS")
    security = section("SECURITY")

    approved = True
    if issues or security:
        approved = False

    return {
        "issues": issues,
        "suggestions": suggestions,
        "security_flags": security,
        "approved": approved
    }


def code_reviewer_node(state) -> dict:
    files = state.get("files", {})
    project_name = state.get("project_name", "project")

    logger.info(f"Code Reviewer starting for {project_name}")

    backend_files = {k: v for k, v in files.items() if k.startswith("backend/") and k.endswith(".py")}

    if not backend_files:
        return {
            "current_task": "documentation",
            "review_feedback": ["No backend files to review"],
            "messages": [AIMessage(content="Code Review: no backend files found to review")]
        }

    code_text = ""
    for path, content in sorted(backend_files.items()):
        code_text += f"\n===== {path} =====\n{content[:2000]}\n"

    code_text = code_text[:12000]

    prompt = f"""Review the following generated FastAPI backend code for project "{project_name}".

Look specifically for:
1. Security issues: SQL injection, missing auth, hardcoded secrets, unsafe deserialization
2. Performance issues: N+1 queries, blocking calls in async, missing pagination
3. Code quality: poor error handling, incorrect SQLAlchemy usage, missing type hints

{code_text}

Use EXACTLY this format:

### ISSUES
- <specific issue with file reference>
### SUGGESTIONS
- <improvement suggestion>
### SECURITY
- <security concern>

If a category has nothing, write 'None' under it."""

    llm = get_llm(model=settings.REVIEW_MODEL, temperature=0.3, max_tokens=3000)
    
    try:
        response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
        review = _parse_review(response.content)
        logger.info(f"Review complete: {len(review['issues'])} issues, {len(review['security_flags'])} security flags, approved={review['approved']}")
    except Exception as e:
        logger.error(f"Code Reviewer failed: {e}")
        review = {
            "issues": [f"Review failed: {e}"],
            "suggestions": [],
            "security_flags": [],
            "approved": False
        }

    feedback = []
    feedback.extend(review["issues"])
    feedback.extend(review["security_flags"])

    summary = (
        f"Review complete: {len(review['issues'])} issues, "
        f"{len(review['security_flags'])} security flags. "
        f"Overall: {'PASS' if review['approved'] else 'REVIEW NEEDED'}"
    )

    return {
        "current_task": "documentation",
        "review_feedback": feedback,
        "messages": [AIMessage(content=summary)]
    }
