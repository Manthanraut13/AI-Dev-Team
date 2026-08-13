from app.graph.state import AgentState
from typing import Union, List


def route_after_arch_approval(state: AgentState) -> Union[List[str], str]:
    if state.get("human_approved"):
        return ["backend_dev", "frontend_dev"]
    return "__end__"


def route_after_final_approval(state: AgentState) -> str:
    if state.get("human_approved"):
        return "approved"
    return "rejected"
