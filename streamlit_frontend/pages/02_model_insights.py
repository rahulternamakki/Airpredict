# pages/02_model_insights.py

import streamlit as st
from config_frontend import REGIONS
from api_client import get_all_shap, get_shap_region_day
from components.charts import build_shap_waterfall, build_shap_feature_bar
from components.sidebar import render_sidebar

st.set_page_config(page_title="Model Insights | Delhi AQI", page_icon="📊", layout="wide")
render_sidebar()

st.title("📊 Model Insights — SHAP Analysis")
st.caption("Understand why the model made each prediction using SHAP feature attributions.")

# ── Controls ──────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    selected_region = st.selectbox("Select Region:", REGIONS)
with col2:
    selected_day = st.selectbox("Select Forecast Day:", [1, 2, 3],
                                 format_func=lambda x: f"Day+{x}")

# ── Fetch specific SHAP entry ─────────────────────────────────
shap_entry = get_shap_region_day(selected_region, selected_day)

if shap_entry:
    # ── Key metrics ───────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Base AQI (model average)", f"{shap_entry.get('base_value', 0):.1f}")
    col_b.metric(f"Predicted AQI (Day+{selected_day})", shap_entry.get("predicted_value", "–"))
    delta = shap_entry.get("predicted_value", 0) - shap_entry.get("base_value", 0)
    col_c.metric("SHAP Contribution (total)", f"{delta:+.1f}")

    st.divider()

    # ── Waterfall + Bar side by side ──────────────────────────
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Waterfall Chart")
        st.plotly_chart(build_shap_waterfall(shap_entry), use_container_width=True)
    with col_right:
        st.subheader("Feature Impact (SHAP Values)")
        st.plotly_chart(build_shap_feature_bar(shap_entry), use_container_width=True)

    st.divider()

    # ── Feature details table ─────────────────────────────────
    st.subheader("🔍 Feature Detail Table")
    import pandas as pd
    rows = []
    for f in shap_entry.get("top_features", []):
        direction = "↑ Increases AQI" if f["shap_value"] > 0 else "↓ Reduces AQI"
        rows.append({
            "Feature":         f["feature"],
            "Observed Value":  f["actual_value"],
            "SHAP Value":      f"{f['shap_value']:+.3f}",
            "Direction":       direction,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── All-regions overview (expander) ──────────────────────
    with st.expander("🌐 View SHAP summary for all regions (Day+1)"):
        all_shap = get_all_shap()
        if all_shap:
            day1_entries = [e for e in all_shap if e.get("prediction_day") == 1]
            for entry in day1_entries:
                st.subheader(entry["region"])
                st.plotly_chart(
                    build_shap_feature_bar(entry), 
                    use_container_width=True,
                    key=f"shap_{entry['region']}"
                )
