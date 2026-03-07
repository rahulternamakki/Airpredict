# streamlit_frontend/streamlit_frontend.py

import streamlit as st
from config_frontend import PAGE_CONFIG
from api_client import check_api_health

# ── Page config (must be first Streamlit call) ───────────────
st.set_page_config(**PAGE_CONFIG)

# ── Sidebar nav ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/"
             "Flag_of_Delhi.svg/240px-Flag_of_Delhi.svg.png", width=80)
    st.title("Delhi AQI\nIntelligence")
    st.divider()

    # API health indicator
    if check_api_health():
        st.success("🟢 API Connected")
    else:
        st.error("🔴 API Offline\nStart: `uvicorn delhi_aqi_system.api.main:app --port 8000`")

    st.caption("Navigate using the sidebar pages above.")
    st.divider()
    st.caption("Delhi AQI Prediction System\nXGBoost + SHAP + Gemini AI")

# ── Landing page content ──────────────────────────────────────
st.title("🌫️ Delhi AQI Intelligence System")
st.markdown("""
Welcome to the **Delhi AQI Intelligence System** — a research-grade air quality
forecasting and explanation platform powered by **XGBoost**, **SHAP**, and **Gemini AI**.

Use the sidebar to navigate between pages:

| Page | What it shows |
|---|---|
| 🏠 Dashboard | 3-day AQI forecast for all Delhi regions with color-coded cards |
| 📊 Model Insights | SHAP feature importance plots — why each prediction was made |
| 🔄 What-If Scenarios | Counterfactual analysis — how much interventions could reduce AQI |
| 🤖 AI Explanation | Gemini-generated scientific narrative of today's forecast |
| 🤖 AI Agents | Toggle between Vayu (public assistant) and DELPHI (policy advisor) on one page |
""")
