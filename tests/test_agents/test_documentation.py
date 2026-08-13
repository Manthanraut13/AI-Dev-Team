"""Documentation agent smoke test — mocked LLM, no git hook."""
from plugin.schemas.outputs import DocsOutput
from plugin.agents.documentation import documentation_agent


DOCS_FILES = """### FILE: README.md
# Weather CLI

A tiny CLI that prints the weather.

## Quick Start

    pip install -r requirements.txt

### FILE: docs/API.md
# API Reference

### GET /weather/{city}

Returns the current weather for the given city.

### FILE: CHANGELOG.md
## 2026-08-10 - Initial release

### Changed
- Added weather CLI MVP
"""


async def test_docs_returns_valid_output(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.documentation", raw_content=DOCS_FILES)
    result = await documentation_agent(["app.py", "requirements.txt"])

    assert isinstance(result, DocsOutput)
    assert result.readme_updated is True
    assert result.api_docs_updated is True
    assert result.changelog_entry != ""


async def test_docs_writes_readme(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.documentation", raw_content=DOCS_FILES)
    await documentation_agent(["app.py"])

    assert (tmp_project / "README.md").exists()
    content = (tmp_project / "README.md").read_text(encoding="utf-8")
    assert "Weather CLI" in content


async def test_docs_writes_api_md(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.documentation", raw_content=DOCS_FILES)
    await documentation_agent(["app.py"])

    assert (tmp_project / "docs" / "API.md").exists()
    content = (tmp_project / "docs" / "API.md").read_text(encoding="utf-8")
    assert "GET /weather/{city}" in content


async def test_docs_writes_changelog(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.documentation", raw_content=DOCS_FILES)
    await documentation_agent(["app.py"])

    assert (tmp_project / "CHANGELOG.md").exists()
    content = (tmp_project / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "Initial release" in content


async def test_docs_upserts_to_references(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.documentation", raw_content=DOCS_FILES)
    await documentation_agent(["app.py"])

    collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "references" in collections
