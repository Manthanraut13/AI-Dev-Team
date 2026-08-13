"""Supervisor LangGraph — a simple ReAct loop with tool-calling.

This is the heart of the Codex-style chat: the main agent receives user messages,
decides whether to call tools (plan_project, build_project, etc.), and streams
its reply back token-by-token. The graph runs in a worker thread so blocking LLM
calls don't freeze the event loop; events are bridged to WS via an asyncio.Queue.

No checkpointer, no interrupts — the session store is the single source of truth.
Each chat run is stateless: we feed the accumulated session.messages into the graph,
stream the response, and write the final messages back to the session.
"""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from app.config import settings
from app.utils.llm import get_llm

if TYPE_CHECKING:
    from app.services.session_store import Session


logger = logging.getLogger(__name__)


class SupervisorState(TypedDict):
    """State for the supervisor ReAct loop — just the message history."""
    messages: Annotated[List[BaseMessage], add_messages]


def build_supervisor_graph(
    session: "Session",
    broadcast: Callable[[str, Dict[str, Any]], None],
    tools: Optional[List[BaseTool]] = None,
) -> StateGraph:
    """Build the supervisor graph bound to a session and broadcaster.

    If `tools` is None, we create the default tool set via make_tools().
    The graph is stateless (no checkpointer) — caller manages session persistence.
    """
    from app.supervisor.prompts import SUPERVISOR_SYSTEM_PROMPT
    from app.supervisor.tools import make_tools

    if tools is None:
        tools = make_tools(session, broadcast)

    # Bind tools to the LLM.
    llm = get_llm(model=settings.SUPERVISOR_MODEL, temperature=0.3)
    llm_with_tools = llm.bind_tools(tools)

    def main_agent_node(state: SupervisorState) -> Dict[str, Any]:
        """The main agent — calls the LLM (with tools bound)."""
        # Prepend system prompt if this is the first turn.
        messages = list(state.get("messages", []))
        if not any(isinstance(m, HumanMessage) for m in messages):
            # No user message yet (shouldn't happen, but guard).
            return {"messages": []}

        # Inject system prompt as the first message.
        system_msg = HumanMessage(content=SUPERVISOR_SYSTEM_PROMPT, role="system")
        full_messages = [system_msg] + messages

        try:
            response = llm_with_tools.invoke(full_messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"Supervisor LLM error: {e}")
            return {"messages": [AIMessage(content=f"Error: {e}")]}

    # Build the graph.
    graph = StateGraph(SupervisorState)
    graph.add_node("main_agent", main_agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("main_agent")

    # Conditional edge: if the last message has tool calls, go to tools; else END.
    def should_continue(state: SupervisorState) -> str:
        last = state["messages"][-1] if state["messages"] else None
        if hasattr(last, "tool_calls") and last.tool_calls:  # type: ignore[attr-defined]
            return "tools"
        return END

    graph.add_conditional_edges("main_agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "main_agent")

    return graph


async def run_supervisor_turn(
    session: "Session",
    user_message: str,
    broadcast: Callable[[str, Dict[str, Any]], None],
    on_token: Optional[Callable[[str], None]] = None,
    on_agent_update: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> List[BaseMessage]:
    """Run one supervisor turn (user message → agent reply with tool calls).

    Streams tokens via `on_token` callback. Returns the final message list.
    This runs the graph in a thread to avoid blocking the event loop.
    """
    from app.supervisor.prompts import SUPERVISOR_SYSTEM_PROMPT
    from app.supervisor.tools import make_tools

    # Append user message to session.
    session.messages.append({"type": "HumanMessage", "content": user_message})

    # Build a fresh graph for this turn.
    tools = make_tools(session, broadcast)
    graph = build_supervisor_graph(session, broadcast, tools=tools)
    compiled = graph.compile()

    # Prepare input state from session messages.
    input_messages: List[BaseMessage] = []
    for m in session.messages:
        mtype = m.get("type", "")
        content = m.get("content", "")
        if "Human" in mtype:
            input_messages.append(HumanMessage(content=content))
        else:
            input_messages.append(AIMessage(content=content))

    # Run the graph in a thread, streaming events.
    q: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def producer():
        try:
            for event in compiled.stream(
                {"messages": input_messages},
                stream_mode=["messages", "updates"],
                config={"recursion_limit": 40},
            ):
                loop.call_soon_threadsafe(q.put_nowait, event)
        except Exception as e:
            logger.error(f"Supervisor stream error: {e}")
            loop.call_soon_threadsafe(q.put_nowait, {"error": str(e)})
        finally:
            loop.call_soon_threadsafe(q.put_nowait, None)

    task = asyncio.create_task(asyncio.to_thread(producer))

    final_messages: List[BaseMessage] = []
    try:
        while True:
            item = await q.get()
            if item is None:
                break
            if isinstance(item, dict) and "error" in item:
                # Surface error to user.
                if on_token:
                    on_token(f"\n[Error: {item['error']}]")
                break

            # Handle streaming modes. When stream_mode is a LIST, LangGraph emits
            # (mode, payload) tuples; when a single mode, it emits the payload directly.
            if isinstance(item, tuple):
                if (
                    len(item) == 2
                    and isinstance(item[0], str)
                    and item[0] in ("messages", "updates", "values", "custom")
                ):
                    mode, payload = item
                else:
                    mode, payload = None, item

                if mode == "messages":
                    # payload is (message_chunk, metadata_dict)
                    chunk, metadata = payload
                    node = metadata.get("langgraph_node") if isinstance(metadata, dict) else None
                    content = chunk.content if hasattr(chunk, "content") else chunk
                    if node == "main_agent" and content and on_token:
                        on_token(content)
                    continue

                # Single-mode "messages" stream: payload is (message_chunk, metadata_dict).
                if (
                    mode is None
                    and isinstance(payload, tuple)
                    and len(payload) == 2
                    and isinstance(payload[1], dict)
                ):
                    chunk, metadata = payload
                    node = metadata.get("langgraph_node")
                    content = chunk.content if hasattr(chunk, "content") else chunk
                    if node == "main_agent" and content and on_token:
                        on_token(content)
                    continue

                # Fall through for non-tuple-prefixed payloads (single-mode stream).
                if isinstance(payload, dict):
                    item = payload
                else:
                    continue

            if isinstance(item, dict):
                # Node update from stream_mode="updates" (or single-mode "updates").
                for node_name, node_output in item.items():
                    if node_name == "main_agent":
                        msgs = node_output.get("messages", [])
                        if msgs:
                            final_messages.extend(msgs)
                    elif node_name == "tools":
                        if on_agent_update:
                            # Tool execution — broadcast as agent_update.
                            tool_name = "tool"
                            if isinstance(node_output, dict) and "messages" in node_output:
                                for tm in node_output["messages"]:
                                    if hasattr(tm, "name"):
                                        tool_name = tm.name
                            on_agent_update({"node": tool_name, "status": "complete"})

    finally:
        task.cancel()

    # Persist final messages to session.
    for m in final_messages:
        if isinstance(m, AIMessage):
            session.messages.append({"type": "AIMessage", "content": m.content})
        elif isinstance(m, HumanMessage):
            session.messages.append({"type": "HumanMessage", "content": m.content})

    return final_messages
