"""Product Manager agent smoke test — mocked LLM, no network."""
import json

from plugin.schemas.outputs import PMOutput
from plugin.agents.product_manager import product_manager_agent


PM_PAYLOAD = {
    "project_name": "weather-cli",
    "summary": "A tiny CLI that prints the weather for a city.",
    "functional_requirements": [
        "Accept a city argument",
        "Print current temperature",
        "Show forecast for the next 3 days",
    ],
    "non_functional_requirements": ["Runs offline", "Fast startup"],
    "prioritized_tasks": ["Parse CLI args", "Call weather API", "Render output"],
}


async def test_pm_returns_valid_output(tmp_project, mock_llm, qdrant_unavailable):
    fake = mock_llm("plugin.agents.product_manager", structured_payload=PM_PAYLOAD)
    result = await product_manager_agent("a tiny CLI that prints the weather")

    assert isinstance(result, PMOutput)
    assert result.project_name == "weather-cli"
    assert len(result.functional_requirements) == 3
    assert fake.invoke_count == 1


async def test_pm_writes_requirements_md(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.product_manager", structured_payload=PM_PAYLOAD)
    await product_manager_agent("a tiny CLI that prints the weather")

    md = (tmp_project / ".ai-devteam" / "requirements.md").read_text(encoding="utf-8")
    assert "# Requirements — weather-cli" in md
    assert "Accept a city argument" in md
    assert "## Prioritized Tasks" in md


async def test_pm_updates_project_context(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.product_manager", structured_payload=PM_PAYLOAD)
    await product_manager_agent("a tiny CLI that prints the weather")

    ctx = json.loads(
        (tmp_project / ".ai-devteam" / "project_context.json").read_text(encoding="utf-8")
    )
    assert ctx["project_name"] == "weather-cli"
    assert ctx["requirements"][0] == "Accept a city argument"
    assert ctx["decisions"] == PM_PAYLOAD["prioritized_tasks"]


async def test_pm_upserts_to_projects_collection(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.product_manager", structured_payload=PM_PAYLOAD)
    await product_manager_agent("a tiny CLI that prints the weather")

    collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "projects" in collections
