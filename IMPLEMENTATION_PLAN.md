# Implementation Plan
## AI Dev Team — Universal Coding Platform Plugin (v2)

**Version:** 1.0 · **Date:** 2026-08-10 · **Status:** Draft — awaiting build order
**Source docs:** PRD.md (v2.0), Techstack.md, Workflow.md, Agent.md, Integration.md

---

## 1. What Changed (v1 Web App → v2 Plugin)

| Dimension | v1 (current on disk) | v2 (target) |
|-----------|---------------------|-------------|
| Frontend | Next.js web UI (`frontend/`) | **None** — results surface inside the user's coding platform |
| Backend | FastAPI HTTP server + sessions/preview (`backend/app/api/*`, `services/*`) | **No HTTP server** — FastMCP server on stdio |
| Agent interface | `*_node(state: AgentState) -> AgentState` (LangGraph node) | `async def *_agent(input) -> <Name>Output` (MCP tool) |
| Memory | `short_term.py` state helpers + `long_term.py` (Qdrant) | `memory/context.py` (project_context.json) + `memory/long_term.py` (Qdrant) |
| Activation | User clicks Run in web UI | Event-driven: file save / commit / slash command |
| Package | `backend/app/` | `plugin/` (new canonical package at repo root) |

---

## 2. Key Decisions (need your call before Phase 1)

| # | Decision | Recommendation | Alternatives |
|---|----------|----------------|--------------|
| D1 | **Repo layout** | Build `plugin/` **inside this repo root**, port agent code from `backend/`, then retire `backend/` + `frontend/` once the plugin is verified | Fresh clean `ai-dev-team-plugin/` subfolder and delete old web app entirely |
| D2 | **Orchestration** | Agents are **standalone** MCP tools (per Agent.md). The `/devteam` pipeline is a thin async orchestrator calling agents in sequence. LangGraph optional later | Keep the full v1 LangGraph graph as the pipeline engine |
| D3 | **Primary platform** | **Claude Code** first (stdio MCP — verifiable in this very session), then Cline/Roo/OpenCode/Codex rule-file generators | All platforms in parallel |
| D4 | **Qdrant (LTM)** | Wire in but **degrade gracefully** (skip lookup when Qdrant is down — per Workflow §11) from day 1 | Hard dependency (must run Qdrant container) |
| D5 | **Old code** | Keep `backend/` + `frontend/` on disk (unused) until Phase 7, then delete after your confirmation | Delete immediately |

---

## 3. Reuse Audit (what ports vs. rewrites vs. new)

### Port as-is (fix imports only: `app.*` → `plugin.*`)
- `backend/app/utils/llm.py` → `plugin/utils/llm.py` (get_llm, invoke_with_retry — verified, good)
- `backend/app/utils/retry.py` → `plugin/utils/retry.py`
- `backend/app/memory/long_term.py` → `plugin/memory/long_term.py` (MemoryService class — verified, complete)
- `backend/app/tools/search.py` → `plugin/tools/search.py` (Tavily)
- `backend/app/tools/crawl.py` → `plugin/tools/crawl.py` (Firecrawl)
- `backend/app/tools/github.py` → `plugin/tools/github.py` (Phase 8 optional)
- `backend/app/utils/files.py` → `plugin/utils/files.py` (if still relevant)

### Rewrite (new interface, reuse core logic)
- `backend/app/config.py` → `plugin/config.py` — **strip** DB/Clerk/Supabase/CORS; keep model routing + API keys
- `backend/app/memory/short_term.py` → `plugin/memory/context.py` — state helpers → **file-based** `project_context.json` read/write
- `backend/app/schemas/outputs.py` → `plugin/schemas/outputs.py` — expand to all 8 Agent.md output schemas
- All `backend/app/agents/*.py` → `plugin/agents/*.py` — node signature → `async def *_agent(...) -> <Name>Output`; keep prompt + LLM call + schema + retry

