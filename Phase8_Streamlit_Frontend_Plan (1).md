# PHASE 8 — Streamlit Frontend (API-Connected)
## Complete Implementation Plan: 5-Page App via FastAPI
### Delhi AQI Prediction System

---

## Overview & Core Design Decision

The Streamlit frontend **never imports or calls any backend Python module directly**.
Every data fetch goes through the FastAPI layer (`http://localhost:8000/api/v1/...`).

This is a clean separation of concerns:

| Concern | Who handles it |
|---|---|
| All ML, SHAP, counterfactual, Gemini logic | FastAPI backend (already built) |
| Data fetching | `requests` calls to FastAPI endpoints |
| UI rendering, session state, chat | Streamlit frontend only |
| Authentication | None (research POC) |

---

## Architecture Diagram

```
USER BROWSER
    │
    ▼
STREAMLIT APP (streamlit_frontend.py)
    │
    │  HTTP requests via `requests` library
    ▼
FASTAPI BACKEND (uvicorn delhi_aqi_system.api.main:app --port 8000)
    │
    ├── GET  /api/v1/predictions          → Dashboard page
    ├── GET  /api/v1/predictions/summary  → Dashboard summary cards
    ├── GET  /api/v1/predictions/{region} → Region-level detail
    ├── GET  /api/v1/shap                 → Model Insights page
    ├── GET  /api/v1/shap/{region}/day/{day} → Waterfall plot data
    ├── GET  /api/v1/counterfactual       → What-If page
    ├── GET  /api/v1/explanation          → AI Explanation page
    ├── POST /api/v1/agent/chat           → AI Agents page (both agents)
    ├── GET  /api/v1/agent/questions/{type} → Suggested questions (both agents)
    └── POST /api/v1/pipeline/run         → Pipeline trigger (admin)
         │
         ▼
    outputs/latest_result.json  (single source of truth)
```

---

## File Structure to Create

```
streamlit_frontend/              ← NEW top-level folder (sibling to delhi_aqi_system/)
├── streamlit_frontend.py        ← Main entry point (multipage router)
├── api_client.py                ← All HTTP calls to FastAPI (one place, never scattered)
├── config_frontend.py           ← API base URL, timeout, page config constants
├── pages/
│   ├── 01_dashboard.py          ← AQI Forecast Overview
│   ├── 02_model_insights.py     ← SHAP Analysis
│   ├── 03_whatif.py             ← Counterfactual Scenarios
│   ├── 04_ai_explanation.py     ← Gemini Scientific Summary
│   └── 05_ai_agents.py          ← Vayu + DELPHI on one page with toggle switch
├── components/
│   ├── aqi_card.py              ← Reusable AQI value card with color coding
│   ├── charts.py                ← All Plotly chart builders
│   ├── chat_ui.py               ← Chat bubble renderer (shared by both agents)
│   └── staleness_banner.py      ← Data freshness warning component
└── requirements_frontend.txt    ← Streamlit + requests + plotly only
```

> **Rule:** `pages/` files only call functions from `api_client.py` and `components/`.
> They never call `requests` directly. All HTTP logic lives in `api_client.py`.

---

## Implementation Order

| Phase | What you build | Files created |
|---|---|---|
| **Phase 8.1 — Foundation** | Config + API client + all reusable components + main entry point | `config_frontend.py`, `api_client.py`, `components/`, `streamlit_frontend.py` |
| **Phase 8.2 — Dashboard** | Page 1: AQI forecast cards + charts + table | `pages/01_dashboard.py` |
| **Phase 8.3 — Model Insights** | Page 2: SHAP waterfall + feature bar + detail table | `pages/02_model_insights.py` |
| **Phase 8.4 — What-If Scenarios** | Page 3: Counterfactual bar chart + scenario cards | `pages/03_whatif.py` |
| **Phase 8.5 — AI Explanation** | Page 4: Gemini 5-section text display | `pages/04_ai_explanation.py` |
| **Phase 8.6 — AI Agents** | Page 5: Vayu + DELPHI on one page with toggle | `pages/05_ai_agents.py` |
| **Phase 8.7 — Final Setup** | Install deps, run checklist, verify full stack | `requirements_frontend.txt` |

