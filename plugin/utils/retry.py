"""Retry helpers for LLM calls (ported from v1 backend, imports updated)."""
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def with_retry(max_attempts: int = 3, base_delay: float = 8.0):
    """Retry a function that calls an LLM when hitting rate limits or transient errors.

    Retries on:
    - HTTP 429 (rate limit)
    - HTTP 5xx (server errors)
    - HTTP 413 (too large / tokens per minute)
    Backs off exponentially between attempts.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    msg = str(e)
                    is_retryable = (
                        "429" in msg
                        or "rate limit" in msg.lower()
                        or "rate_limit_exceeded" in msg
                        or "413" in msg
                        or "Request too large" in msg
                        or "5" in msg[:5]
                        or "tool_use_failed" in msg
                    )
                    if not is_retryable or attempt == max_attempts:
                        raise
                    logger.warning(
                        f"Retrying ({attempt}/{max_attempts}) after LLM error: {msg[:100]} "
                        f"(waiting {delay:.0f}s)"
                    )
                    time.sleep(delay)
                    delay *= 1.6
            return func(*args, **kwargs)
        return wrapper
    return decorator
