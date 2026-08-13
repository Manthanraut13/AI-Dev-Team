from typing import TypedDict, List, Dict, Annotated
from langchain_core.messages import BaseMessage


def merge_messages(left: List[BaseMessage], right: List[BaseMessage]) -> List[BaseMessage]:
    if not left:
        return right
    if not right:
        return left
    return left + right


def merge_files(left: Dict[str, str], right: Dict[str, str]) -> Dict[str, str]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


def take_latest(left: str, right: str) -> str:
    return right if right else (left or "")


class AgentState(TypedDict):
    project_name: str
    user_idea: str
    requirements: List[str]
    architecture: Dict
    current_task: Annotated[str, take_latest]
    files: Annotated[Dict[str, str], merge_files]
    messages: Annotated[List[BaseMessage], merge_messages]
    review_feedback: List[str]
    test_results: Dict
    documentation: Dict[str, str]
    human_approved: bool
    github_pr_url: str
    errors: List[Dict]
    fixes: List[str]
