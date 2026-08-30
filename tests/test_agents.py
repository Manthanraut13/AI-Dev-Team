"""Unit tests for AI Dev Team agents with mocked LLM."""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
import os


@pytest.fixture
def mock_llm():
    """Create a mock LLM that returns structured output."""
    mock = MagicMock()
    mock.with_structured_output.return_value = mock
    mock.invoke = MagicMock()

    # `invoke_with_retry` prefers `ainvoke`; keep both in sync so tests exercise
    # the same async path production uses.
    async def _ainvoke(messages, **kwargs):
        return mock.invoke(messages, **kwargs)

    mock.ainvoke = _ainvoke
    return mock


@pytest.fixture(autouse=True)
def temp_ai_devteam(tmp_path, monkeypatch):
    """Create a temp .ai-devteam directory for each test, and chdir into tmp_path.

    `monkeypatch.chdir` keeps every agent's CWD-relative writes (e.g. the
    documentation agent writing README.md at the project root) inside the temp
    dir — otherwise tests silently write into the real repo.
    """
    ai_dir = tmp_path / ".ai-devteam"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "logs").mkdir()
    (ai_dir / "tests").mkdir()
    (ai_dir / "reviews").mkdir()
    (ai_dir / "research").mkdir()
    monkeypatch.chdir(tmp_path)

    # Set up paths - patch project_root so ai_devteam_dir() returns our temp dir
    import plugin.paths as paths_module

    def mock_project_root():
        return tmp_path

    monkeypatch.setattr(paths_module, "project_root", mock_project_root)

    # Also patch the already-imported functions in output module
    import plugin.tools.output as output_module
    monkeypatch.setattr(output_module, "ai_devteam_dir", lambda: tmp_path / ".ai-devteam")

    yield ai_dir


class TestProductManagerAgent:
    @pytest.mark.asyncio
    async def test_product_manager_returns_valid_output(self, mock_llm, temp_ai_devteam):
        from plugin.schemas.outputs import PMOutput
        from plugin.agents.product_manager import product_manager_agent

        # Mock the structured output
        expected = PMOutput(
            project_name="Test Project",
            summary="A test project",
            functional_requirements=["Req 1", "Req 2"],
            non_functional_requirements=["NFR 1"],
            prioritized_tasks=["Task 1", "Task 2"],
        )
        mock_llm.invoke.return_value = expected

        with patch("plugin.agents.product_manager.get_llm", return_value=mock_llm):
            result = await product_manager_agent("Build a test app")

        assert isinstance(result, PMOutput)
        assert result.project_name == "Test Project"
        assert len(result.functional_requirements) == 2
        # Check artifacts written (product_manager writes to .ai-devteam/ root, not subdir)
        req_file = temp_ai_devteam / "requirements.md"
        assert req_file.exists()


class TestArchitectAgent:
    @pytest.mark.asyncio
    async def test_architect_requires_requirements(self, mock_llm, temp_ai_devteam):
        from plugin.agents.architect import architect_agent

        with patch("plugin.agents.architect.get_llm", return_value=mock_llm):
            with pytest.raises(ValueError, match="needs requirements"):
                await architect_agent([])

    @pytest.mark.asyncio
    async def test_architect_returns_valid_output(self, mock_llm, temp_ai_devteam):
        from plugin.schemas.outputs import ArchitectOutput
        from plugin.agents.architect import architect_agent

        expected = ArchitectOutput(
            detected_stack=["Python", "FastAPI"],
            api_endpoints=[{"method": "GET", "path": "/health", "description": "Health check"}],
            db_schema=[{"table": "users", "columns": [{"name": "id", "type": "int"}]}],
            folder_structure="backend/\n  app/\n    main.py",
            tech_decisions=["Use FastAPI for API"],
        )
        mock_llm.invoke.return_value = expected

        with patch("plugin.agents.architect.get_llm", return_value=mock_llm):
            result = await architect_agent(["Req 1", "Req 2"])

        assert isinstance(result, ArchitectOutput)
        assert len(result.api_endpoints) == 1


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_research_returns_valid_output(self, mock_llm, temp_ai_devteam):
        from plugin.schemas.outputs import ResearchOutput
        from plugin.agents.research import research_agent

        expected = ResearchOutput(
            topic="FastAPI",
            summary="FastAPI is a modern web framework",
            key_findings=["Fast", "Async", "Type hints"],
            useful_links=["https://fastapi.tiangolo.com"],
            code_examples=["app = FastAPI()"],
        )
        mock_llm.invoke.return_value = expected

        with patch("plugin.agents.research.get_llm", return_value=mock_llm):
            with patch("plugin.agents.research.web_search", return_value=[]):
                with patch("plugin.agents.research.firecrawl_scrape", return_value=None):
                    result = await research_agent("FastAPI")

        assert isinstance(result, ResearchOutput)
        assert result.topic == "FastAPI"


