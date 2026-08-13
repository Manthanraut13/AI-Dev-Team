from langchain_core.messages import HumanMessage, AIMessage
from app.graph.state import AgentState
from app.schemas.outputs import RequirementsOutput
from app.config import settings
from app.utils.llm import get_llm, invoke_with_retry
import logging

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior product manager with extensive experience in software development. 
Given a software idea, produce a structured list of:
1. Functional requirements - what the system must do
2. Non-functional requirements - quality attributes (performance, security, scalability, etc.)
3. Prioritized tasks - ordered list of implementation tasks

Always respond with valid JSON matching the schema provided.
Be specific and actionable in your requirements.
Each requirement should be clear, testable, and unambiguous."""

USER_PROMPT_TEMPLATE = """Software Idea: {idea}

Please analyze this idea and produce:
1. A comprehensive list of functional requirements
2. Non-functional requirements (security, performance, usability, etc.)
3. A prioritized breakdown of tasks

Format your response as valid JSON."""


def product_manager_node(state: AgentState) -> AgentState:
    logger.info(f"Product Manager Agent starting for project: {state.get('project_name', 'unknown')}")
    
    user_idea = state.get("user_idea", "")
    if not user_idea:
        logger.error("No user_idea found in state")
        return {
            "current_task": "error",
            "messages": [
                AIMessage(content="Error: No user idea provided")
            ]
        }
    
    llm = get_llm(temperature=0.7)
    
    structured_llm = llm.with_structured_output(RequirementsOutput)
    
    messages = [
        HumanMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=USER_PROMPT_TEMPLATE.format(idea=user_idea))
    ]
    
    try:
        result = invoke_with_retry(structured_llm, messages)
        
        requirements = []
        requirements.extend([f"[FUNC] {req}" for req in result.functional])
        requirements.extend([f"[NFR] {req}" for req in result.non_functional])
        
        logger.info(f"Generated {len(requirements)} requirements and {len(result.tasks)} tasks")
        
        return {
            "requirements": requirements,
            "current_task": "architect",
            "messages": [
                AIMessage(
                    content=f"Generated {len(requirements)} requirements:\n" +
                    "\n".join(requirements[:5]) +
                    (f"\n... and {len(requirements) - 5} more" if len(requirements) > 5 else "")
                )
            ]
        }
        
    except Exception as e:
        logger.error(f"Product Manager Agent failed: {e}")
        return {
            "current_task": "error",
            "messages": [
                AIMessage(content=f"Product Manager Agent error: {str(e)}")
            ]
        }
