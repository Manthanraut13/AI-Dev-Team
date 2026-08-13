# Integration Guide
## AI Dev Team Plugin — Platform Setup & API Keys

> All keys go into a `.env` file at the plugin root. Never commit `.env` to git.

---

## Quick Install (Any Platform)

```bash
git clone https://github.com/yourname/ai-dev-team-plugin
cd ai-dev-team-plugin
pip install -r requirements.txt
cp .env.example .env
# Fill in .env values using the guide below, then:
python install.py --platform claude-code   # or: cline | roocode | opencode | codex
```

`install.py` will:
- Create `.ai-devteam/config.toml` in your project
- Generate the correct platform rules file
- Register the MCP server in the platform's config
- Install the git post-commit hook

---

## Part 1: API Keys

---

### 1. Groq API

**Used by:** All 8 agents (LLM inference — free and fast)

1. Go to [https://console.groq.com](https://console.groq.com) → Sign up
2. **API Keys** → **Create API Key**
3. Copy the key

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

**Verify:**
```bash
curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

---

### 2. LangSmith

**Used by:** Automatic tracing of all LLM calls

1. Go to [https://smith.langchain.com](https://smith.langchain.com) → Sign up (free)
2. **Settings** → **API Keys** → **Create API Key**
3. Create a project called `ai-dev-team-plugin`

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls__xxxxxxxxxxxxxxxxxxxx
LANGCHAIN_PROJECT=ai-dev-team-plugin
```

No code changes needed — tracing activates automatically.

---

### 3. Tavily Search

**Used by:** Research Agent (web search)

1. Go to [https://tavily.com](https://tavily.com) → Sign up (1,000 free searches/month)
2. **Dashboard** → copy API Key

```env
TAVILY_API_KEY=tvly-xxxxxxxxxxxxxxxxxxxx
```

---

### 4. Exa

**Used by:** Research Agent (semantic search)

1. Go to [https://exa.ai](https://exa.ai) → Sign up (free credits on signup)
2. **Dashboard** → **API Keys** → **Create Key**

```env
EXA_API_KEY=xxxxxxxxxxxxxxxxxxxx
```

---

### 5. Firecrawl

**Used by:** Research Agent (docs crawling)

1. Go to [https://firecrawl.dev](https://firecrawl.dev) → Sign up (500 free credits)
2. **Dashboard** → **API Keys**

```env
FIRECRAWL_API_KEY=fc-xxxxxxxxxxxxxxxxxxxx
```

---

### 6. GitHub Token

**Used by:** Documentation Agent (auto-commit), GitHub Automation (PR creation)

1. [https://github.com/settings/tokens](https://github.com/settings/tokens)
2. **Generate new token (classic)**
3. Name: `ai-dev-team-plugin` | Scopes: `repo`, `workflow`
4. Copy immediately after generation

```env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITHUB_USERNAME=your-github-username
```

**Verify:**
```bash
curl -H "Authorization: token $GITHUB_TOKEN" https://api.github.com/user
```

---

### 7. Qdrant (Local — Recommended)

**Used by:** All agents (long-term memory)

No API key needed for local. Start with Docker:

```bash
docker run -p 6333:6333 -v $(pwd)/qdrant_data:/qdrant/storage qdrant/qdrant
```

```env
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
```

Initialize collections after Qdrant starts:
```bash
python plugin/scripts/init_qdrant.py
```

**Qdrant Cloud (optional):**
1. [https://cloud.qdrant.io](https://cloud.qdrant.io) → Free 1GB cluster
2. Copy Cluster URL and API Key

```env
QDRANT_URL=https://xxxxxx.qdrant.io
QDRANT_API_KEY=xxxxxxxxxxxxxxxx
```

---

## Part 2: Platform-Specific Setup

---

### Claude Code

**How it works:** Plugin runs as an MCP server. Claude Code calls plugin tools directly. `CLAUDE.md` tells Claude when to auto-call each tool.

**Install:**
```bash
python install.py --platform claude-code
```

**What it does:**
1. Adds to `~/.claude/claude.json`:
```json
{
  "mcpServers": {
    "ai-dev-team": {
      "command": "python",
      "args": ["/path/to/plugin/server.py"],
      "env": { "GROQ_API_KEY": "..." }
    }
  }
}
```
2. Creates `CLAUDE.md` in your project root with tool usage instructions

**Manual verify:**
```bash
claude mcp list   # should show: ai-dev-team
```

---

### Cline (VS Code)

**How it works:** Plugin MCP server + `.clinerules` file instructs Cline when to call each tool.

**Install:**
```bash
python install.py --platform cline
```

**What it does:**
1. Adds MCP server to VS Code `settings.json`:
```json
{
  "cline.mcpServers": {
    "ai-dev-team": {
      "command": "python",
      "args": ["/path/to/plugin/server.py"]
    }
  }
}
```
2. Creates `.clinerules` in your project root

**Manual verify:**
Open VS Code → Cline panel → MCP Servers → `ai-dev-team` should appear as connected.

---

### Roo Code (VS Code)

**How it works:** Same MCP server + `.roorules` file configures Roo's custom mode behavior.

**Install:**
```bash
python install.py --platform roocode
```

**What it does:**
1. Adds MCP server to Roo Code settings (same `settings.json` structure as Cline)
2. Creates `.roorules` in your project root
3. Registers a custom Roo mode: `devteam` that pre-loads all plugin tools

**Manual verify:**
Roo Code panel → Settings → MCP → `ai-dev-team` listed.

---

### OpenCode

**How it works:** MCP server registered in `~/.config/opencode/config.json`.

**Install:**
```bash
python install.py --platform opencode
```

**What it does:**
Adds to `~/.config/opencode/config.json`:
```json
{
  "mcp": {
    "ai-dev-team": {
      "command": "python",
      "args": ["/path/to/plugin/server.py"],
      "type": "local"
    }
  }
}
```

---

### Codex CLI

**How it works:** MCP server added to Codex config. Slash commands invoke tools directly.

**Install:**
```bash
python install.py --platform codex
```

**What it does:**
Adds to `~/.codex/config.json`:
```json
{
  "mcpServers": [
    {
      "name": "ai-dev-team",
      "command": "python /path/to/plugin/server.py"
    }
  ]
}
```

---

### Any MCP-Compatible Platform (Generic)

The plugin exposes a standard MCP server on stdio. To connect any MCP-compatible platform manually:

```bash
# Start the server (stdio mode)
python plugin/server.py

# Or HTTP mode (for platforms that prefer HTTP transport)
python plugin/server.py --transport http --port 8765
```

Then register it in your platform's MCP config pointing to the same command.

---

## Part 3: Git Hook Setup

The Documentation Agent triggers on commits. The installer sets this up automatically. To install manually:

```bash
python install.py --hooks-only
```

This writes `.git/hooks/post-commit`:
```bash
#!/bin/bash
python /path/to/plugin/triggers/git_hook.py commit
```

---

## Part 4: Verify Full Installation

```bash
python install.py --verify
```

Output should show:
```
✓ GROQ_API_KEY         set
✓ LANGCHAIN_API_KEY    set
✓ TAVILY_API_KEY       set
✓ EXA_API_KEY          set
✓ FIRECRAWL_API_KEY    set
✓ GITHUB_TOKEN         set
✓ Qdrant               reachable at http://localhost:6333
✓ MCP server           starts successfully
✓ Platform             claude-code — CLAUDE.md present
✓ Git hooks            post-commit installed
```

---

## Part 5: Complete .env Reference

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

## Free Tier Summary

| Service | Free Allowance |
|---------|---------------|
| Groq | ~14,400 req/day |
| LangSmith | 5,000 traces/month |
| Tavily | 1,000 searches/month |
| Exa | Free credits on signup |
| Firecrawl | 500 credits on signup |
| GitHub | Unlimited |
| Qdrant (local) | Unlimited |
| Qdrant Cloud | 1GB free cluster |
