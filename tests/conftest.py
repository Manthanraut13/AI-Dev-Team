"""Shared fixtures for the AI Dev Team test suite.

Three fixtures cover 95% of the tests:

- `tmp_project`       — chdir into a fresh temp dir with `.ai-devteam/` created,
                        so no test ever writes into the real repo.
- `mock_llm`          — replaces each agent module's `get_llm` with a FakeLLM
                        that returns a configurable payload, so agents never hit
                        the network (no Groq key needed).
- `qdrant_unavailable`— replaces `qdrant_search`/`qdrant_upsert` in every agent
                        module with recording stubs (return []/None), so agents
                        don't need a live Qdrant. Also asserts the memory wiring
                        by capturing the upsert/search calls.

Agents import their collaborators (`get_llm`, `qdrant_search`, ...) *by name*
(`from plugin.utils.llm import get_llm`), so patching happens on the agent module
itself — not on the source module — or the patch would be a no-op.
"""
from __future__ import annotations

import importlib
from pathlib import Path

import pytest


# Every agent module that pulls in get_llm / qdrant_* by name.
AGENT_MODULES = [
    "plugin.agents.product_manager",
    "plugin.agents.architect",
    "plugin.agents.research",
    "plugin.agents.backend_dev",
    "plugin.agents.frontend_dev",
    "plugin.agents.qa_engineer",
    "plugin.agents.code_reviewer",
    "plugin.agents.documentation",
]


@pytest.fixture
def tmp_project(tmp_path, monkeypatch):
    """Fresh working dir with `.ai-devteam/` pre-created; CWD switched into it."""
    monkeypatch.chdir(tmp_path)
    from plugin.paths import ensure_dirs

    ensure_dirs()
    return tmp_path


# --------------------------------------------------------------------------
# Mock LLM
# --------------------------------------------------------------------------
class FakeLLM:
    """Drop-in ChatGroq stand-in.

    - Structured agents call `llm.with_structured_output(Schema).invoke(...)`;
      `structured_payload` (a dict, or callable taking the Schema) is used to
      build a Schema instance.
    - File agents call `llm.invoke(...)` and read `response.content`;
      `raw_content` is returned wrapped in an object with `.content`.
    """

    def __init__(self, structured_payload=None, raw_content=""):
        self._payload = structured_payload
        self._raw = raw_content
        self.schema = None
        self.invoke_count = 0

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages, **kwargs):
        self.invoke_count += 1
        if self.schema is not None:
            payload = self._payload(self.schema) if callable(self._payload) else self._payload
            return self.schema(**payload)
        return _ContentResponse(self._raw)

    async def ainvoke(self, messages, **kwargs):
        return self.invoke(messages, **kwargs)


class _ContentResponse:
    def __init__(self, content):
        self.content = content


@pytest.fixture
def mock_llm(monkeypatch):
    """Install a FakeLLM into one agent module's `get_llm`.

    Usage:
        fake = mock_llm("plugin.agents.product_manager",
                        structured_payload={...})
        fake = mock_llm("plugin.agents.backend_dev",
                        raw_content="### FILE: app/main.py\\n...")
    """

    def _install(module_path: str, **llm_kwargs) -> FakeLLM:
        module = importlib.import_module(module_path)
        fake = FakeLLM(**llm_kwargs)
        monkeypatch.setattr(module, "get_llm", lambda *a, **k: fake)
        return fake

    return _install


# --------------------------------------------------------------------------
# Mock Qdrant (graceful-degradation path)
# --------------------------------------------------------------------------
@pytest.fixture
def qdrant_unavailable(monkeypatch):
    """Stub qdrant_search/qdrant_upsert in every agent module; record the calls.

    Returns `{"search": [...], "upsert": [...]}` lists of call tuples so tests
    can assert the memory wiring ran.
    """
    calls = {"search": [], "upsert": []}

    def fake_search(collection, query, limit=3):
        calls["search"].append((collection, query, limit))
        return []

    def fake_upsert(collection, content, metadata=None):
        calls["upsert"].append((collection, content, metadata))
        return None

    for mod_name in AGENT_MODULES:
        module = importlib.import_module(mod_name)
        monkeypatch.setattr(module, "qdrant_search", fake_search, raising=False)
        monkeypatch.setattr(module, "qdrant_upsert", fake_upsert, raising=False)

    return calls
