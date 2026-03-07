# agents/agent_core.py

import google.generativeai as genai
import time
from config import GEMINI_API_KEY, AGENT_MODEL, MAX_RETRIES
from agents.system_prompts import get_system_prompt

genai.configure(api_key=GEMINI_API_KEY)

agent_model = genai.GenerativeModel(
    model_name=AGENT_MODEL,   # "gemini-1.5-flash"
    generation_config=genai.types.GenerationConfig(
        temperature=0.7,      # More conversational than Phase 6 explanation (0.2)
        max_output_tokens=1024,
        top_p=0.9
    )
)


def build_agent_messages(user_message: str, agent_type: str,
                          context: str, history: list) -> list:
    """
    Builds the full message list for Gemini.

    Structure:
      [0] user:  system prompt + full context block
      [1] model: acknowledgement
      [2..N]     conversation history (alternating user/model turns)
      [N+1] user: current message
    """
    system_prompt = get_system_prompt(agent_type)

    setup_turn = (
        f"{system_prompt}\n\n"
        f"=== DATA CONTEXT (use this to answer questions) ===\n"
        f"{context}\n"
        f"=== END OF DATA CONTEXT ===\n\n"
        f"You are now ready to assist. Await the user's question."
    )

    messages = [
        {"role": "user",  "parts": [setup_turn]},
        {"role": "model", "parts": [
            "Understood. I have reviewed today's Delhi AQI data and I am ready to assist."
        ]},
    ]

    # Append conversation history
    for turn in history:
        messages.append({"role": turn["role"], "parts": [turn["content"]]})

    # Append current user message
    messages.append({"role": "user", "parts": [user_message]})

    return messages


def call_agent(user_message: str, agent_type: str,
               context: str, history: list,
               max_retries: int = MAX_RETRIES) -> str:
    """
    Calls Gemini Flash with full conversation history. Returns response text.

    Args:
        user_message : latest message from the user
        agent_type   : "public" or "policy"
        context      : pre-built context string from context_builder.py
        history      : list of {"role": "user"/"model", "content": "..."}
        max_retries  : retry attempts on API failure

    Returns:
        response_text (str)
    """
    messages = build_agent_messages(user_message, agent_type, context, history)

    for attempt in range(max_retries):
        try:
            # Pass all messages except the last as history, last as new message
            chat     = agent_model.start_chat(history=messages[:-1])
            response = chat.send_message(messages[-1]["parts"][0])
            return response.text
        except Exception as e:
            wait = 2 ** attempt
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                return (
                    "I'm having trouble connecting right now. "
                    "Please try again in a moment. 🔄"
                )


def add_to_history(history: list, role: str, content: str) -> list:
    """Appends a turn to conversation history. Returns updated list."""
    history.append({"role": role, "content": content})
    return history


def clear_history() -> list:
    """Returns a fresh empty history list."""
    return []


def trim_history_if_needed(history: list, max_turns: int = 20) -> list:
    """
    Keeps only the last max_turns pairs of (user + model) turns.
    Prevents token limit errors in long conversations.
    Removes oldest pairs first.
    """
    if len(history) > max_turns * 2:
        history = history[-(max_turns * 2):]
    return history
