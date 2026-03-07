import os
import sys
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Add pipeline directory to sys.path before importing dependencies and routers
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pipeline_dir = os.path.join(base_dir, "pipeline")
agents_dir = os.path.join(base_dir, "agents")

if pipeline_dir not in sys.path:
    sys.path.insert(0, pipeline_dir)
if agents_dir not in sys.path:
    sys.path.insert(0, agents_dir)
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

# Import routers
from api.routers import predictions, shap, counterfactual, explanation, agent, pipeline

app = FastAPI(
    title="Delhi AQI System API",
    version="1.0.0",
    description="API for the Delhi AQI Prediction System, providing forecasts, SHAP analysis, counterfactuals, and AI chat."
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(predictions.router, prefix="/api/v1")
app.include_router(shap.router, prefix="/api/v1")
app.include_router(counterfactual.router, prefix="/api/v1")
app.include_router(explanation.router, prefix="/api/v1")
app.include_router(agent.router, prefix="/api/v1")
app.include_router(pipeline.router, prefix="/api/v1")

@app.on_event("startup")
async def startup_event():
    print("=" * 60)
    print("Delhi AQI System API starting up...")
    print(f"Added to sys.path: {pipeline_dir}")
    print(f"Added to sys.path: {agents_dir}")
    print("=" * 60)

@app.get("/", summary="Root endpoint", description="Returns basic status")
def read_root():
    return {"status": "ok", "message": "Delhi AQI API running"}

@app.get("/health", summary="Health check", description="Returns system health status and timestamp")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# HOW TO RUN
# bash
# # From the project root (parent of delhi_aqi_system/):
# uvicorn delhi_aqi_system.api.main:app --reload --port 8000
# 
# # API docs will be available at:
# # http://localhost:8000/docs   (Swagger UI)
# # http://localhost:8000/redoc  (ReDoc)
