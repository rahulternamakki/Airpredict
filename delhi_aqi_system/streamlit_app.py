import json
import os
import streamlit as st
from datetime import datetime

# Phase 7 UI imports
from agents.context_builder import build_context_for_agent
from agents.agent_core import call_agent, add_to_history, trim_history_if_needed
from agents.suggested_questions import get_suggested_questions

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
            f"Model: {result.get('gemini_model_used', 'gemini-2.5-flash-lite')} | "
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


# ─────────────────────────────────────────────────────────────────
# PHASE 7: AGENT CHAT UI
# ─────────────────────────────────────────────────────────────────

def init_agent_session_state():
    if "active_agent" not in st.session_state:
        st.session_state.active_agent = "public"          # default on page load

    if "public_history" not in st.session_state:
        st.session_state.public_history = []

    if "policy_history" not in st.session_state:
        st.session_state.policy_history = []

    # Build contexts once per session (not on every message)
    if "public_context" not in st.session_state:
        try:
            st.session_state.public_context = build_context_for_agent("public")
        except Exception as e:
            st.session_state.public_context = f"Error building context: {e}"

    if "policy_context" not in st.session_state:
        try:
            st.session_state.policy_context = build_context_for_agent("policy")
        except Exception as e:
            st.session_state.policy_context = f"Error building context: {e}"


AGENT_CONFIG = {
    "public": {
        "label":       "👤 Public Assistant",
        "name":        "Vayu",
        "subtitle":    "Air quality help for Delhi residents",
        "color":       "#0D7377",
        "bg":          "#F0FAF9",
        "avatar":      "🌿",
        "placeholder": "Ask about air quality, health tips, safe areas...",
        "welcome": (
            "Namaste! 🌿 I'm **Vayu**, your air quality assistant for Delhi.\n\n"
            "I can help you understand today's air quality, health risks, and how "
            "to protect yourself and your family. What would you like to know?"
        ),
    },
    "policy": {
        "label":       "🏛️ Policy Advisor",
        "name":        "DELPHI",
        "subtitle":    "Technical briefing for officials & researchers",
        "color":       "#1A237E",
        "bg":          "#F3F4F9",
        "avatar":      "📊",
        "placeholder": "Ask about interventions, GRAP stages, emission drivers...",
        "welcome": (
            "Good day. I'm **DELPHI** — Delhi Environmental and Pollution Intelligence Assistant.\n\n"
            "I have full access to today's AQI predictions, SHAP feature attributions, "
            "and counterfactual intervention scenarios for all 6 Delhi regions. "
            "How can I assist your analysis?"
        ),
    }
}

def render_agent_page():
    init_agent_session_state()

    active = st.session_state.active_agent
    cfg    = AGENT_CONFIG[active]

    # ── Dynamic colored header ────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            background: {cfg['color']};
            padding: 16px 20px;
            border-radius: 10px;
            margin-bottom: 16px;
        ">
            <h2 style="color: white; margin: 0;">{cfg['avatar']} {cfg['name']}</h2>
            <p style="color: rgba(255,255,255,0.85); margin: 4px 0 0 0; font-size: 0.9rem;">
                {cfg['subtitle']}
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # ── Toggle Switch ─────────────────────────────────────────────
    other_agent  = "policy" if active == "public" else "public"
    other_label  = AGENT_CONFIG[other_agent]["label"]
    toggle_text  = f"⇄ Switch to {other_label}"

    col_left, col_mid, col_right = st.columns([2, 3, 2])
    with col_mid:
        st.markdown(
            f"<p style='text-align:center; color:{cfg['color']}; font-size:0.8rem; margin-bottom:4px;'>"
            f"Active: <strong>{cfg['label']}</strong></p>",
            unsafe_allow_html=True
        )
        if st.button(toggle_text, use_container_width=True):
            st.session_state.active_agent = other_agent
            # Histories are preserved in their own keys — not cleared on switch
            st.rerun()

    st.divider()

    # ── Get active agent's history and context ────────────────────
    if active == "public":
        history = st.session_state.public_history
        context = st.session_state.public_context
    else:
        history = st.session_state.policy_history
        context = st.session_state.policy_context

    # ── Conversation History Display ──────────────────────────────
    with st.container():
        if not history:
            # Show welcome message for first visit
            with st.chat_message("assistant", avatar=cfg["avatar"]):
                st.markdown(cfg["welcome"])
        else:
            for turn in history:
                role   = "user" if turn["role"] == "user" else "assistant"
                avatar = "🧑" if role == "user" else cfg["avatar"]
                with st.chat_message(role, avatar=avatar):
                    st.markdown(turn["content"])

    # ── Suggested Question Chips ──────────────────────────────────
    st.markdown(
        f"<p style='color:{cfg['color']}; font-size:0.8rem; margin: 8px 0 4px 0;'>"
        f"💡 Try asking:</p>",
        unsafe_allow_html=True
    )

    suggested  = get_suggested_questions(active)
    chip_cols  = st.columns(4)
    for i, question in enumerate(suggested[:4]):
        with chip_cols[i]:
            if st.button(
                question,
                key=f"chip_{active}_{i}",
                use_container_width=True,
                help=question
            ):
                st.session_state[f"chip_msg_{active}"] = question
                st.rerun()

    # ── Chat Input ────────────────────────────────────────────────
    user_input = st.chat_input(cfg["placeholder"])

    # Handle chip click (treated identically to typed input)
    chip_key = f"chip_msg_{active}"
    if chip_key in st.session_state and st.session_state[chip_key]:
        user_input = st.session_state.pop(chip_key)

    # ── Process & Respond ─────────────────────────────────────────
    if user_input:
        with st.chat_message("user", avatar="🧑"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar=cfg["avatar"]):
            with st.spinner("Thinking..."):
                history = trim_history_if_needed(history, max_turns=20)
                response = call_agent(
                    user_message = user_input,
                    agent_type   = active,
                    context      = context,
                    history      = history
                )
            st.markdown(response)

        # Update history in session state
        history = add_to_history(history, "user",  user_input)
        history = add_to_history(history, "model", response)

        if active == "public":
            st.session_state.public_history = history
        else:
            st.session_state.policy_history = history

        st.rerun()

    # ── Footer: Data freshness + Clear Chat ───────────────────────
    st.divider()
    footer_l, footer_r = st.columns([3, 1])

    with footer_l:
        try:
            with open(LATEST_RESULT_PATH) as f:
                meta = json.load(f)
            st.caption(
                f"📅 Data: {meta.get('date', 'Unknown Date')} | "
                f"Updated: {meta.get('pipeline_ran_at', 'Unknown Time')[:16]}"
            )
        except Exception:
            st.caption("📅 Data freshness unavailable")

    with footer_r:
        if st.button("🗑 Clear Chat", use_container_width=True):
            if active == "public":
                st.session_state.public_history = []
            else:
                st.session_state.policy_history = []
            st.rerun()

# ─────────────────────────────────────────────────────────────────
# MAIN APP NAVIGATION
# ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    st.set_page_config(page_title="Delhi AQI System", page_icon="🌤️", layout="wide")
    
    st.sidebar.title("Delhi AQI Navigation")
    page = st.sidebar.radio("Go to:", ["AI Explanation Dashboard", "AI Chat Agents"])
    
    st.sidebar.markdown("---")
    st.sidebar.info("Phase 7 Dual-Agent Intelligence Interface with Streamlit.")
    
    if page == "AI Explanation Dashboard":
        render_explanation_page()
    elif page == "AI Chat Agents":
        render_agent_page()
