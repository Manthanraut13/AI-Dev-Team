"""FastMCP server — exposes the AI Dev Team agents as MCP tools.

This is the "plugin works" milestone. Any MCP-capable coding platform
(Claude Code, Cline, Roo Code, OpenCode, Codex) can mount this server and
call the agents as tools.

Usage:
    python -m plugin.server --transport stdio          # default (platforms spawn this)
    python -m plugin.server --transport http --port 8765
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP

from plugin.config import settings
from plugin.agents.product_manager import product_manager_agent
from plugin.agents.architect import architect_agent
from plugin.agents.research import research_agent
from plugin.agents.backend_dev import backend_dev_agent
from plugin.agents.frontend_dev import frontend_dev_agent
from plugin.agents.qa_engineer import qa_engineer_agent
from plugin.agents.code_reviewer import code_reviewer_agent
from plugin.agents.documentation import documentation_agent
from plugin.graph.pipeline import run_devteam_pipeline, confirm_scaffold
from plugin.memory.context import load_context

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()  # belt-and-suspenders; settings already probes .env itself

mcp = FastMCP("ai-dev-team")


def _require_groq_key() -> None:
    """Fail fast with an actionable message when the LLM key is missing."""
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "Groq key, then restart the server."
        )


@mcp.tool()
async def run_product_manager(idea: str) -> dict:
    """Product Manager agent — turn a rough idea into PRD (requirements + prioritized tasks).

    Args:
        idea: A rough project idea, in plain language.
    """
    _require_groq_key()
    return (await product_manager_agent(idea)).model_dump()


@mcp.tool()
async def run_architect(requirements: list[str] | None = None) -> dict:
    """Architect agent — design stack, API endpoints, DB schema, folder structure.

    Args:
        requirements: Optional list of functional requirements. Omit to use the
            project context (from the last product_manager run).
    """
    _require_groq_key()
    return (await architect_agent(requirements)).model_dump()


@mcp.tool()
async def run_research(topic: str) -> dict:
    """Research agent — web search + crawl + synthesize a topic.

    Args:
        topic: The topic or question to research.
    """
    _require_groq_key()
    return (await research_agent(topic)).model_dump()


@mcp.tool()
async def run_backend_dev(spec: str) -> dict:
    """Backend Developer agent — scaffold a FastAPI backend from a spec.

    Args:
        spec: Backend spec or requirement summary. Returns files — the caller
            must confirm before they are written to `backend/`.
    """
    _require_groq_key()
    return (await backend_dev_agent(spec)).model_dump()


@mcp.tool()
async def run_frontend_dev(spec: str) -> dict:
    """Frontend Developer agent — scaffold a Next.js frontend from a spec.

    Args:
        spec: Frontend spec or requirement summary. Returns files — the caller
            must confirm before they are written to `frontend/`.
    """
    _require_groq_key()
    return (await frontend_dev_agent(spec)).model_dump()


@mcp.tool()
async def run_qa_engineer(file_path: str) -> dict:
    """QA Engineer agent — generate tests for a saved file.

    Args:
        file_path: Path to the source file to test.
    """
    _require_groq_key()
    return (await qa_engineer_agent(file_path)).model_dump()


@mcp.tool()
async def run_code_reviewer(file_path: str) -> dict:
    """Code Reviewer agent — review a file for issues, security, performance.

    Args:
        file_path: Path to the source file to review.
    """
    _require_groq_key()
    return (await code_reviewer_agent(file_path)).model_dump()


@mcp.tool()
async def run_documentation(changed_files: list[str]) -> dict:
    """Documentation agent — update README/API docs/CHANGELOG after a change.

    Args:
        changed_files: List of file paths changed in this commit / change set.
    """
    _require_groq_key()
    return (await documentation_agent(changed_files)).model_dump()


@mcp.tool()
async def run_devteam(idea: str) -> dict:
    """Run the full build pipeline: PM → Architect → (Backend+Frontend) → QA → Review → Docs.

    Args:
        idea: The project idea, in plain language. Scaffold files are returned
            under `pending_scaffold` — confirm with `confirm_scaffold` before use.
    """
    _require_groq_key()
    return await run_devteam_pipeline(idea)


@mcp.tool()
async def confirm_scaffold(target: str, files: dict) -> list[str]:
    """Write approved scaffold files into the project under `backend/` or `frontend/`.

    Args:
        target: Which scaffold to confirm — 'backend' or 'frontend'.
        files: The file map returned by run_backend_dev / run_frontend_dev
            (or the `pending_scaffold` entry from run_devteam).
    """
    return confirm_scaffold(target, files)


@mcp.tool()
async def get_project_context() -> dict:
    """Return the current project context (requirements, architecture, etc.)."""
    return load_context()


def main() -> None:
    """CLI entry point (`ai-dev-team` console script)."""
    parser = argparse.ArgumentParser(description="AI Dev Team MCP plugin server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="MCP transport to serve on (default: stdio)",
    )
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Start the file-save watcher (QA + review on save) alongside the server",
    )
    parser.add_argument(
        "--install-hook",
        action="store_true",
        help="Install the post-commit git hook, then continue serving",
    )
    args = parser.parse_args()

    if not settings.GROQ_API_KEY:
        logger.warning(
            "GROQ_API_KEY is not set — agents will fail with a clear error until "
            "you add it to .env."
        )

    if args.install_hook:
        from plugin.triggers.git_hook import install_hook
        install_hook()

    if args.watch:
        from plugin.triggers.watcher import start_watcher
        start_watcher()

    if args.transport == "http":
        logger.info("AI Dev Team serving HTTP on http://%s:%d", args.host, args.port)
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        logger.info("AI Dev Team serving on stdio")
        mcp.run(transport="stdio")


if __name__ == "__main__":
    sys.exit(main())