### New (doesn't exist anywhere)
- `plugin/server.py` (FastMCP, 9 tools)
- `plugin/tools/output.py` (write_agent_output, log_activity)
- `plugin/triggers/watcher.py` (watchdog), `plugin/triggers/git_hook.py`
- `plugin/integrations/{claude_code,cline,roocode,opencode,codex}.py`
- `install.py`, `plugin/scripts/init_qdrant.py`
- `plugin/graph/pipeline.py` (D2 orchestrator) + `plugin/graph/routers.py` (trigger mapping)
- `pyproject.toml`, `.ai-devteam/` output layer, test suite

### Retire (v1 web-app-only)
`frontend/` · `backend/app/api/*` · `backend/app/services/*` · `backend/app/supervisor/*` · `backend/app/database.py` · `backend/app/models/` · `backend/alembic/` · `docker-compose.yml` · `backend/Dockerfile` · `frontend/Dockerfile` · Clerk/Supabase/Postgres env keys · CORS

---

## 4. Build Phases

> Each phase ends with an **acceptance check**. Do not proceed to the next phase until it passes.

---

### Phase 0 — Decisions & Scaffold (0.5–1 hr)
**Do:** Confirm D1–D5. Lock `.env` key list. Create package skeleton.

**Tasks:**
- [ ] Confirm decisions D1–D5
- [ ] Create `plugin/` package: `__init__.py`, empty sub-packages `agents/ graph/ memory/ tools/ triggers/ integrations/ scripts/ schemas/ utils/`
- [ ] New `requirements.txt` at root (see §5)
- [ ] New `pyproject.toml`

**Acceptance:** `python -c "import plugin; print(plugin.__file__)"` works.

---

### Phase 1 — Shared Core (1–2 hrs)
**Do:** Every agent depends on this; build it first, test it hard.

**Tasks:**
- [ ] `plugin/config.py` — Settings (Groq/LangSmith/search/GitHub/Qdrant + model constants). **Drops** DB/Clerk/Supabase/CORS
- [ ] `plugin/paths.py` — resolve project root, `.ai-devteam/` structure (config.toml, project_context.json, logs/, reviews/, tests/, research/)
- [ ] `plugin/memory/context.py` — `load_context()`, `save_context()`, plus `update_context()` (merge new agent output)
- [ ] `plugin/tools/output.py` — `write_agent_output(agent_name, filename, content)`, `log_activity(...)`, `log_to(agent_activity.log)`
- [ ] `plugin/utils/llm.py` + `plugin/utils/retry.py` — port from backend
- [ ] `plugin/schemas/outputs.py` — all 8 Agent.md output schemas: `PMOutput, ArchitectOutput, ResearchOutput, BackendDevOutput, FrontendDevOutput, QAOutput, ReviewOutput, DocsOutput`
- [ ] `.env.example` — reduce to plugin keys only (drop DB/Clerk/Supabase)
- [ ] `plugin/memory/long_term.py` — port MemoryService, swap import to `plugin.config`

**Acceptance:**
- `python -c "from plugin.memory.context import load_context"` imports clean
- `write_agent_output` creates `.ai-devteam/...` files; `log_activity` appends to `agent_activity.log`
- All 8 Pydantic schemas import and validate a sample payload

---

### Phase 2 — Port the 8 Agents (3–4 hrs)
**Do:** Port `backend/app/agents/*` → `plugin/agents/*`. This is the bulk of the work.

**Per-agent recipe (from Agent.md Core Rules):**
1. Change imports `app.*` → `plugin.*`
2. Change signature: `def X_node(state)` → `async def X_agent(...) -> XOutput`
3. Keep: system prompt, LLM call, `.with_structured_output(<Name>Output)`, retry wrapper
4. Add at start: `load_context()`; at end: `save_context()` (with new output) + `log_activity()`
5. Write result to `.ai-devteam/<agent>/`

