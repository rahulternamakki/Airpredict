# streamlit_frontend/components/staleness_banner.py

import streamlit as st
from datetime import datetime
from config_frontend import STALENESS_HOURS

def render_staleness_banner(pipeline_ran_at: str,
                              gemini_model: str = "",
                              gemini_attempts: int = 1):
    """
    Shows a colored freshness banner based on pipeline_ran_at timestamp.
    """
    try:
        ran_dt    = datetime.fromisoformat(pipeline_ran_at)
        age_hours = (datetime.now() - ran_dt).total_seconds() / 3600
        age_label = f"{age_hours:.0f}h ago"
        date_str  = ran_dt.strftime("%d %b %Y, %I:%M %p")

        col1, col2 = st.columns([4, 1])
        with col1:
            st.caption(f"📅 Pipeline run: **{date_str}**"
                       + (f"  |  Model: `{gemini_model}`" if gemini_model else "")
                       + f"  |  Gemini attempts: {gemini_attempts}/3")
        with col2:
            if age_hours <= 24:
                st.success(f"✓ Fresh ({age_label})")
            elif age_hours <= STALENESS_HOURS:
                st.warning(f"⚠ {age_label}")
            else:
                st.error(f"⚠ Stale ({age_label})\nRun pipeline!")
    except Exception:
        st.caption("Pipeline run time unknown.")
