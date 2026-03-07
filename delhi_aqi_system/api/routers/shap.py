from fastapi import APIRouter, HTTPException
from urllib.parse import unquote
from typing import List
from api.dependencies import get_latest_result, VALID_REGIONS
from api.schemas.shap import ShapEntry

router = APIRouter(prefix="/shap", tags=["shap"])

@router.get("", response_model=List[ShapEntry], summary="Get full SHAP analysis", description="Returns full SHAP analysis list")
def get_all_shap():
    result = get_latest_result()
    return result.get("shap", [])

@router.get("/{region}", response_model=List[ShapEntry], summary="Get SHAP for region", description="Returns SHAP data for a specific region across all prediction days.")
def get_shap_for_region(region: str):
    decoded_region = unquote(region)
    matched_region = next((r for r in VALID_REGIONS if r.lower() == decoded_region.lower()), None)
    
    if not matched_region:
        raise HTTPException(status_code=404, detail=f"Region '{decoded_region}' not found. Valid regions are: {', '.join(VALID_REGIONS)}")
        
    result = get_latest_result()
    shap_data = result.get("shap", [])
    
    region_shap = [s for s in shap_data if s.get("region") == matched_region]
    if not region_shap:
        raise HTTPException(status_code=404, detail=f"No SHAP data found for region '{matched_region}'")
        
    return region_shap

@router.get("/{region}/day/{day}", response_model=ShapEntry, summary="Get SHAP for region and day", description="Returns SHAP data for a specific region and day (1, 2, or 3).")
def get_shap_for_region_day(region: str, day: int):
    if day not in [1, 2, 3]:
        raise HTTPException(status_code=422, detail="Day must be 1, 2, or 3")
        
    decoded_region = unquote(region)
    matched_region = next((r for r in VALID_REGIONS if r.lower() == decoded_region.lower()), None)
    
    if not matched_region:
        raise HTTPException(status_code=404, detail=f"Region '{decoded_region}' not found. Valid regions are: {', '.join(VALID_REGIONS)}")
        
    result = get_latest_result()
    shap_data = result.get("shap", [])
    
    target_shap = next((s for s in shap_data if s.get("region") == matched_region and s.get("prediction_day") == day), None)
    
    if not target_shap:
        raise HTTPException(status_code=404, detail=f"No SHAP data found for region '{matched_region}' on day {day}")
        
    return target_shap
