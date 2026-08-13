"""Synthetic test for the supervisor stream-parsing fix.

Simulates LangGraph's multi-mode stream output
(stream_mode=["messages", "updates"]) and asserts that:
  - main_agent tokens are forwarded to on_token
  - tool-node tokens are NOT forwarded
  - node updates fire on_agent_update for tool execution
  - final assistant messages are persisted to the session
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import AIMessage, AIMessageChunk

# --- Mock the graph BEFORE importing run_turn internals triggers real build. ---
import app.supervisor.graph as g


class FakeCompiled:
    def stream(self, *args, **kwargs):
        yield ("messages", (AIMessageChunk(content="Hello"), {
            "langgraph_node": "main_agent", "langgraph_step": 1}))
        yield ("messages", (AIMessageChunk(content=" world"), {
            "langgraph_node": "main_agent", "langgraph_step": 1}))
        # Tool-node tokens must NOT stream into chat.
        yield ("messages", (AIMessageChunk(content="SECRET-TOOL-TOKEN"), {
            "langgraph_node": "tools", "langgraph_step": 2}))
        yield ("updates", {"main_agent": {"messages": [AIMessage(content="Hello world")]}})
        yield ("updates", {"tools": {"messages": [AIMessage(content="", name="plan_project")]}})


class FakeGraph:
    def compile(self):
        return FakeCompiled()


async def main():
    tokens = []
    updates = []

    def on_token(t):
        tokens.append(t)

    def on_agent_update(u):
        updates.append(u)

    class FakeSession:
        def __init__(self):
            self.messages = []
            self.id = "test-session"
            self.workspace_path = None
            self.idea = None

    session = FakeSession()

    # Monkeypatch the graph builder to avoid real LLM calls.
    orig = g.build_supervisor_graph
    g.build_supervisor_graph = lambda *a, **k: FakeGraph()
    try:
        from app.supervisor.graph import run_supervisor_turn
        result = await asyncio.wait_for(
            run_supervisor_turn(session, "hello", broadcast=lambda *a: None,
                     on_token=on_token, on_agent_update=on_agent_update),
            timeout=120,
        )
    finally:
        g.build_supervisor_graph = orig

    streamed = "".join(tokens)
    print("streamed tokens:", repr(streamed))
    print("agent updates:", updates)
    print("persisted msgs:", session.messages)

    ok = True
    if streamed != "Hello world":
        print("FAIL: expected 'Hello world', got", repr(streamed))
        ok = False
    if "SECRET-TOOL-TOKEN" in streamed:
        print("FAIL: tool tokens leaked into chat")
        ok = False
    if not updates or updates[0].get("node") != "plan_project":
        print("FAIL: expected tool agent_update, got", updates)
        ok = False
    persisted = [m for m in session.messages if m.get("type") == "AIMessage"]
    if not any("Hello world" == m.get("content") for m in persisted):
        print("FAIL: final assistant message not persisted; got", persisted)
        ok = False
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
