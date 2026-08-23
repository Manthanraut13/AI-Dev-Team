# AI Dev Team

MCP server that turns a natural language idea into a working software scaffold via AI agents.

Deployed on **Horizon (FastMCP Cloud)** — works with OpenCode, Claude Code, Cline, and any MCP-compatible platform.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env   # add GROQ_API_KEY
```

## Connect (Remote — Horizon)

The server is deployed at: `https://ai-dev-team.fastmcp.app/mcp`

### OpenCode

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "ai-dev-team": {
      "type": "remote",
      "url": "https://ai-dev-team.fastmcp.app/mcp"
    }
  }
}
```

### Claude Code

Create `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "ai-dev-team": {
      "type": "remote",
      "url": "https://ai-dev-team.fastmcp.app/mcp"
    }
  }
}
```

### Cline / Roo Code

Same as Claude Code — add `.mcp.json` to your project root.

## Connect (Local)

```bash
python -m plugin.server --transport stdio
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `run_product_manager` | Generate requirements from an idea |
| `run_architect` | Design API, DB schema, folder structure |
| `run_research` | Web search + synthesize findings |
| `run_backend_dev` | Scaffold FastAPI backend |
| `run_frontend_dev` | Scaffold Next.js frontend |
| `run_qa_engineer` | Generate tests for a file |
| `run_code_reviewer` | Review file for issues |
| `run_documentation` | Update README/API docs |
| `run_devteam` | Full pipeline (PM → Architect → Devs → QA → Review → Docs) |
| `confirm_scaffold` | Write approved scaffold files to disk |
| `get_project_context` | Return current project context |

## Example

Ask your coding agent:

> "Build me a todo app with user auth and task categories"

The agents will:
1. **Product Manager** — generate requirements and tasks
2. **Architect** — design API endpoints, DB schema, folder structure
3. **Backend Dev** — scaffold FastAPI code
4. **Frontend Dev** — scaffold Next.js code
5. **QA Engineer** — generate tests
6. **Code Reviewer** — review for issues
7. **Documentation** — generate README, API docs

## Documentation

- [Full Documentation](docs/DOCUMENTATION.md) — architecture, agents, API reference
- [Integration Guide](docs/INTEGRATION.md) — platform setup instructions
- [Changelog](docs/CHANGELOG.md) — version history

## Project Structure

```
AI-Dev-Team/
├── plugin/                # Core package
│   ├── server.py          # MCP server (entry point)
│   ├── config.py          # Settings
│   ├── agents/            # 8 AI agents
│   ├── graph/             # Pipeline orchestrator
│   ├── memory/            # Context + Qdrant LTM
│   ├── tools/             # Search, crawl, output
│   ├── triggers/          # File watcher + git hook
│   ├── integrations/      # Platform configs
│   ├── schemas/           # Pydantic v2 outputs
│   └── utils/             # LLM, retry, files, errors
├── tests/                 # Unit tests
├── docs/                  # Documentation
├── requirements.txt       # Dependencies
├── pyproject.toml         # Package config
└── .env.example           # Environment template
```

## Tech Stack

- **Server**: FastMCP (MCP protocol)
- **LLM**: Groq (GPT-OSS-120b, GPT-OSS-20b)
- **Agents**: LangChain + LangGraph
- **Memory**: Qdrant (optional, degrades gracefully)
- **Deployed**: Horizon (FastMCP Cloud)

## Environment Variables

| Key | Required | Purpose |
|-----|----------|---------|
| `GROQ_API_KEY` | Yes | LLM inference |
| `TAVILY_API_KEY` | No | Web search |
| `EXA_API_KEY` | No | Web search |
| `FIRECRAWL_API_KEY` | No | Web scraping |
| `GITHUB_TOKEN` | No | GitHub automation |
| `QDRANT_URL` | No | Long-term memory |

## License

MIT
