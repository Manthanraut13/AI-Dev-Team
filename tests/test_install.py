"""Platform generator idempotency (plugin.integrations).

Every generator's `install()` must:
- succeed on a second run (idempotent merge, no duplicate MCP entries),
- preserve unrelated keys in the target config,
- write its rules file(s) at the project root.

All config paths are redirected into `tmp_path` via env vars, and Claude Code's
CLI-registration branch is stubbed out so tests never touch the real `claude`
binary or the real `~/.claude.json`.
"""
import json
from pathlib import Path

import pytest

from plugin.integrations import GENERATORS, list_platforms, run_install
from plugin.integrations import claude_code


SERVER_CMD = ["python", "-m", "plugin.server"]


@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Point every platform config path into tmp_path."""
    monkeypatch.setenv("APPDATA", str(tmp_path / "appdata"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    # Never try the real `claude` CLI during tests.
    monkeypatch.setattr(claude_code, "_register_via_cli", lambda cmd: False)
    return tmp_path


def config_path(platform: str, base: Path) -> Path:
    home = base / "home"
    appdata = base / "appdata"
    if platform == "claude-code":
        return home / ".claude.json"
    if platform in ("cline", "roocode"):
        return appdata / "Code" / "User" / "settings.json"
    if platform == "opencode":
        return appdata / "opencode" / "config.json"
    if platform == "codex":
        return home / ".codex" / "config.json"
    raise KeyError(platform)


PLATFORMS = [
    ("claude-code", "CLAUDE.md"),
    ("cline", ".clinerules"),
    ("roocode", ".roorules"),
    ("opencode", None),
    ("codex", None),
]


def test_list_platforms_matches_registry():
    assert list_platforms() == sorted(GENERATORS.keys())


def test_unknown_platform_raises_keyerror(fake_home):
    with pytest.raises(KeyError):
        run_install("nope", fake_home, SERVER_CMD)


@pytest.mark.parametrize("platform,rules_file", PLATFORMS)
def test_generator_is_idempotent(fake_home, platform, rules_file):
    project_root = fake_home / "proj"
    project_root.mkdir(exist_ok=True)

    first = run_install(platform, project_root, SERVER_CMD)
    second = run_install(platform, project_root, SERVER_CMD)

    assert first["registered"] is True
    assert second["registered"] is True
    assert first["written"] and second["written"]

    # Rules file written once, still there after the second run.
    if rules_file:
        assert (project_root / rules_file).exists()
        assert first["written"][0].endswith(rules_file)

    # Config holds exactly one ai-dev-team server entry.
    cfg = json.loads(config_path(platform, fake_home).read_text(encoding="utf-8"))
    if platform == "codex":
        servers = [s for s in cfg.get("mcpServers", []) if s.get("name") == "ai-dev-team"]
        assert len(servers) == 1
    else:
        mcp = _find_mcp_block(cfg, platform)
        assert "ai-dev-team" in mcp
        assert len(mcp) == 1


@pytest.mark.parametrize("platform,rules_file", PLATFORMS)
def test_generator_preserves_unrelated_keys(fake_home, platform, rules_file):
    project_root = fake_home / "proj"
    project_root.mkdir(exist_ok=True)

    cfg = config_path(platform, fake_home)
    cfg.parent.mkdir(parents=True, exist_ok=True)
    unrelated = {"top-level": "keep-me", "nested": {"a": 1}}
    cfg.write_text(json.dumps(unrelated), encoding="utf-8")

    run_install(platform, project_root, SERVER_CMD)

    merged = json.loads(cfg.read_text(encoding="utf-8"))
    assert merged["top-level"] == "keep-me"
    assert merged["nested"] == {"a": 1}


@pytest.mark.parametrize("platform,rules_file", PLATFORMS)
def test_generator_never_duplicates_on_multiple_runs(fake_home, platform, rules_file):
    project_root = fake_home / "proj"
    project_root.mkdir(exist_ok=True)

    for _ in range(3):
        run_install(platform, project_root, SERVER_CMD)

    cfg = json.loads(config_path(platform, fake_home).read_text(encoding="utf-8"))
    if platform == "codex":
        servers = [s for s in cfg.get("mcpServers", []) if s.get("name") == "ai-dev-team"]
        assert len(servers) == 1
    else:
        mcp = _find_mcp_block(cfg, platform)
        assert len(mcp) == 1


def _find_mcp_block(cfg: dict, platform: str) -> dict:
    """Locate the mcpServers dict across the three different key layouts."""
    for key in ("mcpServers", "cline.mcpServers", "roo.cline.mcpServers", "mcp"):
        if key in cfg:
            return cfg[key]
    # claude-code writes under mcpServers; opencode under mcp.
    raise AssertionError(f"no MCP key found in {cfg}")
