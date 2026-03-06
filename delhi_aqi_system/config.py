import os
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Gemini Configuration
GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL       = "gemini-1.5-pro"        # Pro for explanation (quality over cost)
GEMINI_TEMPERATURE = 0.2                      # Low = factual, consistent, not creative
GEMINI_MAX_TOKENS  = 4096                     # Enough for detailed 5-section output
GEMINI_TOP_P       = 0.85

# File Paths & Execution Parameters
LATEST_RESULT_PATH = "outputs/latest_result.json"
MAX_RETRIES        = 3
STALENESS_HOURS    = 30                       # Warn user if data older than this
