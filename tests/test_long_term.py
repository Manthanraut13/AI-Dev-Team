"""Long-term memory graceful degradation (plugin.memory.long_term).

The wrappers must NEVER raise when Qdrant is down — agents keep working with
project_context.json only. We force the failure by monkeypatching
`memory_service._initialize` so the test is deterministic even if a local
Qdrant happens to be running.
"""
import pytest

from plugin.memory import long_term
from plugin.memory.long_term import qdrant_search, qdrant_upsert


@pytest.fixture
def qdrant_down(monkeypatch):
    def _boom():
        raise RuntimeError("Qdrant connection refused (test stub)")

    monkeypatch.setattr(long_term.memory_service, "_initialize", _boom)
    return long_term.memory_service


def test_search_returns_empty_list_when_down(qdrant_down):
    assert qdrant_search("patterns", "query here", limit=3) == []


def test_search_returns_empty_for_unknown_collection(qdrant_down):
    assert qdrant_search("does-not-exist", "query") == []


def test_upsert_returns_none_when_down(qdrant_down):
    assert qdrant_upsert("projects", "content", metadata={"k": "v"}) is None


def test_search_does_not_raise_after_multiple_calls(qdrant_down):
    for _ in range(3):
        assert qdrant_search("architectures", "x") == []


def test_upsert_does_not_raise_after_multiple_calls(qdrant_down):
    for _ in range(3):
        assert qdrant_upsert("references", "x") is None
