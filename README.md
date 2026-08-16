# AI Dev Team

LangGraph Multi-Agent System for Autonomous Software Development

A personal AI-powered software engineering team that accepts a natural language idea and autonomously produces fully functional software — including requirements, architecture, backend code, frontend code, tests, documentation, and GitHub pull requests.

## Quick Start

```bash
# 1. Clone and configure
cd "AI Dev Team"
cp .env.example .env
# Edit .env with your API keys (minimum: GROQ_API_KEY)

# 2. Start services
docker-compose up -d

# 3. Open
# Frontend: http://localhost:3002
# Backend:  http://localhost:8001/docs
```

## Architecture

10 specialized AI agents orchestrated via LangGraph:

| Agent | Model | Role |
|-------|-------|------|
| Product Manager | Llama 3.3 | Requirements + task breakdown |
| Architect | Llama 3.3 | API design, DB schema, folder structure |
| Research | Llama 3.3 | Web search → Qdrant LTM storage |
| Backend Dev | Llama 3.3 | FastAPI + SQLAlchemy code generation |
| Frontend Dev | Llama 3.3 | Next.js + TypeScript code generation |
| QA Engineer | Llama 3.3 | Pytest/Playwright test generation |
| Code Reviewer | GPT-OSS-120B | Security/performance review |
| Documentation | GPT-OSS-20B | README, API docs, setup guide |
| GitHub | — | Git commit + PR creation |

## Workflow

```
User Idea → Product Manager → Architect → [Human Checkpoint]
    → Backend Dev ∥ Frontend Dev (parallel)
    → QA Engineer ∥ Code Reviewer (parallel)
    → Documentation → [Human Checkpoint]
    → GitHub Push → Done
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/projects` | Start project generation |
| GET | `/api/projects/{id}` | View project state |
| POST | `/api/projects/{id}/approve` | Approve/reject at checkpoint |
| POST | `/api/projects/{id}/research` | Ad-hoc web research |
| POST | `/api/projects/{id}/github` | Commit + create PR |
| WS | `/ws/{id}` | Real-time agent status |

## Required API Keys

| Key | Source | Required |
|-----|--------|----------|
| `GROQ_API_KEY` | console.groq.com | Yes |
| `LANGCHAIN_API_KEY` | smith.langchain.com | Optional (tracing) |
| `TAVILY_API_KEY` | tavily.com | Optional (research) |
| `EXA_API_KEY` | exa.ai | Optional (research) |
| `FIRECRAWL_API_KEY` | firecrawl.dev | Optional (research) |
| `GITHUB_TOKEN` | github.com/settings/tokens | Optional (PR creation) |

## Tech Stack

- **Backend:** Python 3.12, FastAPI, LangGraph, LangChain, SQLAlchemy 2.0
- **Frontend:** Next.js 15, React 19, TypeScript, Tailwind CSS
- **Infrastructure:** Docker Compose, PostgreSQL, Qdrant (vector DB)
- **Observability:** LangSmith tracing (all LLM calls)

## Running Without Docker

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8001 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Project Structure

```
backend/app/
├── agents/          # 10 AI agent implementations
├── graph/           # LangGraph state, nodes, routers
├── memory/          # Short-term (state) + long-term (Qdrant)
├── tools/           # Search, crawl, GitHub utilities
├── schemas/         # Pydantic output schemas
├── api/             # FastAPI endpoints + WebSocket
└── utils/           # LLM retry helper

frontend/app/
├── page.tsx         # Codex-style dashboard UI
├── layout.tsx       # Root layout with dark theme
└── globals.css      # Dark theme styles
```