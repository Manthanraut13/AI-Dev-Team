# Manual Work Guide
## AI Dev Team — Universal Coding Platform Plugin (v2)

**Version:** 1.0 · **Date:** 2026-08-10 · **Status:** Draft — matches IMPLEMENTATION_PLAN.md
This guide is the **operator's manual** — what to install, configure, run, verify, and how to use the AI Dev Team agents inside your coding platform.

---

## 1. Prerequisites

| Item | Requirement | Check |
|------|-------------|-------|
| Python | **3.12+** | `python --version` |
| Git | Any (Windows: Git for Windows for hooks) | `git --version` |
| Groq API key | Required (all 8 agents) | `GROQ_API_KEY` |
| LangSmith | Optional (tracing) | `LANGCHAIN_API_KEY` |
| Tavily / Exa / Firecrawl | Optional (Research agent) | keys |
| GitHub token | Optional (Docs auto-commit, Phase 8) | `GITHUB_TOKEN` |
| Qdrant | Optional (long-term memory) — runs locally | `docker run -p 6333:6333 qdrant/qdrant` |

> The plugin **works with just a Groq key.** Search, memory, and GitHub are optional upgrades that degrade gracefully when absent.

---

## 2. Install

```bash
# 1. From the repo root
pip install -r requirements.txt

# 2. Create .env (once)
cp .env.example .env
# fill in GROQ_API_KEY at minimum

# 3. Install the plugin for your platform
python install.py --platform claude-code    # or: cline | roocode | opencode | codex

# 4. Verify everything
python install.py --verify
```

`install.py` does three things:
1. Creates `.ai-devteam/config.toml` in your project
2. Writes the platform rules file (`CLAUDE.md` / `.clinerules` / `.roorules` / ...)
3. Registers the MCP server in your platform's config + installs the git post-commit hook

---

## 3. Configuration

### `.env` (secrets — never commit)
```env
GROQ_API_KEY=...
LANGCHAIN_API_KEY=...        # optional
TAVILY_API_KEY=...           # optional
EXA_API_KEY=...              # optional
FIRECRAWL_API_KEY=...        # optional
GITHUB_TOKEN=...             # optional
QDRANT_URL=http://localhost:6333
```

### `.ai-devteam/config.toml` (behavior)
```toml
[plugin]
platform = "claude-code"   # or "auto"
auto_trigger = true
output_dir = ".ai-devteam"

[agents]
enabled = ["product_manager", "architect", "qa", "reviewer", "docs"]
disabled = ["frontend_dev"]   # disable specific agents here

[memory]
qdrant_url = "http://localhost:6333"
```

---

## 4. Using the Agents

### Slash commands (Claude Code, Cline, Roo, etc.)

| Command | MCP tool | What happens |
|---------|----------|--------------|
| `/pm <idea>` | `run_product_manager` | Writes `.ai-devteam/requirements.md` |
| `/architect` | `run_architect` | Writes `.ai-devteam/architecture.md` |
| `/research <topic>` | `run_research` | Writes `.ai-devteam/research/<topic>.md` |
| `/review` | `run_code_reviewer` | Reviews current file → `.ai-devteam/reviews/` |
| `/test` | `run_qa_engineer` | Generates tests → `.ai-devteam/tests/` |
| `/docs` | `run_documentation` | Updates README + changelog |
| `/backend <spec>` / `/frontend <spec>` | `run_backend_dev` / `run_frontend_dev` | Scaffolds files — **asks confirmation first** |
| `/devteam <idea>` | `run_devteam` | Full pipeline: PM → Architect → Backend/Frontend → QA/Review → Docs |
| *(no command)* | `get_project_context` | Returns current project state |

### Automatic triggers (when `auto_trigger = true`)

| You do this | Agents fire |
|-------------|-------------|
| Save a `.py` / `.ts` / `.tsx` file | QA Engineer + Code Reviewer (parallel, debounced 2s) |
| Save a file with an unknown import | Research Agent |
| `git commit` | Documentation Agent |
| New/empty project | Product Manager + Architect |

