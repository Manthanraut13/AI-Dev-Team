# AI Dev Team — Agent Tool Guide

You have access to the `ai-dev-team` MCP server. The 11 tools below turn a
rough idea into a working scaffold (PM → Architect → Backend+Frontend → QA →
Review → Docs). Auto-call them based on the user's request and the slash
commands listed under each role.

## Slash commands

| Slash | Tool to call |
|-------|--------------|
| `/pm <idea>`         | `run_product_manager(idea)` |
| `/architect`         | `run_architect()` (uses context) |
| `/research <topic>`  | `run_research(topic)` |
| `/backend <spec>`    | `run_backend_dev(spec)` |
| `/frontend <spec>`   | `run_frontend_dev(spec)` |
| `/devteam <idea>`    | `run_devteam(idea)` — full pipeline |
| `/docs <files>`      | `run_documentation(changed_files)` |

## Trigger rules

- On any new project idea: call `run_product_manager`.
- After PM, call `run_architect` before any code is written.
- Scaffold files require user confirmation (`requires_confirmation: true`).
  Surface the proposed files to the user; write only after explicit OK.
- All outputs land in `.ai-devteam/` — read but do not modify user source.

## Claude Code specifics

Use the Bash + Read tools for filesystem work. All MCP tools appear in the
tool palette under the `mcp__ai-dev-team__` namespace.
