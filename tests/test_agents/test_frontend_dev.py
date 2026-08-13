"""Frontend Developer agent smoke test — mocked LLM file generation."""
from plugin.schemas.outputs import FrontendDevOutput
from plugin.agents.frontend_dev import frontend_dev_agent


RAW_FILES = """### FILE: app/page.tsx
export default function Home() {
  return <h1>Weather</h1>;
}

### FILE: package.json
{"name": "weather-ui", "scripts": {"dev": "next dev"}}
"""


async def test_frontend_dev_returns_valid_output(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.frontend_dev", raw_content=RAW_FILES)
    result = await frontend_dev_agent("a weather CLI frontend")

    assert isinstance(result, FrontendDevOutput)
    assert result.requires_confirmation is True
    assert "frontend/app/page.tsx" in result.files
    assert "frontend/package.json" in result.files


async def test_frontend_dev_prefixes_all_paths(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.frontend_dev", raw_content=RAW_FILES)
    result = await frontend_dev_agent("a weather CLI frontend")

    for path in result.files:
        assert path.startswith("frontend/"), f"expected frontend/ prefix, got {path}"


async def test_frontend_dev_does_not_write_to_disk(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.frontend_dev", raw_content=RAW_FILES)
    await frontend_dev_agent("a weather CLI frontend")

    assert not (tmp_project / "frontend").exists()


async def test_frontend_dev_searches_and_upserts_patterns(
    tmp_project, mock_llm, qdrant_unavailable
):
    mock_llm("plugin.agents.frontend_dev", raw_content=RAW_FILES)
    await frontend_dev_agent("a weather CLI frontend")

    search_collections = [call[0] for call in qdrant_unavailable["search"]]
    upsert_collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "patterns" in search_collections
    assert "patterns" in upsert_collections
