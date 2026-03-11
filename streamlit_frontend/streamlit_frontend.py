# streamlit_frontend/streamlit_frontend.py

import streamlit as st
import pandas as pd
from config_frontend import PAGE_CONFIG, REGIONS, get_aqi_category
from api_client import get_predictions_summary, get_all_predictions, get_pipeline_status
from components.sidebar import render_sidebar
from components.aqi_card import render_aqi_card
from components.staleness_banner import render_staleness_banner
from components.charts import build_region_comparison_bar, build_3day_trend_line

# ── Page config (must be first Streamlit call) ───────────────
st.set_page_config(**PAGE_CONFIG)

# ── Shared Sidebar ───────────────────────────────────────────
render_sidebar()

# ── Dashboard Content (New Landing Page) ──────────────────────
st.title("🏠 AQI Forecast Dashboard")
st.caption("3-day air quality forecast across all Delhi regions.")

# ── Staleness banner ──────────────────────────────────────────
status = get_pipeline_status()
if status:
    render_staleness_banner(
        status.get("pipeline_ran_at", ""),
        status.get("gemini_model_used", ""),
        status.get("gemini_attempts", 1)
    )

st.divider()

# ── AQI Summary Cards (Day+1 for all regions) ─────────────────
st.subheader("📍 Tomorrow's AQI — All Regions")
summary = get_predictions_summary()
if summary:
    regions_summary = summary.get("regions", [])
    cols = st.columns(len(regions_summary))
    for i, r in enumerate(regions_summary):
        with cols[i]:
            cat = r.get("day_1_category") or get_aqi_category(r["day_1_aqi"])
            render_aqi_card(r["region"], "Day+1", r["day_1_aqi"], cat)

st.divider()

# ── Day Selector + Bar Chart ───────────────────────────────────
all_preds = get_all_predictions()
if all_preds:
    col_ctrl, col_chart = st.columns([1, 3])
    with col_ctrl:
        st.subheader("Compare Day")
        day_choice = st.radio(
            "Select forecast day:",
            ["Day+1", "Day+2", "Day+3"],
            index=0
        )
        day_key = {"Day+1": "day_1", "Day+2": "day_2", "Day+3": "day_3"}[day_choice]

        st.markdown("---")
        st.subheader("Regions to Trend")
        selected_regions = st.multiselect(
            "Select regions for line chart:",
            REGIONS,
            default=["Overall Delhi", "North Delhi", "South Delhi"]
        )

    with col_chart:
        st.plotly_chart(
            build_region_comparison_bar(all_preds, day_key,
                                         title=f"{day_choice} AQI by Region"),
            use_container_width=True
        )

    st.divider()

    # ── 3-Day Trend Line Chart ─────────────────────────────────
    st.subheader("📈 3-Day Trend")
    if selected_regions:
        st.plotly_chart(
            build_3day_trend_line(all_preds, selected_regions),
            use_container_width=True
        )
    else:
        st.info("Select at least one region above to see the trend chart.")

    st.divider()

    # ── Region Detail Table ────────────────────────────────────
    st.subheader("📋 Full 3-Day Forecast Table")
    rows = []
    for region, vals in all_preds.get("regions", {}).items():
        cats = vals.get("category", ["", "", ""])
        rows.append({
            "Region":           region,
            "Day+1 AQI":        vals.get("day_1", "-"),
            "Day+1 Category":   cats[0] if len(cats) > 0 else "-",
            "Day+2 AQI":        vals.get("day_2", "-"),
            "Day+2 Category":   cats[1] if len(cats) > 1 else "-",
            "Day+3 AQI":        vals.get("day_3", "-"),
            "Day+3 Category":   cats[2] if len(cats) > 2 else "-",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