Build in this order. Each phase is independently testable before moving to the next.

---

---

# PHASE 8.1 — Foundation Setup

**What you build:** Everything that all pages depend on — config, API client, shared components, and the main entry point. No page code yet. After this phase, running the app should show a working landing page with a live API health indicator in the sidebar.

**Files to create in this phase:**
```
streamlit_frontend/
├── config_frontend.py
├── api_client.py
├── streamlit_frontend.py
└── components/
    ├── aqi_card.py
    ├── staleness_banner.py
    ├── charts.py
    └── chat_ui.py
```

---

## Step 8.1.1 — Configuration (`config_frontend.py`)

```python
# streamlit_frontend/config_frontend.py

import os

# ── API Connection ──────────────────────────────────────────
API_BASE_URL   = os.getenv("DELHI_AQI_API_URL", "http://localhost:8000")
API_V1         = f"{API_BASE_URL}/api/v1"
REQUEST_TIMEOUT = 15   # seconds — fail fast if API is down

# ── AQI Color Palette (CPCB Standard) ──────────────────────
AQI_COLORS = {
    "Good":                        "#00B050",  # Green
    "Satisfactory":                "#92D050",  # Light Green
    "Moderate":                    "#FFFF00",  # Yellow
    "Poor":                        "#FF7C00",  # Orange
    "Very Poor":                   "#FF0000",  # Red
    "Severe":                      "#7030A0",  # Purple
}

AQI_TEXT_COLORS = {
    # Text color on the colored background (for readability)
    "Good":          "white",
    "Satisfactory":  "black",
    "Moderate":      "black",
    "Poor":          "white",
    "Very Poor":     "white",
    "Severe":        "white",
}

# ── AQI Thresholds (CPCB) ──────────────────────────────────
def get_aqi_category(aqi: int) -> str:
    if aqi <= 50:   return "Good"
    if aqi <= 100:  return "Satisfactory"
    if aqi <= 200:  return "Moderate"
    if aqi <= 300:  return "Poor"
    if aqi <= 400:  return "Very Poor"
    return "Severe"

# ── App Pages Config ────────────────────────────────────────
PAGE_CONFIG = {
    "page_title": "Delhi AQI Intelligence System",
    "page_icon":  "🌫️",
    "layout":     "wide",
    "initial_sidebar_state": "expanded",
}

# ── Regions ─────────────────────────────────────────────────
REGIONS = [
    "Central Delhi", "West Delhi", "East Delhi",
    "North Delhi", "South Delhi", "Overall Delhi"
]

# ── Staleness ───────────────────────────────────────────────
STALENESS_HOURS = 30
```

---

## Step 8.1.2 — API Client (`api_client.py`)

All HTTP calls to FastAPI live here. Pages never call `requests` directly.

