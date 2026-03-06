# PHASE 7 — AI Agents Design
## Complete Plan: Dual-Agent Chat with Switch | Delhi AQI Prediction System

---

## Overview & Key Design Decision: One Page, Two Agents

Both agents live on a **single Streamlit chat page** with a toggle switch at the top.
Switching agents does NOT clear the page — it visually transforms the UI and swaps the
system prompt, while keeping each agent's conversation history separately in session state.

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│                                                             │
│   [ 👤 Public Assistant ]  ←→  [ 🏛️ Policy Advisor ]       │
│              (toggle switch)                                │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Chat history for active agent                        │  │
│  │  (Public and Policy histories stored separately)      │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  [ Type your question...                        ] [Send]    │
│                                                             │
│  Suggested questions (chips — change with agent switch)     │
└─────────────────────────────────────────────────────────────┘
```

---

## Architecture: Full Flow

```
outputs/latest_result.json  (pre-computed by Phase 6 daily pipeline)
        │
        ▼
agents/context_builder.py   → serialize into Public context OR Policy context
        │
        ├──── Public Agent system prompt  (simple, empathetic, citizen-facing)
        └──── Policy Agent system prompt  (technical, quantitative, GRAP-aware)
                │
                ▼
        agents/agent_core.py  → call_agent(message, history, agent_type, context)
                │               uses gemini-1.5-flash (live chat = speed + cost)
                ▼
        Streamlit chat UI (single page, toggle switch, separate histories)
```

**Model choice for agents:** `gemini-1.5-flash`
Phase 6 uses Pro for quality. Agents use Flash — chat is conversational,
latency matters, and cost adds up over many turns. Flash is fast and excellent for dialogue.

---

## File Structure for Phase 7

```
delhi_aqi_system/
├── agents/
│   ├── __init__.py
│   ├── context_builder.py      ← Step 7.2: serialize latest_result.json per agent
│   ├── system_prompts.py       ← Step 7.3: full system prompts for both agents
│   ├── agent_core.py           ← Step 7.4: Gemini call, history, retry
│   └── suggested_questions.py  ← Step 7.5: question chips per agent
└── streamlit_app.py            ← Step 7.6: single-page dual-agent UI with switch
```

---

## Step 7.1 — Shared Agent Foundation

### What Both Agents Share

| Component | Value |
|---|---|
| LLM backbone | `gemini-1.5-flash` |
| Knowledge source | `outputs/latest_result.json` (pre-computed by Phase 6) |
| Context injection | Prepended to every Gemini call as a context block |
| Conversation memory | Per-agent history in `st.session_state`, full history passed each call |
| API key | Same key from `.env` / `config.py` |
| Error handling | Retry with exponential backoff |
| Session scope | In-session only — history clears on browser refresh (research level) |

### What Each Agent Has Separately

| Component | Public Agent | Policy Agent |
|---|---|---|
| System prompt | Citizen-facing, simple, empathetic | Technical, data-driven, GRAP-aware |
| Context slice | Simplified (summary-level, no raw numbers) | Full (all SHAP values, all CF scenarios) |
| Chat history key | `st.session_state.public_history` | `st.session_state.policy_history` |
| Suggested questions | Health/safety questions | Intervention/analysis questions |
| UI color theme | Teal-green (calm, accessible) | Deep navy (professional, official) |
| Agent name | Vayu | DELPHI |
| Response style | Plain language, 2–4 paragraphs | Structured, cites numbers, tables allowed |

---

## Step 7.2 — Context Builder (`agents/context_builder.py`)

Reads `latest_result.json` and produces two different context strings.
**Runs once per session** (cached in `st.session_state`), not on every message.

```python
# agents/context_builder.py

import json
from config import LATEST_RESULT_PATH

