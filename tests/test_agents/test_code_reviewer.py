"""Code Reviewer agent smoke test — real source file, mocked LLM."""
import pytest

from plugin.schemas.outputs import ReviewOutput
from plugin.agents.code_reviewer import code_reviewer_agent


SRC = """def load(path):
    data = open(path).read()
    return data
"""

REVIEW_TEXT = """### ISSUES
- Unclosed file handle in load()
- No error handling for missing path

### SUGGESTIONS
- Use a context manager

### SECURITY
- Path traversal not validated

### PERFORMANCE
- None
"""


def _write_source(tmp_project):
    src = tmp_project / "app.py"
    src.write_text(SRC, encoding="utf-8")
    return src


async def test_reviewer_returns_valid_output(tmp_project, mock_llm, qdrant_unavailable):
    src = _write_source(tmp_project)
    mock_llm("plugin.agents.code_reviewer", raw_content=REVIEW_TEXT)
    result = await code_reviewer_agent(str(src))

    assert isinstance(result, ReviewOutput)
    assert result.file_reviewed == str(src)
    assert len(result.issues) == 2
    assert result.severity == "critical"  # security flag present


async def test_reviewer_writes_markdown(tmp_project, mock_llm, qdrant_unavailable):
    src = _write_source(tmp_project)
    mock_llm("plugin.agents.code_reviewer", raw_content=REVIEW_TEXT)
    await code_reviewer_agent(str(src))

    md = (tmp_project / ".ai-devteam" / "reviews" / "app.md").read_text(encoding="utf-8")
    assert "Severity: **critical**" in md
    assert "Unclosed file handle" in md


async def test_reviewer_upserts_to_patterns(tmp_project, mock_llm, qdrant_unavailable):
    src = _write_source(tmp_project)
    mock_llm("plugin.agents.code_reviewer", raw_content=REVIEW_TEXT)
    await code_reviewer_agent(str(src))

    collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "patterns" in collections


async def test_reviewer_handles_clean_file(tmp_project, mock_llm, qdrant_unavailable):
    src = _write_source(tmp_project)
    mock_llm("plugin.agents.code_reviewer", raw_content="### ISSUES\nNone\n\n### SUGGESTIONS\nNone\n### SECURITY\nNone\n### PERFORMANCE\nNone\n")
    result = await code_reviewer_agent(str(src))

    assert result.severity == "clean"
    assert result.issues == []


async def test_reviewer_raises_for_missing_file(tmp_project, mock_llm, qdrant_unavailable):
    with pytest.raises(FileNotFoundError):
        await code_reviewer_agent(str(tmp_project / "nope.py"))