```python
# streamlit_frontend/api_client.py

import requests
import streamlit as st
from config_frontend import API_V1, REQUEST_TIMEOUT

# ── Generic fetch with error surfacing ──────────────────────

def _get(endpoint: str) -> dict | list | None:
    """
    GET request to the FastAPI backend.
    Returns parsed JSON on success.
    Shows st.error and returns None on failure.
    """
    url = f"{API_V1}{endpoint}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to API at {url}. Is the FastAPI server running?")
        st.code("uvicorn delhi_aqi_system.api.main:app --reload --port 8000")
        return None
    except requests.exceptions.Timeout:
        st.error(f"⏱ Request timed out ({REQUEST_TIMEOUT}s) at {url}.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error {resp.status_code}: {resp.json().get('detail', str(e))}")
        return None

def _post(endpoint: str, payload: dict) -> dict | None:
    """POST request to the FastAPI backend."""
    url = f"{API_V1}{endpoint}"
    try:
        resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Cannot connect to API at {url}.")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"API error {resp.status_code}: {resp.json().get('detail', str(e))}")
        return None

# ── Endpoint-specific helpers ────────────────────────────────

def get_predictions_summary()  -> dict | None:
    return _get("/predictions/summary")

def get_all_predictions()      -> dict | None:
    return _get("/predictions")

def get_region_prediction(region: str) -> dict | None:
    from urllib.parse import quote
    return _get(f"/predictions/{quote(region)}")

def get_all_shap()             -> list | None:
    return _get("/shap")

def get_shap_for_region(region: str) -> list | None:
    from urllib.parse import quote
    return _get(f"/shap/{quote(region)}")

def get_shap_region_day(region: str, day: int) -> dict | None:
    from urllib.parse import quote
    return _get(f"/shap/{quote(region)}/day/{day}")

def get_all_counterfactuals()  -> list | None:
    return _get("/counterfactual")

def get_counterfactual_region(region: str) -> dict | None:
    from urllib.parse import quote
    return _get(f"/counterfactual/{quote(region)}")

def get_full_explanation()     -> dict | None:
    return _get("/explanation")

def get_explanation_section(section: str) -> dict | None:
    # section: "prediction" | "shap" | "counterfactual" | "health" | "intervention"
    return _get(f"/explanation/{section}")

def get_pipeline_status()      -> dict | None:
    return _get("/pipeline/status")

def trigger_pipeline(csv_path: str) -> dict | None:
    return _post("/pipeline/run", {"csv_path": csv_path})

def chat_with_agent(message: str, agent_type: str, history: list) -> dict | None:
    payload = {
        "message":    message,
        "agent_type": agent_type,
        "history":    history   # [{"role": "user"/"model", "content": "..."}]
    }
    return _post("/agent/chat", payload)

def get_suggested_questions(agent_type: str) -> list:
    result = _get(f"/agent/questions/{agent_type}")
    return result if isinstance(result, list) else []

def check_api_health() -> bool:
    """Returns True if API is reachable."""
    try:
        resp = requests.get(f"{API_V1.replace('/api/v1', '')}/health",
                            timeout=5)
        return resp.status_code == 200
    except Exception:
        return False
```

---

## Step 8.1.3 — Reusable Components (`components/`)

### `components/aqi_card.py`

```python
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
```

### `components/staleness_banner.py`

```python
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
```

### `components/charts.py`

