from pydantic import BaseModel, ConfigDict

class ExplanationData(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    prediction_explanation: str
    shap_interpretation: str
    counterfactual_analysis: str
    health_impact_summary: str
    recommended_intervention: str

class ExplanationSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    section: str
    content: str
