"""Supervisor tools — LangGraph tool functions that orchestrate the specialist agents.

Each tool closes over the session and a broadcaster callback so it can:
  - Mutate session state (requirements, architecture, files, etc.)
  - Broadcast agent_update events for the UI sidebar
  - Return a human-readable string for the LLM to incorporate

Phase 1 tools:
  - plan_project(idea) → run product_manager + architect
  - build_project(feedback="") → run devs ∥ QA/reviewer → docs
  - write_to_workspace(overwrite=False) → write files to disk
  - list_workspace() → show file tree
  - read_file(path) → read a file from disk

All tools run the existing agent node functions directly (pure functions from
AgentState → dict). No LangGraph pipeline, no interrupts — just function calls.
"""
from __future__ import annotations

import concurrent.futures
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool

from app.agents.architect import architect_node
from app.agents.backend_dev import backend_dev_node
from app.agents.code_reviewer import code_reviewer_node
from app.agents.documentation import documentation_node
from app.agents.error_handler import error_handler_node
from app.agents.frontend_dev import frontend_dev_node
from app.agents.product_manager import product_manager_node
from app.agents.qa_engineer import qa_engineer_node
from app.services import workspace as ws

if TYPE_CHECKING:
    from app.services.session_store import Session


def make_tools(session: "Session", broadcast: Callable[[str, Dict[str, Any]], None]):
    """Return the list of LangGraph tools bound to a session and broadcaster."""

    def _broadcast_agent(node: str, status: str, message: Optional[str] = None, files_count: Optional[int] = None):
        """Helper to emit an agent_update event."""
        labels = {
            "product_manager": "Product Manager",
            "architect": "Architect",
            "backend_dev": "Backend Developer",
            "frontend_dev": "Frontend Developer",
            "qa_engineer": "QA Engineer",
            "code_reviewer": "Code Reviewer",
            "error_handler": "Error Handler",
            "documentation": "Documentation",
        }
        broadcast("agent_update", {
            "node": node,
            "label": labels.get(node, node),
            "status": status,
            "message": message,
            "files_count": files_count,
            "timestamp": time.time(),
        })

    @tool
    def plan_project(idea: str) -> str:
        """Plan a project from a user idea. Runs Product Manager then Architect.

        Stores requirements and architecture on the session. Returns a summary
        for the user to review and approve before building.
        """
        if not session.workspace_path:
            return "Error: No workspace set. Please set a workspace directory first."

        _broadcast_agent("product_manager", "running", "Analyzing requirements...")
        # Build minimal AgentState for the PM node.
        pm_state = {
            "project_name": session.name,
            "user_idea": idea,
            "requirements": [],
            "architecture": {},
            "files": {},
            "messages": [],
            "review_feedback": [],
            "test_results": {},
            "documentation": {},
            "human_approved": None,
            "github_pr_url": "",
        }
        pm_out = product_manager_node(pm_state)
        reqs = pm_out.get("requirements", [])
        session.requirements = reqs
        session.idea = idea
        _broadcast_agent("product_manager", "complete", f"Generated {len(reqs)} requirements")

        _broadcast_agent("architect", "running", "Designing architecture...")
        arch_state = dict(pm_state)
        arch_state["requirements"] = reqs
        arch_out = architect_node(arch_state)
        arch = arch_out.get("architecture", {})
        session.architecture = arch
        _broadcast_agent("architect", "complete", "Architecture designed")

        # Summarize for the LLM.
        ep_count = len(arch.get("api_endpoints", []))
        tables = len(arch.get("db_schema", []))
        tech = arch.get("tech_decisions", [])[:3]
        tech_str = ", ".join(tech) if tech else "see architecture"

        return (
            f"Plan created:\n"
            f"- {len(reqs)} requirements\n"
            f"- {ep_count} API endpoints, {tables} database tables\n"
            f"- Tech: {tech_str}\n\n"
            f"Present this plan to the user and ask for approval before building."
        )

    @tool
    def build_project(feedback: str = "") -> str:
        """Build the project code. Runs Backend Dev ∥ Frontend Dev, then QA ∥ Code Review, then Docs.

        Stores generated files, test results, review feedback, and documentation on the session.
        The `feedback` parameter is user feedback from a previous build (e.g., "fix the failing tests").
        """
        if not session.requirements or not session.architecture:
            return "Error: No plan found. Please run plan_project first."

        base_state: Dict[str, Any] = {
            "project_name": session.name,
            "user_idea": session.idea,
            "requirements": session.requirements,
            "architecture": session.architecture,
            "files": {},
            "messages": [],
            "review_feedback": [feedback] if feedback else [],
            "test_results": {},
            "documentation": {},
            "human_approved": None,
            "github_pr_url": "",
        }

        # Run backend and frontend devs in parallel.
        files: Dict[str, str] = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            _broadcast_agent("backend_dev", "running", "Generating backend...")
            _broadcast_agent("frontend_dev", "running", "Generating frontend...")
            be_future = pool.submit(backend_dev_node, dict(base_state))
            fe_future = pool.submit(frontend_dev_node, dict(base_state))
            be_out = be_future.result()
            fe_out = fe_future.result()

        be_files = be_out.get("files", {})
        fe_files = fe_out.get("files", {})
        files.update(be_files)
        files.update(fe_files)
        _broadcast_agent("backend_dev", "complete", f"{len(be_files)} files", files_count=len(be_files))
        _broadcast_agent("frontend_dev", "complete", f"{len(fe_files)} files", files_count=len(fe_files))

        # Run QA and Code Reviewer in parallel on the combined files.
        base_state["files"] = files
        _broadcast_agent("qa_engineer", "running", "Generating tests...")
        _broadcast_agent("code_reviewer", "running", "Reviewing code...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            qa_future = pool.submit(qa_engineer_node, dict(base_state))
            cr_future = pool.submit(code_reviewer_node, dict(base_state))
            qa_out = qa_future.result()
            cr_out = cr_future.result()

        test_files = qa_out.get("files", {})
        test_results = qa_out.get("test_results", {})
        files.update(test_files)
        session.test_results = test_results
        _broadcast_agent("qa_engineer", "complete",
                         f"{test_results.get('passed', 0)} passed, {test_results.get('failed', 0)} failed")

        review_feedback = cr_out.get("review_feedback", [])
        session.review_feedback = review_feedback
        _broadcast_agent("code_reviewer", "complete", f"{len(review_feedback)} issues found")

        # Run the Error Handler next — auto-fixes failing tests / reviewer issues.
        base_state["files"] = files
        base_state["review_feedback"] = review_feedback
        base_state["test_results"] = test_results
        _broadcast_agent("error_handler", "running", "Diagnosing failures...")
        eh_out = error_handler_node(dict(base_state))
        fixed_files = eh_out.get("files", {})
        files.update(fixed_files)
        session.test_results = eh_out.get("test_results", test_results)
        session.errors = eh_out.get("errors", [])
        session.fixes = eh_out.get("fixes", [])
        _broadcast_agent(
            "error_handler",
            "complete",
            f"{len(session.fixes)} fix(es), {len(session.errors)} error(s) remaining",
        )

        # Run Documentation last.
        base_state["files"] = files
        base_state["review_feedback"] = review_feedback
        _broadcast_agent("documentation", "running", "Generating docs...")
        doc_out = documentation_node(base_state)
        doc_files = doc_out.get("files", {})
        files.update(doc_files)
        session.documentation = doc_out.get("documentation", {})
        _broadcast_agent("documentation", "complete", f"{len(doc_files)} doc files")

        # Merge into session.
        session.files = files

        # Summarize for the LLM.
        be_count = len([k for k in files if k.startswith("backend/")])
        fe_count = len([k for k in files if k.startswith("frontend/")])
        test_count = len([k for k in files if "test" in k.lower()])
        doc_count = len([k for k in files if k.startswith("docs/")])
        passed = test_results.get("passed", 0)
        failed = test_results.get("failed", 0)

        summary = (
            f"Build complete:\n"
            f"- Backend: {be_count} files\n"
            f"- Frontend: {fe_count} files\n"
            f"- Tests: {test_count} files ({passed} passed, {failed} failed)\n"
            f"- Docs: {doc_count} files\n"
        )
        if review_feedback:
            summary += f"- Review: {len(review_feedback)} issues\n"
        if session.fixes:
            summary += f"- Error Handler: {len(session.fixes)} fix(es) applied\n"
        if session.errors:
            summary += f"- Remaining errors: {len(session.errors)}\n"
        if failed > 0 and not session.fixes:
            summary += "\nSome tests failed. You can ask me to fix them or proceed to write the files as-is."
        else:
            summary += "\nReady to write to workspace."

        return summary

    @tool
    def write_to_workspace(overwrite: bool = False) -> str:
        """Write the generated files to the workspace directory on disk.

        Skips files that already exist with identical content (unless overwrite=True).
        Returns the count of written and skipped files.
        """
        if not session.workspace_path:
            return "Error: No workspace set."
        if not session.files:
            return "Error: No files generated. Run build_project first."

        try:
            written, skipped = ws.write_files(session.workspace_path, session.files, overwrite=overwrite)
        except ws.WorkspaceError as e:
            return f"Error: {e}"

        # Broadcast so the UI file panel refreshes.
        broadcast("workspace.updated", {
            "written": written,
            "skipped": skipped,
            "timestamp": time.time(),
        })

        # Hint the frontend to auto-start the preview (zero clicks).
        broadcast("preview.auto", {
            "session_id": session.id,
            "workspace_path": session.workspace_path,
        })

        msg = f"Wrote {len(written)} files to {session.workspace_path}"
        if skipped:
            msg += f", skipped {len(skipped)} (unchanged)"
        return msg

    @tool
    def list_workspace() -> str:
        """List the files in the workspace directory. Returns a tree summary."""
        if not session.workspace_path:
            return "Error: No workspace set."
        try:
            nodes = ws.list_files(session.workspace_path)
        except ws.WorkspaceError as e:
            return f"Error: {e}"

        dirs = [n for n in nodes if n.type == "dir"]
        files = [n for n in nodes if n.type == "file"]
        return f"Workspace has {len(files)} files in {len(dirs)} directories. Use read_file to view specific files."

    @tool
    def read_file(path: str) -> str:
        """Read a file from the workspace. Use forward slashes for the path."""
        if not session.workspace_path:
            return "Error: No workspace set."
        try:
            _, content = ws.read_file(session.workspace_path, path)
            return content
        except ws.WorkspaceError as e:
            return f"Error: {e}"

    # Return all tools bound to this session.
    return [plan_project, build_project, write_to_workspace, list_workspace, read_file]
