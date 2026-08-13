"""MCP server registry — assert all 11 tools are registered.

Imports `plugin.server` (which builds the FastMCP `mcp` object at import time)
and inspects its tool registry asynchronously via `mcp.list_tools()`.
Skips cleanly if `fastmcp` isn't installed.
"""
import pytest

fastmcp = pytest.importorskip("fastmcp", reason="fastmcp not installed — server test skipped")

from plugin import server  # noqa: E402  (after importorskip)

EXPECTED_TOOLS = {
    "run_product_manager",
    "run_architect",
    "run_research",
    "run_backend_dev",
    "run_frontend_dev",
    "run_qa_engineer",
    "run_code_reviewer",
    "run_documentation",
    "run_devteam",
    "confirm_scaffold",
    "get_project_context",
}


async def test_all_11_tools_registered():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    missing = EXPECTED_TOOLS - names
    assert not missing, f"Missing registered tools: {sorted(missing)}"


async def test_no_unexpected_missing_in_expected():
    tools = await server.mcp.list_tools()
    names = {t.name for t in tools}
    assert len(names) >= 11
