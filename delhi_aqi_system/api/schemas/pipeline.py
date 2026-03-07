from pydantic import BaseModel, ConfigDict
from typing import List

class PipelineRunRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    csv_path: str

class PipelineRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    output_path: str
    gemini_attempts: int
    validation_warnings: List[str]
    date: str
    message: str

class PipelineStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    date: str
    pipeline_ran_at: str
    gemini_model_used: str
    gemini_attempts: int
    validation_warnings: List[str]
