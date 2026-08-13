"""One sample valid payload per agent schema (Pydantic v2)."""
import pytest

from plugin.schemas.outputs import (
    PMOutput,
    ArchitectOutput,
    ResearchOutput,
    BackendDevOutput,
    FrontendDevOutput,
    QAOutput,
    ReviewOutput,
    DocsOutput,
)


def test_pm_output():
    out = PMOutput(
        project_name="weather-cli",
        summary="A tiny CLI that prints the weather.",
        functional_requirements=["Accept a city argument", "Print temperature"],
        non_functional_requirements=["Works offline"],
        prioritized_tasks=["Parse args", "Fetch weather", "Render output"],
    )
    assert out.project_name == "weather-cli"
    assert len(out.functional_requirements) == 2
    assert len(out.prioritized_tasks) == 3


def test_architect_output():
    out = ArchitectOutput(
        detected_stack=["python", "fastapi"],
        api_endpoints=[{"method": "GET", "path": "/health", "description": "health"}],
        db_schema=[{"table": "users", "columns": [{"name": "id", "type": "int"}]}],
        folder_structure="app/\n",
        tech_decisions=["Use FastAPI"],
    )
    assert out.api_endpoints[0]["method"] == "GET"
    assert out.db_schema[0]["table"] == "users"
    assert out.folder_structure == "app/\n"


def test_research_output():
    out = ResearchOutput(
        topic="tavily",
        summary="A search API.",
        key_findings=["Has a free tier"],
        useful_links=["https://tavily.com"],
        code_examples=["from tavily import TavilyClient"],
    )
    assert out.topic == "tavily"
    assert len(out.useful_links) == 1


def test_backend_dev_output_defaults_requires_confirmation():
    out = BackendDevOutput(
        files={"backend/app/main.py": "print('hi')"},
        summary="2 files generated",
    )
    assert out.requires_confirmation is True
    assert "backend/app/main.py" in out.files


def test_frontend_dev_output_defaults_requires_confirmation():
    out = FrontendDevOutput(
        files={"frontend/package.json": "{}"},
        summary="generated",
    )
    assert out.requires_confirmation is True


def test_qa_output_defaults():
    out = QAOutput(
        file_tested="/tmp/app.py",
        test_file_path="/tmp/test_app.py",
        test_file_content="def test_x(): pass",
    )
    assert out.test_count == 0
    assert out.coverage_notes == ""


def test_review_output_defaults_clean():
    out = ReviewOutput(file_reviewed="/tmp/app.py")
    assert out.severity == "clean"
    assert out.issues == []
    assert out.security_flags == []


def test_docs_output_defaults():
    out = DocsOutput()
    assert out.readme_updated is False
    assert out.api_docs_updated is False
    assert out.changelog_entry == ""
    assert out.files_written == []


@pytest.mark.parametrize(
    "schema",
    [PMOutput, ArchitectOutput, ResearchOutput, BackendDevOutput,
     FrontendDevOutput, QAOutput, ReviewOutput, DocsOutput],
)
def test_all_schemas_accept_model_dump(schema):
    # model_dump must be JSON-serialisable for the MCP tools.
    import json

    instance = schema(
        **{
            "project_name": "x", "summary": "s",
            "functional_requirements": [], "non_functional_requirements": [],
            "prioritized_tasks": [],
            "detected_stack": [], "api_endpoints": [], "db_schema": [],
            "folder_structure": "", "tech_decisions": [],
            "topic": "t", "key_findings": [], "useful_links": [], "code_examples": [],
            "files": {}, "requires_confirmation": True,
            "file_tested": "a.py", "test_file_path": "test_a.py", "test_file_content": "",
            "file_reviewed": "a.py",
        }
    )
    json.dumps(instance.model_dump())
