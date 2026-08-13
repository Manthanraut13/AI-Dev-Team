"""Pytest suite for AI Dev Team plugin — Phase 7.

Layout:
- tests/conftest.py          Shared fixtures (tmp project, mock LLM, mock Qdrant).
- tests/test_paths.py        Filesystem conventions.
- tests/test_output.py       write_agent_output + log_activity.
- tests/test_schemas.py      Pydantic schema validation per output type.
- tests/test_long_term.py    qdrant_search / qdrant_upsert graceful degradation.
- tests/test_server_registry.py  MCP server tool list contains all 11 tools.
- tests/test_install.py      Platform generator idempotency.
- tests/test_agents/         Per-agent smoke tests with mocked LLM.
"""