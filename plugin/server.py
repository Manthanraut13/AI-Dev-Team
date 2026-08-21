"""FastMCP server — exposes the AI Dev Team agents as MCP tools.

Lazy imports: agents are imported on first call, not at module load.
This keeps startup fast (<2s) so Claude Code / OpenCode MCP clients
don't timeout during the connection handshake.

Usage:
    python -m plugin.server --transport stdio
    python -m plugin.server --transport http --port 8765
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

from plugin.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

mcp = FastMCP("ai-dev-team")

_agents_imported = False


def _import_agents():
    global _agents_imported
    if _agents_imported:
        return
    t0 = time.time()
    logger.info("Lazy-importing agents (cold start)...")
    from plugin.agents.product_manager import product_manager_agent  # noqa: F811
    from plugin.agents.architect import architect_agent  # noqa: F811
    from plugin.agents.research import research_agent  # noqa: F811
    from plugin.agents.backend_dev import backend_dev_agent  # noqa: F811
    from plugin.agents.frontend_dev import frontend_dev_agent  # noqa: F811
    from plugin.agents.qa_engineer import qa_engineer_agent  # noqa: F811
    from plugin.agents.code_reviewer import code_reviewer_agent  # noqa: F811
    from plugin.agents.documentation import documentation_agent  # noqa: F811
    from plugin.graph.pipeline import run_devteam_pipeline, confirm_scaffold  # noqa: F811
    from plugin.memory.context import load_context  # noqa: F811
    _agents_imported = True
    logger.info(f"Agents imported in {time.time()-t0:.1f}s")


def _require_groq_key() -> None:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your "
            "Groq key, then restart the server."
        )


@mcp.tool()
async def run_product_manager(idea: str) -> dict:
    """Generate requirements from a software idea.

    Args:
        idea: A plain-language description of the software to build.
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.product_manager import product_manager_agent
    return (await product_manager_agent(idea)).model_dump()


@mcp.tool()
async def run_architect(requirements: str = "") -> dict:
    """Design API, DB schema, and folder structure from requirements.

    Args:
        requirements: Requirements text. If empty, reads from project_context.json.
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.architect import architect_agent
    return (await architect_agent(requirements)).model_dump()


@mcp.tool()
async def run_research(topic: str) -> dict:
    """Search the web for docs/libraries and synthesize findings.

    Args:
        topic: The topic to research (e.g. "FastAPI JWT auth patterns").
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.research import research_agent
    return (await research_agent(topic)).model_dump()


@mcp.tool()
async def run_backend_dev(spec: str = "") -> dict:
    """Scaffold a FastAPI backend from project context.

    Args:
        spec: Additional specification. If empty, reads from project_context.json.
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.backend_dev import backend_dev_agent
    return (await backend_dev_agent(spec)).model_dump()


@mcp.tool()
async def run_frontend_dev(spec: str = "") -> dict:
    """Scaffold a Next.js frontend from project context.

    Args:
        spec: Additional specification. If empty, reads from project_context.json.
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.frontend_dev import frontend_dev_agent
    return (await frontend_dev_agent(spec)).model_dump()


@mcp.tool()
async def run_qa_engineer(file_path: str) -> dict:
    """Generate tests for a specific file.

    Args:
        file_path: Absolute or relative path to the file to test.
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.qa_engineer import qa_engineer_agent
    return (await qa_engineer_agent(file_path)).model_dump()


@mcp.tool()
async def run_code_reviewer(file_path: str) -> dict:
    """Review a file for issues, security, and performance.

    Args:
        file_path: Absolute or relative path to the file to review.
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.code_reviewer import code_reviewer_agent
    return (await code_reviewer_agent(file_path)).model_dump()


@mcp.tool()
async def run_documentation(changed_files: list[str]) -> dict:
    """Update README/API docs/CHANGELOG after a change.

    Args:
        changed_files: List of file paths changed in this commit / change set.
    """
    _require_groq_key()
    _import_agents()
    from plugin.agents.documentation import documentation_agent
    return (await documentation_agent(changed_files)).model_dump()


@mcp.tool()
async def run_devteam(idea: str) -> dict:
    """Run the full build pipeline: PM -> Architect -> (Backend+Frontend) -> QA -> Review -> Docs.

    Args:
        idea: The project idea, in plain language. Scaffold files are returned
            under pending_scaffold -- confirm with confirm_scaffold before use.
    """
    _require_groq_key()
    _import_agents()
    from plugin.graph.pipeline import run_devteam_pipeline
    return await run_devteam_pipeline(idea)


@mcp.tool()
async def confirm_scaffold(target: str, files: dict) -> list[str]:
    """Write approved scaffold files into the project under backend/ or frontend/.

    Args:
        target: Which scaffold to confirm -- 'backend' or 'frontend'.
        files: The file map returned by run_backend_dev / run_frontend_dev.
    """
    _import_agents()
    from plugin.graph.pipeline import confirm_scaffold as _confirm
    return _confirm(target, files)


@mcp.tool()
async def get_project_context() -> dict:
    """Return the current project context (requirements, architecture, etc.)."""
    _import_agents()
    from plugin.memory.context import load_context
    return load_context()


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Dev Team MCP plugin server")
    parser.add_argument(
        "--transport", choices=["stdio", "http"], default="stdio",
        help="Transport protocol (default: stdio)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.transport == "http":
        mcp.run(transport="http", host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
