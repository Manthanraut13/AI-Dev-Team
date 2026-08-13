"""File-save watcher — auto-runs QA + Reviewer on saved source files.

Uses watchdog to watch the project (CWD). On a `.py/.ts/.tsx` save, debounces
2s, then runs QA Engineer + Code Reviewer in parallel via the current asyncio
loop. Python files are also scanned for imports with no matching local module —
unknown ones trigger the Research agent.

Bridge: watchdog delivers events on its own thread; we hand the work to the
running asyncio loop with `asyncio.run_coroutine_threadsafe`.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from plugin.tools.output import log_activity
from plugin.utils.files import safe_join

logger = logging.getLogger(__name__)

WATCH_EXTS = {".py", ".ts", ".tsx"}
DEBOUNCE_SECONDS = 2.0
PY_IMPORT_RE = re.compile(r"^\s*(?:import\s+([\w.]+)|from\s+([\w.]+)\s+import)", re.MULTILINE)


class _SaveHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self._pending: dict[str, asyncio.Task] = {}

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix not in WATCH_EXTS or path.name.startswith("."):
            return
        # Debounce: cancel any prior task for this path, schedule a fresh one.
        key = str(path)
        if key in self._pending:
            self._pending[key].cancel()
        self._pending[key] = asyncio.run_coroutine_threadsafe(
            self._debounced(path), self.loop
        )

    async def _debounced(self, path: Path):
        try:
            await asyncio.sleep(DEBOUNCE_SECONDS)
            await self._run_for(path)
        except asyncio.CancelledError:
            pass
        finally:
            self._pending.pop(str(path), None)

    async def _run_for(self, path: Path):
        log_activity("watcher", "file_saved", {"file": str(path)})
        from plugin.agents.qa_engineer import qa_engineer_agent
        from plugin.agents.code_reviewer import code_reviewer_agent

        results = await asyncio.gather(
            qa_engineer_agent(str(path)),
            code_reviewer_agent(str(path)),
            return_exceptions=True,
        )
        for name, res in zip(("qa_engineer", "code_reviewer"), results):
            if isinstance(res, BaseException):
                logger.warning(f"watcher {name} failed for {path}: {res}")
        logger.info(f"watcher: QA + review complete for {path.name}")

        if path.suffix == ".py":
            await self._check_unknown_imports(path)

    async def _check_unknown_imports(self, path: Path):
        """Best-effort: research any import with no matching local module."""
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        local_modules = _local_module_names(Path.cwd())
        unknown = []
        for m in PY_IMPORT_RE.findall(text):
            mod = (m[0] or m[1]).split(".")[0]
            if mod and mod not in local_modules and mod != "__future__":
                unknown.append(mod)
        if unknown:
            log_activity("watcher", "unknown_import", {"modules": unknown[:5], "file": str(path)})
            from plugin.agents.research import research_agent
            await research_agent(f"Library or pattern: {unknown[0]}")


def _local_module_names(root: Path) -> set[str]:
    """Names of importable local modules/folders at the project root."""
    names = set()
    if root.exists():
        for p in root.iterdir():
            if p.suffix == ".py":
                names.add(p.stem)
            elif p.is_dir() and (p / "__init__.py").exists():
                names.add(p.name)
    return names


def start_watcher() -> Observer:
    """Start a background watchdog observer bound to the running loop.

    Call from within the FastMCP app (which already has a loop). Returns the
    Observer so the caller can stop it on shutdown.
    """
    loop = asyncio.get_running_loop()
    handler = _SaveHandler(loop)
    observer = Observer()
    observer.schedule(handler, str(Path.cwd()), recursive=False)
    observer.start()
    logger.info("Watcher started on %s", Path.cwd())
    return observer


async def main() -> None:
    """Standalone: run the watcher in a small asyncio app (for manual testing)."""
    observer = start_watcher()
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())