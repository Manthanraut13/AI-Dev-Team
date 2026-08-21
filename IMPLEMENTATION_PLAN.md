# Implementation Plan

## Current Status: v2.0 — Deployed to Horizon

### Phase 1-7: Complete
All agents, MCP server, triggers, integrations, and tests are done.

### Phase 8: Deployment
- [x] Deploy to Horizon (FastMCP cloud)
- [x] Update docs for remote MCP
- [x] Restructure repo

---

## Architecture

```
User's Coding Platform (OpenCode / Claude Code / Cline)
    │
    ▼
MCP Protocol (stdio or remote)
    │
    ▼
FastMCP Server (plugin/server.py)
    │
    ▼
AI Agents (8 agents via LangChain + Groq)
    │
    ▼
Output (.ai-devteam/ artifacts)
```

## Deployment Options

| Option | Command | Use Case |
|--------|---------|----------|
| **Horizon** | `fastmcp deploy` | Production, shared access |
| **Local stdio** | `python -m plugin.server` | Single user, offline |
| **Local HTTP** | `python -m plugin.server --transport http` | Testing, debugging |
