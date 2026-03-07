# Delhi AQI Prediction System - Full Project Documentation

## 1. Project Overview
The **Delhi AQI Prediction System** is a research-level, end-to-end Machine Learning and Generative AI pipeline. It predicts the Air Quality Index (AQI) for 5 distinct regions in Delhi plus the overall city for the next 1–3 days. Beyond prediction, the system explains *why* the AQI is changing using SHAP (SHapley Additive exPlanations), simulates policy interventions using Counterfactual Analysis ("What-If" scenarios), and leverages Google Gemini LLMs to generate scientific explanations and power two distinct AI conversational agents (Public Assistant and Policy Advisor). A Streamlit frontend serves as the interactive dashboard for the entire system.

## 2. Directory Structure & File Descriptions
The project is organized in the `delhi_aqi_system/` directory:

```text
delhi_aqi_system/
├── data/
│   ├── raw/                  # Contains live_data.csv and raw historical datasets.
│   └── processed/            # Cleaned, feature-engineered datasets.
├── models/
│   └── saved/
│       └── delhi_aqi_all_regions.pkl  # Single bundled file containing 18 XGBoost models (6 regions × 3 horizons).
├── outputs/
│   ├── predictions/          # JSON of 1-3 day predictions.
│   ├── shap/                 # SHAP values and feature contributions.
│   ├── counterfactual/       # "What-If" counterfactual scenario results.
│   └── latest_result.json    # Consolidated JSON of all pipeline outputs + Gemini scientific explanation.
├── pipeline/                 # Core machine learning & processing modules.
│   ├── data_loader.py        # Abstracted data ingestion layer.
│   ├── feature_engineering.py# Creates time-based, lag, and rolling features.
│   ├── model_train.py        # XGBoost training script with Optuna hyperparameter tuning.
│   ├── model_predict.py      # Multi-step 1-3 day prediction inference logic.
│   ├── shap_analysis.py      # Global and Local SHAP value computation.
│   ├── counterfactual.py     # Feature perturbation for policy simulation.
│   └── gemini_explainer.py   # Connects to Gemini API for scientific summary generation.
├── agents/                   # Generative AI Chat Agents logic.
│   ├── __init__.py
│   ├── agent_core.py         # Main agent LLM invocation and history management.
│   ├── context_builder.py    # Injects pipeline JSON outputs into prompt context.
│   ├── suggested_questions.py# Provides contextual starting questions for both agents.
│   └── system_prompts.py     # Defines agent behavior, persona, and strict response rules.
├── run_daily_pipeline.py     # Master orchestrator script running the entire pipeline sequentially.
├── streamlit_app.py          # The frontend Streamlit dashboard with tabs and interactive chat interfaces.
├── config.py                 # Configuration file for API keys, model parameters, and constants.
└── requirements.txt          # Python dependencies.
```

## 3. Implementation Details (Pipeline Architecture)

### Phase 1: Data Pipeline (`pipeline/data_loader.py`, `pipeline/feature_engineering.py`)
- **Data Loading:** Data is currently ingested via CSV. `data_loader.py` is designed to be easily swappable with a live API (e.g., CPCB or OpenWeatherMap) in the future.
- **Feature Engineering:** Extracts datetime components, lag features (1-day, 2-day, 3-day AQI), rolling window means (3-day, 7-day), and handles missing variables. Chronological sorting guarantees no time-series data leakage.

### Phase 2: Model Training (`pipeline/model_train.py`)
- **Direct Multi-Output Strategy:** The system trains an independent `XGBRegressor` for every region and every day horizon (Day+1, Day+2, Day+3). This totals 18 discrete models.
- **Hyperparameter Tuning:** Optuna optimizes each tree based on MAE/RMSE.
- **Packaging:** All 18 models are serialized into a single nested Python dictionary (`delhi_aqi_all_regions.pkl`). 

### Phase 3: Prediction Engine (`pipeline/model_predict.py`)
- Predicts AQI values based on the most recent row of observed data in the data pipeline.
- Because of the direct multi-output strategy, no recursive loop or lag-updating is required during inference. The output is cleanly saved into `predictions_3day.json`.

### Phase 4: SHAP Analysis (`pipeline/shap_analysis.py`)
- **Local SHAP Explanations:** Explains individual predictions by breaking them down into base values plus local feature impacts. 
- Filters the top positive SHAP features driving the pollution upward, converting tree computations into interpretable human values, saved into `shap_candidates.json` and `shap_values.json`.