**Agents:**
| File | Input → Output | Notes |
|------|----------------|-------|
| `product_manager.py` | `idea: str` → `PMOutput` | v1 logic is 1:1; rewrap only |
| `architect.py` | `requirements: list[str] \| None` → `ArchitectOutput` | add Qdrant pattern lookup (Phase 6) |
| `research.py` | `topic: str` → `ResearchOutput` | v1 is a *graph node* that extracts terms from state; rewrite as `research_agent(topic)` using search+crawl+LLM synthesize per Agent.md |
| `backend_dev.py` | `spec: str` → `BackendDevOutput` (files, requires_confirmation=True) | v1 writes files directly; v2 returns files + requires confirmation |
| `frontend_dev.py` | `spec: str` → `FrontendDevOutput` | same as backend_dev |
| `qa_engineer.py` | `file_path: str` → `QAOutput` | adapt to write `.ai-devteam/tests/<mirror>` |
| `code_reviewer.py` | `file_path: str` → `ReviewOutput` | v1 ReviewOutput is close; expand to Agent.md fields (severity, security_flags, perf) |
| `documentation.py` | `changed_files: list[str]` → `DocsOutput` | v1 node → rewrap; diff-patch README rule |

**Acceptance:** A throwaway test script calls each agent with a real Groq key; each returns a validated output object and writes its `.ai-devteam/` artifacts. `python -m py_compile` on all plugin files passes.

---

### Phase 3 — MCP Server (1–2 hrs)
**Do:** Expose agents as MCP tools.

**Tasks:**
- [ ] Add `fastmcp` dependency
- [ ] `plugin/server.py` — `FastMCP("ai-dev-team")` with 9 tools:
  - `run_product_manager(idea)` · `run_architect(requirements?)` · `run_research(topic)`
  - `run_backend_dev(spec)` · `run_frontend_dev(spec)`
  - `run_qa_engineer(file_path)` · `run_code_reviewer(file_path)` · `run_documentation(changed_files)`
  - `get_project_context()`
- [ ] `--transport stdio | http --port 8765` CLI
- [ ] Load `.env` (python-dotenv) before tools run; handle missing Groq key with a clear error

**Acceptance:** `python plugin/server.py` starts clean. An MCP test client (or `mcp` inspector) lists 9 tools and `run_product_manager("todo app")` returns validated output. **This is the "plugin works" milestone.**

---

### Phase 4 — Event Triggers + `/devteam` Pipeline (2–3 hrs)
**Status:** ✅ COMPLETE
**Do:** Automatic activation + the full-pipeline command.

**Tasks:**
- [ ] `plugin/triggers/watcher.py` — watchdog observer (background task)
  - `.py/.ts/.tsx` save → QA + Reviewer in **parallel**, debounce 2s
  - unknown `import` detected (Agent.md `extract_unknown_imports`) → Research
- [ ] `plugin/triggers/git_hook.py` — post-commit → Documentation agent (git diff → changed_files)
- [ ] `plugin/graph/pipeline.py` — `/devteam` orchestrator: PM → Architect → (Backend + Frontend) → QA + Review → Docs; collect agent outputs into a single summary; surface scaffold files with `requires_confirmation` flow
- [ ] `plugin/graph/routers.py` — trigger→agent map (mirror Workflow §4)
- [ ] Add `run_devteam(idea)` MCP tool calling the pipeline
- [ ] `plugin/scripts/init_qdrant.py` — create collections (run if Qdrant available)

**Acceptance:** Watching a test folder: saving a `.py` file auto-writes a review + test within ~5s (debounced). A fake `git commit` invokes the docs agent. `run_devteam` runs the full chain end-to-end.

---

### Phase 5 — Platform Integration + `install.py` (2–3 hrs)
**Status:** ✅ COMPLETE
**Do:** One-command install per platform.

**Tasks:**
- [ ] `plugin/integrations/` generators, each producing the platform rules file + MCP config snippet (per Integration.md):
  - `claude_code.py` → `CLAUDE.md` + `~/.claude/claude.json` entry
  - `cline.py` → `.clinerules` + VS Code settings
  - `roocode.py` → `.roorules` + custom mode
  - `opencode.py` → `opencode.json` MCP block
  - `codex.py` → `~/.codex/config.json` entry
