from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.api.ws import manager
from app.api.projects import active_projects
from app.graph.graph import stream_graph, stream_resume
import asyncio
import logging

logger = logging.getLogger(__name__)

ws_router = APIRouter()


AGENT_LABELS = {
    "product_manager": "Product Manager",
    "architect": "Architect",
    "human_checkpoint_arch": "Awaiting Approval",
    "research": "Research",
    "backend_dev": "Backend Developer",
    "frontend_dev": "Frontend Developer",
    "qa_engineer": "QA Engineer",
    "code_reviewer": "Code Reviewer",
    "documentation": "Documentation",
    "github": "GitHub Automation",
    "human_checkpoint_final": "Final Approval",
}


def _summarize_node(node_name: str, update_data: dict) -> dict:
    label = AGENT_LABELS.get(node_name, node_name)
    
    if node_name == "__start__":
        return {"node": "start", "label": "Starting", "status": "running"}
    
    if node_name == "__end__":
        return {"node": "end", "label": "Done", "status": "complete"}
    
    messages = update_data.get("messages", [])
    message_text = ""
    if messages:
        last = messages[-1]
        if hasattr(last, "content"):
            message_text = last.content[:200]
        elif isinstance(last, dict):
            message_text = str(last.get("content", ""))[:200]

    files = update_data.get("files", {})
    file_count = len(files) if files else 0
    
    test_results = update_data.get("test_results", {})
    review = update_data.get("review_feedback", [])
    
    summary = {"node": node_name, "label": label, "status": "complete"}
    
    if file_count:
        summary["files_generated"] = file_count
    if message_text:
        summary["message"] = message_text
    if test_results:
        summary["test_results"] = test_results
    if review:
        summary["review_issues"] = len(review)
    
    return summary


@ws_router.websocket("/ws/{project_id}")
async def websocket_endpoint(websocket: WebSocket, project_id: str):
    await manager.connect(project_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = {"type": "ping", "project_id": project_id}
            await websocket.send_json(msg)
    except WebSocketDisconnect:
        manager.disconnect(project_id, websocket)


@ws_router.post("/api/projects/{project_id}/stream")
async def stream_project(project_id: str):
    """Stream graph execution as newline-delimited JSON events."""
    from fastapi.responses import StreamingResponse

    state = active_projects.get(project_id)
    if not state:
        return {"error": "Project not found"}

    async def event_generator():
        if state.get("current_task") == "human_checkpoint_arch":
            thread_id = project_id
            for update in stream_resume(thread_id, approved=False, feedback=""):
                msg = _summarize_node(update.get("node", ""), update.get("update", {}))
                yield json.dumps(msg) + "\n"
                await manager.broadcast(project_id, msg)
                await asyncio.sleep(0.01)
        else:
            pass

        yield json.dumps({"type": "stream_end"}) + "\n"

    import json
    return StreamingResponse(event_generator(), media_type="application/x-ndjson")
