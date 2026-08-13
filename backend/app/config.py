from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]

DOTENV_CANDIDATES = [
    Path.cwd() / ".env",
    BACKEND_ROOT / ".env",
    PROJECT_ROOT / ".env",
]


class Settings(BaseSettings):
    GROQ_API_KEY: str = ""
    LANGCHAIN_TRACING_V2: bool = True
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "ai-dev-team"
    
    TAVILY_API_KEY: str = ""
    EXA_API_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""
    
    GITHUB_TOKEN: str = ""
    GITHUB_USERNAME: str = ""
    
    DATABASE_URL: str = "postgresql://aidevteam:aidevteam@localhost:5432/aidevteam"
    
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: str = ""
    CLERK_SECRET_KEY: str = ""
    
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://127.0.0.1:3002",
        "http://localhost:8001",
    ]

    PLANNING_MODEL: str = "llama-3.3-70b-versatile"
    CODE_MODEL: str = "qwen/qwen3.6-27b"
    REVIEW_MODEL: str = "openai/gpt-oss-120b"
    DOCS_MODEL: str = "openai/gpt-oss-20b"
    FAST_MODEL: str = "llama-3.1-8b-instant"
    SUPERVISOR_MODEL: str = "llama-3.3-70b-versatile"

    # Supervisor / Codex-style session workspace paths
    DEFAULT_PROJECTS_DIR: str = "~/ai-dev-team-projects"
    SESSION_DATA_DIR: str = "~/.ai-dev-team/sessions"

    class Config:
        env_file = [str(p) for p in DOTENV_CANDIDATES if p.exists()]
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
