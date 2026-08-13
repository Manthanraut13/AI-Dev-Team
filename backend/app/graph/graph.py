from app.agents.research import research_node
from app.agents.backend_dev import backend_dev_node
from app.agents.frontend_dev import frontend_dev_node
from app.agents.qa_engineer import qa_engineer_node
from app.agents.code_reviewer import code_reviewer_node
from app.agents.documentation import documentation_node
from app.agents.product_manager import product_manager_node
from app.agents.architect import architect_node
from app.agents.github_automation import github_node
from app.agents.error_handler import error_handler_node
from app.graph.checkpoints import (
    human_checkpoint_arch_node,
    human_checkpoint_final_node,
)
from app.graph.routers import (
    route_after_arch_approval,
    route_after_final_approval,
)
from app.graph.state import AgentState
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
import logging

logger = logging.getLogger(__name__)


def build_graph(with_research: bool = False) -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("product_manager", product_manager_node)
    graph.add_node("architect", architect_node)
    graph.add_node("human_checkpoint_arch", human_checkpoint_arch_node)

    if with_research:
        graph.add_node("research", research_node)

    graph.add_node("backend_dev", backend_dev_node)
    graph.add_node("frontend_dev", frontend_dev_node)
    graph.add_node("qa_engineer", qa_engineer_node)
    graph.add_node("code_reviewer", code_reviewer_node)
    graph.add_node("error_handler", error_handler_node)
    graph.add_node("documentation", documentation_node)
    graph.add_node("github", github_node)
    graph.add_node("human_checkpoint_final", human_checkpoint_final_node)

    graph.set_entry_point("product_manager")
    graph.add_edge("product_manager", "architect")
    graph.add_edge("architect", "human_checkpoint_arch")

    graph.add_conditional_edges(
        "human_checkpoint_arch",
        route_after_arch_approval,
    )

    if with_research:
        graph.add_edge("research", "backend_dev")
        graph.add_edge("research", "frontend_dev")

    graph.add_edge("backend_dev", "qa_engineer")
    graph.add_edge("frontend_dev", "qa_engineer")
    graph.add_edge("backend_dev", "code_reviewer")
    graph.add_edge("frontend_dev", "code_reviewer")

    graph.add_edge("qa_engineer", "error_handler")
    graph.add_edge("code_reviewer", "error_handler")
    graph.add_edge("error_handler", "documentation")

    graph.add_edge("documentation", "human_checkpoint_final")

    graph.add_conditional_edges(
        "human_checkpoint_final",
        route_after_final_approval,
        {
            "approved": "github",
            "rejected": "documentation"
        }
    )

    graph.add_edge("github", END)

    return graph


def _initial_state(user_idea: str, project_name: str) -> AgentState:
    from langchain_core.messages import HumanMessage
    return {
        "project_name": project_name,
        "user_idea": user_idea,
        "requirements": [],
        "architecture": {},
        "current_task": "product_manager",
        "files": {},
        "messages": [HumanMessage(content=user_idea)],
        "review_feedback": [],
        "test_results": {},
        "documentation": {},
        "human_approved": None,
        "github_pr_url": "",
        "errors": [],
        "fixes": [],
    }


def run_graph(user_idea: str, project_name: str = "Untitled", thread_id: str = "default") -> AgentState:
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    return _compiled_graph.invoke(_initial_state(user_idea, project_name), config=config)


def resume_graph(thread_id: str, approved: bool, feedback: str = "") -> AgentState:
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    return _compiled_graph.invoke(
        Command(resume={"approved": approved, "feedback": feedback}),
        config=config
    )


def stream_graph(user_idea: str, project_name: str = "Untitled", thread_id: str = "default"):
    """Stream graph execution node-by-node. Yields {node_name: updates} dicts."""
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    return _compiled_graph.stream(
        _initial_state(user_idea, project_name),
        config=config,
        stream_mode="updates"
    )


def stream_resume(thread_id: str, approved: bool, feedback: str = ""):
    """Stream graph resume (approval) node-by-node."""
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
    return _compiled_graph.stream(
        Command(resume={"approved": approved, "feedback": feedback}),
        config=config,
        stream_mode="updates"
    )


_compiled_graph = build_graph(with_research=False).compile(checkpointer=MemorySaver())
compiled_graph = _compiled_graph
