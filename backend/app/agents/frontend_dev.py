from langchain_core.messages import HumanMessage, AIMessage
from typing import Dict
from app.utils.llm import get_llm, invoke_with_retry
from app.utils.files import parse_files
import logging

logger = logging.getLogger(__name__)


def frontend_dev_node(state) -> dict:
    project_name = state.get("project_name", "project")
    architecture = state.get("architecture", {})
    requirements = state.get("requirements", [])

    logger.info(f"Frontend Dev starting for {project_name}")

    if not architecture:
        return {"current_task": "error", "messages": [AIMessage(content="No architecture")]}

    endpoints = [f"{e.get('method','GET')} {e.get('path','/')}" for e in architecture.get("api_endpoints", [])[:6]]
    req_text = "\n".join(f"- {r[:60]}" for r in requirements[:5])
    ep_text = "\n".join(endpoints)

    prompt = f"""Generate a complete Next.js 14 frontend for project "{project_name}".

Requirements:
{req_text}

Backend API:
{ep_text}

Generate ALL of the following files. For each file, use this EXACT format:

### FILE: <relative/path>
<complete file content>

Generate these files:
1. package.json — next@14, react@18, tailwindcss, typescript
2. tsconfig.json — standard Next.js config with @/* alias
3. tailwind.config.js — content globs for app/ and components/
4. postcss.config.js — tailwindcss + autoprefixer
5. app/globals.css — tailwind directives
6. app/layout.tsx — root layout with metadata
7. app/page.tsx — landing page with Tailwind styling
8. lib/api.ts — typed fetch wrappers for every API endpoint above
9. types/index.ts — TypeScript interfaces for API responses

Write complete, runnable code. No placeholders."""

    llm = get_llm(temperature=0.3, max_tokens=4000)
    response = invoke_with_retry(llm, [HumanMessage(content=prompt)])

    files = parse_files(response.content)

    frontend_files = {f"frontend/{k}": v for k, v in files.items()}

    logger.info(f"Generated {len(frontend_files)} frontend files: {list(frontend_files.keys())}")

    return {
        "files": frontend_files,
        "current_task": "human_checkpoint_final",
        "messages": [AIMessage(content=f"Frontend: {len(frontend_files)} files generated")]
    }
