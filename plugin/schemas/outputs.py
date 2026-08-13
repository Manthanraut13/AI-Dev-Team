"""Structured output schemas for every agent (Pydantic v2).

All agents return an instance of their schema — never raw strings or unvalidated
dicts. These mirror Agent.md §Agent Specifications.
"""
from pydantic import BaseModel, Field
from typing import List, Dict


# ---- Product Manager ----
class PMOutput(BaseModel):
    project_name: str
    summary: str
    functional_requirements: List[str]
    non_functional_requirements: List[str]
    prioritized_tasks: List[str]


# ---- Architect ----
class ArchitectOutput(BaseModel):
    detected_stack: List[str] = Field(default_factory=list)
    api_endpoints: List[Dict] = Field(default_factory=list)  # {method, path, description, request_body, response}
    db_schema: List[Dict] = Field(default_factory=list)      # {table, columns: [{name, type, constraints}]}
    folder_structure: str = ""
    tech_decisions: List[str] = Field(default_factory=list)


# ---- Research ----
class ResearchOutput(BaseModel):
    topic: str
    summary: str
    key_findings: List[str]
    useful_links: List[str]
    code_examples: List[str]


# ---- Backend / Frontend Developer ----
class BackendDevOutput(BaseModel):
    files: Dict[str, str]  # {relative_path: file_content}
    summary: str
    requires_confirmation: bool = True


class FrontendDevOutput(BaseModel):
    files: Dict[str, str]
    summary: str
    requires_confirmation: bool = True


# ---- QA Engineer ----
class QAOutput(BaseModel):
    file_tested: str
    test_file_path: str
    test_file_content: str
    test_count: int = 0
    coverage_notes: str = ""


# ---- Code Reviewer ----
class ReviewOutput(BaseModel):
    file_reviewed: str
    issues: List[str] = Field(default_factory=list)
    security_flags: List[str] = Field(default_factory=list)
    performance_notes: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    severity: str = "clean"  # "clean" | "minor" | "major" | "critical"


# ---- Documentation ----
class DocsOutput(BaseModel):
    readme_updated: bool = False
    api_docs_updated: bool = False
    changelog_entry: str = ""
    files_written: List[str] = Field(default_factory=list)
