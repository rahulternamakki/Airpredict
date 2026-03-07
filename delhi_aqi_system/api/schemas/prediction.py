from pydantic import BaseModel, ConfigDict
from typing import Dict, List

class RegionPrediction(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    day_1: float
    day_2: float
    day_3: float
    category: List[str]

class PredictionData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    prediction_date_start: str
    generated_at: str
    regions: Dict[str, RegionPrediction]

class RegionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    region: str
    day_1_aqi: float
    day_1_category: str

class PredictionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    prediction_date_start: str
    generated_at: str
    regions: List[RegionSummary]
