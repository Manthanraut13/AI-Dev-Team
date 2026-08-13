from pydantic import BaseModel
from typing import List, Optional, Dict


class ProjectCreate(BaseModel):
    idea: str
    project_name: Optional[str] = "Untitled"


class ProjectResponse(BaseModel):
    project_name: str
    user_idea: str
    requirements: List[str]
    architecture: Dict
    current_task: str
    messages: List[Dict]
    human_approved: Optional[bool]
    files: Dict[str, str]
    errors: List[Dict] = []
    fixes: List[str] = []


class ApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = ""


class ProjectStateResponse(BaseModel):
    project_name: str
    current_task: str
    human_approved: Optional[bool]
    requirements_count: int
    architecture_status: str
    messages_count: int