```python
# streamlit_frontend/components/charts.py

import plotly.graph_objects as go
import plotly.express as px
from config_frontend import AQI_COLORS, REGIONS

def build_region_comparison_bar(predictions_data: dict,
                                  day_key: str = "day_1",
                                  title: str = "Day+1 AQI by Region") -> go.Figure:
    """
    Grouped bar chart comparing AQI values across all regions for a given day.
    """
    regions, aqi_vals, colors, categories = [], [], [], []
    for region, vals in predictions_data.get("regions", {}).items():
        cat = vals.get("category", ["Unknown"])[int(day_key[-1]) - 1]
        regions.append(region)
        aqi_vals.append(vals.get(day_key, 0))
        colors.append(AQI_COLORS.get(cat, "#888"))
        categories.append(cat)

    fig = go.Figure(go.Bar(
        x=regions, y=aqi_vals,
        marker_color=colors,
        text=[f"{v}<br>{c}" for v, c in zip(aqi_vals, categories)],
        textposition="outside",
    ))
    fig.update_layout(
        title=title,
        xaxis_title="Region", yaxis_title="AQI",
        yaxis=dict(range=[0, max(aqi_vals + [500]) * 1.15]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#333"),
        margin=dict(t=50, b=40),
        showlegend=False
    )
    return fig


def build_3day_trend_line(predictions_data: dict,
                           selected_regions: list = None) -> go.Figure:
    """
    Multi-line chart showing AQI trend across Day+1/2/3 for selected regions.
    """
    fig = go.Figure()
    days = ["Day+1", "Day+2", "Day+3"]
    for region, vals in predictions_data.get("regions", {}).items():
        if selected_regions and region not in selected_regions:
            continue
        aqi_series = [vals.get("day_1", 0), vals.get("day_2", 0), vals.get("day_3", 0)]
        fig.add_trace(go.Scatter(
            x=days, y=aqi_series,
            name=region, mode="lines+markers+text",
            text=aqi_series, textposition="top center"
        ))
    fig.update_layout(
        title="3-Day AQI Trend by Region",
        xaxis_title="Forecast Day", yaxis_title="AQI",
        yaxis=dict(range=[0, 520]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    return fig


def build_shap_waterfall(shap_entry: dict) -> go.Figure:
    """
    Builds a SHAP waterfall chart from a single shap_entry dict.
    shap_entry: {region, prediction_day, base_value, predicted_value, top_features:[...]}
    """
    base   = shap_entry.get("base_value", 0)
    feats  = shap_entry.get("top_features", [])
    labels = ["Base AQI"] + [f["feature"] for f in feats] + ["Predicted AQI"]
    values = [base] + [f["shap_value"] for f in feats] + [shap_entry.get("predicted_value", 0)]
    measure = ["absolute"] + ["relative"] * len(feats) + ["total"]

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=measure,
        x=labels, y=values,
        connector={"line": {"color": "rgb(63,63,63)"}},
        increasing={"marker": {"color": "#EF553B"}},
        decreasing={"marker": {"color": "#00CC96"}},
        totals={"marker":    {"color": "#AB63FA"}},
        text=[f"{v:+.1f}" if i not in (0, len(values)-1) else f"{v:.0f}"
              for i, v in enumerate(values)],
        textposition="outside"
    ))
    region = shap_entry.get("region", "")
    day    = shap_entry.get("prediction_day", "")
    fig.update_layout(
        title=f"SHAP Feature Impact — {region} Day+{day}",
        yaxis_title="AQI",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=60, b=60)
    )
    return fig


def build_counterfactual_bar(cf_entry: dict) -> go.Figure:
    """
    Horizontal bar chart showing original AQI vs each counterfactual scenario.
    """
    scenarios = cf_entry.get("scenarios", [])
    original  = cf_entry.get("original_day1_aqi", 0)
    orig_cat  = cf_entry.get("original_category", "")

    names  = ["Original"] + [s["name"] for s in scenarios]
    values = [original]   + [s["new_aqi"] for s in scenarios]
    cats   = [orig_cat]   + [s["new_category"] for s in scenarios]
    colors = [AQI_COLORS.get(c, "#888") for c in cats]

    fig = go.Figure(go.Bar(
        x=values, y=names,
        orientation="h",
        marker_color=colors,
        text=[f"{v} — {c}" for v, c in zip(values, cats)],
        textposition="inside",
    ))
    fig.update_layout(
        title=f"What-If Scenarios — {cf_entry.get('region', '')}",
        xaxis_title="AQI", xaxis=dict(range=[0, max(values) * 1.1]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=220, t=50)
    )
    return fig


def build_shap_feature_bar(shap_entry: dict) -> go.Figure:
    """
    Horizontal bar chart showing SHAP feature values (positive = red, negative = green).
    """
    feats   = shap_entry.get("top_features", [])
    feature_names = [f["feature"] for f in feats]
    shap_vals     = [f["shap_value"] for f in feats]
    bar_colors    = ["#EF553B" if v > 0 else "#00CC96" for v in shap_vals]

    fig = go.Figure(go.Bar(
        x=shap_vals, y=feature_names,
        orientation="h",
        marker_color=bar_colors,
        text=[f"{v:+.2f}" for v in shap_vals],
        textposition="outside"
    ))
    fig.update_layout(
        title=f"SHAP Values — {shap_entry.get('region', '')} Day+{shap_entry.get('prediction_day', '')}",
        xaxis_title="SHAP Value (impact on AQI)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=150, t=50)
    )
    return fig
```

### `components/chat_ui.py`

```python
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
```

---

## Step 8.1.4 — Main Entry Point (`streamlit_frontend.py`)

