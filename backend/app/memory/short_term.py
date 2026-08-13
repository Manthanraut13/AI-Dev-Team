from app.graph.state import AgentState
from typing import List, Dict, Any


def get_state_value(state: AgentState, key: str, default: Any = None) -> Any:
    return state.get(key, default)


def update_state(state: AgentState, updates: Dict) -> AgentState:
    new_state = dict(state)
    new_state.update(updates)
    return new_state


def add_message(state: AgentState, message: Dict) -> AgentState:
    messages = list(state.get("messages", []))
    messages.append(message)
    return {**state, "messages": messages}


def add_file(state: AgentState, path: str, content: str) -> AgentState:
    files = dict(state.get("files", {}))
    files[path] = content
    return {**state, "files": files}


def get_requirements_summary(state: AgentState) -> str:
    requirements = state.get("requirements", [])
    return "\n".join(f"- {req}" for req in requirements)


def get_architecture_summary(state: AgentState) -> str:
    architecture = state.get("architecture", {})
    if not architecture:
        return "No architecture defined yet."
    
    summary_parts = []
    
    if "api_endpoints" in architecture:
        summary_parts.append("API Endpoints:")
        for ep in architecture["api_endpoints"]:
            summary_parts.append(
                f"  {ep.get('method', 'GET')} {ep.get('path', '/')} - {ep.get('description', '')}"
            )
    
    if "db_schema" in architecture:
        summary_parts.append("\nDatabase Schema:")
        for table in architecture["db_schema"]:
            summary_parts.append(f"  Table: {table.get('table', 'unknown')}")
            for col in table.get("columns", []):
                summary_parts.append(f"    - {col}")
    
    return "\n".join(summary_parts)
