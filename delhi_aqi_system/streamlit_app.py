import json
import os
import streamlit as st
from datetime import datetime

# Provide absolute root or assume run from project dir
try:
    from config import LATEST_RESULT_PATH, STALENESS_HOURS
except ImportError:
    LATEST_RESULT_PATH = "outputs/latest_result.json"
    STALENESS_HOURS = 30

@st.cache_data(ttl=300)  # Cache for 5 minutes, then re-read file
def load_latest_result(filepath=LATEST_RESULT_PATH):
    # Try resolving path absolute to here just in case Streamlit runs from varying dirs
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = filepath
    if not os.path.isabs(filepath):
        full_path = os.path.join(base_dir, filepath)

    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def render_explanation_page():
    result = load_latest_result()

    if result is None:
        st.error("No explanation data found. Run the daily pipeline first.")
        st.code("python run_daily_pipeline.py data/raw/latest.csv")
        return

    explanation = result.get("explanation", {})
    if not dict(explanation):
        st.error("No explanation section found in latest_result.json. Did Gemini API generation fail?")
        return

    # ── Header with freshness indicator ──────────────────────────
    ran_at    = datetime.fromisoformat(result.get("pipeline_ran_at", datetime.now().isoformat()))
    age_hours = (datetime.now() - ran_at).total_seconds() / 3600
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🤖 AI Scientific Explanation")
        st.caption(
            f"Generated: {ran_at.strftime('%d %b %Y, %I:%M %p')} | "
            f"Model: {result.get('gemini_model_used', 'gemini-1.5-pro')} | "
            f"Attempts: {result.get('gemini_attempts', 1)}/3"
        )
    with col2:
        if age_hours <= 24:
            st.success(f"✓ Fresh ({age_hours:.0f}h ago)")
        elif age_hours <= STALENESS_HOURS:
            st.warning(f"⚠ {age_hours:.0f}h old")
        else:
            st.error(f"⚠ Stale ({age_hours:.0f}h old)\nRun pipeline to refresh")

    # Validation warnings (if Gemini didn't fully pass all tests)
    if result.get("validation_warnings"):
        with st.expander("⚠ Data quality notices"):
            for w in result["validation_warnings"]:
                st.warning(w)

    st.divider()

    # ── Section 1: Forecast Explanation ──────────────────────────
    st.subheader("📈 Forecast Explanation")
    st.write(explanation.get("prediction_explanation", "Not generated."))
    st.divider()

    # ── Section 2: SHAP Interpretation ───────────────────────────
    st.subheader("🔍 Why These Predictions? (SHAP Analysis)")
    st.write(explanation.get("shap_interpretation", "Not generated."))
    st.divider()

    # ── Section 3: Counterfactual Analysis ───────────────────────
    st.subheader("🔄 What-If Scenario Analysis")
    st.write(explanation.get("counterfactual_analysis", "Not generated."))
    st.divider()

    # ── Section 4: Health Impact ──────────────────────────────────
    st.subheader("🏥 Health Impact Summary")
    st.write(explanation.get("health_impact_summary", "Not generated."))
    st.divider()

    # ── Section 5: Recommended Intervention ──────────────────────
    st.subheader("✅ Recommended Intervention")
    st.info(explanation.get("recommended_intervention", "Not generated."))

if __name__ == "__main__":
    st.set_page_config(page_title="Delhi AQI - AI Explanation", layout="wide")
    render_explanation_page()
