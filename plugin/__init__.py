"""AI Dev Team — Universal Coding Platform Plugin (v2).

A FastMCP-based plugin that exposes a team of specialized AI agents
(product manager, architect, research, backend/frontend dev, QA, reviewer,
documentation) to any MCP-capable coding platform (Claude Code, Cline,
Roo Code, OpenCode, Codex CLI).

Agents are standalone async functions returning validated Pydantic outputs.
They are activated by slash commands, file-save events (watchdog), and git
commits, and write results under `.ai-devteam/`.
"""

__version__ = "2.0.0"