- [ ] `install.py` CLI: `--platform <name>`, `--hooks-only`, `--verify`, `--init`
  - `--init`: create `.ai-devteam/config.toml` + copy `.env.example → .env` (if absent)
  - `--verify`: check all keys, Qdrant reachability, MCP server start, platform file present, hook installed (mirror Integration.md Part 4)
- [ ] Git hook install that works on **Windows** (Git for Windows bash shim) as well as Unix

**Acceptance:** `python install.py --platform claude-code` writes `CLAUDE.md` + registers MCP server; `python install.py --verify` reports all-green (with keys set). Claude Code `mcp list` shows `ai-dev-team`.

---

### Phase 6 — Memory Wiring + Error Handling (1–2 hrs)
**Status:** ✅ COMPLETE
**Do:** Close the loop on LTM + resilience.

**Tasks:**
- [ ] Qdrant wiring: architect → `qdrant_search("architectures")`; backend/frontend_dev → `qdrant_search("patterns")`; research → `qdrant_upsert("references")`; every agent end → upsert output
- [ ] All Qdrant calls wrapped so a down Qdrant never fails an agent (Workflow §11: "skip LTM, run with project_context only")
- [ ] Timeout guard (60s agent kill), retry on invalid JSON up to 3×, `error_handler` on pipeline failures → log + notify
- [ ] `project_context.json` lifecycle complete: created on `--init`, updated by every agent, read at startup

**Acceptance:** With Qdrant container stopped, all agents still work. With it running, architect retrieves a past architecture and references it in output. `agent_activity.log` shows start/end for every run.

---

### Phase 7 — Testing, E2E, Cleanup (2–4 hrs)
**Status:** ✅ COMPLETE (74/74 tests passing)
**Do:** Prove it works inside a real coding platform, then retire the web app.

**Tasks:**
- [ ] Unit tests (`pytest` + `pytest-asyncio`): each agent with mocked LLM, `server.py` tool registry, watcher debounce, `install.py --verify` logic
- [ ] **E2E in this session:** `install.py --platform claude-code` → invoke `/pm`, `/architect`, `/devteam` via MCP tools → confirm outputs in `.ai-devteam/`
- [ ] Update `README.md` (plugin install/usage), finalize `.env.example`, write `WORK_GUIDE.md`
- [ ] **Delete `backend/` + `frontend/` + `docker-compose.yml` (after your explicit OK)** — DB/Clerk/Supabase keys removed from `.env`
- [ ] `git init` + first commit (only when you order)

**Acceptance:** Fresh-machine walkthrough passes: install → verify → build a sample project with `/devteam` → all artifacts in `.ai-devteam/`.

---

### Phase 8 — Stretch (optional, after your order)
- [ ] GitHub automation: auto-commit + PR creation (`plugin/tools/github.py`, `github_automation` agent) — reuses `backend/app/tools/github.py`
- [ ] LangSmith tracing re-verified for all plugin LLM calls
- [ ] Multi-platform live verification (Cline/Roo/OpenCode/Codex)

---

## 5. Dependencies (`requirements.txt`)

```text
fastmcp
langgraph                 # optional (D2); pipeline may be pure-async
langchain
langchain-groq
langchain-community
langchain-huggingface
langsmith
sentence-transformers
qdrant-client
pydantic
pydantic-settings
gitpython
tavily-python
firecrawl-py
exa-py
watchdog
python-dotenv
httpx
pytest
pytest-asyncio
```
**Removed vs v1:** fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, python-multipart.

---

## 6. Risks & Notes

- **Cold import is slow** (~2 min first LLM import on this machine — known; not a hang). Same applies to plugin startup. Document in WORK_GUIDE.
- **Windows git hooks** use Git-for-Windows `sh`; install.py must emit a `.sh` hook + fallback note. Watchdog works on Windows.
- **MCP server lifetime** — for stdio transport, the platform (Claude Code) spawns the server on demand; no port, no orphan processes (v1's port-8001 problem disappears).
- **No port conflicts:** the plugin replaces the FastAPI backend on 8001 entirely.
