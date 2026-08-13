# Workflow
## AI Dev Team — Universal Coding Platform Plugin

---

## 1. How the Plugin Fits into a Coding Session

```
User opens project in Claude Code / Cline / Roo Code / OpenCode
                        │
                        ▼
         Plugin MCP server starts (local, background process)
                        │
                        ▼
         watchdog monitors project file system
                        │
          ┌─────────────┼──────────────────┐
          ▼             ▼                  ▼
    File saved      git commit        User slash cmd
          │             │                  │
          ▼             ▼                  ▼
     QA + Review    Docs Agent       Named agent runs
          │             │                  │
          └─────────────┴──────────────────┘
                        │
                        ▼
         Output written to .ai-devteam/ folder
                        │
                        ▼
       Platform surfaces result (inline, terminal, sidebar)
```

---

## 2. Plugin Startup Sequence

```
1. User runs: python install.py --platform claude-code
2. install.py detects project root
3. Creates .ai-devteam/config.toml
4. Generates platform rules file (CLAUDE.md / .clinerules / .roorules)
5. Registers MCP server in platform config
6. Starts: python plugin/server.py (MCP server on stdio)
7. Starts: python plugin/triggers/watcher.py (file system monitor)
8. Loads or creates .ai-devteam/project_context.json
9. If new project: auto-triggers Product Manager + Architect
10. Plugin is ready — user continues coding normally
```

---

## 3. LangGraph State

```python
class AgentState(TypedDict):
    # Project context
    project_root: str
    project_name: str
    detected_stack: list[str]       # e.g. ["fastapi", "react", "postgres"]

    # Agent outputs
    requirements: list[str]
    architecture: dict
    files_changed: list[str]        # files that triggered this run
    generated_files: dict[str, str] # path → content
    review_comments: list[str]
    test_files: dict[str, str]
    research_findings: dict[str, str]
    documentation: dict[str, str]

    # Control
    trigger_event: str              # "file_save" | "commit" | "slash_cmd" | "new_project"
    active_agents: list[str]        # which agents should run this cycle
    current_agent: str
    messages: list[BaseMessage]
```

---

## 4. Trigger → Agent Mapping

| Trigger Event | Condition | Agents Activated |
|---------------|-----------|-----------------|
| `new_project` | Empty/new repo detected | Product Manager → Architect |
| `file_save` | `.py` file saved | QA Engineer + Code Reviewer (parallel) |
| `file_save` | `.ts` / `.tsx` file saved | QA Engineer + Code Reviewer (parallel) |
| `file_save` | Unknown `import` detected | Research Agent |
| `git_commit` | Commit hook fires | Documentation Agent |
| `slash_cmd:/pm` | User types `/pm <idea>` | Product Manager |
| `slash_cmd:/architect` | User types `/architect` | Architect |
| `slash_cmd:/research` | User types `/research <topic>` | Research Agent |
| `slash_cmd:/review` | User types `/review` | Code Reviewer |
| `slash_cmd:/test` | User types `/test` | QA Engineer |
| `slash_cmd:/docs` | User types `/docs` | Documentation Agent |
| `slash_cmd:/devteam` | User types `/devteam <idea>` | Full pipeline |

---

## 5. MCP Server Tool Definitions

```python
# plugin/server.py
from fastmcp import FastMCP
from plugin.agents import *

mcp = FastMCP("ai-dev-team")

@mcp.tool()
async def run_product_manager(idea: str) -> dict:
    """Generate requirements from a software idea or feature description."""
    return await product_manager_agent(idea)

@mcp.tool()
async def run_architect(requirements: list[str] | None = None) -> dict:
    """Design API, DB schema, and folder structure for the current project."""
    return await architect_agent(requirements)

@mcp.tool()
async def run_research(topic: str) -> dict:
    """Search and summarize documentation and libraries for a given topic."""
    return await research_agent(topic)

@mcp.tool()
async def run_qa_engineer(file_path: str) -> dict:
    """Generate tests for the given file path."""
    return await qa_engineer_agent(file_path)

@mcp.tool()
async def run_code_reviewer(file_path: str) -> dict:
    """Review the given file for issues, security, and best practices."""
    return await code_reviewer_agent(file_path)

@mcp.tool()
async def run_documentation(changed_files: list[str]) -> dict:
    """Update README, API docs, and changelog based on changed files."""
    return await documentation_agent(changed_files)

@mcp.tool()
async def run_backend_dev(spec: str) -> dict:
    """Generate backend scaffolding (FastAPI + SQLAlchemy) from a spec."""
    return await backend_dev_agent(spec)

@mcp.tool()
async def run_frontend_dev(spec: str) -> dict:
    """Generate frontend scaffolding (Next.js + React) from a spec."""
    return await frontend_dev_agent(spec)

@mcp.tool()
async def get_project_context() -> dict:
    """Return the current project context (requirements, architecture, stack)."""
    return load_project_context()

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

---

## 6. Platform Rules Files

### CLAUDE.md (Claude Code)
```markdown
# AI Dev Team Plugin — Active

