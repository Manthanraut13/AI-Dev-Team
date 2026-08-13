from langchain_core.messages import HumanMessage, AIMessage
from app.graph.state import AgentState
from app.schemas.outputs import ArchitectureOutput
from app.memory.long_term import memory_service
from app.utils.llm import get_llm, invoke_with_retry
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software architect with expertise in:
- FastAPI and Python backend development
- Next.js, React, and TypeScript frontend development
- PostgreSQL database design
- RESTful API design
- Scalable system architecture

Given a list of requirements, produce a comprehensive architecture design including:
1. API endpoints (method, path, description)
2. Database schema (tables and columns)
3. Folder structure for the project
4. Key technology decisions and rationale

Always respond with valid JSON matching the schema provided.
Focus on practical, implementable designs."""

USER_PROMPT_TEMPLATE = """Requirements:
{requirements}

{context}

Please design the architecture for a system meeting these requirements.
Consider:
- RESTful API best practices
- Proper database normalization
- Clear separation of concerns
- Scalability and maintainability

Format your response as valid JSON."""


def architect_node(state: AgentState) -> AgentState:
    logger.info(f"Architect Agent starting for project: {state.get('project_name', 'unknown')}")
    
    requirements = state.get("requirements", [])
    if not requirements:
        logger.error("No requirements found in state")
        return {
            "current_task": "error",
            "messages": [
                AIMessage(content="Error: No requirements to design architecture from")
            ]
        }
    
    context_parts = []
    
    try:
        past_architectures = memory_service.search(
            collection="architectures",
            query="\n".join(requirements[:5]),
            limit=3
        )
        
        if past_architectures:
            context_parts.append("Relevant patterns from past projects:")
            for i, arch in enumerate(past_architectures, 1):
                context_parts.append(f"\n{i}. {arch['content'][:500]}...")
            logger.info(f"Found {len(past_architectures)} relevant past architectures")
    except Exception as e:
        logger.warning(f"Could not retrieve from long-term memory: {e}")
    
    context = "\n".join(context_parts) if context_parts else ""
    
    llm = get_llm(temperature=0.7)
    
    structured_llm = llm.with_structured_output(ArchitectureOutput)
    
    requirements_text = "\n".join(f"- {req}" for req in requirements)
    
    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(
            requirements=requirements_text,
            context=context
        ))
    ]
    
    try:
        result = invoke_with_retry(structured_llm, messages)
        
        architecture = {
            "api_endpoints": result.api_endpoints,
            "db_schema": result.db_schema,
            "folder_structure": result.folder_structure,
            "tech_decisions": result.tech_decisions
        }
        
        logger.info(f"Generated architecture with {len(result.api_endpoints)} endpoints and {len(result.db_schema)} tables")
        
        try:
            memory_service.store(
                collection="architectures",
                content=f"Project: {state.get('project_name')}\n\nRequirements: {requirements_text[:1000]}\n\nArchitecture: {str(architecture)[:2000]}",
                metadata={
                    "project_name": state.get("project_name"),
                    "type": "architecture"
                }
            )
        except Exception as e:
            logger.warning(f"Could not store architecture in long-term memory: {e}")
        
        return {
            "architecture": architecture,
            "current_task": "human_checkpoint_arch",
            "messages": [
                AIMessage(
                    content=f"Architecture designed:\n" +
                    f"- {len(result.api_endpoints)} API endpoints\n" +
                    f"- {len(result.db_schema)} database tables\n" +
                    f"- {len(result.tech_decisions)} technology decisions"
                )
            ]
        }
        
    except Exception as e:
        logger.error(f"Architect Agent failed: {e}")
        return {
            "current_task": "error",
            "messages": [
                AIMessage(content=f"Architect Agent error: {str(e)}")
            ]
        }
