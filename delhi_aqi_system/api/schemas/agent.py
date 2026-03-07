from pydantic import BaseModel, ConfigDict
from typing import List

class HistoryTurn(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    role: str
    content: str

class AgentChatRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    message: str
    agent_type: str = "public"
    history: List[HistoryTurn] = []

class AgentChatResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    response: str
    agent_type: str
    suggested_questions: List[str]
