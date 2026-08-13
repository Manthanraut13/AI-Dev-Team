"""Filesystem conventions (plugin.paths)."""
from pathlib import Path

import pytest

from plugin import paths


def test_project_root_is_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert paths.project_root() == tmp_path


def test_ai_devteam_dir_lives_under_project_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert paths.ai_devteam_dir() == tmp_path / ".ai-devteam"


def test_ensure_dirs_creates_full_tree(tmp_project):
    tree = paths.ensure_dirs()
    expected = [
        "root",
        "logs",
        "reviews",
        "tests",
        "research",
        "docs",
    ]
    for key in expected:
        assert tree[key].is_dir(), f"missing {key} -> {tree[key]}"


def test_ensure_dirs_is_idempotent(tmp_project):
    first = paths.ensure_dirs()
    second = paths.ensure_dirs()
    assert first == second
    # Re-running must not raise and must return the same map.
    assert (tmp_project / ".ai-devteam" / "logs").is_dir()


def test_context_config_log_paths(tmp_project):
    assert paths.context_file() == tmp_project / ".ai-devteam" / "project_context.json"
    assert paths.config_file() == tmp_project / ".ai-devteam" / "config.toml"
    assert paths.log_file() == tmp_project / ".ai-devteam" / "logs" / "agent_activity.log"


def test_ensure_dirs_creates_parent_automatically(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    log_dir = paths.log_file().parent
    assert not log_dir.exists()
    paths.ensure_dirs()
    assert log_dir.exists()
