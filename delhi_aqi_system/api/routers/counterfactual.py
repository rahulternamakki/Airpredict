from fastapi import APIRouter, HTTPException
from urllib.parse import unquote
from typing import List
from api.dependencies import get_latest_result, VALID_REGIONS
from api.schemas.counterfactual import CounterfactualEntry

router = APIRouter(prefix="/counterfactual", tags=["counterfactual"])

@router.get("", response_model=List[CounterfactualEntry], summary="Get all counterfactuals", description="Returns all counterfactual results")
def get_all_counterfactuals():
    result = get_latest_result()
    return result.get("counterfactuals", [])

@router.get("/{region}", response_model=CounterfactualEntry, summary="Get counterfactuals for region", description="Returns counterfactual scenarios for a specific region.")
def get_counterfactual_for_region(region: str):
    decoded_region = unquote(region)
    matched_region = next((r for r in VALID_REGIONS if r.lower() == decoded_region.lower()), None)
    
    if not matched_region:
        raise HTTPException(status_code=404, detail=f"Region '{decoded_region}' not found. Valid regions are: {', '.join(VALID_REGIONS)}")
        
    result = get_latest_result()
    cf_data = result.get("counterfactuals", [])
    
    region_cf = next((c for c in cf_data if c.get("region") == matched_region), None)
    if not region_cf:
        raise HTTPException(status_code=404, detail=f"No counterfactual data found for region '{matched_region}'")
        
    return region_cf