```python
# streamlit_frontend/streamlit_frontend.py

import streamlit as st
from config_frontend import PAGE_CONFIG
from api_client import check_api_health

# ── Page config (must be first Streamlit call) ───────────────
st.set_page_config(**PAGE_CONFIG)

# ── Sidebar nav ──────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/"
             "Flag_of_Delhi.svg/240px-Flag_of_Delhi.svg.png", width=80)
    st.title("Delhi AQI\nIntelligence")
    st.divider()

    # API health indicator
    if check_api_health():
        st.success("🟢 API Connected")
    else:
        st.error("🔴 API Offline\nStart: `uvicorn delhi_aqi_system.api.main:app --port 8000`")

    st.caption("Navigate using the sidebar pages above.")
    st.divider()
    st.caption("Delhi AQI Prediction System\nXGBoost + SHAP + Gemini AI")

# ── Landing page content ──────────────────────────────────────
st.title("🌫️ Delhi AQI Intelligence System")
st.markdown("""
Welcome to the **Delhi AQI Intelligence System** — a research-grade air quality
forecasting and explanation platform powered by **XGBoost**, **SHAP**, and **Gemini AI**.

Use the sidebar to navigate between pages:

| Page | What it shows |
|---|---|
| 🏠 Dashboard | 3-day AQI forecast for all Delhi regions with color-coded cards |
| 📊 Model Insights | SHAP feature importance plots — why each prediction was made |
| 🔄 What-If Scenarios | Counterfactual analysis — how much interventions could reduce AQI |
| 🤖 AI Explanation | Gemini-generated scientific narrative of today's forecast |
| 🤖 AI Agents | Toggle between Vayu (public assistant) and DELPHI (policy advisor) on one page |
""")
```

> **Phase 8.1 done.** Run `streamlit run streamlit_frontend.py` — you should see the landing page and a green "API Connected" badge in the sidebar if FastAPI is running.

---

---

# PHASE 8.2 — Dashboard Page

**What you build:** Page 1 — the AQI forecast overview. Shows tomorrow's AQI cards for all 6 regions, a day-selector bar chart, a 3-day trend line, and the full forecast table.

**Data source:** `predictions` section of `latest_result.json` via:
- `GET /api/v1/predictions/summary` → summary cards
- `GET /api/v1/predictions` → bar chart + trend line + table
- `GET /api/v1/pipeline/status` → staleness banner

**File to create:** `pages/01_dashboard.py`

---

## Step 8.2.1 — Dashboard Page (`pages/01_dashboard.py`)

```python
# pages/01_dashboard.py

import streamlit as st
from config_frontend import REGIONS
from api_client import get_predictions_summary, get_all_predictions, get_pipeline_status
from components.aqi_card import render_aqi_card
from components.staleness_banner import render_staleness_banner
from components.charts import build_region_comparison_bar, build_3day_trend_line

st.set_page_config(page_title="Dashboard | Delhi AQI", page_icon="🏠", layout="wide")

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
            from config_frontend import get_aqi_category
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
    import pandas as pd
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
```

> **Phase 8.2 done.** The Dashboard page shows color-coded AQI cards, an interactive bar chart with a day selector, a 3-day trend line, and the full forecast table — all from `predictions` data only.

---

---

# PHASE 8.3 — Model Insights Page

**What you build:** Page 2 — SHAP analysis. Shows why the model made each prediction using base value → feature contributions → predicted value waterfall, plus a feature impact bar chart and detail table.

**Data source:** `shap` section of `latest_result.json` via:
- `GET /api/v1/shap/{region}/day/{day}` → main charts (18 possible entries: 6 regions × 3 days)
- `GET /api/v1/shap` → all-regions overview in expander

**File to create:** `pages/02_model_insights.py`

---

## Step 8.3.1 — Model Insights Page (`pages/02_model_insights.py`)

