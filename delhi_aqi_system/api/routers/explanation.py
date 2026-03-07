from fastapi import APIRouter, HTTPException
from api.dependencies import get_latest_result
from api.schemas.explanation import ExplanationData, ExplanationSectionResponse

router = APIRouter(prefix="/explanation", tags=["explanation"])

@router.get("", response_model=ExplanationData, summary="Get full explanation", description="Returns the full Gemini explanation object (all 5 sections) from latest_result.json")
def get_full_explanation():
    result = get_latest_result()
    return result.get("explanation", {})

def _get_explanation_section(section_name: str) -> dict:
    result = get_latest_result()
    explanation = result.get("explanation", {})
    if section_name not in explanation:
        raise HTTPException(status_code=404, detail=f"Section '{section_name}' not found in explanation")
    
    return {"section": section_name, "content": explanation[section_name]}

@router.get("/prediction", response_model=ExplanationSectionResponse, summary="Get prediction explanation")
def get_prediction_explanation():
    return _get_explanation_section("prediction_explanation")

@router.get("/health", response_model=ExplanationSectionResponse, summary="Get health impact summary")
def get_health_impact():
    return _get_explanation_section("health_impact_summary")

@router.get("/intervention", response_model=ExplanationSectionResponse, summary="Get recommended intervention")
def get_intervention():
    return _get_explanation_section("recommended_intervention")

@router.get("/shap", response_model=ExplanationSectionResponse, summary="Get SHAP interpretation")
def get_shap_interpretation():
    return _get_explanation_section("shap_interpretation")

@router.get("/counterfactual", response_model=ExplanationSectionResponse, summary="Get counterfactual analysis")
def get_counterfactual_analysis():
    return _get_explanation_section("counterfactual_analysis")
