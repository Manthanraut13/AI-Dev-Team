"""Research agent smoke test — mocked web search + crawl + LLM."""
from plugin.schemas.outputs import ResearchOutput
from plugin.agents.research import research_agent


RESEARCH_PAYLOAD = {
    "topic": "tavily api",
    "summary": "Tavily is a search API for LLMs.",
    "key_findings": ["Has a free tier", "Returns clean results"],
    "useful_links": ["https://tavily.com"],
    "code_examples": ["from tavily import TavilyClient"],
}


async def test_research_returns_valid_output(
    tmp_project, mock_llm, qdrant_unavailable, monkeypatch
):
    monkeypatch.setattr(
        "plugin.agents.research.web_search",
        lambda q, max_results=5: [
            {"title": "Tavily", "url": "https://tavily.com", "content": "a search api"}
        ],
    )
    monkeypatch.setattr(
        "plugin.agents.research.firecrawl_scrape", lambda url, max_length=3000: "scraped body"
    )
    mock_llm("plugin.agents.research", structured_payload=RESEARCH_PAYLOAD)

    result = await research_agent("tavily api")

    assert isinstance(result, ResearchOutput)
    assert result.topic == "tavily api"
    assert "free tier" in " ".join(result.key_findings)


async def test_research_degrades_without_search_keys(
    tmp_project, mock_llm, qdrant_unavailable, monkeypatch
):
    # No keys configured -> web_search returns [], firecrawl returns None,
    # and the agent still produces a ResearchOutput from general knowledge.
    monkeypatch.setattr("plugin.agents.research.web_search", lambda q, max_results=5: [])
    monkeypatch.setattr(
        "plugin.agents.research.firecrawl_scrape", lambda url, max_length=3000: None
    )
    mock_llm("plugin.agents.research", structured_payload=RESEARCH_PAYLOAD)

    result = await research_agent("tavily api")
    assert isinstance(result, ResearchOutput)


async def test_research_writes_markdown(tmp_project, mock_llm, qdrant_unavailable, monkeypatch):
    monkeypatch.setattr("plugin.agents.research.web_search", lambda q, max_results=5: [])
    monkeypatch.setattr(
        "plugin.agents.research.firecrawl_scrape", lambda url, max_length=3000: None
    )
    mock_llm("plugin.agents.research", structured_payload=RESEARCH_PAYLOAD)

    await research_agent("tavily api")

    md = (tmp_project / ".ai-devteam" / "research" / "tavily_api.md").read_text(encoding="utf-8")
    assert "# Research — tavily api" in md
    assert "https://tavily.com" in md


async def test_research_upserts_to_references(tmp_project, mock_llm, qdrant_unavailable, monkeypatch):
    monkeypatch.setattr("plugin.agents.research.web_search", lambda q, max_results=5: [])
    monkeypatch.setattr(
        "plugin.agents.research.firecrawl_scrape", lambda url, max_length=3000: None
    )
    mock_llm("plugin.agents.research", structured_payload=RESEARCH_PAYLOAD)

    await research_agent("tavily api")

    collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "references" in collections
