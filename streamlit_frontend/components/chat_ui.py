# streamlit_frontend/components/chat_ui.py

import streamlit as st

def render_chat_history(history: list, agent_name: str,
                         agent_avatar: str, user_avatar: str = "👤"):
    """
    Renders a full conversation history using st.chat_message.
    history: list of {"role": "user"|"model", "content": "..."}
    """
    for turn in history:
        role = turn["role"]
        if role == "user":
            with st.chat_message("user", avatar=user_avatar):
                st.write(turn["content"])
        else:
            with st.chat_message("assistant", avatar=agent_avatar):
                st.write(turn["content"])


def render_question_chips(questions: list, key_prefix: str):
    """
    Renders clickable question chips. Returns clicked question text or None.
    """
    cols = st.columns(len(questions))
    for i, q in enumerate(questions):
        with cols[i]:
            if st.button(f"💬 {q}", key=f"{key_prefix}_chip_{i}",
                          use_container_width=True):
                return q
    return None