### Phase 5: Counterfactual Scenarios (`pipeline/counterfactual.py`)
- Uses the top reducible SHAP features identified in Phase 4 (e.g., PM2.5, NOX, Traffic Index, skipping non-reducible features like Temperature).
- Simulates targeted policy actions by synthetically reducing these feature weights by 25% and dynamically predicting the new resulting AQI value. Contains individual and combined (multi-feature) scenario analyses, exported to `counterfactual_results.json`.

### Phase 6: Core LLM Summarization (`pipeline/gemini_explainer.py`)
- Consolidates all generated JSONs (Predictions, SHAP, Counterfactuals) into a unified payload sent to the `gemini-1.5-pro` API. 
- The LLM outputs a highly structured 5-part scientific summary: Forecast Explanation, SHAP Interpretation, Counterfactual Analysis, Health Impact, and Recommended Interventions.

### Phase 7: AI Chat Agents (`agents/`)
Dual specialized agents interacting via `gemini-1.5-flash`:
- **Vayu (Public Assistant):** Simplistic, empathetic, uses everyday language. Focused on health advisories and safe locations.
- **DELPHI (Policy Advisor):** Technical, data-driven. Recommends policy actions utilizing counterfactual calculations and SHAP attributions.
- Employs RAG-lite by dynamically converting all prediction/SHAP JSON outputs into system context.

### Phase 8: Orchestration & Frontend (`run_daily_pipeline.py`, `streamlit_app.py`)
- **Orchestrator:** `run_daily_pipeline.py` sequences Phases 3-6 and bundles all JSON files + LLM summary into a master `outputs/latest_result.json`.
- **Frontend:** Streamlit reads this latest JSON file instantly (avoiding costly live recalculations). Features the Scientific Summary dashboard and the dynamic Chat Agent UI with session state memories and persona toggling.

---

## 4. API Backend Design Recommendations
Currently, `streamlit_app.py` acts as a monolithic frontend reading local JSON files. To decouple this system and create scalable endpoints for web or mobile apps, the following API architecture using **FastAPI** is highly recommended:

### Architecture Strategy
The orchestration script (`run_daily_pipeline.py`) should be adapted to run on a CRON schedule (e.g., daily at 6 AM). The Python backend API will serve the generated static data instantly, while proxying dynamically generated LLM chat messages.

### Recommended Tech Stack
- **Framework:** FastAPI (High performance, async native, auto-generates Swagger/OpenAPI docs).
- **Server:** Uvicorn.
- **Data storage for API:** Load the `latest_result.json` into memory on API startup or serve via a lightweight cache like Redis.

### API Endpoint Blueprints

#### 1. System Health & Dashboard Data
- **`GET /api/v1/health`**
  - Returns pipeline status, last generated timestamp, and data freshness metrics.
- **`GET /api/v1/dashboard`**
  - Consumes `predictions_3day.json`.
  - Returns current day's AQI and the next 1-3 day predictions for all 6 regions.
- **`GET /api/v1/insights`**
  - Consumes `shap_values.json` and `counterfactual_results.json`.
  - Returns the top 5 driving pollutants and "What-If" percentage reduction data.

#### 2. Scientific Explanations
- **`GET /api/v1/explanation`**
  - Consumes the `explanation` object from `latest_result.json`.
  - Returns the pre-generated Gemini scientific responses (Forecast, Health Impact, Recommendations).

#### 3. Conversational AI Agents (Dynamic)
- **`POST /api/v1/chat`**
  - Payload: `{ "user_message": "Is it safe outside?", "agent_type": "public", "history": [...] }`
  - Controller Logic:
    1. Validate `agent_type` (must be `public` or `policy`).
    2. Import logic from `agents.context_builder` and `agents.agent_core`.
    3. Feed context + history + user message to `call_agent()`.
  - Returns: LLM's dynamically generated string response.
  - *Optionally implement WebSockets or Server-Sent Events (SSE) for streaming text chunks back to the client.*

### Next Steps for API Migration
1. Initialize a `server.py` or `main.py` FastAPI app.
2. Abstract the file-reading logic in `streamlit_app.py` into dedicated Python handler functions to be referenced by FastAPI router endpoints.
3. Establish CORS middleware in FastAPI to accept requests from an external frontend (e.g., Next.js, React, or mobile app).
