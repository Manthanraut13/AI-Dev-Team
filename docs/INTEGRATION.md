# Integration Guide

## Remote (Horizon — Recommended)

The server is deployed at: `https://ai-dev-team.fastmcp.app/mcp`

### OpenCode

Edit `~/.config/opencode/opencode.json`:

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

Restart OpenCode. The 11 tools appear in the tool palette.

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

Restart Claude Code. Type `/mcp` to verify.

### Cline / Roo Code

Same as Claude Code — add `.mcp.json` to your project root.

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

| Platform | Remote (Horizon) | Local (stdio) |
|----------|------------------|---------------|
| OpenCode | `opencode.json` | `opencode.json` |
| Claude Code | `.mcp.json` | `.mcp.json` |
| Cline | `.mcp.json` | `.mcp.json` |
| Roo Code | `.mcp.json` | `.mcp.json` |
| Codex CLI | `~/.codex/config.json` | `~/.codex/config.json` |
