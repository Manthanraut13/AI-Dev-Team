from fastapi import APIRouter, HTTPException
from app.schemas.api import ProjectCreate, ProjectResponse, ApprovalRequest
from app.graph.graph import run_graph, resume_graph, stream_graph, stream_resume
from app.agents.research import research_node
from app.tools.github import github_commit_and_pr
from app.graph.state import AgentState
from app.api.ws import manager
from typing import Dict
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

active_projects: Dict[str, AgentState] = {}


AGENT_LABELS = {
    "product_manager": "Product Manager",
    "architect": "Architect",
    "human_checkpoint_arch": "Awaiting Approval",
    "research": "Research",
    "backend_dev": "Backend Developer",
    "frontend_dev": "Frontend Developer",
    "qa_engineer": "QA Engineer",
    "code_reviewer": "Code Reviewer",
    "error_handler": "Error Handler",
    "documentation": "Documentation",
    "github": "GitHub Automation",
    "human_checkpoint_final": "Final Approval",
}


def _serialize(state: AgentState) -> dict:
    messages = [
        {"type": msg.__class__.__name__, "content": msg.content}
        for msg in state.get("messages", [])
    ]
    return ProjectResponse(
        project_name=state.get("project_name", "Untitled"),
        user_idea=state.get("user_idea", ""),
        requirements=state.get("requirements", []),
        architecture=state.get("architecture", {}),
        current_task=state.get("current_task", ""),
        messages=messages,
        human_approved=state.get("human_approved"),
        files=state.get("files", {}),
        errors=state.get("errors", []),
        fixes=state.get("fixes", []),
    )


async def _broadcast(project_id: str, node_name: str, update: dict):
    label = AGENT_LABELS.get(node_name, node_name)
    event = {
        "type": "agent_update",
        "node": node_name,
        "label": label,
        "status": "complete",
    }
    files = update.get("files")
    if files:
        event["files_count"] = len(files)
    msgs = update.get("messages", [])
    if msgs and hasattr(msgs[-1], "content"):
        event["message"] = msgs[-1].content[:200]
    try:
        await manager.broadcast(project_id, event)
    except Exception:
        pass


@router.post("/projects", response_model=ProjectResponse)
async def create_project(project: ProjectCreate):
    project_id = str(uuid.uuid4())

    for update in stream_graph(
        user_idea=project.idea,
        project_name=project.project_name or "Untitled",
        thread_id=project_id
    ):
        node_name = update.get("node", "")
        node_update = update.get("update", {})
        if node_name and node_name.startswith("__"):
            continue
        await _broadcast(project_id, node_name, node_update)
        logger.info(f"  [{project_id}] {node_name} complete")

    state = run_graph(
        user_idea=project.idea,
        project_name=project.project_name or "Untitled",
        thread_id=project_id
    )
    active_projects[project_id] = state
    await _broadcast(project_id, "checkpoint", {"current_task": state.get("current_task", "")})
    return _serialize(state)


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    if project_id not in active_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    return _serialize(active_projects[project_id])
    return _serialize(active_projects[project_id])


@router.post("/projects/{project_id}/approve", response_model=ProjectResponse)
async def approve_architecture(project_id: str, approval: ApprovalRequest):
    if project_id not in active_projects:
        raise HTTPException(status_code=404, detail="Project not found")

    current_task = active_projects[project_id].get("current_task", "")
    if current_task not in ("human_checkpoint_arch", "human_checkpoint_final"):
        raise HTTPException(
            status_code=400,
            detail=f"Project is not awaiting approval (current_task={current_task})"
        )

    await _broadcast(project_id, "approval", {
        "label": "Approval",
        "status": "complete",
        "message": "approved" if approval.approved else "rejected"
    })

    for update in stream_resume(
        thread_id=project_id,
        approved=approval.approved,
        feedback=approval.feedback or ""
    ):
        node_name = update.get("node", "")
        node_update = update.get("update", {})
        if node_name and node_name.startswith("__"):
            continue
        await _broadcast(project_id, node_name, node_update)

    result = resume_graph(
        thread_id=project_id,
        approved=approval.approved,
        feedback=approval.feedback or ""
    )

    active_projects[project_id] = result
    return _serialize(result)


@router.post("/projects/{project_id}/research")
async def run_research(project_id: str):
    if project_id not in active_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    state = active_projects[project_id]
    result = research_node(state)
    
    messages = list(state.get("messages", []))
    if "messages" in result:
        messages.extend(result["messages"])
    
    active_projects[project_id] = {
        **state,
        "messages": messages
    }
    
    return {"status": "completed", "project_id": project_id}


@router.post("/projects/{project_id}/github")
async def github_push(project_id: str):
    if project_id not in active_projects:
        raise HTTPException(status_code=404, detail="Project not found")

    state = active_projects[project_id]
    files = state.get("files", {})
    project_name = state.get("project_name", "project")

    if not files:
        raise HTTPException(status_code=400, detail="No files generated yet")

    try:
        pr_url = github_commit_and_pr(files=files, project_name=project_name)
        state["github_pr_url"] = pr_url
        state["messages"].append(
            type("AIMessage", (), {
                "content": f"GitHub: PR created at {pr_url}",
                "additional_kwargs": {},
                "response_metadata": {},
                "tool_calls": [],
                "invalid_tool_calls": []
            })()
        )
        return {"status": "success", "pr_url": pr_url, "files_count": len(files)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GitHub push failed: {str(e)[:200]}")


@router.get("/projects", response_model=list[str])
async def list_projects():
    return list(active_projects.keys())


@router.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    if project_id not in active_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    del active_projects[project_id]
    return {"message": "Project deleted"}