def load_result() -> dict:
    with open(LATEST_RESULT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# PUBLIC AGENT CONTEXT
# Simplified — no raw SHAP numbers, no jargon
# ─────────────────────────────────────────────

def build_public_context(result: dict) -> str:
    preds       = result["predictions"]
    explanation = result["explanation"]
    date        = result["date"]

    lines = [
        f"=== TODAY'S AIR QUALITY DATA (Date: {date}) ===",
        "",
        "FORECAST FOR NEXT 3 DAYS:"
    ]

    for region, vals in preds["regions"].items():
        lines.append(
            f"• {region}: "
            f"Tomorrow = {vals['day_1']} AQI ({vals['category'][0]}), "
            f"Day after = {vals['day_2']} AQI ({vals['category'][1]}), "
            f"3 days ahead = {vals['day_3']} AQI ({vals['category'][2]})"
        )

    lines += [
        "",
        "AQI CATEGORIES (for reference):",
        "0–50 = Good | 51–100 = Satisfactory | 101–200 = Moderate",
        "201–300 = Poor | 301–400 = Very Poor | 401–500 = Severe",
        "",
        "WHAT IS CAUSING TODAY'S POLLUTION (plain language):",
        explanation["prediction_explanation"][:600],
        "",
        "HEALTH IMPACT SUMMARY:",
        explanation["health_impact_summary"],
        "",
        "BEST IMPROVEMENT POSSIBLE:",
        explanation["recommended_intervention"][:300],
    ]

    return "\n".join(lines)


# ─────────────────────────────────────────────
# POLICY AGENT CONTEXT
# Full data — SHAP values, all CF scenarios,
# complete scientific explanation
# ─────────────────────────────────────────────

def build_policy_context(result: dict) -> str:
    preds       = result["predictions"]
    shap        = result["shap"]
    cf          = result["counterfactuals"]
    explanation = result["explanation"]
    date        = result["date"]

    lines = [
        f"=== DELHI AQI TECHNICAL BRIEFING (Date: {date}) ===",
        "",
        "── REGION-WISE 3-DAY PREDICTIONS ──"
    ]

    for region, vals in preds["regions"].items():
        d1, d2, d3 = vals['day_1'], vals['day_2'], vals['day_3']
        trend = "↑ WORSENING" if d3 > d1 + 10 else ("↓ IMPROVING" if d3 < d1 - 10 else "→ STABLE")
        lines.append(
            f"• {region}: Day+1={d1} ({vals['category'][0]}), "
            f"Day+2={d2} ({vals['category'][1]}), "
            f"Day+3={d3} ({vals['category'][2]}) | Trend: {trend}"
        )

    lines += ["", "── SHAP FEATURE DRIVERS (Day+1, per region) ──"]
    for entry in shap:
        lines.append(
            f"\n{entry['region']} | "
            f"Base={entry['base_value']:.1f} → Predicted={entry['predicted_value']}"
        )
        for feat in entry["top_features"]:
            direction = "↑ increases AQI" if feat["shap_value"] > 0 else "↓ decreases AQI"
            lines.append(
                f"  {feat['feature']}: value={feat['actual_value']}, "
                f"SHAP={feat['shap_value']:+.2f} ({direction})"
            )

    lines += ["", "── COUNTERFACTUAL INTERVENTION SCENARIOS ──"]
    for entry in cf:
        lines.append(
            f"\n{entry['region']} | "
            f"Original AQI: {entry['original_day1_aqi']} ({entry['original_category']})"
        )
        for s in entry["scenarios"]:
            lines.append(
                f"  [{s['type'].upper()}] {s['name']}: "
                f"Vary {s['features_varied']} → "
                f"New AQI={s['new_aqi']} ({s['new_category']}) | "
                f"Reduction={s['aqi_reduction']} pts ({s['percent_improvement']})"
            )

    lines += [
        "",
        "── SCIENTIFIC ANALYSIS (Pre-generated by Phase 6) ──",
        "",
        "FORECAST EXPLANATION:",
        explanation["prediction_explanation"],
        "",
        "SHAP INTERPRETATION:",
        explanation["shap_interpretation"],
        "",
        "COUNTERFACTUAL ANALYSIS:",
        explanation["counterfactual_analysis"],
        "",
        "HEALTH IMPACT:",
        explanation["health_impact_summary"],
        "",
        "RECOMMENDED INTERVENTION:",
        explanation["recommended_intervention"],
    ]

    return "\n".join(lines)


def build_context_for_agent(agent_type: str) -> str:
    """
    Main entry point. Returns context string for the given agent type.
    agent_type: "public" or "policy"
    """
    result = load_result()
    if agent_type == "public":
        return build_public_context(result)
    elif agent_type == "policy":
        return build_policy_context(result)
    else:
        raise ValueError(f"Unknown agent_type: {agent_type}")
```

---

## Step 7.3 — System Prompts (`agents/system_prompts.py`)

```python
# agents/system_prompts.py

# ─────────────────────────────────────────────
# PUBLIC AGENT — "Vayu"
# ─────────────────────────────────────────────

PUBLIC_AGENT_SYSTEM_PROMPT = """
You are Vayu — a friendly, caring AI air quality assistant for Delhi residents.
Your name means "air" in Hindi. You help everyday citizens understand Delhi's
air quality and protect themselves and their families.

YOUR PERSONALITY:
- Warm, empathetic, and patient — like a knowledgeable friend
- You speak in simple, everyday English (you may use familiar Hindi words naturally,
  e.g., "dilli", "bacche", "aaj")
- You never use scientific jargon without immediately explaining it simply
- You are reassuring when AQI is moderate, and clearly alarming (but not panicky) when severe

YOUR KNOWLEDGE SCOPE:
- AQI forecasts for the next 3 days across all Delhi regions
- What each AQI category means in practice (can I go outside? should I wear a mask?)
- Health advice for different people: children, elderly, pregnant women, asthma patients
- Simple protective actions: N95 masks, air purifiers, windows closed, indoor plants
- Why some areas are more polluted than others (in plain language, not technical terms)
- What time of day is typically cleaner (early morning vs peak traffic hours)
- Seasonal patterns (winters are worse due to crop burning, summers have dust storms)

YOUR STRICT RULES:
1. NEVER cite raw SHAP values or say "SHAP contribution of +28.4"
2. NEVER mention GRAP stages, regulatory thresholds, or policy mechanisms by name
3. NEVER say "the XGBoost model predicts" — just say "our forecast shows"
4. Keep responses to 2–4 short paragraphs maximum
5. Always end with a clear, actionable recommendation for the user
6. If asked about policy details, say:
   "That's a question for policy experts — I'm here to help you stay safe personally!"
7. If AQI is above 300 (Very Poor or Severe), ALWAYS add a health warning prominently

OFF-TOPIC HANDLING RULES:
8. If the user asks something completely unrelated to air quality, weather, health,
   or Delhi environment (e.g., cricket scores, recipes, coding help, general knowledge),
   respond ONLY with:
   "I'm Vayu, your Delhi air quality assistant 🌿 I can only help with questions about
   air quality, pollution levels, health advice, and safe activities in Delhi.
   Is there something about today's air quality I can help you with?"
   Do NOT attempt to answer the off-topic question even partially.

9. If the question is PARTIALLY related (e.g., "how does traffic affect health?" or
   "is humidity related to pollution?"), answer it — but always tie the answer back
   to today's Delhi AQI data.

10. If the user asks about AQI in OTHER cities (Mumbai, Bengaluru, etc.),
    respond: "I only have data for Delhi right now. For other cities, you can check
    the CPCB website (cpcb.nic.in) or AQI India app. Want me to tell you about
    Delhi's air quality instead?"

RESPONSE FORMAT:
- Conversational paragraphs, no bullet points (except when listing protective actions)
- Start with a direct answer
- Use relatable comparisons (e.g., "breathing today's air is like smoking X cigarettes")

REGION MAPPING (citizens use neighborhood names, not region names):
- North Delhi: Rohini, Pitampura, Model Town, Shalimar Bagh, Burari
- South Delhi: Lajpat Nagar, Saket, Hauz Khas, Greater Kailash, Chhatarpur
- East Delhi: Preet Vihar, Mayur Vihar, Shahdara, Patparganj, Vivek Vihar
- West Delhi: Dwarka, Janakpuri, Uttam Nagar, Rajouri Garden, Tilak Nagar
- Central Delhi: Connaught Place, Karol Bagh, Paharganj, Daryaganj, Chandni Chowk
"""


# ─────────────────────────────────────────────
# POLICY AGENT — "DELPHI"
# ─────────────────────────────────────────────

POLICY_AGENT_SYSTEM_PROMPT = """
You are DELPHI — Delhi Environmental and Pollution Intelligence Assistant.
You serve government officials, environmental regulators, urban planners, and
researchers who need precise, data-driven analysis for pollution policy decisions.

YOUR IDENTITY:
- Precise, authoritative, and quantitative
- You speak the language of policy: intervention effectiveness, GRAP stages,
  regulatory thresholds, emission source attribution, cost-benefit framing
- You cite specific numbers from the data in every substantive response
- You structure answers clearly — numbered points or tables for comparisons

YOUR DEEP KNOWLEDGE:
- GRAP Stage triggers: Stage I (AQI 201–300), Stage II (301–400),
  Stage III (401–450), Stage IV (>450)
- GRAP Stage I: ban brick kilns, stone crushers; strict PUC enforcement
- GRAP Stage II: ban diesel generators (except essential); heightened dust control
- GRAP Stage III: ban non-essential construction; 50% government vehicle cap
- GRAP Stage IV: school closures, truck entry ban, consider odd-even scheme
- Delhi emission source breakdown (approximate, season-dependent):
  Transport ~28%, Dust (road+construction) ~28%, Industry ~18%,
  Biomass burning ~17%, Other ~9%
- Stubble burning peaks Oct 15–Nov 15, can contribute 30–40% of PM2.5 on severe days
- CPCB AQI: sub-indices for PM2.5, PM10, NO2, SO2, CO, O3, NH3, Pb — max = AQI
- Health economic burden: estimated ₹70,000+ crore annual cost to Delhi

YOUR CAPABILITIES WITH THE PROVIDED DATA:
- Cross-region comparison using 3-day prediction + SHAP data
- Intervention impact quantification using counterfactual scenario results
- GRAP stage determination and recommended actions based on predicted AQI
- Identifying which emission source (via SHAP top feature) to target first
- Ranking interventions by AQI reduction per unit of regulatory effort
- Time-criticality: Day+1 vs Day+3 trend direction per region

YOUR STRICT RULES:
1. Always cite the specific AQI number, SHAP value, or CF delta you reference
2. When recommending an intervention, always state:
   (a) expected AQI reduction in points and %,
   (b) which region benefits most,
   (c) which GRAP stage it helps avoid or exit
3. If a question involves a policy not in the counterfactual data, say so explicitly
   and give a qualitative assessment with stated uncertainty
4. Do not oversell model precision — acknowledge this is a research-level PoC
5. For comparisons, use a markdown table or numbered ranking
6. Maximum length: 200–400 words per response — comprehensive but not verbose

OFF-TOPIC HANDLING RULES:
7. If the user asks something completely unrelated to air quality, pollution, environment,
   public health, or Delhi policy (e.g., financial markets, sports, general coding,
   unrelated government topics), respond ONLY with:
   "I'm DELPHI, a specialized assistant for Delhi air quality policy analysis.
   I can only assist with questions about AQI predictions, emission drivers, intervention
   effectiveness, and GRAP-related decisions. How can I help with today's pollution data?"
   Do NOT attempt to answer the off-topic question even partially.

8. If the question is about environmental policy in OTHER cities or countries, respond:
   "My analysis is scoped to Delhi's AQI data and GRAP framework. I don't have
   comparable data for other regions, so any answer would be speculative.
   Shall I focus on Delhi's current situation instead?"

9. If the question is PARTIALLY related (e.g., "how does monsoon affect policy timelines?"
   or "what is PM2.5 scientifically?"), answer it fully — it is within scope.

RESPONSE FORMAT:
- Lead with a direct answer (1–2 sentences)
- Support with specific data (numbers, SHAP values, CF deltas)
- For comparisons: table or numbered ranking
- Close with a policy recommendation or next-step framing
"""


def get_system_prompt(agent_type: str) -> str:
    if agent_type == "public":
        return PUBLIC_AGENT_SYSTEM_PROMPT
    elif agent_type == "policy":
        return POLICY_AGENT_SYSTEM_PROMPT
    else:
        raise ValueError(f"Unknown agent_type: {agent_type}")
```

---

## Step 7.4 — Agent Core (`agents/agent_core.py`)

```python
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
```

---

## Step 7.5 — Suggested Questions (`agents/suggested_questions.py`)

```python
# agents/suggested_questions.py

PUBLIC_QUESTIONS = [
    "Is it safe to go outside tomorrow in South Delhi?",
    "Which area has the best air quality right now?",
    "What does AQI 250 mean for my child?",
    "Will the air get better in the next 3 days?",
    "Should I wear an N95 mask today?",
    "What time of day is safest to go for a walk?",
    "Why is North Delhi more polluted than South Delhi?",
    "What can I do at home to reduce my exposure?",
]

POLICY_QUESTIONS = [
    "Which region needs emergency intervention in the next 3 days?",
    "What is the most impactful single intervention right now?",
    "What GRAP stage is Delhi in based on today's forecast?",
    "Compare AQI reduction across all counterfactual scenarios.",
    "What are the top 3 emission drivers in East Delhi today?",
    "How much would odd-even vehicle restrictions improve AQI?",
    "Which region shows the worst 3-day deterioration trend?",
    "Quantify the benefit of reducing industrial emissions by 30%.",
]

def get_suggested_questions(agent_type: str) -> list:
    if agent_type == "public":
        return PUBLIC_QUESTIONS
    return POLICY_QUESTIONS
```

---

## Step 7.6 — Streamlit UI: Single Page, Two Agents with Toggle

```python
# streamlit_app.py — render_agent_page() function

import streamlit as st
import json
from agents.context_builder     import build_context_for_agent
from agents.agent_core          import call_agent, add_to_history, trim_history_if_needed
from agents.suggested_questions import get_suggested_questions
from config                     import LATEST_RESULT_PATH


# ─────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZATION — call once at app startup
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
        st.session_state.public_context = build_context_for_agent("public")

    if "policy_context" not in st.session_state:
        st.session_state.policy_context = build_context_for_agent("policy")


# ─────────────────────────────────────────────────────────────────
# AGENT CONFIGURATION
# ─────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────
# MAIN PAGE RENDERER
# ─────────────────────────────────────────────────────────────────

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
                f"📅 Data: {meta['date']} | "
                f"Updated: {meta['pipeline_ran_at'][:16]}"
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
```

---

## Step 7.7 — config.py Additions for Phase 7

Add to existing `config.py`:

```python
# Phase 7 additions
AGENT_MODEL       = "gemini-1.5-flash"   # Flash for live chat (fast + cost-efficient)
AGENT_TEMPERATURE = 0.7                  # More conversational than Phase 6 (0.2)
AGENT_MAX_TOKENS  = 1024
HISTORY_MAX_TURNS = 20                   # Max turns before trimming oldest
```

---

## Step 7.8 — Session State Reference

| Key | Type | Set by | Used by | Notes |
|---|---|---|---|---|
| `active_agent` | `str` | Toggle button | Page renderer | `"public"` or `"policy"` |
| `public_history` | `list[dict]` | `add_to_history()` | `call_agent()` | Preserved when switching to Policy |
| `policy_history` | `list[dict]` | `add_to_history()` | `call_agent()` | Preserved when switching to Public |
| `public_context` | `str` | `build_context_for_agent()` | `call_agent()` | Built ONCE per session |
| `policy_context` | `str` | `build_context_for_agent()` | `call_agent()` | Built ONCE per session |
| `chip_msg_public` | `str` | Chip button | Chat handler | Cleared after use with `.pop()` |
| `chip_msg_policy` | `str` | Chip button | Chat handler | Cleared after use with `.pop()` |

---

## Step 7.9 — Conversation Flow Diagram

```
User opens Chat page
        │
        ▼
init_agent_session_state()
  ├── active_agent     = "public"
  ├── public_history   = []
  ├── policy_history   = []
  ├── public_context   ← reads latest_result.json ONCE → simplified context
  └── policy_context   ← reads latest_result.json ONCE → full context
        │
        ▼
Render page (active = "public")
  └── Show Vayu welcome message (no history yet)
        │
        ├─── User types / clicks chip ──────────────────────────────────────┐
        │                                                                    │
        │         call_agent(msg, "public", public_context, public_history)  │
        │                   │                                                │
        │         build_agent_messages()                                     │
        │         [system+context | ack | ...history | new_msg]              │
        │                   │                                                │
        │         Gemini Flash API call                                      │
        │                   │                                                │
        │         Display response → append to public_history → rerun ───────┘
        │
        ├─── User clicks toggle switch
        │         active_agent = "policy"
        │         rerun() → page re-renders with DELPHI theme + navy color
        │         public_history is UNTOUCHED (preserved for when user switches back)
        │                   │
        │         User chats with DELPHI → policy_history grows independently
        │
        └─── User clicks "Clear Chat"
                  current agent's history = []
                  rerun()
```

---

## Step 7.10 — Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| **One page, toggle switch** | Cleaner UX — users don't navigate; easy to compare both agents on the same question |
| **Separate session histories per agent** | Switching agents never loses conversation; user can freely switch back and forth |
| **Context built ONCE per session** | `build_context_for_agent()` reads `latest_result.json` only on session start — no re-reads per message |
| **Different context slices** | Public gets trimmed, jargon-free summary; Policy gets full SHAP + CF data. Injecting raw numbers into Public wastes tokens and risks Vayu citing SHAP values to citizens |
| **History trimming at 20 turns** | Prevents token limit errors in long conversations; 20 turns = ~40 messages = sufficient context |
| **`gemini-1.5-flash` for agents** | Chat must feel instant; Flash is ~3–5x faster than Pro and perfectly suited for dialogue |
| **`temperature=0.7` for agents** | Higher than Phase 6 (0.2) — agents need to feel natural and conversational, not robotic |
| **Region mapping in Public prompt** | Citizens say "Dwarka" not "West Delhi" — mapping handles this without NLP |
| **Named agents (Vayu / DELPHI)** | Names create distinct identities — users engage differently with a named assistant |
| **Welcome message instead of empty chat** | First-time users need orientation — explains what the agent can do |
| **Chip questions change on switch** | Health/safety chips for Public; technical/intervention chips for Policy |
| **"Clear Chat" per agent** | Clears only the active agent's history — the other agent's conversation is preserved |
| **Dynamic colored header** | Visual reinforcement of which agent is active — teal = Public (calm), navy = Policy (official) |
| **Off-topic handling in system prompt** | Agents politely redirect without answering unrelated questions — keeps focus and prevents misuse |

---

## Step 7.11 — Off-Topic Handling (Complete Reference)

This is enforced entirely through the system prompts (Steps 7.3). No extra code needed.
The three cases and how each agent handles them:

### Case 1: Completely Unrelated Question
Examples: "Who won IPL 2024?", "Write me a Python function", "What's a good recipe for dal?"

| Agent | Response behaviour |
|---|---|
| **Vayu (Public)** | "I'm Vayu, your Delhi air quality assistant 🌿 I can only help with questions about air quality, pollution levels, health advice, and safe activities in Delhi. Is there something about today's air quality I can help you with?" |
| **DELPHI (Policy)** | "I'm DELPHI, a specialized assistant for Delhi air quality policy analysis. I can only assist with questions about AQI predictions, emission drivers, intervention effectiveness, and GRAP-related decisions. How can I help with today's pollution data?" |

Both agents: **do not attempt a partial answer**, do not apologize excessively, and immediately invite the user back to their scope.

### Case 2: Partially Related Question
Examples: "How does traffic affect health?", "Is humidity related to pollution?",
"What does PM2.5 mean scientifically?", "How does monsoon affect policy timelines?"

Both agents: **answer fully** — these are within scope. Vayu answers in plain language,
DELPHI answers with technical depth. Both tie the answer back to today's Delhi data
where possible.

### Case 3: AQI Question But Wrong City / Region
Examples: "What's the AQI in Mumbai?", "How is Bengaluru's air quality?"

| Agent | Response behaviour |
|---|---|
| **Vayu (Public)** | "I only have data for Delhi right now. For other cities, you can check the CPCB website (cpcb.nic.in) or the AQI India app. Want me to tell you about Delhi's air quality instead?" |
| **DELPHI (Policy)** | "My analysis is scoped to Delhi's AQI data and GRAP framework. I don't have comparable data for other regions. Shall I focus on Delhi's current situation instead?" |

### Why This Is Handled in the System Prompt (Not in Code)

Doing off-topic detection in Python code (e.g., keyword matching or a separate
classifier call) would add latency and complexity for minimal gain. Gemini is fully
capable of following these rules when they are written clearly in the system prompt.
The system prompt approach means:
- Zero extra latency (no pre-classification step)
- No extra API calls
- Handles nuanced edge cases (partially related questions) that keyword matching would miss
- Easy to adjust — just edit the system prompt text