```python
# pages/02_model_insights.py

import streamlit as st
from config_frontend import REGIONS
from api_client import get_all_shap, get_shap_region_day
from components.charts import build_shap_waterfall, build_shap_feature_bar

st.set_page_config(page_title="Model Insights | Delhi AQI", page_icon="📊", layout="wide")

st.title("📊 Model Insights — SHAP Analysis")
st.caption("Understand why the model made each prediction using SHAP feature attributions.")

# ── Controls ──────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    selected_region = st.selectbox("Select Region:", REGIONS)
with col2:
    selected_day = st.selectbox("Select Forecast Day:", [1, 2, 3],
                                 format_func=lambda x: f"Day+{x}")

# ── Fetch specific SHAP entry ─────────────────────────────────
shap_entry = get_shap_region_day(selected_region, selected_day)

if shap_entry:
    # ── Key metrics ───────────────────────────────────────────
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Base AQI (model average)", f"{shap_entry.get('base_value', 0):.1f}")
    col_b.metric(f"Predicted AQI (Day+{selected_day})", shap_entry.get("predicted_value", "–"))
    delta = shap_entry.get("predicted_value", 0) - shap_entry.get("base_value", 0)
    col_c.metric("SHAP Contribution (total)", f"{delta:+.1f}")

    st.divider()

    # ── Waterfall + Bar side by side ──────────────────────────
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Waterfall Chart")
        st.plotly_chart(build_shap_waterfall(shap_entry), use_container_width=True)
    with col_right:
        st.subheader("Feature Impact (SHAP Values)")
        st.plotly_chart(build_shap_feature_bar(shap_entry), use_container_width=True)

    st.divider()

    # ── Feature details table ─────────────────────────────────
    st.subheader("🔍 Feature Detail Table")
    import pandas as pd
    rows = []
    for f in shap_entry.get("top_features", []):
        direction = "↑ Increases AQI" if f["shap_value"] > 0 else "↓ Reduces AQI"
        rows.append({
            "Feature":         f["feature"],
            "Observed Value":  f["actual_value"],
            "SHAP Value":      f"{f['shap_value']:+.3f}",
            "Direction":       direction,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # ── All-regions overview (expander) ──────────────────────
    with st.expander("🌐 View SHAP summary for all regions (Day+1)"):
        all_shap = get_all_shap()
        if all_shap:
            day1_entries = [e for e in all_shap if e.get("prediction_day") == 1]
            for entry in day1_entries:
                st.subheader(entry["region"])
                st.plotly_chart(build_shap_feature_bar(entry), use_container_width=True)
```

> **Phase 8.3 done.** The Model Insights page shows only SHAP data — base value, feature contributions, predicted value. No prediction cards, no counterfactual scenarios. Dropdown selects any of the 18 combinations (6 regions × 3 days).

---

---

# PHASE 8.4 — What-If Scenarios Page

**What you build:** Page 3 — counterfactual analysis. Shows what AQI would be if key emission features were reduced, with individual and combined scenarios per region.

**Data source:** `counterfactuals` section of `latest_result.json` via:
- `GET /api/v1/counterfactual/{region}` → main view (5–8 scenarios per region)
- `GET /api/v1/counterfactual` → cross-region comparison in expander

**File to create:** `pages/03_whatif.py`

---

## Step 8.4.1 — What-If Scenarios Page (`pages/03_whatif.py`)

```python
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
```

> **Phase 8.4 done.** The What-If page shows only counterfactual data — original AQI, intervention scenarios, and reduction results. No SHAP values, no forecast cards.

---

---

# PHASE 8.5 — AI Explanation Page

**What you build:** Page 4 — the Gemini-generated scientific summary. Displays all 5 pre-written text sections from the pipeline output. No charts, no live API calls to Gemini — just reads and displays the saved text.

**Data source:** `explanation` section of `latest_result.json` via:
- `GET /api/v1/explanation` → all 5 text sections
- `GET /api/v1/pipeline/status` → staleness banner

**File to create:** `pages/04_ai_explanation.py`

---

## Step 8.5.1 — AI Explanation Page (`pages/04_ai_explanation.py`)

```python
# pages/04_ai_explanation.py

import streamlit as st
from api_client import get_full_explanation, get_pipeline_status
from components.staleness_banner import render_staleness_banner

st.set_page_config(page_title="AI Explanation | Delhi AQI", page_icon="🤖", layout="wide")

st.title("🤖 AI Scientific Explanation")
st.caption("Gemini-generated atmospheric science analysis of today's AQI forecast.")

# ── Staleness banner ──────────────────────────────────────────
status = get_pipeline_status()
if status:
    render_staleness_banner(
        status.get("pipeline_ran_at", ""),
        status.get("gemini_model_used", ""),
        status.get("gemini_attempts", 1)
    )

# ── Validation warnings ───────────────────────────────────────
if status and status.get("validation_warnings"):
    with st.expander("⚠ Data quality notices"):
        for w in status["validation_warnings"]:
            st.warning(w)

st.divider()

# ── Fetch and render explanation ──────────────────────────────
explanation = get_full_explanation()
if explanation:
    # Section 1 — Forecast Explanation
    with st.container():
        st.subheader("📈 Forecast Explanation")
        st.write(explanation.get("prediction_explanation", "Not available."))

    st.divider()

    # Section 2 — SHAP Interpretation
    with st.container():
        st.subheader("🔍 Why These Predictions? (SHAP Interpretation)")
        st.write(explanation.get("shap_interpretation", "Not available."))

    st.divider()

    # Section 3 — Counterfactual Analysis
    with st.container():
        st.subheader("🔄 What-If Scenario Analysis")
        st.write(explanation.get("counterfactual_analysis", "Not available."))

    st.divider()

    # Section 4 — Health Impact
    with st.container():
        st.subheader("🏥 Health Impact Summary")
        st.write(explanation.get("health_impact_summary", "Not available."))

    st.divider()

    # Section 5 — Recommended Intervention
    with st.container():
        st.subheader("✅ Recommended Intervention")
        st.info(explanation.get("recommended_intervention", "Not available."))
else:
    st.error("No explanation found. Ensure the pipeline has run successfully.")
    st.code("python run_daily_pipeline.py data/raw/latest.csv")
```

