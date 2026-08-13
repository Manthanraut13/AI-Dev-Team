from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict, List
from app.utils.llm import get_llm, invoke_with_retry
from app.utils.files import parse_files
from app.utils.test_runner import materialize_and_run
import logging

logger = logging.getLogger(__name__)


def qa_engineer_node(state) -> dict:
    architecture = state.get("architecture", {})
    files = state.get("files", {})
    project_name = state.get("project_name", "project")

    logger.info(f"QA Engineer starting for {project_name}")

    if not architecture:
        return {
            "current_task": "error",
            "messages": [AIMessage(content="QA Engineer error: No architecture in state")]
        }

    endpoints = [
        f"{e.get('method','GET')} {e.get('path','/')}"
        for e in architecture.get("api_endpoints", [])[:6]
    ]
    ep_text = "\n".join(endpoints)

    backend_files = [k for k in files if k.startswith("backend/") and k.endswith(".py")]
    frontend_files = [k for k in files if k.startswith("frontend/")]

    llm = get_llm(temperature=0.3, max_tokens=4000)

    test_files: Dict[str, str] = {}

    if backend_files:
        prompt = f"""Project: {project_name}
Generate Pytest tests for the backend. API endpoints:
{ep_text}

Generated backend files: {", ".join(backend_files)}

Use this format for each file:

### FILE: tests/test_api.py
<complete pytest test file with fixtures using httpx AsyncClient and pytest-asyncio>

Write tests for the main endpoints. Use async tests with an async test client."""
        try:
            response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
            parsed = parse_files(response.content, trim_prose=True)
            for k, v in parsed.items():
                test_files[f"backend/{k}"] = v
            logger.info(f"Generated {len(parsed)} backend test files")
        except Exception as e:
            logger.error(f"Backend test generation failed: {e}")

    if frontend_files:
        prompt = f"""Project: {project_name}
Generate Playwright tests for the frontend. The frontend calls this API:
{ep_text}

Generated frontend files: {", ".join(frontend_files[:5])}

Use this format for each file:

### FILE: tests/e2e.spec.ts
<complete Playwright test file using @playwright/test>

Write basic page-load and navigation smoke tests."""
        try:
            response = invoke_with_retry(llm, [HumanMessage(content=prompt)])
            parsed = parse_files(response.content, trim_prose=True)
            for k, v in parsed.items():
                test_files[f"frontend/{k}"] = v
            logger.info(f"Generated {len(parsed)} frontend test files")
        except Exception as e:
            logger.error(f"Frontend test generation failed: {e}")

    test_results = {"passed": 0, "failed": 0, "logs": "Tests not run: generated code is not on disk yet", "exit_code": -1}

    if test_files:
        all_files = {**files, **test_files}
        backend_keys = [k for k in all_files if k.startswith("backend/")]

        if backend_keys:
            logger.info("Attempting to run backend tests...")
            test_results = materialize_and_run(all_files, timeout=60)

    return {
        "files": test_files,
        "test_results": test_results,
        "current_task": "documentation",
        "messages": [
            AIMessage(
                content=(
                    f"QA complete: {len(test_files)} test files generated. "
                    f"Results: {test_results.get('passed', 0)} passed, "
                    f"{test_results.get('failed', 0)} failed"
                )
            )
        ]
    }
