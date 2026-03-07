import os
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from api.dependencies import get_base_dir, get_latest_result
from api.schemas.pipeline import PipelineRunRequest, PipelineRunResponse, PipelineStatusResponse

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

@router.post("/run", response_model=PipelineRunResponse, summary="Trigger daily pipeline", description="Triggers the full daily pipeline with a new CSV data file path")
async def run_pipeline(request: PipelineRunRequest):
    target_path = request.csv_path
    
    # Check if absolute path; if not, assume relative to base_dir
    if not os.path.isabs(target_path):
        target_path = os.path.join(get_base_dir(), target_path)
        
    if not os.path.exists(target_path):
        raise HTTPException(status_code=400, detail=f"CSV file not found at path: {target_path}")
        
    try:
        from run_daily_pipeline import run_daily_pipeline
        
        # Run the pipeline in a separate thread so it doesn't block
        output_path = await run_in_threadpool(run_daily_pipeline, target_path)
        
        # Use get_latest_result to fetch metadata since it just ran and updated it
        latest_metadata = get_latest_result()
        
        return {
            "success": True,
            "output_path": output_path,
            "gemini_attempts": latest_metadata.get("gemini_attempts", 0),
            "validation_warnings": latest_metadata.get("validation_warnings", []),
            "date": latest_metadata.get("date", ""),
            "message": "Pipeline completed successfully."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")

@router.get("/status", response_model=PipelineStatusResponse, summary="Get pipeline status", description="Returns metadata about the last pipeline run from latest_result.json")
def get_pipeline_status():
    result = get_latest_result()
    return {
        "date": result.get("date", ""),
        "pipeline_ran_at": result.get("pipeline_ran_at", ""),
        "gemini_model_used": result.get("gemini_model_used", ""),
        "gemini_attempts": result.get("gemini_attempts", 0),
        "validation_warnings": result.get("validation_warnings", [])
    }
