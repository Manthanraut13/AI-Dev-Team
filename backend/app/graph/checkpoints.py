from langgraph.types import interrupt
from langchain_core.messages import AIMessage
from app.graph.state import AgentState
import logging

logger = logging.getLogger(__name__)


def human_checkpoint_arch_node(state: AgentState) -> AgentState:
    logger.info("Human checkpoint reached (architecture review)")

    decision = interrupt({
        "task": "human_checkpoint_arch",
        "payload": state.get("architecture", {}),
        "requirements": state.get("requirements", [])
    })

    approved = bool(decision.get("approved"))
    feedback = decision.get("feedback", "")

    logger.info(f"Human decision: approved={approved}")

    if approved:
        message = AIMessage(content="Architecture approved. Proceeding.")
    else:
        message = AIMessage(content=f"Architecture rejected. Feedback: {feedback}")

    return {
        "human_approved": approved,
        "messages": [message]
    }


def human_checkpoint_final_node(state: AgentState) -> AgentState:
    logger.info("Human checkpoint reached (final review)")

    decision = interrupt({
        "task": "human_checkpoint_final",
        "payload": state.get("files", {}),
        "documentation": state.get("documentation", {})
    })

    approved = bool(decision.get("approved"))
    feedback = decision.get("feedback", "")

    logger.info(f"Human decision: approved={approved}")

    if approved:
        message = AIMessage(content="Final review approved. Proceeding to GitHub.")
    else:
        message = AIMessage(content=f"Final review rejected. Feedback: {feedback}")

    return {
        "human_approved": approved,
        "messages": [message]
    }
