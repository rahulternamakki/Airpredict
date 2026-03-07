# streamlit_frontend/config_frontend.py

import os

# ── API Connection ──────────────────────────────────────────
API_BASE_URL   = os.getenv("DELHI_AQI_API_URL", "http://localhost:8000")
API_V1         = f"{API_BASE_URL}/api/v1"
REQUEST_TIMEOUT = 15   # seconds — fail fast if API is down

# ── AQI Color Palette (CPCB Standard) ──────────────────────
AQI_COLORS = {
    "Good":                        "#00B050",  # Green
    "Satisfactory":                "#92D050",  # Light Green
    "Moderate":                    "#FFFF00",  # Yellow
    "Poor":                        "#FF7C00",  # Orange
    "Very Poor":                   "#FF0000",  # Red
    "Severe":                      "#7030A0",  # Purple
}

AQI_TEXT_COLORS = {
    # Text color on the colored background (for readability)
    "Good":          "white",
    "Satisfactory":  "black",
    "Moderate":      "black",
    "Poor":          "white",
    "Very Poor":     "white",
    "Severe":        "white",
}

# ── AQI Thresholds (CPCB) ──────────────────────────────────
def get_aqi_category(aqi: int) -> str:
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Satisfactory"
    if aqi <= 200:  return "Moderate"
    if aqi <= 300:  return "Poor"
    if aqi <= 400:  return "Very Poor"
    return "Severe"

# ── App Pages Config ────────────────────────────────────────
PAGE_CONFIG = {
    "page_title": "Delhi AQI Intelligence System",
    "page_icon":  "🌫️",
    "layout":     "wide",
    "initial_sidebar_state": "expanded",
}

# ── Regions ─────────────────────────────────────────────────
REGIONS = [
    "Central Delhi", "West Delhi", "East Delhi",
    "North Delhi", "South Delhi", "Overall Delhi"
]

# ── Staleness ───────────────────────────────────────────────
STALENESS_HOURS = 30
