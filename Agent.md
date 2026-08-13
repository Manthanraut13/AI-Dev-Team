# Agent Guide
## AI Dev Team — Universal Coding Platform Plugin

> **For AI Coding Agents:** This file defines the exact role, trigger condition, MCP tool name, inputs, outputs, model, and implementation rules for each agent. Read this before writing or modifying any agent file.

---

## Core Rules for All Agents

1. Every agent is an `async` Python function: `async def <name>_agent(input) -> AgentOutput`
2. Every agent is also exposed as an MCP tool in `plugin/server.py`
3. All LLM calls use `ChatGroq` from `langchain-groq`
4. All outputs use **Pydantic v2** — never return raw strings or unvalidated dicts
5. Every agent reads `project_context.json` at the start and updates it at the end
6. Agents write results to `.ai-devteam/<agent_name>/` — never directly to source code (except scaffold agents, which ask for confirmation)
7. All agents must log to `.ai-devteam/logs/agent_activity.log` on start and end

---

## Shared Utilities (import from these, don't rewrite)

```python
from plugin.memory.context import load_context, save_context
from plugin.memory.long_term import qdrant_search, qdrant_upsert
from plugin.tools.output import write_agent_output, log_activity
```

---

## Agent Specifications

---

### 1. Product Manager Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/product_manager.py` |
| **MCP Tool** | `run_product_manager(idea: str) -> dict` |
| **Model** | `llama-3.3-70b-versatile` (Groq) |
| **Trigger** | New project, `/pm <idea>` slash command, `/devteam` pipeline |
| **Reads** | `idea` (user input string) + `project_context.json` |
| **Writes** | `.ai-devteam/requirements.md`, updates `project_context.json` |

**Pydantic Output:**
```python
class PMOutput(BaseModel):
    project_name: str
    summary: str
    functional_requirements: list[str]
    non_functional_requirements: list[str]
    prioritized_tasks: list[str]
```

**System Prompt:**
```
You are a senior product manager embedded in a developer's coding environment.
Given a software idea, produce clear functional requirements, non-functional requirements,
and a prioritized task list. Be concise — this is for a developer, not a business stakeholder.
Respond only in valid JSON matching the schema.
```

**Implementation:**
1. Load `project_context.json`
2. Call LLM with idea + existing context
3. Validate via `PMOutput`
4. Write `requirements.md` to `.ai-devteam/`
5. Update `project_context.json` with `project_name`, `requirements`

---

### 2. Architect Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/architect.py` |
| **MCP Tool** | `run_architect(requirements: list[str] | None) -> dict` |
| **Model** | `llama-3.3-70b-versatile` (Groq) |
| **Trigger** | After Product Manager, `/architect` slash command |
| **Reads** | `project_context.json` (requirements), Qdrant (past architectures) |
| **Writes** | `.ai-devteam/architecture.md`, updates `project_context.json` |

**Pydantic Output:**
```python
class ArchitectOutput(BaseModel):
    detected_stack: list[str]
    api_endpoints: list[dict]       # {method, path, description, request_body, response}
    db_schema: list[dict]           # {table, columns: [{name, type, constraints}]}
    folder_structure: str           # ASCII tree
    tech_decisions: list[str]
```

**Implementation:**
1. Load `project_context.json` for requirements
2. `qdrant_search("architectures", query=str(requirements), top_k=3)` — inject as context
3. Call LLM → validate `ArchitectOutput`
4. Write `architecture.md` (formatted Markdown)
5. Update `project_context.json` with `architecture`, `detected_stack`

---

### 3. Research Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/research.py` |
| **MCP Tool** | `run_research(topic: str) -> dict` |
| **Model** | `llama-3.3-70b-versatile` (Groq) |
| **Trigger** | Unknown import detected in saved file, `/research <topic>` |
| **Tools Used** | `TavilySearch`, `ExaSearch`, `Firecrawl` |
| **Writes** | `.ai-devteam/research/<topic>.md` |

**Pydantic Output:**
```python
class ResearchOutput(BaseModel):
    topic: str
    summary: str
    key_findings: list[str]
    useful_links: list[str]
    code_examples: list[str]
```

**Implementation:**
1. Tavily search: `topic + detected_stack` → top 5 results
2. Exa semantic search: topic → top 3 deep results
3. Firecrawl top 2 URLs → extract full markdown text
4. LLM synthesizes into `ResearchOutput`
5. Write `.ai-devteam/research/<topic>.md`
6. Embed summary → `qdrant_upsert("references", text=summary, meta={topic})`

**Import Detection:**
```python
import ast, re

def extract_unknown_imports(file_path: str, known_stdlib: set) -> list[str]:
    with open(file_path) as f:
        tree = ast.parse(f.read())
    imports = [node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)]
    return [i for i in imports if i not in known_stdlib and i not in sys.stdlib_module_names]
```

---

### 4. Backend Developer Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/backend_dev.py` |
| **MCP Tool** | `run_backend_dev(spec: str) -> dict` |
| **Model** | `qwen/qwen3-coder` (Groq) |
| **Trigger** | `/devteam` full pipeline, explicit `/backend` command |
| **Reads** | `project_context.json` (architecture, requirements), Qdrant (code patterns) |
| **Writes** | Scaffold files to project tree (with user confirmation via MCP response) |

