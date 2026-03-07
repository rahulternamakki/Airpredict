from pydantic import BaseModel, ConfigDict
from typing import List

class ShapFeature(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    feature: str
    shap_value: float
    actual_value: float

class ShapEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    region: str
    prediction_day: int
    base_value: float
    predicted_value: float
    top_features: List[ShapFeature]