class TestBackendDevAgent:
    @pytest.mark.asyncio
    async def test_backend_dev_returns_valid_output(self, mock_llm, temp_ai_devteam):
        from plugin.schemas.outputs import BackendDevOutput
        from plugin.agents.backend_dev import backend_dev_agent

        # Mock raw response with content attribute that parse_files expects
        # Note: agent prefixes "backend/" to all paths, so mock uses app/main.py
        mock_response = MagicMock()
        mock_response.content = """### FILE: app/main.py
from fastapi import FastAPI
app = FastAPI()

### FILE: requirements.txt
fastapi
uvicorn"""
        mock_llm.invoke.return_value = mock_response

        with patch("plugin.agents.backend_dev.get_llm", return_value=mock_llm):
            result = await backend_dev_agent("Simple API")

        assert isinstance(result, BackendDevOutput)
        assert result.requires_confirmation is True
        assert len(result.files) == 2
        assert "backend/app/main.py" in result.files


class TestFrontendDevAgent:
    @pytest.mark.asyncio
    async def test_frontend_dev_returns_valid_output(self, mock_llm, temp_ai_devteam):
        from plugin.schemas.outputs import FrontendDevOutput
        from plugin.agents.frontend_dev import frontend_dev_agent

        mock_response = MagicMock()
        mock_response.content = """### FILE: frontend/package.json
{"name": "test"}

### FILE: frontend/app/page.tsx
export default function Page() { return <div>Hi</div> }"""
        mock_llm.invoke.return_value = mock_response

        with patch("plugin.agents.frontend_dev.get_llm", return_value=mock_llm):
            result = await frontend_dev_agent("Simple UI")

        assert isinstance(result, FrontendDevOutput)
        assert result.requires_confirmation is True
        assert len(result.files) == 2


class TestQAEngineerAgent:
    @pytest.mark.asyncio
    async def test_qa_engineer_creates_test_file(self, mock_llm, temp_ai_devteam, tmp_path):
        from plugin.schemas.outputs import QAOutput
        from plugin.agents.qa_engineer import qa_engineer_agent

        # Create a source file to test
        src_file = tmp_path / "app.py"
        src_file.write_text("def hello(): return 'world'")

        mock_response = MagicMock()
        mock_response.content = """### FILE: test_app.py
def test_hello():
    assert hello() == 'world'"""
        mock_llm.invoke.return_value = mock_response

        with patch("plugin.agents.qa_engineer.get_llm", return_value=mock_llm):
            result = await qa_engineer_agent(str(src_file))

        assert isinstance(result, QAOutput)
        assert result.test_count >= 1


class TestCodeReviewerAgent:
    @pytest.mark.asyncio
    async def test_code_reviewer_returns_valid_output(self, mock_llm, temp_ai_devteam, tmp_path):
        from plugin.schemas.outputs import ReviewOutput
        from plugin.agents.code_reviewer import code_reviewer_agent

        # Create a source file
        src_file = tmp_path / "app.py"
        src_file.write_text("def hello(): return 'world'")

        # Mock raw response with content in delimited review format
        mock_response = MagicMock()
        mock_response.content = """### ISSUES
- Missing type hints

### SUGGESTIONS
- Add type hints

### SECURITY
None

### PERFORMANCE
None"""
        mock_llm.invoke.return_value = mock_response

        with patch("plugin.agents.code_reviewer.get_llm", return_value=mock_llm):
            result = await code_reviewer_agent(str(src_file))

        assert isinstance(result, ReviewOutput)
        assert result.severity == "minor"
        assert len(result.issues) == 1
        # Check review file written
        review_file = temp_ai_devteam / "reviews" / "app.md"
        assert review_file.exists()


class TestDocumentationAgent:
    @pytest.mark.asyncio
    async def test_documentation_returns_valid_output(self, mock_llm, temp_ai_devteam, tmp_path):
        from plugin.schemas.outputs import DocsOutput
        from plugin.agents.documentation import documentation_agent

        # Mock raw response with content in FILE: format that parse_files expects
        mock_response = MagicMock()
        mock_response.content = """### FILE: README.md
# Test Project
A simple test project.

### FILE: docs/API.md
# API Reference
Endpoints documented here.

### FILE: CHANGELOG.md
## [2026-08-16] - Initial commit
### Changed
- Added tests"""
        mock_llm.invoke.return_value = mock_response

        with patch("plugin.agents.documentation.get_llm", return_value=mock_llm):
            result = await documentation_agent(["app.py"])

        assert isinstance(result, DocsOutput)
        assert result.readme_updated is True
        assert result.api_docs_updated is True
        assert len(result.files_written) == 3