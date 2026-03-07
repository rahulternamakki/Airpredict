from pydantic import BaseModel, ConfigDict
from typing import Dict, List, Optional

class Scenario(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    name: str
    type: str
    feature_changes: Dict[str, float]
    new_aqi: float
    new_category: str
    aqi_reduction: float
    percent_improvement: str
    original_feature_value: Optional[Dict[str, float]] = None
    perturbed_feature_value: Optional[Dict[str, float]] = None
    original_feature_values: Optional[Dict[str, float]] = None
    perturbed_feature_values: Optional[Dict[str, float]] = None

class CounterfactualEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    region: str
    original_day1_aqi: float
    original_category: str
    method: str
    scenarios: List[Scenario]
