from fastapi import APIRouter, HTTPException, Depends
from urllib.parse import unquote
from api.dependencies import get_latest_result, VALID_REGIONS
from api.schemas.prediction import PredictionData, PredictionSummaryResponse

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.get("", response_model=PredictionData, summary="Get full 3-day forecast", description="Returns full 3-day forecast for all regions from latest_result.json")
def get_all_predictions():
    result = get_latest_result()
    return result.get("predictions", {})

@router.get("/summary", response_model=PredictionSummaryResponse, summary="Get forecast summary", description="Returns prediction_date_start, generated_at, and a list of Day 1 AQI for all regions")
def get_predictions_summary():
    result = get_latest_result()
    preds = result.get("predictions", {})
    
    summary_regions = []
    regions_data = preds.get("regions", {})
    
    for r_name, r_data in regions_data.items():
        summary_regions.append({
            "region": r_name,
            "day_1_aqi": r_data.get("day_1", 0),
            "day_1_category": r_data.get("category", [""])[0] if r_data.get("category") else ""
        })
        
    return {
        "prediction_date_start": preds.get("prediction_date_start", ""),
        "generated_at": preds.get("generated_at", ""),
        "regions": summary_regions
    }

@router.get("/{region}", summary="Get forecast for a specific region", description="Returns 3-day forecast for a single region (URL-encode spaces). Returns 404 if region not found.")
def get_prediction_for_region(region: str):
    decoded_region = unquote(region)
    # Case-insensitive match against valid regions
    matched_region = next((r for r in VALID_REGIONS if r.lower() == decoded_region.lower()), None)
    
    if not matched_region:
        raise HTTPException(status_code=404, detail=f"Region '{decoded_region}' not found. Valid regions are: {', '.join(VALID_REGIONS)}")
        
    result = get_latest_result()
    preds = result.get("predictions", {}).get("regions", {})
    
    region_data = preds.get(matched_region)
    if not region_data:
        raise HTTPException(status_code=404, detail=f"No data found for region '{matched_region}'")
        
    return region_data
