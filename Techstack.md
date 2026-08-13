# Tech Stack
## AI Dev Team — Universal Coding Platform Plugin

---

## 1. Plugin Core Layer

| Tool | Role | Notes |
|------|------|-------|
| **Python 3.12** | Plugin runtime | All agent logic, MCP server |
| **FastMCP** | MCP server framework | Exposes agent tools to platforms via MCP protocol |
| **LangGraph** | Agent orchestration | State machine connecting all agents |
| **LangChain** | Agent internals | Prompt building, LLM wrappers, tool calling |
| **Pydantic v2** | Structured output validation | All agent outputs validated before writing to disk |

---

## 2. Platform Integration Layer

| Platform | Integration Mechanism | Config File Generated |
|----------|-----------------------|-----------------------|
| **Claude Code** | MCP Server (stdio) | `CLAUDE.md` |
| **Cline** | MCP Server + rules | `.clinerules` |
| **Roo Code** | MCP Server + modes | `.roorules` |
| **OpenCode** | MCP Server (stdio) | `opencode.json` MCP block |
| **Codex CLI** | MCP Server (stdio) | `codex.json` MCP block |
| **VS Code** | VS Code Extension wrapping MCP | `settings.json` update |

All platforms consume the same underlying MCP server — only the config file format differs.

---

## 3. MCP Server Design

```
Plugin MCP Server (local, stdio transport)
├── tool: run_product_manager
├── tool: run_architect
├── tool: run_research
├── tool: run_backend_dev
├── tool: run_frontend_dev
├── tool: run_qa_engineer
├── tool: run_code_reviewer
├── tool: run_documentation
└── tool: get_project_context
```

Each tool accepts a JSON input and returns a structured JSON result. The platform agent calls these tools based on rules files or explicit user commands.

---

## 4. AI & LLM Layer

| Tool | Role |
|------|------|
| **Groq API** | LLM inference (free, fast) |
| **LangSmith** | Tracing all LLM calls |
| `llama-3.3-70b-versatile` | Planning, requirements, architecture |
| `qwen/qwen3-coder` | Code generation (backend, frontend, tests) |
| `deepseek-r1-distill-llama-70b` | Code review and analysis |
| `gemma2-9b-it` | Documentation generation |

---

## 5. Memory Layer

| Layer | Technology | Storage Location |
|-------|------------|-----------------|
| Project Context (STM) | JSON file | `.ai-devteam/project_context.json` |
| Long-Term Memory | Qdrant (local Docker) | `qdrant_data/` volume |
| Agent Output Cache | Markdown/JSON files | `.ai-devteam/<agent>/` |

---

## 6. Tool Integrations

| Tool | Purpose | Agent |
|------|---------|-------|
| **Tavily** | Web search | Research Agent |
| **Exa** | Semantic search | Research Agent |
| **Firecrawl** | Docs crawling | Research Agent |
| **GitPython** | Git operations | Documentation Agent, GitHub node |
| **GitHub REST API** | PR creation | GitHub Automation |
| **watchdog** (Python) | File system events | Event trigger system |
| **GitPython** | Detect commits | Documentation Agent trigger |

---

## 7. Event Trigger System

```python
# Uses Python watchdog to monitor file system
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
```

| Event | Agent(s) Triggered |
|-------|--------------------|
| `.py` / `.ts` / `.tsx` file saved | QA Engineer, Code Reviewer |
| New repo / empty project detected | Product Manager, Architect |
| `git commit` detected | Documentation Agent |
| Unknown `import` in saved file | Research Agent |
| Slash command from platform | Specific agent by name |

---

## 8. Output Structure

All plugin outputs go to `.ai-devteam/` in the project root — never cluttering the user's source code.

```
.ai-devteam/
├── config.toml               ← User configuration
├── project_context.json      ← Live project state (STM)
├── requirements.md           ← Product Manager output
├── architecture.md           ← Architect output
├── research/
│   └── <topic>.md            ← Research Agent findings
├── reviews/
│   └── <filename>.md         ← Code Reviewer output per file
├── tests/                    ← QA Agent generated tests
└── logs/
    └── agent_activity.log    ← What ran, when, result summary
```

---

## 9. Dependency Files

### `requirements.txt`
```
fastmcp
langgraph
langchain
langchain-groq
langsmith
qdrant-client
pydantic
gitpython
tavily-python
firecrawl-py
exa-py
watchdog
python-dotenv
toml
```

---

## 10. Environment Variables

```env
# LLM
GROQ_API_KEY=

# Tracing
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=ai-dev-team-plugin

# Search & Crawl
TAVILY_API_KEY=
EXA_API_KEY=
FIRECRAWL_API_KEY=

# GitHub
GITHUB_TOKEN=
GITHUB_USERNAME=

# Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

---

## 11. Folder Structure (Plugin Repo)

```
ai-dev-team-plugin/
├── plugin/
│   ├── server.py              ← FastMCP server entry point
│   ├── agents/
│   │   ├── product_manager.py
│   │   ├── architect.py
│   │   ├── research.py
│   │   ├── backend_dev.py
│   │   ├── frontend_dev.py
│   │   ├── qa_engineer.py
│   │   ├── code_reviewer.py
│   │   └── documentation.py
│   ├── graph/
│   │   ├── graph.py           ← LangGraph definition
│   │   ├── state.py           ← AgentState
│   │   └── routers.py         ← Conditional edge functions
│   ├── memory/
│   │   ├── context.py         ← project_context.json read/write
│   │   └── long_term.py       ← Qdrant helpers
│   ├── triggers/
│   │   └── watcher.py         ← watchdog file system monitor
│   ├── integrations/
│   │   ├── claude_code.py     ← Generates CLAUDE.md
│   │   ├── cline.py           ← Generates .clinerules
│   │   ├── roocode.py         ← Generates .roorules
│   │   └── opencode.py        ← Generates opencode.json MCP block
│   └── tools/
│       ├── search.py
│       ├── crawl.py
│       └── github.py
├── install.py                 ← One-command installer
├── .env.example
├── pyproject.toml
└── README.md
```
