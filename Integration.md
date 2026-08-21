# Integration Guide

## Deploy to Horizon (Recommended)

Horizon is FastMCP's managed cloud for MCP servers. Free tier available.

### Setup

```bash
pip install fastmcp
fastmcp auth login
```

### Deploy

```bash
cd "C:\Users\ADMIN\Desktop\AI Dev Team"
fastmcp deploy plugin/server.py --name ai-dev-team
```

This gives you a public URL like:
```
https://ai-dev-team-abc123.prefect.io/mcp
```

### Connect from OpenCode

Edit `~/.config/opencode/opencode.jsonc`:

```json
{
  "mcp": {
    "ai-dev-team": {
      "type": "remote",
      "url": "https://ai-dev-team-abc123.prefect.io/mcp"
    }
  }
}
```

Restart OpenCode. The tools appear in the tool palette.

### Connect from Claude Code

Create `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "ai-dev-team": {
      "type": "remote",
      "url": "https://ai-dev-team-abc123.prefect.io/mcp"
    }
  }
}
```

Restart Claude Code. Type `/mcp` to verify.

### Connect from Cline / Roo Code

Same as Claude Code — add the `.mcp.json` to your project root.

---

## Local Development

### Run locally (stdio)

```bash
python -m plugin.server --transport stdio
```

### Run locally (HTTP)

```bash
python -m plugin.server --transport http --port 8765
```

### OpenCode local config

```json
{
  "mcp": {
    "ai-dev-team": {
      "type": "local",
      "command": "python",
      "args": ["-m", "plugin.server"]
    }
  }
}
```

---

## API Keys

| Key | Required | Purpose |
|-----|----------|---------|
| `GROQ_API_KEY` | Yes | LLM inference (all agents) |
| `TAVILY_API_KEY` | No | Web search (Research agent) |
| `EXA_API_KEY` | No | Web search (Research agent) |
| `FIRECRAWL_API_KEY` | No | Web scraping (Research agent) |
| `GITHUB_TOKEN` | No | GitHub automation |
| `QDRANT_URL` | No | Long-term memory |

Get a Groq key at https://console.groq.com (free tier available).

---

## Supported Platforms

| Platform | Local | Remote (Horizon) |
|----------|-------|------------------|
| Claude Code | `.mcp.json` | `.mcp.json` |
| OpenCode | `opencode.jsonc` | `opencode.jsonc` |
| Cline | `.mcp.json` | `.mcp.json` |
| Roo Code | `.mcp.json` | `.mcp.json` |
| Codex CLI | `~/.codex/config.json` | `~/.codex/config.json` |
