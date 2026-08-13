"""Central error-handling helpers — agent timeout, invalid-output retry, log+notify.

Used by:
- Each agent (optional wrap around LLM calls) to enforce AGENT_TIMEOUT_SECONDS
  and retry on Pydantic validation failures up to INVALID_JSON_RETRIES times.
- `plugin.graph.pipeline.run_devteam_pipeline` to capture any uncaught exception
  into a structured error dict instead of raising.

Design notes:
- All helpers are async-safe (`asyncio.wait_for`).
- Logging goes through `plugin.tools.output.log_activity` so the activity log
  in `.ai-devteam/logs/agent_activity.log` records every error event.
- Failures are NEVER swallowed silently — every path logs and (when called from
  the pipeline) returns a structured dict the caller can inspect.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, TypeVar

from pydantic import ValidationError

from plugin.tools.output import log_activity

logger = logging.getLogger(__name__)

# Per Agent.md and the implementation plan §6.
AGENT_TIMEOUT_SECONDS = 60
INVALID_JSON_RETRIES = 3

T = TypeVar("T")


async def run_agent(
    name: str,
    coro_factory: Callable[[int], Awaitable[T]],
    *,
    timeout: float = AGENT_TIMEOUT_SECONDS,
    max_invalid_output_retries: int = INVALID_JSON_RETRIES,
) -> T:
    """Wrap an agent coroutine factory with timeout + invalid-output retry.

    Args:
        name: Agent name for logging.
        coro_factory: Callable taking the attempt number (1-based) and returning
            a fresh coroutine. Each retry produces a new coroutine; the agent
            can inject a "Respond with valid JSON." hint into the prompt on
            attempts > 1.
        timeout: Per-attempt timeout (seconds).
        max_invalid_output_retries: Extra attempts allowed when the coroutine
            raises `pydantic.ValidationError` (typically from the LLM returning
            a value that doesn't match the agent's Pydantic schema).

    Raises:
        asyncio.TimeoutError: if any attempt exceeds `timeout`.
        The original exception (Pydantic or otherwise) after retries are
        exhausted. The final exception is also logged.
    """
    last_error: Exception | None = None
    total_attempts = 1 + max_invalid_output_retries

    for attempt in range(1, total_attempts + 1):
        try:
            return await asyncio.wait_for(coro_factory(attempt), timeout=timeout)
        except ValidationError as e:
            last_error = e
            log_activity(name, "invalid_output_retry", {"attempt": attempt, "error": str(e)[:200]})
            logger.warning(
                f"{name}: invalid output on attempt {attempt}/{total_attempts}: {e}"
            )
            if attempt >= total_attempts:
                break
            continue
        except asyncio.TimeoutError as e:
            last_error = e
            log_activity(name, "timeout", {"attempt": attempt, "timeout": timeout})
            logger.warning(f"{name}: timed out after {timeout}s on attempt {attempt}")
            raise
        except Exception as e:
            # Non-retryable: log and re-raise immediately.
            log_activity(name, "error", {"attempt": attempt, "error": str(e)[:200]})
            logger.exception(f"{name}: uncaught exception on attempt {attempt}")
            raise

    # All retries exhausted.
    log_activity(name, "retries_exhausted", {"attempts": total_attempts, "error": str(last_error)[:200]})
    raise last_error  # type: ignore[misc]


def error_response(stage: str, error: Exception, partial_results: dict | None = None) -> dict:
    """Build the standard pipeline error dict.

    Returned by `run_devteam_pipeline` on any uncaught failure so the MCP tool
    can always return a JSON-serialisable response.
    """
    return {
        "status": "error",
        "stage": stage,
        "error": f"{type(error).__name__}: {error}",
        "error_type": type(error).__name__,
        "partial_results": partial_results or {},
    }