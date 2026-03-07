from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from typing import List
from api.dependencies import VALID_AGENT_TYPES
from api.schemas.agent import AgentChatRequest, AgentChatResponse

# We import these after the app setup script has added their paths in main.py, 
# but for local dev to work cleanly, relying on the startup event.
# The `call_agent` etc are available once added to path.
try:
    from agent_core import call_agent
    from context_builder import build_context_for_agent
    from suggested_questions import get_suggested_questions
except ImportError:
    # They will be resolved at runtime by dependencies.py / main.py
    pass

router = APIRouter(prefix="/agent", tags=["agent"])

@router.post("/chat", response_model=AgentChatResponse, summary="Send message to AI agent", description="Sends a message to the AI agent and returns the response")
async def chat_with_agent(request: AgentChatRequest):
    if request.agent_type not in VALID_AGENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid agent_type. Must be one of: {', '.join(VALID_AGENT_TYPES)}")
        
    try:
        from context_builder import build_context_for_agent
        from agent_core import call_agent
        from suggested_questions import get_suggested_questions
        
        context = await run_in_threadpool(build_context_for_agent, request.agent_type)
        
        formatted_history = [{"role": turn.role, "content": turn.content} for turn in request.history]
        
        response_text = await run_in_threadpool(
            call_agent, 
            request.message, 
            request.agent_type, 
            context, 
            formatted_history
        )
        
        suggested = await run_in_threadpool(get_suggested_questions, request.agent_type)
        
        # Select 3 randomly (if there are more than 3)
        import random
        if len(suggested) > 3:
            suggested = random.sample(suggested, 3)
            
        return {
            "response": response_text,
            "agent_type": request.agent_type,
            "suggested_questions": suggested
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with agent: {str(e)}")

@router.get("/questions/{agent_type}", response_model=List[str], summary="Get suggested starter questions")
async def get_questions(agent_type: str):
    if agent_type not in VALID_AGENT_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid agent_type. Must be one of: {', '.join(VALID_AGENT_TYPES)}")
        
    try:
        from suggested_questions import get_suggested_questions
        suggested = await run_in_threadpool(get_suggested_questions, agent_type)
        return suggested
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
