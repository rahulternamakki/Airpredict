# streamlit_frontend/components/sidebar.py

import streamlit as st
from api_client import check_api_health

def render_sidebar():
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
