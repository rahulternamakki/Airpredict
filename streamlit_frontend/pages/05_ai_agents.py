# pages/05_ai_agents.py

import streamlit as st
from api_client import chat_with_agent, get_suggested_questions
from components.chat_ui import render_chat_history, render_question_chips

st.set_page_config(page_title="AI Agents | Delhi AQI",
                   page_icon="🤖", layout="wide")

# ── Session state init (both agents) ─────────────────────────
if "public_history" not in st.session_state:
    st.session_state.public_history = []
if "policy_history" not in st.session_state:
    st.session_state.policy_history = []
if "public_suggestions" not in st.session_state:
    st.session_state.public_suggestions = get_suggested_questions("public")
if "policy_suggestions" not in st.session_state:
    st.session_state.policy_suggestions = get_suggested_questions("policy")

# ── Agent toggle switch ───────────────────────────────────────
st.title("🤖 AI Assistant")
st.caption("Switch between agents at any time — both conversation histories are preserved.")

agent_choice = st.radio(
    "Select Agent:",
    options=["🌿 Vayu — Public Assistant", "🏛️ DELPHI — Policy Advisor"],
    horizontal=True,
    label_visibility="collapsed"
)

is_public = agent_choice.startswith("🌿")
agent_type    = "public"  if is_public else "policy"
agent_name    = "Vayu"    if is_public else "DELPHI"
agent_avatar  = "🌿"      if is_public else "🏛️"
spinner_text  = "Vayu is thinking..." if is_public else "DELPHI is analysing..."
chat_placeholder = (
    "Ask Vayu about Delhi's air quality, health, and safety..."
    if is_public else
    "Query DELPHI about interventions, emission drivers, GRAP status..."
)
theme_bg    = "#E8F5E9" if is_public else "#E3F2FD"
theme_color = "#2E7D32" if is_public else "#1565C0"
chips_label = "💡 Try a suggested question:" if is_public else "📊 Technical query starters:"
history_key      = "public_history"      if is_public else "policy_history"
suggestions_key  = "public_suggestions"  if is_public else "policy_suggestions"

# ── Active agent identity badge ───────────────────────────────
st.markdown(f"""
<div style="
    background:{theme_bg};
    border-left: 5px solid {theme_color};
    border-radius: 8px;
    padding: 10px 16px;
    margin: 8px 0 16px 0;
    display: flex; align-items: center; gap: 12px;
">
    <span style="font-size:1.8rem;">{agent_avatar}</span>
    <div>
        <b style="color:{theme_color}; font-size:1rem;">{agent_name}</b><br>
        <small style="color:#555;">
            {"Citizen-facing · Plain language · Health & safety focus"
              if is_public else
             "Policy-maker · Technical · SHAP & GRAP aware · Data-driven"}
        </small>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Suggested question chips ──────────────────────────────────
st.caption(chips_label)
clicked_q = render_question_chips(
    st.session_state[suggestions_key][:4],
    key_prefix=agent_type
)

# ── Chat history for the active agent ────────────────────────
with st.container():
    render_chat_history(
        st.session_state[history_key],
        agent_name=agent_name,
        agent_avatar=agent_avatar
    )

# ── Chat input ────────────────────────────────────────────────
user_input = st.chat_input(chat_placeholder)

message_to_send = clicked_q or user_input

if message_to_send:
    st.session_state[history_key].append({
        "role": "user", "content": message_to_send
    })

    with st.spinner(spinner_text):
        result = chat_with_agent(
            message    = message_to_send,
            agent_type = agent_type,
            history    = st.session_state[history_key][:-1]
        )

    if result:
        response_text = result.get("response", "Sorry, I could not generate a response.")
        st.session_state[history_key].append({
            "role": "model", "content": response_text
        })
        if result.get("suggested_questions"):
            st.session_state[suggestions_key] = result["suggested_questions"]

    st.rerun()

st.divider()

# ── Bottom action bar ─────────────────────────────────────────
active_history = st.session_state[history_key]

col_export, col_clear, col_spacer = st.columns([1, 1, 2])

with col_export:
    if active_history:
        export_text = "\n\n".join(
            [f"[{t['role'].upper()}] {t['content']}" for t in active_history]
        )
        st.download_button(
            f"📥 Export {agent_name} Chat (.txt)",
            data=export_text,
            file_name=f"{agent_name.lower()}_conversation.txt",
            mime="text/plain"
        )

with col_clear:
    if active_history:
        if st.button(f"🗑️ Clear {agent_name} Chat", key=f"clear_{agent_type}"):
            st.session_state[history_key] = []
            st.rerun()
