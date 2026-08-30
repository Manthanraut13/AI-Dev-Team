"""Security regression tests: path-traversal guards + async retry behaviour.

Run with: pytest tests/test_security.py -v
"""
import os

import pytest


# ---------------------------------------------------------------------------
# safe_join — the shared guard all file writers must route through
# ---------------------------------------------------------------------------
class TestSafeJoin:
    def test_allows_relative_paths(self, tmp_path):
        from plugin.utils.files import safe_join

        out = safe_join(str(tmp_path), "docs/API.md")
        assert out == os.path.join(str(tmp_path), "docs", "API.md")

    def test_rejects_traversal(self, tmp_path):
        from plugin.utils.files import safe_join

        with pytest.raises(PermissionError):
            safe_join(str(tmp_path), "../escape.txt")
        with pytest.raises(PermissionError):
            safe_join(str(tmp_path), "a/../../escape.txt")
        with pytest.raises(PermissionError):
            safe_join(str(tmp_path), "../../../../../../../escape.txt")

    def test_rejects_dotdot_in_subpath(self, tmp_path):
        from plugin.utils.files import safe_join

        with pytest.raises(PermissionError):
            safe_join(str(tmp_path), "a/b/../../../etc/passwd")


# ---------------------------------------------------------------------------
# write_agent_output — central filename guard in tools/output.py
# ---------------------------------------------------------------------------
def test_write_agent_output_rejects_traversal(tmp_project):
    from plugin.tools.output import write_agent_output

    with pytest.raises(PermissionError):
        write_agent_output("research", "../../escape.md", "x")


def test_write_agent_output_absolute_filename_cannot_escape(tmp_project):
    # Absolute paths are normalised inside `.ai-devteam/` — never outside it.
    from plugin.tools.output import write_agent_output

    path = write_agent_output("research", "/etc/passwd", "x")
    root = str(tmp_project / ".ai-devteam")
    assert str(path).startswith(root)


# ---------------------------------------------------------------------------
# research.py — topic-derived filename sanitization
# ---------------------------------------------------------------------------
def test_research_topic_slugifies_to_safe_filename():
    from plugin.utils.files import slugify

    evil = "../../tmp/evil"
    safe = slugify(evil)
    assert ".." not in safe and "/" not in safe and "\\" not in safe
    assert safe  # non-empty


# ---------------------------------------------------------------------------
# documentation.py — LLM-controlled rel_paths cannot escape the project
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_documentation_rejects_traversal_path(tmp_project):
    from types import SimpleNamespace
    from unittest.mock import patch

    from plugin.agents.documentation import documentation_agent

    llm_response = SimpleNamespace(
        content="### FILE: ../../evil.md\n# Injected content\n"
    )

    class Fake:
        async def ainvoke(self, messages, **kwargs):
            return llm_response

    with patch("plugin.agents.documentation.get_llm", return_value=Fake()):
        with pytest.raises(PermissionError):
            await documentation_agent(["app.py"])


# ---------------------------------------------------------------------------
# invoke_with_retry — async, non-blocking, retries rate limits
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invoke_with_retry_retries_rate_limit():
    from plugin.utils.llm import invoke_with_retry

    calls = 0

    class Fake:
        async def ainvoke(self, messages, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise Exception("429 rate limit exceeded")
            return "ok"

    result = await invoke_with_retry(Fake(), ["hi"], max_attempts=3, base_delay=0.01)
    assert result == "ok"
    assert calls == 2


@pytest.mark.asyncio
async def test_invoke_with_retry_uses_ainvoke_when_available():
    from plugin.utils.llm import invoke_with_retry

    used_ainvoke = False

    class Fake:
        async def ainvoke(self, messages, **kwargs):
            nonlocal used_ainvoke
            used_ainvoke = True
            return "value"

    await invoke_with_retry(Fake(), ["hi"])
    assert used_ainvoke


@pytest.mark.asyncio
async def test_invoke_with_retry_raises_on_non_retryable():
    from plugin.utils.llm import invoke_with_retry

    class Fake:
        async def ainvoke(self, messages, **kwargs):
            raise Exception("400 bad request")

    with pytest.raises(Exception, match="400"):
        await invoke_with_retry(Fake(), ["hi"], max_attempts=3, base_delay=0.01)


@pytest.mark.asyncio
async def test_invoke_with_retry_raises_after_max_attempts():
    from plugin.utils.llm import invoke_with_retry

    class Fake:
        async def ainvoke(self, messages, **kwargs):
            raise Exception("429 rate limit exceeded")

    with pytest.raises(Exception, match="429"):
        await invoke_with_retry(Fake(), ["hi"], max_attempts=3, base_delay=0.01)