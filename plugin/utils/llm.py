"""Shared LLM factory + retry invocation."""
import asyncio
import logging

from langchain_groq import ChatGroq
from plugin.config import settings

logger = logging.getLogger(__name__)


def get_llm(
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> ChatGroq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Create a `.env` file at the plugin root "
            "(see .env.example) and re-run the agent."
        )
    return ChatGroq(
        model=model or settings.PLANNING_MODEL,
        temperature=temperature,
        api_key=settings.GROQ_API_KEY,
        max_tokens=max_tokens,
        timeout=120,
        max_retries=3,
    )


async def invoke_with_retry(llm, messages, max_attempts: int = 4, base_delay: float = 8.0, **kwargs):
    """Invoke the LLM with exponential backoff on rate limits / transient errors.

    Async: uses `ainvoke` when available and sleeps with `asyncio.sleep` so the
    MCP server's event loop is never blocked by a retry backoff (previously a
    synchronous `time.sleep(8-33s)` stalled every concurrent tool call).
    """
    # Prefer the async runnable; fall back to the sync invoke wrapped in a thread.
    if hasattr(llm, "ainvoke"):
        call = lambda msgs, **kw: llm.ainvoke(msgs, **kw)
    elif hasattr(llm, "invoke"):
        call = lambda msgs, **kw: asyncio.to_thread(lambda: llm.invoke(msgs, **kw))
    else:
        raise TypeError(f"Unsupported LLM object: {type(llm)!r}")

    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return await call(messages, **kwargs)
        except Exception as e:
            msg = str(e)
            is_retryable = (
                "429" in msg
                or "rate limit" in msg.lower()
                or "rate_limit_exceeded" in msg
                or "413" in msg
                or "Request too large" in msg
                or "tool_use_failed" in msg
                or "timeout" in msg.lower()
            )
            if not is_retryable or attempt == max_attempts:
                raise
            logger.warning(
                f"LLM retry {attempt}/{max_attempts}: {msg[:120]} (waiting {delay:.0f}s)"
            )
            await asyncio.sleep(delay)
            delay *= 1.6
    raise RuntimeError("Unreachable: invoke_with_retry exhausted attempts")
