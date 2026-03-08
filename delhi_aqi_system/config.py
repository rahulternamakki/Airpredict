import os
from dotenv import load_dotenv

# Load variables from .env file
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

# Gemini / Vertex AI Configuration
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY") # Optional for Vertex AI if using ADC
GCP_PROJECT        = os.getenv("GOOGLE_CLOUD_PROJECT", "your-project-id")
GCP_LOCATION       = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

GEMINI_MODEL       = "gemini-2.0-flash-001"   # Recommended for Vertex AI
GEMINI_TEMPERATURE = 0.2                      # Low = factual, consistent, not creative
GEMINI_MAX_TOKENS  = 4096                     # Enough for detailed 5-section output
GEMINI_TOP_P       = 0.85

# File Paths & Execution Parameters
base_dir = os.path.dirname(os.path.abspath(__file__))
LATEST_RESULT_PATH = os.path.join(base_dir, "outputs", "latest_result.json")
MAX_RETRIES        = 3
STALENESS_HOURS    = 30                       # Warn user if data older than this

# Phase 7 additions
AGENT_MODEL       = "gemini-2.0-flash-001"   # Flash for live chat
AGENT_TEMPERATURE = 0.7                  # More conversational than Phase 6 (0.2)
AGENT_MAX_TOKENS  = 1024
HISTORY_MAX_TURNS = 20                   # Max turns before trimming oldest