> **Phase 8.5 done.** The AI Explanation page displays the 5 Gemini-written sections. No raw numbers, no charts — pure text from the `explanation` key. The staleness banner tells users when data was last generated.

---

---

# PHASE 8.6 — AI Agents Page

**What you build:** Page 5 — the dual-agent chat interface. Both Vayu (public) and DELPHI (policy) live on one page with a toggle switch. Switching agents swaps the full UI theme, suggested questions, and active chat history — without clearing either agent's conversation.

**Data source:** Live chat via FastAPI agent endpoints:
- `POST /api/v1/agent/chat` (with `agent_type: "public"` or `"policy"`)
- `GET /api/v1/agent/questions/public`
- `GET /api/v1/agent/questions/policy`

**File to create:** `pages/05_ai_agents.py`

---

## Step 8.6.1 — UI Layout (Toggle Switch Design)

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 AI Assistant                                            │
│                                                             │
│   [ 🌿 Vayu — Public Assistant ]  ←→  [ 🏛️ DELPHI — Policy ]│
│              (radio toggle switch)                          │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Chat history for active agent (independently stored) │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  Suggested question chips (change with each agent switch)   │
│                                                             │
│  [ Type your question...                        ] [Send]    │
└─────────────────────────────────────────────────────────────┘
```

---

## Step 8.6.2 — AI Agents Page (`pages/05_ai_agents.py`)

```python
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
```

> **Phase 8.6 done.** Both agents are on one page. The toggle switch swaps the full UI theme, chips, chat history, and input placeholder. Neither conversation is lost when switching. Export and Clear operate on the currently active agent only.

---

---

# PHASE 8.7 — Final Setup & Verification

**What you do:** Install dependencies, confirm all pages run correctly, and verify the full checklist before calling the frontend complete.

---

## Step 8.7.1 — `requirements_frontend.txt`

```
streamlit>=1.35.0
requests>=2.31.0
plotly>=5.20.0
pandas>=2.0.0
```

> Do **not** include `xgboost`, `shap`, `google-generativeai`, or other ML dependencies. Those belong to the backend.

---

## Step 8.7.2 — Session State Architecture

All state lives in `st.session_state`. Pages only fetch from API once per session per page load (no redundant calls on widget interactions).

| Key | Type | Set by | Used by |
|---|---|---|---|
| `public_history` | `list[dict]` | `05_ai_agents.py` | AI Agents page (Vayu active) |
| `public_suggestions` | `list[str]` | `05_ai_agents.py` (API) | Vayu chip questions |
| `policy_history` | `list[dict]` | `05_ai_agents.py` | AI Agents page (DELPHI active) |
| `policy_suggestions` | `list[str]` | `05_ai_agents.py` (API) | DELPHI chip questions |

> Both histories are initialised when the page first loads. Switching the toggle never resets either — each agent resumes exactly where the user left off.

---

## Step 8.7.3 — How to Run (Full Stack)

```bash
# Terminal 1 — Start FastAPI backend (from project root, parent of delhi_aqi_system/)
uvicorn delhi_aqi_system.api.main:app --reload --port 8000

# Terminal 2 — Start Streamlit frontend (from streamlit_frontend/ folder)
cd streamlit_frontend/
streamlit run streamlit_frontend.py --server.port 8501