This project has the AI Dev Team plugin enabled. Use these tools automatically:

## Auto-triggers
- When user describes a new feature → call `run_product_manager`
- When asked about architecture → call `run_architect`
- Before writing backend code → call `get_project_context` to load requirements/architecture

## Available slash commands
- /pm <idea> → run_product_manager
- /architect → run_architect
- /research <topic> → run_research
- /review → run_code_reviewer on current file
- /test → run_qa_engineer on current file
- /docs → run_documentation
- /devteam <idea> → run full pipeline
```

### .clinerules (Cline)
```markdown
# AI Dev Team Plugin Rules

## Behavior
- On every new task, call get_project_context first to understand the project
- After writing any .py or .ts file, call run_code_reviewer on it
- When user requests feature development, call run_product_manager first

## MCP Tools Available
run_product_manager, run_architect, run_research, run_qa_engineer,
run_code_reviewer, run_documentation, run_backend_dev, run_frontend_dev,
get_project_context
```

### .roorules (Roo Code)
```markdown
# AI Dev Team Plugin — Roo Code Integration

Always begin new sessions by calling get_project_context.
When generating code files, follow architecture from run_architect output.
After generating any implementation file, call run_qa_engineer on it.
Surface run_code_reviewer results as inline suggestions.
```

---

## 7. File System Watcher

```python
# plugin/triggers/watcher.py
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import asyncio, subprocess

class ProjectEventHandler(FileSystemEventHandler):

    def on_modified(self, event):
        if event.is_directory:
            return
        path = event.src_path

        # File save triggers
        if path.endswith((".py", ".ts", ".tsx")):
            self._trigger_agents(["qa_engineer", "code_reviewer"], file_path=path)

        # Detect unknown imports
        if self._has_unknown_imports(path):
            self._trigger_agents(["research"], file_path=path)

    def _trigger_agents(self, agents: list[str], file_path: str):
        # Calls MCP tools via internal async runner (non-blocking)
        asyncio.create_task(dispatch_agents(agents, file_path))

# Git commit hook (installed by install.py into .git/hooks/post-commit)
# #!/bin/bash
# python plugin/triggers/git_hook.py commit
```

---

## 8. Agent Execution Flow (Internal LangGraph)

When any trigger fires, the graph routes to only the relevant agents:

```python
# graph/routers.py
def route_by_trigger(state: AgentState) -> list[str]:
    trigger = state["trigger_event"]
    routing = {
        "new_project":  ["product_manager", "architect"],
        "file_save":    ["qa_engineer", "code_reviewer"],
        "git_commit":   ["documentation"],
        "slash_cmd:/pm": ["product_manager"],
        "slash_cmd:/devteam": ["product_manager", "architect",
                               "backend_dev", "qa_engineer",
                               "code_reviewer", "documentation"],
    }
    return routing.get(trigger, [])
```

Agents run in parallel wherever possible (QA + Reviewer always parallel).

---

## 9. Output Writing

Every agent writes results to `.ai-devteam/` — never to the user's source directly (except scaffold generators like Backend Dev / Frontend Dev which write to the project tree with user confirmation).

```python
# Shared output writer used by all agents
def write_agent_output(agent_name: str, filename: str, content: str):
    path = f".ai-devteam/{agent_name}/{filename}"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    log_activity(agent_name, filename)
```

---

## 10. Memory Workflow

### Load Context (start of every agent run)
```
1. Read .ai-devteam/project_context.json → inject into prompt
2. Qdrant similarity search on (project_name + current task) → top-3 past patterns
3. Both injected into agent system prompt as context
```

### Save Context (end of every agent run)
```
1. Update .ai-devteam/project_context.json with new agent output
2. Embed agent output → upsert to Qdrant collection "project_memory"
```

---

## 11. Error Handling

| Error | Behavior |
|-------|----------|
| LLM returns invalid JSON | Retry up to 3× with schema reminder |
| Qdrant unavailable | Skip LTM lookup, run with project_context.json only |
| File watcher misfire | Debounce 2s; skip if file unchanged since last run |
| Agent timeout (>60s) | Kill, log to `agent_activity.log`, notify via terminal |
| Platform MCP connection lost | MCP server auto-restarts via process supervisor |
