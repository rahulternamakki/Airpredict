import os
import sys
import json
from fastapi import HTTPException

# Constants
VALID_REGIONS = [
    "Central Delhi",
    "West Delhi",
    "East Delhi",
    "South Delhi",
    "North Delhi",
    "Overall Delhi"
]

VALID_AGENT_TYPES = ["public", "policy"]

def get_base_dir() -> str:
    """Returns the absolute path to the delhi_aqi_system/ directory."""
    # Assuming this file is at delhi_aqi_system/api/dependencies.py
    current_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(current_dir)
    return base_dir

def setup_sys_path():
    """Adds the pipeline and agent directories to sys.path so modules can be imported."""
    base_dir = get_base_dir()
    pipeline_dir = os.path.join(base_dir, "pipeline")
    agents_dir = os.path.join(base_dir, "agents")
    
    if pipeline_dir not in sys.path:
        sys.path.insert(0, pipeline_dir)
    if agents_dir not in sys.path:
        sys.path.insert(0, agents_dir)
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

def get_latest_result() -> dict:
    """Loads and returns outputs/latest_result.json, raises HTTPException(503) if file not found."""
    base_dir = get_base_dir()
    latest_result_path = os.path.join(base_dir, "outputs", "latest_result.json")
    
    if not os.path.exists(latest_result_path):
        raise HTTPException(status_code=503, detail="Latest result data not found. System might be running the pipeline.")
        
    try:
        with open(latest_result_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading result data: {str(e)}")
