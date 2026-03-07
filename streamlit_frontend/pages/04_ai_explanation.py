# pages/04_ai_explanation.py

import streamlit as st
from api_client import get_full_explanation, get_pipeline_status
from components.staleness_banner import render_staleness_banner

st.set_page_config(page_title="AI Explanation | Delhi AQI", page_icon="🤖", layout="wide")

st.title("🤖 AI Scientific Explanation")
st.caption("Gemini-generated atmospheric science analysis of today's AQI forecast.")

# ── Staleness banner ──────────────────────────────────────────
status = get_pipeline_status()
if status:
    render_staleness_banner(
        status.get("pipeline_ran_at", ""),
        status.get("gemini_model_used", ""),
        status.get("gemini_attempts", 1)
    )

# ── Validation warnings ───────────────────────────────────────
if status and status.get("validation_warnings"):
    with st.expander("⚠ Data quality notices"):
        for w in status["validation_warnings"]:
            st.warning(w)

st.divider()

# ── Fetch and render explanation ──────────────────────────────
explanation = get_full_explanation()
if explanation:
    # Section 1 — Forecast Explanation
    with st.container():
        st.subheader("📈 Forecast Explanation")
        st.write(explanation.get("prediction_explanation", "Not available."))

    st.divider()

    # Section 2 — SHAP Interpretation
    with st.container():
        st.subheader("🔍 Why These Predictions? (SHAP Interpretation)")
        st.write(explanation.get("shap_interpretation", "Not available."))

    st.divider()

    # Section 3 — Counterfactual Analysis
    with st.container():
        st.subheader("🔄 What-If Scenario Analysis")
        st.write(explanation.get("counterfactual_analysis", "Not available."))

    st.divider()

    # Section 4 — Health Impact
    with st.container():
        st.subheader("🏥 Health Impact Summary")
        st.write(explanation.get("health_impact_summary", "Not available."))

    st.divider()

    # Section 5 — Recommended Intervention
    with st.container():
        st.subheader("✅ Recommended Intervention")
        st.info(explanation.get("recommended_intervention", "Not available."))
else:
    st.error("No explanation found. Ensure the pipeline has run successfully.")
    st.code("python run_daily_pipeline.py data/raw/latest.csv")
