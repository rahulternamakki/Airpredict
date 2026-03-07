# streamlit_frontend/components/aqi_card.py

import streamlit as st
from config_frontend import AQI_COLORS, AQI_TEXT_COLORS

def render_aqi_card(region: str, day_label: str,
                    aqi: int, category: str, trend: str = ""):
    """
    Renders a colored AQI metric card.
    trend: "↑ Worsening" | "↓ Improving" | "→ Stable" or empty string
    """
    bg_color   = AQI_COLORS.get(category, "#888888")
    text_color = AQI_TEXT_COLORS.get(category, "white")
    trend_html = f"<p style='font-size:0.75rem; margin:0;'>{trend}</p>" if trend else ""

    st.markdown(f"""
    <div style="
        background-color: {bg_color};
        color: {text_color};
        padding: 14px 16px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 8px;
    ">
        <p style="font-weight:700; font-size:0.85rem; margin:0 0 4px 0;">{region}</p>
        <p style="font-size:0.7rem; margin:0 0 6px 0; opacity:0.85;">{day_label}</p>
        <p style="font-size:2rem; font-weight:800; margin:0; line-height:1;">{aqi}</p>
        <p style="font-size:0.75rem; margin:4px 0 0 0;">{category}</p>
        {trend_html}
    </div>
    """, unsafe_allow_html=True)
