from langchain_groq import ChatGroq
from app.config import settings
from app.utils.retry import with_retry
import time
import logging

logger = logging.getLogger(__name__)


def get_llm(
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int | None = None,
) -> ChatGroq:
    return ChatGroq(
        model=model or settings.PLANNING_MODEL,
        temperature=temperature,
        api_key=settings.GROQ_API_KEY,
        max_tokens=max_tokens,
        timeout=120,
        max_retries=3,
    )


def invoke_with_retry(llm, messages, max_attempts: int = 4, base_delay: float = 8.0, **kwargs):
    """Invoke an LLM with exponential backoff on rate limits / transient errors."""
    delay = base_delay
    for attempt in range(1, max_attempts + 1):
        try:
            return llm.invoke(messages, **kwargs)
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
            time.sleep(delay)
            delay *= 1.6
    return llm.invoke(messages, **kwargs)