---

## 5. Output Location

Everything the agents produce lives in `.ai-devteam/` — never cluttering your source:

```
.ai-devteam/
├── config.toml               ← your config
├── project_context.json      ← live project state (agents read/update this)
├── requirements.md           ← Product Manager
├── architecture.md           ← Architect
├── research/<topic>.md       ← Research
├── reviews/<filename>.md     ← Code Reviewer
├── tests/…                   ← QA Engineer (mirrors saved file path)
└── logs/
    └── agent_activity.log    ← every agent run (start/end + result)
```

Scaffold agents (`backend_dev`, `frontend_dev`) are the exception — they write real files **to your project tree, but only after you approve** (the platform shows you the generated files first).

---

## 6. Verification Checklist

Run `python install.py --verify`. All green looks like:

```
✓ GROQ_API_KEY         set
✓ LANGCHAIN_API_KEY    set
✓ TAVILY_API_KEY       set
✓ EXA_API_KEY          set
✓ FIRECRAWL_API_KEY    set
✓ GITHUB_TOKEN         set
✓ Qdrant               reachable at http://localhost:6333   (optional)
✓ MCP server           starts successfully
✓ Platform             claude-code — CLAUDE.md present
✓ Git hooks            post-commit installed
```

Manual smoke test (Claude Code):
```
claude mcp list                      → ai-dev-team listed
# then in a project:
/architect
# → .ai-devteam/architecture.md exists and is non-empty
```

---

## 7. Troubleshooting

| Problem | Likely cause | Fix |
|---------|--------------|-----|
| "No Groq API key" error | `.env` missing/empty | `cp .env.example .env`, fill `GROQ_API_KEY` |
| Agents slow to start (~1–2 min first call) | Cold LLM-import on this machine — **known, not a hang** | Wait; subsequent calls are fast. Keep the MCP server alive |
| `429 rate limit` | Groq quota | Built-in retry (up to 3×, backoff); wait or upgrade tier |
| Invalid JSON from LLM | Model drift | Auto-retry with schema reminder (up to 3×) |
| Agent timeout (>60s) | Slow LLM | Killed + logged to `agent_activity.log`; re-run |
| Qdrant errors | Qdrant container down | **Ignored by design** — agents run with `project_context.json` only. Start Qdrant to re-enable LTM |
| Research agent "no results" | No Tavily/Exa/Firecrawl keys | Add keys, or accept requirement-level research without web |
| Git commit trigger doesn't fire | Hook not installed / Windows shell | `python install.py --hooks-only`; on Windows ensure Git for Windows (hook uses `sh`) |
| MCP server won't register | FastMCP missing | `pip install fastmcp`; re-run `install.py --verify` |

---

## 8. Platform-Specific Notes

| Platform | Install flag | Rules file | MCP registration |
|----------|--------------|------------|------------------|
| Claude Code | `--platform claude-code` | `CLAUDE.md` | `~/.claude/claude.json` |
| Cline | `--platform cline` | `.clinerules` | VS Code `settings.json` |
| Roo Code | `--platform roocode` | `.roorules` | Roo modes + settings |
| OpenCode | `--platform opencode` | `opencode.json` block | `~/.config/opencode/config.json` |
| Codex CLI | `--platform codex` | `codex.json` block | `~/.codex/config.json` |
| Generic MCP | — (manual) | — | `python plugin/server.py --transport http --port 8765` |

---

## 9. Safety Rules (for the operator)

1. **Never commit `.env`** — it's in `.gitignore`.
2. **Scaffold agents ask before writing** — don't approve generated files you haven't skimmed.
3. **Agent output never overwrites your source** except via explicit approval.
4. **Qdrant down ≠ broken plugin** — it's an enhancement, not a dependency.
