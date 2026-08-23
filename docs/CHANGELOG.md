# Changelog

## [2.0.0] - 2026-08-23

### Added
- Deployed to Horizon (FastMCP Cloud)
- Remote MCP server at `https://ai-dev-team.fastmcp.app/mcp`
- Lazy imports in server.py (startup from 39s to 4s)
- OAuth authentication for Horizon

### Fixed
- `sys.path` for Horizon Docker container
- MCP connection timeout (lazy imports)
- Conflicting configs in .claude.json

### Changed
- Removed heavy deps (torch, sentence-transformers) from requirements.txt
- Updated default models to available Groq models
- Restructured repo for cleanliness

## [1.0.0] - 2026-08-17

### Added
- Full v2 plugin architecture
- 8 AI agents (PM, Architect, Research, Backend/Frontend Dev, QA, Reviewer, Docs)
- MCP server with 11 tools
- File watcher + git hooks
- 74 unit tests
- Platform integrations (Claude Code, OpenCode, Cline, Roo Code, Codex)
