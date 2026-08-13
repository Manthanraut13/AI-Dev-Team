"""Architect agent smoke test — mocked LLM + mocked past architectures."""
import json

import pytest

from plugin.schemas.outputs import ArchitectOutput
from plugin.agents.architect import architect_agent


REQS = ["Accept a city argument", "Print current temperature"]

ARCH_PAYLOAD = {
    "detected_stack": ["python", "fastapi"],
    "api_endpoints": [
        {"method": "GET", "path": "/weather/{city}", "description": "current weather"}
    ],
    "db_schema": [{"table": "cities", "columns": [{"name": "name", "type": "str"}]}],
    "folder_structure": "app/\n  api/\n  models.py\n",
    "tech_decisions": ["FastAPI for its async support"],
}


async def test_architect_returns_valid_output(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.architect", structured_payload=ARCH_PAYLOAD)
    result = await architect_agent(REQS)

    assert isinstance(result, ArchitectOutput)
    assert result.detected_stack == ["python", "fastapi"]
    assert result.api_endpoints[0]["path"] == "/weather/{city}"


async def test_architect_writes_architecture_md(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.architect", structured_payload=ARCH_PAYLOAD)
    await architect_agent(REQS)

    md = (tmp_project / ".ai-devteam" / "architecture.md").read_text(encoding="utf-8")
    assert "## API Endpoints" in md
    assert "/weather/{city}" in md
    assert "## Database Schema" in md


async def test_architect_updates_context(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.architect", structured_payload=ARCH_PAYLOAD)
    await architect_agent(REQS)

    ctx = json.loads(
        (tmp_project / ".ai-devteam" / "project_context.json").read_text(encoding="utf-8")
    )
    assert ctx["architecture"]["api_endpoints"][0]["path"] == "/weather/{city}"
    assert ctx["detected_stack"] == ["python", "fastapi"]


async def test_architect_searches_and_upserts_qdrant(
    tmp_project, mock_llm, qdrant_unavailable
):
    mock_llm("plugin.agents.architect", structured_payload=ARCH_PAYLOAD)
    await architect_agent(REQS)

    search_collections = [call[0] for call in qdrant_unavailable["search"]]
    upsert_collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "architectures" in search_collections
    assert "architectures" in upsert_collections


async def test_architect_raises_without_requirements(
    tmp_project, mock_llm, qdrant_unavailable
):
    from plugin.memory.context import reset_context

    reset_context()
    with pytest.raises(ValueError):
        await architect_agent()
