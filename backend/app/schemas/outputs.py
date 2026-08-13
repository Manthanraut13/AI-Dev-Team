from pydantic import BaseModel
from typing import List


class RequirementsOutput(BaseModel):
    functional: List[str]
    non_functional: List[str]
    tasks: List[str]


class ArchitectureOutput(BaseModel):
    api_endpoints: List[dict]
    db_schema: List[dict]
    folder_structure: str
    tech_decisions: List[str]


class ReviewOutput(BaseModel):
    issues: List[str]
    suggestions: List[str]
    security_flags: List[str]
    approved: bool
