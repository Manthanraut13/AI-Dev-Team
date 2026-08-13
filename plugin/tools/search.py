"""Web search tools (Tavily + Exa), ported from v1 backend. Missing keys are
handled gracefully — they log a warning and return no results.
"""
from typing import List, Dict
from plugin.config import settings
import logging

logger = logging.getLogger(__name__)


def tavily_search(query: str, max_results: int = 5) -> List[Dict]:
    if not settings.TAVILY_API_KEY:
        logger.warning("TAVILY_API_KEY not set, skipping Tavily search")
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.TAVILY_API_KEY)
        response = client.search(query=query, max_results=max_results, include_raw_content=False)
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", ""),
                "source": "tavily",
            }
            for r in response.get("results", [])
        ]
    except ImportError:
        logger.warning("tavily-python not installed")
        return []
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


def exa_search(query: str, max_results: int = 5) -> List[Dict]:
    if not settings.EXA_API_KEY:
        logger.warning("EXA_API_KEY not set, skipping Exa search")
        return []
    try:
        from exa_py import Exa
        client = Exa(api_key=settings.EXA_API_KEY)
        response = client.search_and_contents(query=query, num_results=max_results, text=True)
        return [
            {
                "title": r.title or "",
                "url": r.url or "",
                "content": (r.text or "")[:2000],
                "source": "exa",
            }
            for r in response.results
        ]
    except ImportError:
        logger.warning("exa-py not installed")
        return []
    except Exception as e:
        logger.error(f"Exa search failed: {e}")
        return []


def web_search(query: str, max_results: int = 5) -> List[Dict]:
    """Combined web search — Tavily first, Exa as fallback."""
    results = tavily_search(query, max_results)
    if not results:
        results = exa_search(query, max_results)
    return results[:max_results]
