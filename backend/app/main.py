import os
os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import health, projects, ws_routes, sessions, ws_sessions

app = FastAPI(
    title="AI Dev Team API",
    description="LangGraph Multi-Agent System for Software Development",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(sessions.router, prefix="/api", tags=["Sessions"])
app.include_router(ws_sessions.ws_router, tags=["WebSocket"])


@app.on_event("startup")
async def startup_event():
    tracing = os.environ.get("LANGCHAIN_TRACING_V2", "false")
    project = settings.LANGCHAIN_PROJECT
    print(f"LangSmith tracing: {'ON' if tracing == 'true' else 'OFF'} (project: {project})")

    required = {"GROQ_API_KEY": settings.GROQ_API_KEY}
    optional = {
        "TAVILY_API_KEY": settings.TAVILY_API_KEY,
        "EXA_API_KEY": settings.EXA_API_KEY,
        "FIRECRAWL_API_KEY": settings.FIRECRAWL_API_KEY,
        "GITHUB_TOKEN": settings.GITHUB_TOKEN,
        "GITHUB_USERNAME": settings.GITHUB_USERNAME,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        print(f"WARNING: Missing required keys: {', '.join(missing)}")
    for k, v in optional.items():
        if not v:
            print(f"  {k}: not set (optional)")

    try:
        from app.memory.long_term import memory_service
        if memory_service.is_ready():
            print("Memory service initialized (Qdrant)")
        else:
            print("Memory service unavailable (Qdrant down)")
    except Exception as e:
        print(f"Memory service init failed: {e}")


@app.get("/")
async def root():
    return {
        "message": "AI Dev Team API",
        "docs": "/docs",
        "version": "1.0.0"
    }
