from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from app.graph.state import AgentState
from app.tools.search import web_search
from app.tools.crawl import firecrawl_scrape
from app.memory.long_term import memory_service
from app.config import settings
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


def _extract_search_terms(state: AgentState) -> List[str]:
    """Extract tech terms from requirements and architecture for web search."""
    terms = []
    
    requirements = state.get("requirements", [])
    for r in requirements[:8]:
        words = r.split()
        for i in range(len(words)):
            for j in range(i+2, min(i+5, len(words)+1)):
                phrase = " ".join(words[i:j])
                if len(phrase) > 5 and not phrase.lower().startswith(("a ", "the ", "and ", "or ")):
                    terms.append(phrase)
    
    architecture = state.get("architecture", {})
    for decision in architecture.get("tech_decisions", [])[:5]:
        terms.append(decision[:60])
    
    for ep in architecture.get("api_endpoints", [])[:4]:
        path = ep.get("path", "")
        if path and path != "/":
            terms.append(f"REST API {path}")
    
    seen = set()
    unique_terms = []
    for t in terms:
        key = t.lower().strip()
        if key not in seen:
            seen.add(key)
            unique_terms.append(t)
    
    return unique_terms[:10]


def _search_and_collect(terms: List[str], max_per_term: int = 3) -> List[Dict]:
    """Search web for each term and collect results."""
    all_results = []
    for term in terms:
        results = web_search(term, max_results=max_per_term)
        all_results.extend(results)
    
    seen_urls = set()
    unique = []
    for r in all_results:
        url = r.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(r)
    
    return unique


def _scrape_top_results(results: List[Dict], max_scrape: int = 3) -> List[Dict]:
    """Scrape content from top search results using Firecrawl."""
    enriched = []
    scraped = 0
    for r in results:
        if scraped >= max_scrape:
            break
        url = r.get("url", "")
        if not url:
            continue
        content = firecrawl_scrape(url)
        if content:
            r["full_content"] = content
            scraped += 1
        enriched.append(r)
    return enriched


def research_node(state: AgentState) -> dict:
    """Research Agent: searches web for relevant docs, stores in Qdrant LTM."""
    project_name = state.get("project_name", "project")
    logger.info(f"Research Agent starting for {project_name}")
    
    terms = _extract_search_terms(state)
    if not terms:
        return {
            "messages": [AIMessage(content="Research: no search terms extracted")]
        }
    
    logger.info(f"Searching for {len(terms)} terms")
    
    results = _search_and_collect(terms)
    if not results:
        return {
            "messages": [AIMessage(content="Research: no web results found")]
        }
    
    logger.info(f"Found {len(results)} unique results")
    
    enriched = _scrape_top_results(results, max_scrape=2)
    
    stored_count = 0
    for r in enriched:
        content = r.get("full_content") or r.get("content", "")
        if not content:
            continue
        
        store_text = f"Title: {r.get('title', '')}\nURL: {r.get('url', '')}\n\n{content}"
        
        try:
            memory_service.store(
                collection="references",
                content=store_text[:3000],
                metadata={
                    "project_name": project_name,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "source": r.get("source", "web")
                }
            )
            stored_count += 1
        except Exception as e:
            logger.warning(f"Failed to store reference: {e}")
    
    summary = (
        f"Research complete: {len(terms)} terms searched, "
        f"{len(results)} results found, {stored_count} references stored in LTM"
    )
    logger.info(summary)
    
    return {
        "messages": [AIMessage(content=summary)]
    }
