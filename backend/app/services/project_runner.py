"""Project Runner — launches the generated app (backend + frontend) for live
preview, streams logs over WebSocket, and tears down process trees on stop.

Called from the REST ``POST /sessions/{id}/run`` endpoint and triggered
automatically via the ``preview.auto`` WS event (frontend-initiated) after
``write_to_workspace`` succeeds.

Windows note: npm/next/uvicorn spawn child processes; ``taskkill /T /F`` is
used to kill the full tree on stop to avoid orphan ports.
"""
from __future__ import annotations

import asyncio
import logging
import os
import socket
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

BACKEND_BASE_PORT = 8100
FRONTEND_BASE_PORT = 3100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _python() -> str:
    """Return the path to the current Python interpreter.

    Honors the active virtualenv if any (sys.executable already points there).
    """
    import sys
    return sys.executable


# ---------------------------------------------------------------------------
# Port allocation
# ---------------------------------------------------------------------------


def _free_port(base: int) -> int:
    """Return the first free port starting at *base*."""
    for port in range(base, base + 200):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return base


# ---------------------------------------------------------------------------
# ProjectRunner
# ---------------------------------------------------------------------------


class ProjectRunner:
    """Per-session lifecycle manager for the generated app."""

    def __init__(
        self,
        workspace_path: str,
        broadcast: Callable[[str, Dict[str, Any]], None],
    ) -> None:
        self.workspace_path = workspace_path
        self._broadcast = broadcast

        self.state: str = "stopped"  # stopped | installing | starting | running | error
        self.backend_url: str = ""
        self.frontend_url: str = ""
        self.message: str = ""

        self._processes: Dict[str, asyncio.subprocess.Process] = {}
        self._backend_port: int = 0
        self._frontend_port: int = 0
        self._task: Optional[asyncio.Task[None]] = None
        self._stop_event = asyncio.Event()

    # --- public API ---------------------------------------------------------

    async def start(self) -> Dict[str, Any]:
        """Start the generated app. Returns the status snapshot.

        Calling start while already running will stop first then restart.
        Calling start while installing / starting is a no-op (returns current
        status).
        """
        if self.state in ("installing", "starting"):
            return self.status_snapshot()
        await self.stop()
        self._task = asyncio.create_task(self._run())
        return self.status_snapshot()

    async def stop(self) -> Dict[str, Any]:
        """Stop all running processes and return status."""
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        for name, proc in list(self._processes.items()):
            await self._kill_process_tree(proc, name)
        self._processes.clear()
        self.state = "stopped"
        self.message = ""
        self._emit_status("stopped")
        return self.status_snapshot()

    def status_snapshot(self) -> Dict[str, Any]:
        return {
            "status": self.state,
            "backend_url": self.backend_url,
            "frontend_url": self.frontend_url,
            "message": self.message,
        }

    # --- internal -----------------------------------------------------------

    async def _run(self) -> None:
        """Main lifecycle coroutine: install deps → start servers."""
        self._stop_event = asyncio.Event()

        backend_dir = os.path.join(self.workspace_path, "backend")
        frontend_dir = os.path.join(self.workspace_path, "frontend")
        has_backend = os.path.isfile(os.path.join(backend_dir, "requirements.txt"))
        has_frontend = os.path.isfile(os.path.join(frontend_dir, "package.json"))

        if not (has_backend or has_frontend):
            self._fail("No runnable stack found (looked for backend/requirements.txt and frontend/package.json)")
            return

        try:
            # ---- install deps ----
            if has_backend:
                self._set("installing", "Installing backend dependencies...")
                if not await self._run_install(
                    [_python(), "-m", "pip", "install", "-r", "requirements.txt"],
                    backend_dir,
                    "backend",
                ):
                    return

            if has_frontend:
                self._set("installing", "Installing frontend dependencies (npm install)...")
                if not await self._run_install(
                    ["npm", "install"],
                    frontend_dir,
                    "frontend",
                ):
                    return

            # ---- allocate ports ----
            self._backend_port = _free_port(BACKEND_BASE_PORT)
            self._frontend_port = _free_port(FRONTEND_BASE_PORT)

            # ---- start backend ----
            if has_backend:
                self._set("starting", "Starting backend server...")
                proc = await self._spawn(
                    [_python(), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(self._backend_port)],
                    backend_dir,
                    "backend",
                )
                if proc is None:
                    return
                self._processes["backend"] = proc
                self.backend_url = f"http://127.0.0.1:{self._backend_port}"

            # ---- start frontend ----
            if has_frontend:
                self._set("starting", "Starting frontend server...")
                proc = await self._spawn(
                    ["npx", "next", "dev", "--hostname", "127.0.0.1", "--port", str(self._frontend_port)],
                    frontend_dir,
                    "frontend",
                )
                if proc is None:
                    return
                self._processes["frontend"] = proc
                self.frontend_url = f"http://127.0.0.1:{self._frontend_port}"

            self._set("running", "Running")
            self._emit_ready()

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._fail(f"Failed to start: {exc}")

    async def _run_install(self, cmd: list, cwd: str, service: str) -> bool:
        """Run an install command, streaming each line to the client."""
        self._log(service, f"$ {' '.join(cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            self._fail(f"Command not found ({cmd[0]}): {exc}")
            return False

        assert proc.stdout is not None
        try:
            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    self._log(service, line)
        except asyncio.CancelledError:
            await self._kill_process_tree(proc, service)
            raise

        await proc.wait()
        if self._stop_event.is_set():
            return False
        if proc.returncode != 0:
            self._fail(f"{service} dependency install failed (exit {proc.returncode})")
            return False
        self._log(service, "install finished")
        return True

    async def _spawn(self, cmd: list, cwd: str, service: str) -> Optional[asyncio.subprocess.Process]:
        """Start a long-running process and stream its output."""
        self._log(service, f"$ {' '.join(cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            self._fail(f"Command not found ({cmd[0]}): {exc}")
            return None

        asyncio.create_task(self._stream_output(proc, service))
        return proc

    async def _stream_output(self, proc: asyncio.subprocess.Process, service: str) -> None:
        """Read stdout line-by-line and broadcast as preview.log."""
        assert proc.stdout is not None
        try:
            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                if line:
                    self._log(service, line)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        # When the process exits we do NOT mark it stopped — the runner
        # stays in ``running`` state so the user can see logs. A crash is
        # surfaced as an error line in the logs.

    async def _kill_process_tree(self, proc: asyncio.subprocess.Process, name: str) -> None:
        """Kill a process and (on Windows) its full tree."""
        if proc.returncode is not None:
            return
        pid = proc.pid
        if pid is None:
            return
        try:
            if os.name == "nt":
                self._log(name, "stopping process tree…")
                kill = await asyncio.create_subprocess_exec(
                    "taskkill", "/PID", str(pid), "/T", "/F",
                    stdout=asyncio.subprocess.DEVNULL,
                    stderr=asyncio.subprocess.DEVNULL,
                )
                await kill.wait()
            else:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    proc.kill()
        except Exception as exc:
            logger.warning(f"kill {name} failed: {exc}")

    # --- helpers ------------------------------------------------------------

    def _set(self, state: str, message: str) -> None:
        self.state = state
        self.message = message
        self._emit_status(state)

    def _fail(self, message: str) -> None:
        self.state = "error"
        self.message = message
        self._emit_status("error")

    def _log(self, service: str, line: str) -> None:
        self._broadcast("preview.log", {"service": service, "line": line})

    def _emit_status(self, state: str) -> None:
        self._broadcast("preview.status", self.status_snapshot())

    def _emit_ready(self) -> None:
        self._broadcast("preview.ready", {
            "frontend_url": self.frontend_url,
            "backend_url": self.backend_url,
        })


# ---------------------------------------------------------------------------
# Module-level registry
# ---------------------------------------------------------------------------

_runners: Dict[str, ProjectRunner] = {}


def get_runner(
    session_id: str,
    workspace_path: str,
    broadcast: Callable[[str, Dict[str, Any]], None],
) -> ProjectRunner:
    """Get or create a ProjectRunner for the given session.

    Reuses an existing runner when the workspace is unchanged, but always
    refreshes the broadcast closure so events stream to the current client
    (a runner created via REST with a no-op broadcaster must be rewired when
    a WebSocket connects later).
    """
    runner = _runners.get(session_id)
    if runner is None or runner.workspace_path != workspace_path:
        runner = ProjectRunner(workspace_path, broadcast)
        _runners[session_id] = runner
    else:
        runner._broadcast = broadcast
    return runner


def pop_runner(session_id: str) -> Optional[ProjectRunner]:
    """Remove and return a runner without stopping it (caller may await stop)."""
    return _runners.pop(session_id, None)


def remove_runner(session_id: str) -> None:
    """Remove and stop a runner (best-effort)."""
    runner = _runners.pop(session_id, None)
    if runner is None:
        return
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(runner.stop())
    except RuntimeError:
        pass
