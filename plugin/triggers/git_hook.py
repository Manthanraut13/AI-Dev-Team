"""Post-commit hook — runs the Documentation agent after every git commit.

Installs a `.git/hooks/post-commit` script that collects the changed files via
`git diff --name-only` and invokes the Documentation agent, which diff-patches
README/docs/CHANGELOG. Uses subprocess (not GitPython) so the hook works even
when GitPython isn't installed.
"""
from __future__ import annotations

import asyncio
import logging
import subprocess
from pathlib import Path

from plugin.paths import project_root
from plugin.tools.output import log_activity

logger = logging.getLogger(__name__)

HOOK_NAME = "post-commit"

HOOK_TEMPLATE = """#!/bin/sh
# AI Dev Team post-commit hook — auto-updates docs after each commit.
# Installed by plugin/triggers/git_hook.py. Uninstall: delete this file.
cd "$(git rev-parse --show-toplevel)" || exit 0
exec python -m plugin.triggers.git_hook run >/dev/null 2>&1
"""


def git_root() -> Path | None:
    """Return the repo root if CWD is inside a git repo, else None."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        return Path(out.stdout.strip())
    except Exception:
        return None


def changed_files_since_last_commit() -> list[str]:
    """Files changed in the last commit (`git diff --name-only HEAD~1 HEAD`)."""
    try:
        out = subprocess.run(
            ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        return [l for l in out.stdout.splitlines() if l.strip()]
    except Exception:
        try:
            out = subprocess.run(
                ["git", "diff", "--cached", "--name-only"],
                capture_output=True, text=True, check=True, timeout=10,
            )
            return [l for l in out.stdout.splitlines() if l.strip()]
        except Exception:
            return []


def install_hook() -> Path | None:
    """Install the post-commit hook into the repo's `.git/hooks/`. Returns path or None."""
    root = git_root()
    if root is None:
        logger.warning("Not inside a git repo — post-commit hook not installed.")
        return None
    hooks_dir = root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / HOOK_NAME
    hook_path.write_text(HOOK_TEMPLATE, encoding="utf-8")
    # Make executable (POSIX). On Windows this is a no-op but harmless.
    try:
        hook_path.chmod(0o755)
    except OSError:
        pass
    logger.info(f"Installed post-commit hook at {hook_path}")
    return hook_path


def uninstall_hook() -> None:
    """Remove the installed hook."""
    root = git_root()
    if root is None:
        return
    hook_path = root / ".git" / "hooks" / HOOK_NAME
    if hook_path.exists():
        hook_path.unlink()
        logger.info(f"Removed post-commit hook at {hook_path}")


async def _run_documentation() -> None:
    """Run the documentation agent over the last commit's changed files."""
    from plugin.agents.documentation import documentation_agent

    changed = changed_files_since_last_commit()
    if not changed:
        logger.info("No changed files detected — skipping documentation.")
        return
    log_activity("git_hook", "post_commit", {"changed_files_count": len(changed)})
    await documentation_agent(changed)


def run_once() -> None:
    """Synchronous entry used by the hook script."""
    try:
        asyncio.run(_run_documentation())
    except Exception as e:
        logger.error(f"post-commit documentation failed: {e}")


def main() -> None:
    """CLI: `python -m plugin.triggers.git_hook install | uninstall | run`."""
    import sys
    logging.basicConfig(level=logging.INFO)
    action = sys.argv[1] if len(sys.argv) > 1 else "run"
    if action == "install":
        install_hook()
    elif action == "uninstall":
        uninstall_hook()
    elif action == "run":
        run_once()
    else:
        print("usage: python -m plugin.triggers.git_hook {install|uninstall|run}")


if __name__ == "__main__":
    main()