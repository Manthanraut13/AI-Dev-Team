"""QA Engineer agent smoke test — real source file, mocked LLM."""
import pytest

from plugin.schemas.outputs import QAOutput
from plugin.agents.qa_engineer import qa_engineer_agent


SRC = """def add(a, b):
    return a + b


def greet(name):
    return f"hello {name}"
"""

TEST_FILE = """### FILE: test_math.py
def test_add():
    assert add(1, 2) == 3


def test_greet():
    assert greet("bob") == "hello bob"
"""


def _write_source(tmp_project):
    src = tmp_project / "app.py"
    src.write_text(SRC, encoding="utf-8")
    return src


async def test_qa_returns_valid_output(tmp_project, mock_llm, qdrant_unavailable):
    src = _write_source(tmp_project)
    mock_llm("plugin.agents.qa_engineer", raw_content=TEST_FILE)
    result = await qa_engineer_agent(str(src))

    assert isinstance(result, QAOutput)
    assert result.file_tested == str(src)
    assert result.test_count == 2


async def test_qa_writes_test_under_ai_devteam(tmp_project, mock_llm, qdrant_unavailable):
    src = _write_source(tmp_project)
    mock_llm("plugin.agents.qa_engineer", raw_content=TEST_FILE)
    result = await qa_engineer_agent(str(src))

    assert str(result.test_file_path).startswith(str(tmp_project / ".ai-devteam" / "tests"))
    assert result.test_file_path.endswith("test_math.py")


async def test_qa_upserts_to_patterns(tmp_project, mock_llm, qdrant_unavailable):
    src = _write_source(tmp_project)
    mock_llm("plugin.agents.qa_engineer", raw_content=TEST_FILE)
    await qa_engineer_agent(str(src))

    collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "patterns" in collections


async def test_qa_raises_for_missing_file(tmp_project, mock_llm, qdrant_unavailable):
    with pytest.raises(FileNotFoundError):
        await qa_engineer_agent(str(tmp_project / "nope.py"))
