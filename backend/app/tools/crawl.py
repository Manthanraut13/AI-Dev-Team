from typing import Optional, Dict
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def _get_app():
    from firecrawl import V1FirecrawlApp
    return V1FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)


def firecrawl_scrape(url: str, max_length: int = 3000) -> Optional[str]:
    """Scrape a URL using Firecrawl, return cleaned text content."""
    if not settings.FIRECRAWL_API_KEY:
        logger.warning("FIRECRAWL_API_KEY not set, skipping Firecrawl")
        return None
    
    try:
        app = _get_app()
        result = app.scrape_url(url, formats=["markdown"])
        content = result.markdown or ""
        if content and len(content) > max_length:
            content = content[:max_length] + "..."
        logger.info(f"Firecrawl scraped {url[:60]}: {len(content)} chars")
        return content
    except ImportError:
        logger.warning("firecrawl-py not installed")
        return None
    except Exception as e:
        logger.error(f"Firecrawl scrape failed for {url[:60]}: {e}")
        return None


def firecrawl_crawl(url: str, limit: int = 3) -> list[Dict]:
    """Crawl a site starting from URL, return list of page contents."""
    if not settings.FIRECRAWL_API_KEY:
        logger.warning("FIRECRAWL_API_KEY not set, skipping Firecrawl crawl")
        return []
    
    try:
        app = _get_app()
        crawl_result = app.crawl_url(url, limit=limit)
        pages = []
        for page in crawl_result.get("data", []):
            content = page.get("markdown", "")
            page_url = page.get("metadata", {}).get("sourceURL", url)
            if content:
                pages.append({
                    "url": page_url,
                    "content": content[:3000],
                    "source": "firecrawl"
                })
        logger.info(f"Firecrawl crawled {url[:60]}: {len(pages)} pages")
        return pages
    except ImportError:
        logger.warning("firecrawl-py not installed")
        return []
    except Exception as e:
        logger.error(f"Firecrawl crawl failed: {e}")
        return []
