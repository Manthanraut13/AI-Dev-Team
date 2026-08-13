from langchain_core.messages import AIMessage
from app.graph.state import AgentState
from app.tools.github import github_commit_and_pr
import logging

logger = logging.getLogger(__name__)


def github_node(state) -> dict:
    project_name = state.get("project_name", "project")
    files = state.get("files", {})

    logger.info(f"GitHub Automation starting for {project_name} ({len(files)} files)")

    if not files:
        return {
            "current_task": "complete",
            "messages": [AIMessage(content="GitHub: no files to commit")]
        }

    try:
        pr_url = github_commit_and_pr(
            files=files,
            project_name=project_name
        )
        logger.info(f"GitHub PR created: {pr_url}")
        return {
            "current_task": "complete",
            "github_pr_url": pr_url,
            "messages": [AIMessage(content=f"GitHub: PR created at {pr_url}")]
        }
    except Exception as e:
        logger.error(f"GitHub Automation failed: {e}")
        return {
            "current_task": "error",
            "messages": [AIMessage(content=f"GitHub error: {str(e)[:200]}")]
        }
