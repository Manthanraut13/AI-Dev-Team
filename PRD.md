# Product Requirements Document (PRD)
## AI Dev Team — Universal Coding Platform Plugin

**Version:** 2.0  
**Last Updated:** 2026-08-10  
**Status:** Active  

---

## 1. Overview

### 1.1 Product Summary
A universal plugin/extension that integrates an AI software development team into any coding agent platform (Claude Code, OpenCode, Codex CLI, Cline, Roo Code, etc.). When the user codes with their preferred AI platform, the dev team agents activate in the background — handling requirements, architecture, review, testing, and documentation automatically, without interrupting the user's flow.

### 1.2 Core Concept
```
User codes with Claude Code / Cline / Roo Code / OpenCode / Codex
                        │
                        ▼
           Plugin hooks into platform events
                        │
                        ▼
         AI Dev Team agents activate in background
                        │
                        ▼
    Results surface back in the same platform (comments, PRs, docs)
```

### 1.3 What Changes from a Web App
- **No separate frontend UI** — everything happens inside the user's existing coding platform
- **No manual trigger** — agents respond to platform events (file save, commit, PR open, prompt submission)
- **Platform-native output** — results appear as inline suggestions, comments, terminal output, or sidebar panels depending on the platform
- **Single install** — one plugin config file connects to all supported platforms

---

## 2. Supported Platforms

| Platform | Integration Type | Hook Mechanism |
|----------|-----------------|----------------|
| **Claude Code** | MCP Server | MCP tool calls, slash commands |
| **Cline** | MCP Server + `.clinerules` | MCP tools, Cline rules file |
| **Roo Code** | MCP Server + `.roorules` | MCP tools, Roo modes |
| **OpenCode** | MCP Server | MCP tool calls |
| **Codex CLI** | MCP Server + hooks | MCP tools |
| **VS Code + Copilot** | VS Code Extension | VS Code extension API |
| **Any MCP-compatible agent** | MCP Server | Standard MCP protocol |

---

## 3. Goals & Success Criteria

| Goal | Metric |
|------|--------|
| Zero-friction integration | User runs one install command; plugin works with their existing platform |
| Background operation | Agents run without blocking the user's coding session |
| Platform-agnostic | Same plugin works across all supported platforms via MCP |
| Agent specialization | Each agent has one clearly defined job and prompt scope |
| Persistent memory | Agents remember project context and past decisions across sessions |
| Surfaced output | Agent results appear natively inside the user's platform |

---

## 4. User Stories

| ID | Story | Priority |
|----|-------|----------|
| US-01 | As a user of Claude Code, when I describe a feature, the Product Manager agent auto-generates requirements in the background | P0 |
| US-02 | As a user, when I start a new project, the Architect agent produces a structure and schema without me asking | P0 |
| US-03 | As a user, when I write backend code, the QA agent auto-generates tests for the file I just edited | P0 |
| US-04 | As a user, when I save a file, the Code Reviewer agent runs silently and surfaces issues as comments | P1 |
| US-05 | As a user, when I commit code, the Documentation agent updates the README and changelog automatically | P1 |
| US-06 | As a user, I can invoke any agent explicitly via a slash command (`/architect`, `/review`, `/test`) | P1 |
| US-07 | As a user, the Research agent finds relevant docs/libraries when it detects unfamiliar packages | P2 |
| US-08 | As a user, I can see what the background agents did in a structured log | P2 |
| US-09 | As a user, agent memory persists across sessions so it knows the full project context | P2 |

---

## 5. Functional Requirements

### 5.1 Plugin Core

**FR-01: MCP Server**  
- Plugin runs as a local MCP server (`stdio` or `http` transport)
- Exposes one MCP tool per agent (e.g., `run_architect`, `run_qa`, `run_reviewer`)
- Compatible with any MCP-capable platform

**FR-02: Platform Rules Files**  
- Auto-generate `.clinerules` / `.roorules` / `CLAUDE.md` on install
- Rules files instruct the platform agent to call plugin tools at specific triggers

