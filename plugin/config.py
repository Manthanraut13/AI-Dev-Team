"""Plugin settings — loaded from `.env` at the repo root or current working dir.

Only plugin-relevant keys are kept (LLM, tracing, search, GitHub, Qdrant).
Web-app-only fields from v1 (Postgres, Clerk, Supabase, CORS, session dirs)
were removed in the v2 plugin pivot.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOTENV_CANDIDATES = [
    Path.cwd() / ".env",
    PROJECT_ROOT / ".env",
]


class Settings(BaseSettings):
    # ---- LLM (required) ----
    GROQ_API_KEY: str = ""

    # ---- Tracing (LangSmith, optional) ----
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "ai-dev-team"

    # ---- Search & Crawl (optional) ----
    TAVILY_API_KEY: str = ""
    EXA_API_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""

    # ---- GitHub (optional) ----
    GITHUB_TOKEN: str = ""
    GITHUB_USERNAME: str = ""

    # ---- Long-term memory (Qdrant, optional — degrades gracefully) ----
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # ---- Model routing ----
    # Defaults match the model set proven on this machine. Agent.md lists an
    # alternative set (e.g. qwen3-coder, deepseek-r1-distill-llama-70b,
    # gemma2-9b-it) which can be enabled by setting these env vars.
    PLANNING_MODEL: str = "openai/gpt-oss-120b"
    CODE_MODEL: str = "openai/gpt-oss-120b"
    REVIEW_MODEL: str = "openai/gpt-oss-120b"
    DOCS_MODEL: str = "openai/gpt-oss-120b"
    FAST_MODEL: str = "openai/gpt-oss-20b"
    SUPERVISOR_MODEL: str = "openai/gpt-oss-120b"

    model_config = SettingsConfigDict(
        env_file=[str(p) for p in DOTENV_CANDIDATES if p.exists()],
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
