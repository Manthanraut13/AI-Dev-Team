"""write_agent_output + log_activity behaviour."""
import json
from pathlib import Path

import pytest

from plugin.tools.output import write_agent_output, log_activity
from plugin.tools.output import AGENT_DIRS


@pytest.mark.parametrize(
    "agent_name,subdir",
    [
        ("product_manager", ""),   # requirements.md at .ai-devteam root
        ("architect", ""),         # architecture.md at .ai-devteam root
        ("research", "research"),
        ("code_reviewer", "reviews"),
        ("qa_engineer", "tests"),
        ("documentation", "docs"),
    ],
)
def test_write_agent_output_lands_in_expected_subdir(tmp_project, agent_name, subdir):
    path = write_agent_output(agent_name, "out.md", "# hello")
    expected_dir = tmp_project / ".ai-devteam" / subdir if subdir else tmp_project / ".ai-devteam"
    assert path.parent == expected_dir
    assert path.read_text(encoding="utf-8") == "# hello"


def test_write_agent_output_unknown_agent_gets_own_subdir(tmp_project):
    path = write_agent_output("mystery_agent", "x.txt", "hi")
    assert path.parent == tmp_project / ".ai-devteam" / "mystery_agent"
    assert path.exists()


def test_write_agent_output_creates_nested_parents(tmp_project):
    path = write_agent_output("qa_engineer", "deep/nested/test_x.py", "content")
    assert path.parent == tmp_project / ".ai-devteam" / "tests" / "deep" / "nested"
    assert path.exists()


def test_agent_dirs_map_covers_documented_agents():
    # Every agent name in AGENT_DIRS is a known value (no accidental renames).
    assert set(AGENT_DIRS) == {
        "product_manager",
        "architect",
        "research",
        "code_reviewer",
        "qa_engineer",
        "documentation",
    }


def test_log_activity_writes_one_json_line(tmp_project):
    log_activity("product_manager", "run", {"idea": "hello", "n": 3})
    path = tmp_project / ".ai-devteam" / "logs" / "agent_activity.log"
    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["agent"] == "product_manager"
    assert entry["event"] == "run"
    assert entry["idea"] == "hello"
    assert entry["n"] == 3
    assert "timestamp" in entry


def test_log_activity_omits_details_when_none(tmp_project):
    log_activity("architect", "start")
    lines = (tmp_project / ".ai-devteam" / "logs" / "agent_activity.log").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    entry = json.loads(lines[0])
    assert entry == {"timestamp": entry["timestamp"], "agent": "architect", "event": "start"}


def test_log_activity_appends_multiple_entries(tmp_project):
    log_activity("a", "one")
    log_activity("b", "two")
    lines = (tmp_project / ".ai-devteam" / "logs" / "agent_activity.log").read_text(
        encoding="utf-8"
    ).strip().splitlines()
    assert len(lines) == 2