**FR-03: Event-Driven Agent Activation**  
- File save → QA Agent, Code Reviewer Agent
- New project / empty repo → Product Manager, Architect
- Commit → Documentation Agent
- Import of unknown package → Research Agent
- Explicit slash command → respective agent

**FR-04: Background Execution**  
- All agent calls are non-blocking (async)
- Results are written to: inline comments, `.ai-devteam/` output folder, or terminal panel
- User is notified with a subtle summary, not interrupted mid-prompt

### 5.2 Agent Requirements

**FR-05: Product Manager Agent**  
- Triggered when: user describes a new feature or project in their prompt
- Output: `requirements.md` written to `.ai-devteam/` folder

**FR-06: Architect Agent**  
- Triggered when: new project detected or user runs `/architect`
- Output: `architecture.md` with API design, DB schema, folder structure

**FR-07: Research Agent**  
- Triggered when: unknown import/library detected in edited file
- Output: summary written to `.ai-devteam/research/` with links and usage examples

**FR-08: Backend Developer Agent**  
- Triggered when: user explicitly requests or architecture is approved
- Output: scaffold files written to project directory

**FR-09: Frontend Developer Agent**  
- Triggered when: user explicitly requests via slash command
- Output: component and page scaffold files

**FR-10: QA Engineer Agent**  
- Triggered when: any `.py`, `.ts`, `.tsx` file is saved
- Output: test file written to `tests/` mirroring the saved file path

**FR-11: Code Reviewer Agent**  
- Triggered when: file is saved or on explicit `/review`
- Output: review comments written to `.ai-devteam/reviews/<filename>.md`

**FR-12: Documentation Agent**  
- Triggered when: git commit is detected
- Output: updates `README.md`, `docs/API.md`, `CHANGELOG.md`

### 5.3 Memory

**FR-13: Project Context Memory (Short-Term)**  
- Plugin maintains a `project_context.json` in `.ai-devteam/`
- Stores: project name, detected stack, active requirements, architecture decisions
- Loaded at plugin startup; updated after each agent run

**FR-14: Long-Term Memory (Qdrant)**  
- Embeds and stores: past agent outputs, decisions, code patterns
- Retrieved at start of each agent run to provide project context

### 5.4 Configuration

**FR-15: Single Config File**
```toml
# .ai-devteam/config.toml
[plugin]
platform = "claude-code"   # or "cline", "roocode", "opencode", "auto"
auto_trigger = true
output_dir = ".ai-devteam"

[agents]
enabled = ["product_manager", "architect", "qa", "reviewer", "docs"]
disabled = ["frontend_dev"]   # user can disable specific agents

[memory]
qdrant_url = "http://localhost:6333"
```

---

## 6. Non-Functional Requirements

| ID | Requirement | Detail |
|----|-------------|--------|
| NFR-01 | Zero UI overhead | No separate app window; everything is in-platform |
| NFR-02 | Fast background execution | Agent runs must complete in <30s for lightweight tasks |
| NFR-03 | Platform compatibility | Works wherever MCP is supported |
| NFR-04 | Local-first | MCP server runs locally; no cloud dependency except LLM APIs |
| NFR-05 | Non-intrusive | Never blocks user; agent outputs are async and passive |
| NFR-06 | Single config | One `.ai-devteam/config.toml` configures everything |

---

## 7. Development Phases

| Phase | Deliverable |
|-------|-------------|
| 1 | MCP server with all agent tools registered; manual invocation works |
| 2 | Platform rules files (CLAUDE.md, .clinerules, .roorules) for auto-trigger |
| 3 | Event-driven triggers (file save, commit hooks) |
| 4 | Qdrant long-term memory integration |
| 5 | Research Agent with Tavily/Exa/Firecrawl |
| 6 | GitHub automation (auto-commit, PR creation) |

---

## 8. Out of Scope

- Standalone web UI (removed in v2.0)
- SaaS or multi-user deployment
- Billing or licensing systems
