# pages/03_whatif.py

import streamlit as st
import pandas as pd
from config_frontend import REGIONS, AQI_COLORS
from api_client import get_all_counterfactuals, get_counterfactual_region
from components.charts import build_counterfactual_bar

st.set_page_config(page_title="What-If | Delhi AQI", page_icon="🔄", layout="wide")

st.title("🔄 What-If Scenario Analysis")
st.caption("Counterfactual interventions: how much can AQI be reduced by changing key emission drivers?")

# ── Region selector ───────────────────────────────────────────
selected_region = st.selectbox("Select Region:", REGIONS)

cf_entry = get_counterfactual_region(selected_region)

if cf_entry:
    # ── Summary header ────────────────────────────────────────
    orig_aqi = cf_entry.get("original_day1_aqi", "—")
    orig_cat = cf_entry.get("original_category", "—")

    col1, col2, col3 = st.columns(3)
    col1.metric("Original Day+1 AQI", orig_aqi)
    col2.metric("Category", orig_cat)
    scenarios = cf_entry.get("scenarios", [])
    if scenarios:
        best = min(scenarios, key=lambda s: s.get("new_aqi", 9999))
        col3.metric("Best Achievable AQI", best.get("new_aqi", "—"),
                    delta=f"-{best.get('aqi_reduction', 0)} pts",
                    delta_color="inverse")

    st.divider()

    # ── Horizontal bar chart ──────────────────────────────────
    st.subheader("📉 AQI Reduction by Scenario")
    st.plotly_chart(build_counterfactual_bar(cf_entry), use_container_width=True)

    st.divider()

    # ── Scenario cards ────────────────────────────────────────
    st.subheader("📋 Individual Scenario Details")
    for s in scenarios:
        s_type  = s.get("type", "individual").upper()
        new_aqi = s.get("new_aqi", "—")
        new_cat = s.get("new_category", "—")
        reduct  = s.get("aqi_reduction", 0)
        pct     = s.get("percent_improvement", "—")
        color   = AQI_COLORS.get(new_cat, "#888")

        with st.expander(f"{'🔹' if s_type=='INDIVIDUAL' else '🔶'} {s['name']}  →  {new_aqi} AQI ({new_cat})  |  Reduction: {reduct} pts ({pct})"):
            feat_changes = s.get("feature_changes", {})
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Feature Changes Applied:**")
                for feat, change in feat_changes.items():
                    st.write(f"• {feat}: `{change}%` reduction")
            with col_b:
                st.markdown("**Result:**")
                st.markdown(f"""
                <div style="background:{color}; color:white; padding:10px; border-radius:8px; text-align:center;">
                    <b>{new_aqi}</b><br>{new_cat}
                </div>
                """, unsafe_allow_html=True)
                st.caption(f"AQI reduced by {reduct} pts ({pct})")

    st.divider()

    # ── Cross-region comparison (expander) ───────────────────
    with st.expander("🌐 Compare best scenario across all regions"):
        all_cf = get_all_counterfactuals()
        if all_cf:
            rows = []
            for entry in all_cf:
                scens = entry.get("scenarios", [])
                if scens:
                    best_s = min(scens, key=lambda s: s.get("new_aqi", 9999))
                    rows.append({
                        "Region":           entry["region"],
                        "Original AQI":     entry["original_day1_aqi"],
                        "Best Scenario":    best_s["name"],
                        "New AQI":          best_s["new_aqi"],
                        "Reduction (pts)":  best_s["aqi_reduction"],
                        "Improvement":      best_s["percent_improvement"],
                        "New Category":     best_s["new_category"],
                    })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
