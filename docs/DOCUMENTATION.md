# AI Dev Team — Full Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [MCP Server](#mcp-server)
4. [Agents](#agents)
5. [Pipeline](#pipeline)
6. [Memory System](#memory-system)
7. [Deployment](#deployment)
8. [Configuration](#configuration)
9. [Development](#development)
10. [API Reference](#api-reference)

---

## Overview

AI Dev Team is an MCP (Model Context Protocol) server that accepts a natural language software idea and autonomously generates a complete project scaffold — requirements, architecture, backend code, frontend code, tests, and documentation.

### What It Does

1. **You describe an idea** — "Build a todo app with user auth"
2. **AI agents work** — 8 specialized agents handle each phase
3. **You get artifacts** — requirements, architecture, code, tests, docs

### How It Works

```
Your Idea
    │
    ▼
┌─────────────────┐
│ Product Manager  │ → Requirements + Tasks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Architect     │ → API Design + DB Schema + Folder Structure
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│Backend │ │Frontend│ → Scaffold Code
│  Dev   │ │  Dev   │
└───┬────┘ └───┬────┘
    │          │
    └────┬─────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│   QA   │ │ Reviewer│ → Tests + Code Review
│Engineer│ │        │
└───┬────┘ └───┬────┘
    │          │
    └────┬─────┘
         │
         ▼
┌─────────────────┐
│  Documentation  │ → README + API Docs
└─────────────────┘
```

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────┐
│                MCP Client                        │
│  (OpenCode / Claude Code / Cline / Roo Code)    │
└──────────────────────┬──────────────────────────┘
                       │ MCP Protocol (SSE/HTTP)
                       ▼
┌─────────────────────────────────────────────────┐
│              FastMCP Server                      │
│              (plugin/server.py)                  │
│                                                  │
│  ┌──────────────┐  ┌──────────────┐             │
│  │  11 MCP Tools │  │  Auth (OAuth) │             │
│  └──────┬───────┘  └──────────────┘             │
│         │                                        │
│         ▼                                        │
│  ┌──────────────────────────────────┐           │
│  │         Agent Router             │           │
│  │  (routes tool calls to agents)   │           │
│  └──────────────┬───────────────────┘           │
│                 │                                │
│     ┌───────────┼───────────┐                   │
│     ▼           ▼           ▼                   │
│  ┌──────┐  ┌────────┐  ┌────────┐              │
│  │Agents│  │ Memory │  │ Tools  │              │
│  │ (8)  │  │Context │  │Search  │              │
│  │      │  │+ Qdrant│  │Crawl   │              │
│  └──────┘  └────────┘  └────────┘              │
└─────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              Groq Cloud (LLM)                    │
│  GPT-OSS-120b (planning, code, review)          │
│  GPT-OSS-20b (fast tasks)                       │
└─────────────────────────────────────────────────┘
```

### File Structure

```
AI-Dev-Team/
├── plugin/                    # Core package
│   ├── __init__.py
│   ├── server.py              # MCP server (entry point)
│   ├── config.py              # Settings (env vars, model names)
│   ├── paths.py               # Filesystem conventions
│   │
│   ├── agents/                # 8 AI agents
│   │   ├── product_manager.py # Requirements generation
│   │   ├── architect.py       # API/DB/folder design
│   │   ├── research.py        # Web search + LTM
│   │   ├── backend_dev.py     # FastAPI scaffolding
│   │   ├── frontend_dev.py    # Next.js scaffolding
│   │   ├── qa_engineer.py     # Test generation
│   │   ├── code_reviewer.py   # Code review
│   │   └── documentation.py   # README/docs generation
│   │
│   ├── graph/                 # Orchestration
│   │   └── pipeline.py        # Full pipeline (run_devteam)
│   │
│   ├── memory/                # State management
│   │   ├── context.py         # project_context.json
│   │   └── long_term.py       # Qdrant vector memory
│   │
│   ├── tools/                 # External integrations
│   │   ├── search.py          # Tavily/Exa/Firecrawl
│   │   ├── crawl.py           # Web scraping
│   │   └── output.py          # File writing + logging
│   │
│   ├── triggers/              # Automation
│   │   ├── watcher.py         # File-save → QA + Review
│   │   └── git_hook.py        # Post-commit → Docs
│   │
│   ├── integrations/          # Platform configs
│   │   ├── _common.py         # Shared helpers
│   │   ├── opencode.py
│   │   ├── claude_code.py
│   │   ├── cline.py
│   │   ├── roocode.py
│   │   └── codex.py
│   │
│   ├── schemas/               # Data models
│   │   └── outputs.py         # Pydantic v2 schemas
│   │
│   └── utils/                 # Utilities
│       ├── llm.py             # Groq client + retry
│       ├── retry.py           # Exponential backoff
│       ├── files.py           # FILE: parser
│       └── errors.py          # Error handling
│
├── tests/                     # 74 unit tests
│   ├── test_schemas.py        # Schema validation
│   ├── test_agents.py         # Agent output validation
│   ├── test_server_registry.py # MCP tool registry
│   ├── test_pipeline.py       # Pipeline orchestration
│   ├── test_install.py        # Platform installer
│   ├── test_long_term.py      # Qdrant memory
│   ├── test_output.py         # File output
│   ├── test_retry.py          # Retry logic
│   └── test_context.py        # Context management
│
├── install.py                 # Platform installer CLI
├── requirements.txt           # Python dependencies
├── pyproject.toml             # Package config
├── .env.example               # Environment template
├── README.md                  # Quick start guide
├── Integration.md             # Platform integration guide
├── WORK_GUIDE.md              # Operator manual
├── IMPLEMENTATION_PLAN.md     # Development roadmap
├── CHANGELOG.md               # Version history
└── .ai-devteam/               # Runtime artifacts
    ├── project_context.json   # Live project state
    ├── config.toml            # Runtime config
    ├── requirements.md        # Generated requirements
    ├── architecture.md        # Generated architecture
    ├── logs/                  # Agent activity logs
    ├── reviews/               # Code reviews
    └── tests/                 # Generated tests
```

---

## MCP Server

### What is MCP?

MCP (Model Context Protocol) is a standard for AI coding assistants to connect to external tools and services. The AI Dev Team server exposes its agents as MCP tools.

### Server Entry Point

`plugin/server.py` is the main entry point. It:

1. Loads environment variables
2. Creates a FastMCP server instance
3. Registers 11 tools (agent wrappers)
4. Starts on stdio (for MCP clients) or HTTP (for testing)

### Lazy Imports

The server uses lazy imports — agents are loaded on first call, not at startup. This keeps startup fast (~4s vs ~39s) so MCP clients don't timeout.

```python
@mcp.tool()
async def run_product_manager(idea: str) -> dict:
    _import_agents()  # Loads all agents on first call
    from plugin.agents.product_manager import product_manager_agent
    return (await product_manager_agent(idea)).model_dump()
```

### Transport Modes

| Mode | Command | Use Case |
|------|---------|----------|
| **stdio** | `python -m plugin.server` | MCP clients (default) |
| **HTTP** | `python -m plugin.server --transport http` | Testing, debugging |

---

## Agents

### Product Manager (`run_product_manager`)

**Input**: Natural language idea (string)
**Output**: `PMOutput` (Pydantic model)

```python
class PMOutput(BaseModel):
    project_name: str
    summary: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    prioritized_tasks: list[str]
```

**What it does**: Analyzes the idea, generates functional/non-functional requirements, and creates a prioritized task list.

---

### Architect (`run_architect`)

**Input**: Requirements text (string)
**Output**: `ArchitectOutput` (Pydantic model)

```python
class ArchitectOutput(BaseModel):
    detected_stack: list[str]
    api_endpoints: list[dict]    # [{method, path, description}]
    db_schema: list[dict]        # [{table, columns: [{name, type}]}]
    folder_structure: str
    tech_decisions: list[str]
```

**What it does**: Designs the tech stack, API endpoints, database schema, and project structure.

---

### Research (`run_research`)

**Input**: Topic string
**Output**: `ResearchOutput` (Pydantic model)

```python
class ResearchOutput(BaseModel):
    topic: str
    summary: str
    key_findings: list[str]
    useful_links: list[str]
    code_examples: list[str]
```

**What it does**: Searches the web (Tavily/Exa/Firecrawl), synthesizes findings, and stores results in long-term memory.

---

### Backend Dev (`run_backend_dev`)

**Input**: Spec string (optional)
**Output**: `BackendDevOutput` (Pydantic model)

```python
class BackendDevOutput(BaseModel):
    files: dict[str, str]  # {filepath: content}
    requires_confirmation: bool  # Always True
```

**What it does**: Generates FastAPI backend code — models, schemas, routes, database setup.

---

### Frontend Dev (`run_frontend_dev`)

**Input**: Spec string (optional)
**Output**: `FrontendDevOutput` (Pydantic model)

```python
class FrontendDevOutput(BaseModel):
    files: dict[str, str]  # {filepath: content}
    requires_confirmation: bool  # Always True
```

**What it does**: Generates Next.js frontend code — pages, components, types, API client.

---

### QA Engineer (`run_qa_engineer`)

**Input**: File path (string)
**Output**: `QAOutput` (Pydantic model)

```python
class QAOutput(BaseModel):
    file_path: str
    tests: dict[str, str]  # {test_filepath: content}
    summary: str
```

**What it does**: Analyzes a source file and generates pytest tests.

---

### Code Reviewer (`run_code_reviewer`)

**Input**: File path (string)
**Output**: `ReviewOutput` (Pydantic model)

```python
class ReviewOutput(BaseModel):
    file_path: str
    summary: str
    issues: list[dict]  # [{severity, line, message, suggestion}]
    overall_rating: str
```

**What it does**: Reviews code for security, performance, and style issues.

---

### Documentation (`run_documentation`)

**Input**: List of changed file paths
**Output**: `DocsOutput` (Pydantic model)

```python
class DocsOutput(BaseModel):
    files: dict[str, str]  # {doc_filepath: content}
    summary: str
```

**What it does**: Updates README, API docs, and CHANGELOG based on code changes.

---

### Full Pipeline (`run_devteam`)

**Input**: Idea string
**Output**: Pipeline result dict

Runs all agents in sequence:
1. Product Manager → requirements
2. Architect → design
3. Backend Dev + Frontend Dev (parallel) → code
4. QA Engineer + Code Reviewer (parallel) → tests + review
5. Documentation → docs

Returns `pending_scaffold` if code was generated (requires `confirm_scaffold` to write files).

---

## Pipeline

### `run_devteam(idea)`

The main orchestrator. Calls agents in order, collects results, and returns a summary.

```python
result = await run_devteam_pipeline("A todo app with auth")
# result = {
#   "project_name": "TodoApp",
#   "requirements": {...},
#   "architecture": {...},
#   "pending_scaffold": {"backend": {...}, "frontend": {...}},
#   "artifacts": [...]
# }
```

### `confirm_scaffold(target, files)`

Writes approved scaffold files to disk after user confirmation.

```python
confirm_scaffold("backend", result["pending_scaffold"]["backend"])
# Creates backend/ directory with all generated files
```

---

## Memory System

### Short-term Memory (`project_context.json`)

Stores the current project state. Updated by every agent.

```json
{
  "project_name": "TodoApp",
  "detected_stack": ["FastAPI", "PostgreSQL", "Next.js"],
  "requirements": [...],
  "architecture": {...},
  "files": {...},
  "last_updated": "2026-08-23T10:00:00Z"
}
```

### Long-term Memory (Qdrant)

Optional vector database for storing past projects. Used by:
- **Architect**: Looks up similar past architectures
- **Research**: Stores search results for reuse
- **Backend/Frontend Dev**: References past code patterns

Degrades gracefully — all agents work without Qdrant.

---

## Deployment

### Horizon (Recommended)

```bash
# Install FastMCP CLI
pip install fastmcp

# Login
fastmcp auth login

# Deploy
fastmcp deploy plugin/server.py --name ai-dev-team

# Get URL
fastmcp list
```

### Local

```bash
# stdio mode (for MCP clients)
python -m plugin.server

# HTTP mode (for testing)
python -m plugin.server --transport http --port 8765
```

---

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key |
| `TAVILY_API_KEY` | No | — | Tavily search API |
| `EXA_API_KEY` | No | — | Exa search API |
| `FIRECRAWL_API_KEY` | No | — | Firecrawl scraping API |
| `GITHUB_TOKEN` | No | — | GitHub automation |
| `QDRANT_URL` | No | `http://localhost:6333` | Qdrant server URL |
| `QDRANT_API_KEY` | No | — | Qdrant API key |

### Model Configuration

Default models in `plugin/config.py`:

```python
PLANNING_MODEL = "openai/gpt-oss-120b"   # PM, Architect
CODE_MODEL = "openai/gpt-oss-120b"       # Backend/Frontend Dev
REVIEW_MODEL = "openai/gpt-oss-120b"     # Code Reviewer
DOCS_MODEL = "openai/gpt-oss-120b"       # Documentation
FAST_MODEL = "openai/gpt-oss-20b"        # Fast tasks
SUPERVISOR_MODEL = "openai/gpt-oss-20b"  # Pipeline supervisor
```

Override via environment variables or `.ai-devteam/config.toml`.

---

## Development

### Setup

```bash
git clone https://github.com/Manthanraut13/AI-Dev-Team.git
cd AI-Dev-Team
pip install -r requirements.txt
cp .env.example .env
```

### Run Tests

```bash
pytest tests/ -v
```

### Run Server Locally

```bash
python -m plugin.server --transport http --port 8765
```

### Test Agents Directly

```python
import asyncio
from plugin.agents.product_manager import product_manager_agent

result = asyncio.run(product_manager_agent("A todo app with auth"))
print(result.project_name)
print(result.functional_requirements)
```

### Adding a New Agent

1. Create `plugin/agents/my_agent.py`
2. Define input/output schemas in `plugin/schemas/outputs.py`
3. Add MCP tool in `plugin/server.py`
4. Add tests in `tests/`

---

## API Reference

### MCP Tools

#### `run_product_manager(idea: str) -> dict`
Generate requirements from a software idea.

#### `run_architect(requirements: str = "") -> dict`
Design API, DB schema, and folder structure.

#### `run_research(topic: str) -> dict`
Search the web and synthesize findings.

#### `run_backend_dev(spec: str = "") -> dict`
Scaffold a FastAPI backend.

#### `run_frontend_dev(spec: str = "") -> dict`
Scaffold a Next.js frontend.

#### `run_qa_engineer(file_path: str) -> dict`
Generate tests for a file.

#### `run_code_reviewer(file_path: str) -> dict`
Review a file for issues.

#### `run_documentation(changed_files: list[str]) -> dict`
Update README/API docs/CHANGELOG.

#### `run_devteam(idea: str) -> dict`
Run the full pipeline.

#### `confirm_scaffold(target: str, files: dict) -> list[str]`
Write approved scaffold files to disk.

#### `get_project_context() -> dict`
Return current project context.

---

## License

MIT
