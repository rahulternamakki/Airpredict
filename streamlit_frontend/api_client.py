# streamlit_frontend/api_client.py

import requests
import streamlit as st
from config_frontend import API_V1, REQUEST_TIMEOUT

# ── Generic fetch with error surfacing ──────────────────────

def _get(endpoint: str) -> dict | list | None:
    """
    GET request to the FastAPI backend.
    Returns parsed JSON on success.
    Shows st.error and returns None on failure.
    """
    url = f"{API_V1}{endpoint}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to API at {url}. Is the FastAPI server running?")
        st.code("uvicorn delhi_aqi_system.api.main:app --reload --port 8000")
        return None
    except requests.exceptions.Timeout:
        st.error(f"⏱ Request timed out ({REQUEST_TIMEOUT}s) at {url}.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error {resp.status_code}: {resp.json().get('detail', str(e))}")
        return None

def _post(endpoint: str, payload: dict) -> dict | None:
    """POST request to the FastAPI backend."""
    url = f"{API_V1}{endpoint}"
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to API at {url}.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error {resp.status_code}: {resp.json().get('detail', str(e))}")
        return None

# ── Endpoint-specific helpers ────────────────────────────────

def get_predictions_summary()  -> dict | None:
    return _get("/predictions/summary")

def get_all_predictions()      -> dict | None:
    return _get("/predictions")

def get_region_prediction(region: str) -> dict | None:
    from urllib.parse import quote
    return _get(f"/predictions/{quote(region)}")

def get_all_shap()             -> list | None:
    return _get("/shap")

def get_shap_for_region(region: str) -> list | None:
    from urllib.parse import quote
    return _get(f"/shap/{quote(region)}")

def get_shap_region_day(region: str, day: int) -> dict | None:
    from urllib.parse import quote
    return _get(f"/shap/{quote(region)}/day/{day}")

def get_all_counterfactuals()  -> list | None:
    return _get("/counterfactual")

def get_counterfactual_region(region: str) -> dict | None:
    from urllib.parse import quote
    return _get(f"/counterfactual/{quote(region)}")

def get_full_explanation()     -> dict | None:
    return _get("/explanation")

def get_explanation_section(section: str) -> dict | None:
    # section: "prediction" | "shap" | "counterfactual" | "health" | "intervention"
    return _get(f"/explanation/{section}")

def get_pipeline_status()      -> dict | None:
    return _get("/pipeline/status")

def trigger_pipeline(csv_path: str) -> dict | None:
    return _post("/pipeline/run", {"csv_path": csv_path})

def chat_with_agent(message: str, agent_type: str, history: list) -> dict | None:
    payload = {
        "message":    message,
        "agent_type": agent_type,
        "history":    history   # [{"role": "user"/"model", "content": "..."}]
    }
    return _post("/agent/chat", payload)

def get_suggested_questions(agent_type: str) -> list:
    result = _get(f"/agent/questions/{agent_type}")
    return result if isinstance(result, list) else []

def check_api_health() -> bool:
    """Returns True if API is reachable."""
    try:
        resp = requests.get(f"{API_V1.replace('/api/v1', '')}/health",
                            timeout=5)
        return resp.status_code == 200
    except Exception:
        return False
