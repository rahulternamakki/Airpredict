# agents/agent_core.py

import vertexai
from vertexai.generative_models import GenerativeModel, ChatSession, GenerationConfig
import time
from config import GCP_PROJECT, GCP_LOCATION, AGENT_MODEL, MAX_RETRIES
from agents.system_prompts import get_system_prompt
from vertexai.generative_models import GenerativeModel, Content, Part, GenerationConfig

_model = None

def get_model():
    """Lazy initialization of the Vertex AI model."""
    global _model
    if _model is None:
        print(f"[Agent] Initializing Vertex AI: project={GCP_PROJECT}, location={GCP_LOCATION}")
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        _model = GenerativeModel(
            model_name=AGENT_MODEL,   # e.g. "gemini-2.0-flash-001"
            generation_config=GenerationConfig(
                temperature=0.7,
                max_output_tokens=1024,
                top_p=0.9
            )
        )
    return _model



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
    Calls Vertex Gemini with full conversation history using generate_content.
    Returns response text.
    """
    messages = build_agent_messages(user_message, agent_type, context, history)
    
    # Convert list of dicts to list of Content objects for the SDK
    content_messages = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        content_messages.append(Content(role=role, parts=[Part.from_text(msg["parts"][0])]))

    model = get_model()

    for attempt in range(max_retries):
        try:
            print(f"[Agent] Calling generate_content (attempt {attempt+1})...")
            # Log the number of tokens or message count might be useful
            print(f"[Agent] Message count: {len(content_messages)}")
            
            start_time = time.time()
            response = model.generate_content(content_messages)
            print(f"[Agent] Response received in {time.time() - start_time:.2f}s")
            
            return response.text
        except Exception as e:
            wait = 2 ** attempt
            print(f"[Agent] Attempt {attempt+1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(wait)
            else:
                return (
                    f"I'm having trouble connecting to Vertex AI: {str(e)}. "
                    "Please check your GCP project and credentials. 🔄"
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