# Access:
# FastAPI docs:    http://localhost:8000/docs
# Streamlit app:   http://localhost:8501
```

---

## Step 8.7.4 — Implementation Checklist

Before declaring the frontend complete, verify each item:

**Phase 8.1 — Foundation**
- [ ] All endpoints have a corresponding function in `api_client.py`
- [ ] `_get()` and `_post()` show user-friendly `st.error()` messages on failure
- [ ] No page ever calls `requests` directly — always through `api_client.py`
- [ ] `check_api_health()` is called in sidebar and shows connection status

**Phase 8.2 — Dashboard**
- [ ] Summary cards load with correct AQI colors per CPCB categories
- [ ] Day selector switches bar chart between Day+1, Day+2, Day+3
- [ ] 3-day trend line chart works with multi-region selection
- [ ] Full forecast table renders correctly

**Phase 8.3 — Model Insights**
- [ ] Region + day dropdown fetches correct SHAP entry via API
- [ ] Waterfall chart shows base → features → prediction flow correctly
- [ ] Feature bar chart correctly colors positive (red) vs negative (green) SHAP
- [ ] All-regions expander loads and renders without crashing

**Phase 8.4 — What-If Scenarios**
- [ ] Region dropdown shows correct counterfactual entry
- [ ] Horizontal bar chart shows all scenarios vs original correctly
- [ ] Best scenario is highlighted in header metrics
- [ ] Cross-region comparison table loads in expander

**Phase 8.5 — AI Explanation**
- [ ] All 5 sections display with correct content
- [ ] Staleness banner correctly shows fresh/stale status
- [ ] Validation warnings display in expander when present

**Phase 8.6 — AI Agents**
- [ ] Toggle switch renders with `st.radio(horizontal=True)` and correctly sets `agent_type`
- [ ] Switching agents swaps: header badge, chips, chat history, input placeholder, spinner text
- [ ] Switching agents does NOT clear either conversation history
- [ ] Both `public_history` and `policy_history` are initialised on first page load
- [ ] Chip clicks correctly use the active agent's `key_prefix` to avoid Streamlit key collisions
- [ ] Export button downloads active agent's conversation as `.txt`
- [ ] Clear button only clears the currently active agent's history
- [ ] History is stateless server-side (full history sent with each request)

**General**
- [ ] `st.set_page_config()` is the FIRST call in every page file
- [ ] No ML library imports anywhere in the frontend
- [ ] API offline state is handled gracefully with instructions to start server
- [ ] `requirements_frontend.txt` does not include backend dependencies

---

## Design & UX Summary

| Page | Primary Color | Agent Name | Tone |
|---|---|---|---|
| Dashboard | White / AQI-color coded | — | Informational |
| Model Insights | White / Red-Green SHAP | — | Technical |
| What-If | White / AQI-color coded | — | Analytical |
| AI Explanation | White | — | Scientific |
| AI Agents | Green (Vayu) / Blue (DELPHI) toggle | Vayu 🌿 + DELPHI 🏛️ | Dual-mode: warm ↔ formal |

---

## Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| All HTTP calls in `api_client.py` only | Single place to change base URL, add auth headers, or mock for testing |
| Stateless chat (full history sent per request) | Matches FastAPI backend design; frontend is the state holder |
| Both agents on one page with `st.radio` toggle | Follows Phase 7 design intent; users can switch context mid-session without losing either conversation |
| Separate `session_state` keys per agent even on one page | Switching the toggle never clobbers history — both agents resume exactly where the user left off |
| `st.rerun()` after each chat message | Forces Streamlit to re-render the full chat history after appending new turns |
| Plotly for all charts | Interactive, zoomable, exportable — better UX than static Matplotlib in Streamlit |
| `@st.cache_data` not used on API calls | Data freshness matters for AQI — we want every page load to get current data from the API |
| Export available for both agents | Either persona's conversation may be worth saving — no reason to restrict it |
| `check_api_health()` in sidebar | Immediate feedback if the backend isn't running — saves debugging time |

---

*This plan covers the complete API-connected Streamlit frontend for Phase 8. The Streamlit app has no direct dependency on any ML, pipeline, or Gemini code — it communicates exclusively through the FastAPI layer built in Phase 8 (FastAPI).*
