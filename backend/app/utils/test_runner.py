"""Shared pytest runner used by QA Engineer and Error Handler agents.

Writes the provided backend files (and any extra test files) to a temp
directory, then runs pytest against it. Returns a structured result dict
that both agents can consume.

Extracted from qa_engineer.py so the Error Handler agent can re-run
pytest after applying fixes without duplicating the subprocess logic.
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
from typing import Dict, Optional


def materialize_and_run(
    files: Dict[str, str],
    *,
    timeout: int = 60,
    extra_requirements: Optional[list[str]] = None,
) -> Dict:
    """Materialize the backend files (keys under ``backend/...``) to a temp
    directory and run pytest.

    Args:
        files: Map of ``backend/<rel_path>`` -> source. Anything not under
            ``backend/`` is ignored.
        timeout: Per-test-run timeout in seconds.
        extra_requirements: Optional pip packages to install before running
            tests (e.g. ``["httpx", "pytest-asyncio"]``). The temp dir is
            reusable; installs go to a shared ``.pip`` dir under the temp
            root so subsequent calls don't re-install.

    Returns:
        A dict with keys ``passed`` (int), ``failed`` (int), ``logs`` (str,
        last 2000 chars of pytest output), ``exit_code`` (int).
    """
    backend_keys = [k for k in files if k.startswith("backend/")]
    if not backend_keys:
        return {
            "passed": 0,
            "failed": 0,
            "logs": "No backend files to test",
            "exit_code": -1,
        }

    # Reuse the same temp dir across calls (module-level) so pip installs
    # done for a previous run stick around for subsequent fix-round runs.
    tmp = _get_or_create_tmp()
    for key in backend_keys:
        rel = key[len("backend/"):]
        dest = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(files[key])

    tests_dir = os.path.join(tmp, "tests")
    if not os.path.isdir(tests_dir):
        return {
            "passed": 0,
            "failed": 0,
            "logs": "No tests directory found after materializing files",
            "exit_code": -1,
        }

    return run_pytest(tmp, timeout=timeout)


# ---------------------------------------------------------------------------
# Low-level pytest runner (unchanged from the original qa_engineer version,
# just refactored into a reusable function).
# ---------------------------------------------------------------------------


def run_pytest(directory: str, timeout: int = 60) -> Dict:
    """Best-effort pytest run against a directory. Returns results dict."""
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests", "-q", "--tb=line"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        logs = (result.stdout or "") + "\n" + (result.stderr or "")
        match = re.search(r"(\d+) passed(?:, (\d+) failed)?", logs)
        passed = int(match.group(1)) if match else 0
        failed = int(match.group(2)) if match and match.group(2) else 0
        return {
            "passed": passed,
            "failed": failed,
            "logs": logs[-2000:],
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 0,
            "logs": f"Test run timed out after {timeout}s",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "passed": 0,
            "failed": 0,
            "logs": f"Could not run tests: {e}",
            "exit_code": -1,
        }


# ---------------------------------------------------------------------------
# Shared temp directory
# ---------------------------------------------------------------------------

_tmp_dir: Optional[str] = None


def _get_or_create_tmp() -> str:
    """Return a reusable temp directory for materializing backend code."""
    global _tmp_dir
    if _tmp_dir and os.path.isdir(_tmp_dir):
        return _tmp_dir
    _tmp_dir = tempfile.mkdtemp(prefix="aidevtest_")
    return _tmp_dir
