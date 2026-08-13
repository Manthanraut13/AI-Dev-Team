"""Backend Developer agent smoke test — mocked LLM file generation."""
from plugin.schemas.outputs import BackendDevOutput
from plugin.agents.backend_dev import backend_dev_agent


RAW_FILES = """### FILE: app/models.py
from sqlalchemy.orm import Mapped, mapped_column

class User(Base):
    id: Mapped[int]

### FILE: app/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"ok": True}
"""


async def test_backend_dev_returns_valid_output(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.backend_dev", raw_content=RAW_FILES)
    result = await backend_dev_agent("a weather CLI backend")

    assert isinstance(result, BackendDevOutput)
    assert result.requires_confirmation is True
    assert "backend/app/models.py" in result.files
    assert "backend/app/main.py" in result.files


async def test_backend_dev_prefixes_all_paths(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.backend_dev", raw_content=RAW_FILES)
    result = await backend_dev_agent("a weather CLI backend")

    for path in result.files:
        assert path.startswith("backend/"), f"expected backend/ prefix, got {path}"


async def test_backend_dev_does_not_write_to_disk(tmp_project, mock_llm, qdrant_unavailable):
    mock_llm("plugin.agents.backend_dev", raw_content=RAW_FILES)
    await backend_dev_agent("a weather CLI backend")

    # requires_confirmation=True means no scaffold files on disk.
    assert not (tmp_project / "backend").exists()


async def test_backend_dev_searches_and_upserts_patterns(
    tmp_project, mock_llm, qdrant_unavailable
):
    mock_llm("plugin.agents.backend_dev", raw_content=RAW_FILES)
    await backend_dev_agent("a weather CLI backend")

    search_collections = [call[0] for call in qdrant_unavailable["search"]]
    upsert_collections = [call[0] for call in qdrant_unavailable["upsert"]]
    assert "patterns" in search_collections
    assert "patterns" in upsert_collections
