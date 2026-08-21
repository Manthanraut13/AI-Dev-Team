# Work Guide

## Deploy to Horizon (FastMCP Cloud)

### Prerequisites

- Python 3.12+
- Groq API key (free at https://console.groq.com)
- FastMCP CLI

### Step 1: Install & Login

```bash
pip install fastmcp
fastmcp auth login
```

### Step 2: Deploy

```bash
cd "C:\Users\ADMIN\Desktop\AI Dev Team"
fastmcp deploy plugin/server.py --name ai-dev-team
```

### Step 3: Get Your URL

```bash
fastmcp list
```

Copy the URL (e.g. `https://ai-dev-team-abc123.prefect.io/mcp`).

### Step 4: Configure Your Platform

**OpenCode** — edit `~/.config/opencode/opencode.jsonc`:
```json
{
  "mcp": {
    "ai-dev-team": {
      "type": "remote",
      "url": "YOUR_URL_HERE"
    }
  }
}
```

**Claude Code** — create `.mcp.json` in your project:
```json
{
  "mcpServers": {
    "ai-dev-team": {
      "type": "remote",
      "url": "YOUR_URL_HERE"
    }
  }
}
```

### Step 5: Test

Restart your platform. Type `/mcp` or check the tool palette for `ai-dev-team`.

---

## Local Development

### Run Server

```bash
python -m plugin.server --transport stdio   # for MCP clients
python -m plugin.server --transport http    # for testing
```

### Run Tests

```bash
pytest tests/ -v
```

### Test Agents Directly

```python
import asyncio
from plugin.agents.product_manager import product_manager_agent

result = asyncio.run(product_manager_agent("A todo app with auth"))
print(result.project_name)
print(result.functional_requirements)
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Required:
- `GROQ_API_KEY` — Groq API key

Optional:
- `TAVILY_API_KEY` — for web search
- `EXA_API_KEY` — for web search
- `FIRECRAWL_API_KEY` — for web scraping
- `GITHUB_TOKEN` — for GitHub automation
- `QDRANT_URL` — for long-term memory