**Pydantic Output:**
```python
class BackendDevOutput(BaseModel):
    files: dict[str, str]   # {relative_path: file_content}
    summary: str
    requires_confirmation: bool
```

**Code Generation Rules:**
- FastAPI with `async def` route handlers only
- SQLAlchemy 2.0 style (`select()`, not legacy `query()`)
- Pydantic v2 schemas for request/response
- Use `logging` not `print()`
- Always include type hints
- One file per resource (routes, models, schemas, services)

**Implementation:**
1. `qdrant_search("patterns", query=spec)` — retrieve similar past code
2. Build prompt with architecture + patterns + spec
3. Generate all files in one LLM call → validate `BackendDevOutput`
4. Return files with `requires_confirmation: True` — platform displays files to user
5. On confirmation: write files to project tree

---

### 5. Frontend Developer Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/frontend_dev.py` |
| **MCP Tool** | `run_frontend_dev(spec: str) -> dict` |
| **Model** | `qwen/qwen3-coder` (Groq) |
| **Trigger** | `/devteam` full pipeline, explicit `/frontend` command |
| **Reads** | `project_context.json` (architecture, API endpoints) |
| **Writes** | Scaffold files to project tree (with user confirmation) |

**Pydantic Output:**
```python
class FrontendDevOutput(BaseModel):
    files: dict[str, str]   # {relative_path: file_content}
    summary: str
    requires_confirmation: bool
```

**Code Generation Rules:**
- TypeScript only — no `.js` files
- `"use client"` only on interactive components (not pages by default)
- Tailwind CSS for all styling — no inline styles, no CSS modules
- shadcn/ui components from `@/components/ui/`
- React Query for data fetching — no raw `fetch` in components
- `lib/api.ts` as the only place that calls backend endpoints

---

### 6. QA Engineer Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/qa_engineer.py` |
| **MCP Tool** | `run_qa_engineer(file_path: str) -> dict` |
| **Model** | `qwen/qwen3-coder` (Groq) |
| **Trigger** | Any `.py` / `.ts` / `.tsx` file saved (via watchdog) |
| **Reads** | Content of `file_path`, `project_context.json` |
| **Writes** | `.ai-devteam/tests/<mirrored_path>_test.py` or `.spec.ts` |

**Pydantic Output:**
```python
class QAOutput(BaseModel):
    file_tested: str
    test_file_path: str
    test_file_content: str
    test_count: int
    coverage_notes: str
```

**Rules:**
- For `.py` files: generate Pytest tests with `pytest-asyncio` for async routes
- For `.ts/.tsx` files: generate Jest unit tests or Playwright e2e tests depending on file type (component → Jest, page → Playwright)
- Always mock external dependencies
- Test happy path + at least 2 edge cases per function

---

### 7. Code Reviewer Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/code_reviewer.py` |
| **MCP Tool** | `run_code_reviewer(file_path: str) -> dict` |
| **Model** | `deepseek-r1-distill-llama-70b` (Groq) |
| **Trigger** | Any `.py` / `.ts` / `.tsx` file saved (parallel with QA) |
| **Reads** | Content of `file_path` |
| **Writes** | `.ai-devteam/reviews/<filename>.md` |

**Pydantic Output:**
```python
class ReviewOutput(BaseModel):
    file_reviewed: str
    issues: list[str]           # bugs, logic errors
    security_flags: list[str]   # SQL injection, hardcoded secrets, missing auth
    performance_notes: list[str]
    suggestions: list[str]      # refactoring, best practices
    severity: str               # "clean" | "minor" | "major" | "critical"
```

**Review Checklist the LLM must check:**
- SQL injection / unsanitized inputs
- Hardcoded secrets or API keys
- Missing authentication/authorization guards
- N+1 query patterns
- Unhandled exceptions
- Missing input validation
- Dead code
- Functions > 50 lines (flag for refactor)

---

### 8. Documentation Agent

| Property | Value |
|----------|-------|
| **File** | `plugin/agents/documentation.py` |
| **MCP Tool** | `run_documentation(changed_files: list[str]) -> dict` |
| **Model** | `gemma2-9b-it` (Groq) |
| **Trigger** | `git commit` detected (via post-commit hook) |
| **Reads** | `project_context.json`, diff of `changed_files`, existing `README.md` |
| **Writes** | Updates `README.md`, `docs/API.md`, `CHANGELOG.md` in project root |

**Pydantic Output:**
```python
class DocsOutput(BaseModel):
    readme_updated: bool
    api_docs_updated: bool
    changelog_entry: str
    files_written: list[str]
```

**Rules:**
- Never rewrite README from scratch — diff-patch the changed sections only
- Changelog entry format: `## [date] - <commit summary>\n### Changed\n- ...`
- API docs generated from architecture `api_endpoints` in `project_context.json`

---

## Adding a New Agent (Checklist)

- [ ] Create `plugin/agents/<name>.py` with `async def <name>_agent(...) -> <Name>Output`
- [ ] Define `<Name>Output(BaseModel)` in the same file or `plugin/schemas/outputs.py`
- [ ] Add `@mcp.tool()` entry in `plugin/server.py`
- [ ] Add trigger mapping in `plugin/triggers/watcher.py` (if event-driven)
- [ ] Add slash command mapping in platform rules files (`CLAUDE.md`, `.clinerules`, `.roorules`)
- [ ] Update `plugin/graph/routers.py` to include the new agent in relevant routes
- [ ] Document the agent in this file
