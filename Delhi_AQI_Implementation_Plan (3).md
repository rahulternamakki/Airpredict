# Delhi AQI Prediction System — Implementation Plan
### Research-Level Proof of Concept | XGBoost + SHAP + Counterfactual + Gemini LLM + Streamlit

---

## Project Overview

A research-level end-to-end pipeline that:
1. Trains an XGBoost model on region-wise Delhi AQI data (weather + air pollution + human activity)
2. Predicts next 1–3 days AQI for 5 Delhi regions + Overall Delhi
3. Explains predictions using SHAP
4. Runs Counterfactual ("What-If") scenarios on top polluting features
5. Feeds all outputs to Gemini LLM for scientific explanation generation
6. Serves a Streamlit frontend with two specialized AI agents (Public + Policy Maker)

---

## Architecture Overview

```
[Final Dataset CSV]
        │
        ▼
┌─────────────────────┐
│  DATA PIPELINE      │  ← Load, validate, engineer features, time-series split
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  XGBOOST MODEL      │  ← Train per-region models, evaluate (MAE, RMSE, R²)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  PREDICTION ENGINE  │  ← Predict 1-day, 2-day, 3-day AQI per region + Delhi overall
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  SHAP EXPLAINER     │  ← Global + local feature importance, top 5–8 polluting features
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  COUNTERFACTUAL     │  ← "What-If" scenarios on top SHAP features (5–8, incl. combos)
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  GEMINI LLM LAYER   │  ← Receives predictions + SHAP + counterfactual → scientific summary
└────────┬────────────┘
         │
         ▼
┌─────────────────────────────────────────┐
│  STREAMLIT FRONTEND                     │
│  ┌────────────────┐ ┌────────────────┐  │
│  │  Public Agent  │ │ Policy Agent   │  │
│  │  (Gemini API)  │ │ (Gemini API)   │  │
│  └────────────────┘ └────────────────┘  │
└─────────────────────────────────────────┘
```

---

## Step-by-Step Implementation Plan

---

### PHASE 1 — Project Setup & Data Pipeline

#### Step 1.1 — Project Structure Setup
```
delhi_aqi_system/
├── data/
│   ├── raw/                  ← Place your final dataset CSV here
│   └── processed/            ← Cleaned, feature-engineered data saved here
├── models/
│   └── saved/
│       └── delhi_aqi_all_regions.pkl  ← Single PKL containing all 6 region models as a dict
├── outputs/
│   ├── predictions/          ← JSON/CSV of 1-3 day predictions
│   ├── shap/                 ← SHAP values, plots
│   └── counterfactual/       ← Counterfactual scenario results
├── agents/
│   ├── public_agent.py       ← Public-facing Gemini chatbot agent
│   └── policy_agent.py       ← Policy-maker Gemini chatbot agent
├── pipeline/
│   ├── data_loader.py
│   ├── feature_engineering.py
│   ├── model_train.py
│   ├── model_predict.py
│   ├── shap_analysis.py
│   ├── counterfactual.py
│   └── gemini_explainer.py
├── streamlit_app.py          ← Main Streamlit app
├── config.py                 ← API keys, paths, constants
└── requirements.txt
```

#### Step 1.2 — Dataset Loading & Validation
- Load the final CSV dataset
- Identify 5 Delhi regions + overall Delhi columns
- Confirm: datetime column is present and properly formatted
- Check for nulls, outliers, duplicate timestamps
- Confirm AQI target column and all feature columns (weather, pollution, human activity)
- Sort entire dataset by datetime (ascending) — critical for time-series integrity

#### Step 1.3 — Feature Engineering
- Parse datetime → extract: hour, day_of_week, month, season, is_weekend, is_holiday (Delhi public holidays)
- Create **lag features** for AQI: lag_1day, lag_2day, lag_3day per region
- Create **rolling window features**: 3-day rolling mean, 7-day rolling mean of AQI per region
- Create interaction features (e.g., temp × humidity, wind_speed × PM2.5) — these will be relevant for counterfactuals later
- Normalize/scale continuous features if needed (XGBoost is scale-invariant but good for interpretability)
- Save the processed dataset to `data/processed/`

---

### PHASE 2 — XGBoost Model Training

#### Step 2.1 — Time-Series Train/Test Split (80-20)
- **IMPORTANT:** Do NOT use random split — use chronological split
- Sort by datetime → take first 80% rows as train, last 20% rows as test
- No data leakage: test set is always temporally after train set
- Log the exact date boundary of the split for documentation

#### Step 2.2 — Model Architecture Decision
- Train **three XGBoost models per region** — one model for each prediction horizon (Day+1, Day+2, Day+3)
- That gives **18 models total** (6 regions × 3 horizons), all stored in a single PKL dict
- Each model is trained with its own target variable:
  - `model_day1`: target = AQI shifted 1 day forward
  - `model_day2`: target = AQI shifted 2 days forward
  - `model_day3`: target = AQI shifted 3 days forward
- This is the **Direct Multi-Output strategy** — train each horizon independently so the prediction code simply loads the PKL and calls `.predict(X)` for each day with no recursive dependency or iterative lag updates needed
- Features: all weather + pollution + human activity + engineered lag/rolling features (same feature set for all 3 horizon models)
- **All 18 trained models are bundled into a single PKL file** as a nested Python dictionary:
```python
all_models = {
    "North Delhi":   {"day_1": <XGBRegressor>, "day_2": <XGBRegressor>, "day_3": <XGBRegressor>},
    "South Delhi":   {"day_1": <XGBRegressor>, "day_2": <XGBRegressor>, "day_3": <XGBRegressor>},
    "East Delhi":    {"day_1": <XGBRegressor>, "day_2": <XGBRegressor>, "day_3": <XGBRegressor>},
    "West Delhi":    {"day_1": <XGBRegressor>, "day_2": <XGBRegressor>, "day_3": <XGBRegressor>},
    "Central Delhi": {"day_1": <XGBRegressor>, "day_2": <XGBRegressor>, "day_3": <XGBRegressor>},
    "Overall Delhi": {"day_1": <XGBRegressor>, "day_2": <XGBRegressor>, "day_3": <XGBRegressor>}
}
# Save:  joblib.dump(all_models, "models/saved/delhi_aqi_all_regions.pkl")
# Load:  all_models = joblib.load("models/saved/delhi_aqi_all_regions.pkl")
```
- To predict Day+2 for East Delhi: `all_models["East Delhi"]["day_2"].predict(X)`
- To run SHAP for Day+1 for North Delhi: `shap.TreeExplainer(all_models["North Delhi"]["day_1"])`
- **Benefit:** Prediction code stays clean and stateless — just load PKL → call `.predict(X)` per region per day. No loop-back, no iterative lag updates at prediction time

#### Step 2.3 — XGBoost Hyperparameters & Tuning (Optuna)
- Use **Optuna** for hyperparameter search — improves accuracy and is already part of the implementation
- Optuna search space per model:
  - n_estimators: 200–500
  - max_depth: 4–6
  - learning_rate: 0.01–0.1
  - subsample: 0.6–1.0
  - colsample_bytree: 0.6–1.0
  - min_child_weight: 1–10
- Run Optuna per region per day horizon (i.e., 18 separate tuning runs), or share best params across horizons within the same region to save time at research level
- Use MAE or RMSE as the Optuna objective metric
- Each tuned model is a **plain `xgb.XGBRegressor`** — do NOT use `MultiOutputRegressor` wrapper
- `MultiOutputRegressor` would break `shap.TreeExplainer` and contradict the nested dict structure; keep every model as a standalone `XGBRegressor` fitted to one target at a time
- Training loop structure:
```python
all_models = {}
for region in regions:
    all_models[region] = {}
    for day in [1, 2, 3]:
        # Optuna finds best_params for this region+horizon
        model = xgb.XGBRegressor(**best_params)
        model.fit(X_train, y_train[f'AQI_target_day{day}'])
        all_models[region][f'day_{day}'] = model
```

#### Step 2.4 — Model Evaluation
- Evaluate on test set (last 20%)
- Metrics per region: MAE, RMSE, R², MAPE
- Plot: Actual vs Predicted AQI line chart per region on test period
- Save all 18 models together into a single file: `models/saved/delhi_aqi_all_regions.pkl` (nested dict: region → day horizon → model)
- Log metrics to a summary table for documentation

---

### PHASE 3 — Prediction Engine (1–3 Days)

#### Step 3.1 — Live Data Input via CSV (API-Ready Design)
- Design a CSV template with column structure exactly matching the training feature set
- The CSV represents the most recent available data window (last N days needed for lag feature computation)
- **CSV is the current input method** — but the data ingestion layer must be written as a separate, swappable module (`data_loader.py`) so that in the future the CSV read can be replaced with a live API call (e.g., CPCB API, OpenWeatherMap API) without touching any other part of the pipeline
- The module exposes a single interface: `load_live_data(source)` — today `source` is a CSV path, tomorrow it can be an API endpoint
- Compute all lag features and rolling features from this live window the same way as training

#### Step 3.2 — Multi-Step Prediction Logic (Direct, No Recursion)
- Since the model was trained with direct multi-output targets (Day+1, Day+2, Day+3 as separate models), prediction is straightforward — no recursive loop, no lag updates:
  - **Day+1:** `all_models[region]["day_1"].predict(X_live)` — uses latest live features directly
  - **Day+2:** `all_models[region]["day_2"].predict(X_live)` — same live features, different model horizon
  - **Day+3:** `all_models[region]["day_3"].predict(X_live)` — same live features, different model horizon
- Run this for all 6 regions in a loop → produces 18 predictions total
- No weather forecast assumption needed — all 3 days predict from the same current observed feature snapshot

#### Step 3.3 — Prediction Output Format
```json
{
  "prediction_date": "2024-01-15",
  "generated_at": "2024-01-12",
  "regions": {
    "North Delhi": {"day_1": 187, "day_2": 201, "day_3": 195, "category": ["Unhealthy", "Very Unhealthy", "Unhealthy"]},
    "South Delhi": {"day_1": 143, "day_2": 156, "day_3": 149, ...},
    "East Delhi": {...},
    "West Delhi": {...},
    "Central Delhi": {...},
    "Overall Delhi": {"day_1": 168, "day_2": 178, "day_3": 172, ...}
  }
}
```
- Attach AQI category labels (Good / Moderate / Unhealthy for Sensitive / Unhealthy / Very Unhealthy / Hazardous)
- Save predictions to `outputs/predictions/`

---

### PHASE 4 — SHAP Analysis

#### Step 4.1 — SHAP Explainer Setup
- Use `shap.TreeExplainer` (optimized for XGBoost/tree-based models)
- Generate SHAP values for:
  - The test set (global understanding)
  - The live prediction input rows (local/instance-level explanation)

#### Step 4.2 — Global SHAP Analysis (Per Region)
- **SHAP Summary Plot:** Bar chart of mean absolute SHAP values — shows overall feature importance
- **SHAP Beeswarm Plot:** Shows distribution of SHAP impact per feature
- **Identify Top 5–8 Most Impactful Pollution-Related Features** globally across all regions
  - Expected candidates: PM2.5, PM10, NO2, SO2, CO, Temperature, Wind Speed, Humidity, Traffic Index
  - These top features will feed directly into Counterfactual analysis

#### Step 4.3 — Local SHAP Analysis (For Each Prediction)
- For each Day+1, Day+2, Day+3 prediction per region: generate local SHAP waterfall plot
- Shows why the model predicted that specific AQI value
- Shows which features pushed AQI up vs. down from the base value
- Save SHAP plots as PNG files to `outputs/shap/`
- Save SHAP values as JSON/CSV for passing to Gemini

#### Step 4.4 — SHAP Output Format for Downstream Use
```json
{
  "region": "North Delhi",
  "prediction_day": 1,
  "base_value": 145.3,
  "predicted_value": 187,
  "top_features": [
    {"feature": "PM2.5", "shap_value": +28.4, "actual_value": 156.2},
    {"feature": "NO2", "shap_value": +12.1, "actual_value": 89.3},
    {"feature": "Wind Speed", "shap_value": -8.7, "actual_value": 2.1},
    ...
  ]
}
```

---

### PHASE 5 — Counterfactual Analysis ("What-If") using DiCE

#### Step 5.1 — Feature Selection for Counterfactuals
- **Source: Top 5 features ranked by SHAP contribution for the actual Day+1 prediction** (local SHAP values from Phase 4, not global importance)
- Specifically, take the 5 features with the **highest positive SHAP values** from the Day+1 local SHAP output per region — these are the features actively driving AQI upward in that specific prediction
- This means counterfactual features are **dynamically determined per region per prediction run**, not hardcoded — different regions or dates may yield different top-5 features
- The SHAP output from Step 4.4 is directly consumed here: sort `top_features` by `shap_value` descending → take top 5
- Example: if SHAP for North Delhi Day+1 ranks [PM2.5, NO2, Traffic_Index, SO2, Humidity] as top 5 contributors → these 5 become the counterfactual variables for North Delhi

#### Step 5.2 — DiCE Library Setup
- Use **DiCE (Diverse Counterfactual Explanations)** — `dice_ml` library — the research-standard tool for generating counterfactual explanations for ML models
- DiCE generates counterfactuals by finding realistic alternative input values that would change the model's output (AQI) to a desired target range
- DiCE integration steps:
  - Wrap the trained XGBRegressor in a `dice_ml.Model` object: `dice_ml.Model(model=all_models[region]["day_1"], backend="sklearn")`
  - Wrap the training data in a `dice_ml.Data` object: specify feature names, continuous features, and the outcome column
  - Mark the top 5 SHAP features as the **features to vary** (`features_to_vary`) — all other features are kept fixed at their live observed values
  - Set realistic feature ranges/constraints (e.g., PM2.5 cannot go below 0, Wind Speed cannot exceed physically realistic bounds) using DiCE's `permitted_range` parameter
  - Instantiate the DiCE explainer: `dice_ml.Dice(dice_data, dice_model, method="random")` — random method works well for XGBoost at research level

#### Step 5.3 — Individual Feature Counterfactuals (5 scenarios — one per top SHAP feature)
For each of the 5 SHAP-selected features, generate DiCE counterfactuals constraining only that one feature to vary:
- **Scenario 1:** Vary only [SHAP Feature #1] → DiCE finds values that reduce AQI
- **Scenario 2:** Vary only [SHAP Feature #2] → DiCE finds values that reduce AQI
- **Scenario 3:** Vary only [SHAP Feature #3] → DiCE finds values that reduce AQI
- **Scenario 4:** Vary only [SHAP Feature #4] → DiCE finds values that reduce AQI
- **Scenario 5:** Vary only [SHAP Feature #5] → DiCE finds values that reduce AQI
- Set `desired_range` in DiCE to target a lower AQI bracket (e.g., if original AQI = 187 "Unhealthy", target `desired_range=[0, 150]`)
- For meteorological features (e.g., Wind Speed) where increase improves AQI, set `permitted_range` accordingly
- Extract from DiCE output: the counterfactual feature value, the resulting predicted AQI, delta, new category
- Report per scenario: Original AQI → Counterfactual AQI → Delta → New AQI Category

#### Step 5.4 — Combined Feature Counterfactuals (2–3 scenarios)
Allow DiCE to vary multiple SHAP-selected features simultaneously for realistic policy interventions:
- **Combined Scenario A:** `features_to_vary` = Top 2 SHAP features → DiCE generates diverse counterfactuals → simulates "dual-source intervention"
- **Combined Scenario B:** `features_to_vary` = Top 3 SHAP features → simulates "tri-source intervention"
- **Combined Scenario C:** `features_to_vary` = All top 5 SHAP features → simulates "moderate across-the-board" policy
- For each combined scenario, generate `num_counterfactuals=3` diverse DiCE solutions and report the best one (lowest AQI achieved)
- Show AQI improvement delta per region for each combined scenario

#### Step 5.5 — Counterfactual Output Format
```json
{
  "region": "North Delhi",
  "original_day1_aqi": 187,
  "original_category": "Unhealthy",
  "method": "DiCE (Diverse Counterfactual Explanations)",
  "scenarios": [
    {
      "name": "Vary PM2.5 only",
      "type": "individual",
      "features_varied": ["PM2.5"],
      "original_feature_values": {"PM2.5": 156.2},
      "counterfactual_feature_values": {"PM2.5": 98.4},
      "new_aqi": 159,
      "new_category": "Unhealthy for Sensitive Groups",
      "aqi_reduction": 28,
      "percent_improvement": "15.0%"
    },
    {
      "name": "Top 3 features combined",
      "type": "combined",
      "features_varied": ["PM2.5", "NO2", "Traffic_Index"],
      "original_feature_values": {"PM2.5": 156.2, "NO2": 89.3, "Traffic_Index": 0.78},
      "counterfactual_feature_values": {"PM2.5": 91.0, "NO2": 55.1, "Traffic_Index": 0.45},
      "new_aqi": 131,
      "new_category": "Unhealthy for Sensitive Groups",
      "aqi_reduction": 56,
      "percent_improvement": "29.9%"
    }
  ]
}
```
- Save all counterfactual outputs to `outputs/counterfactual/`

---

### PHASE 6 — Gemini LLM Integration (Scientific Explanation)

#### Step 6.1 — Gemini API Setup
- Use `google-generativeai` Python SDK
- Model: `gemini-1.5-pro` or `gemini-1.5-flash` (flash for cost efficiency in research)
- Store API key securely in `config.py` or `.env` file
- Implement rate limiting and error handling (retry logic)

#### Step 6.2 — Structured Prompt Construction
Build a comprehensive prompt that feeds ALL outputs to Gemini:

**Prompt Template Structure:**
```
SYSTEM CONTEXT:
You are an environmental science AI assistant. Analyze the following Delhi AQI data 
and provide a rigorous scientific explanation. Use appropriate atmospheric chemistry 
and environmental science terminology.

DATA INPUT:
[Region-wise 1-3 day AQI predictions]
[SHAP top feature contributions with values]
[Counterfactual scenario results]

ANALYSIS REQUESTED:
1. Explain the predicted AQI trend scientifically
2. Explain why the top SHAP features are driving AQI in this direction
3. Interpret each counterfactual scenario and its feasibility as a policy intervention
4. Provide scientific context on health impacts for predicted AQI levels
5. Identify the most impactful intervention based on counterfactual results
```

#### Step 6.3 — Gemini Output Processing
- Parse Gemini response into structured sections:
  - `prediction_explanation` (scientific narrative of the forecast)
  - `shap_interpretation` (what each driver means atmospherically)
  - `counterfactual_analysis` (policy impact interpretation)
  - `health_impact_summary` (health risk narrative for predicted levels)
  - `recommended_intervention` (best scenario based on data)
- Save complete Gemini output to `outputs/gemini_explanation.json`

---

### PHASE 7 — AI Agents Design

#### Step 7.1 — Shared Agent Foundation
Both agents share:
- Access to all pre-generated outputs (predictions, SHAP, counterfactuals, Gemini explanation)
- Gemini API as the LLM backbone for conversation
- A **system prompt** that defines their role, tone, and knowledge scope
- Knowledge injected via context: all output JSONs + scientific environmental background

**Context Injection Strategy (RAG-lite for research level):**
- Serialize all outputs into a structured context string
- Prepend to every Gemini API call as system/context
- Keep context under token limits by summarizing large arrays

#### Step 7.2 — Public Agent
**Purpose:** Help common citizens understand AQI, health impacts, and protective actions

**System Prompt Key Characteristics:**
- Tone: Simple, empathetic, accessible language (avoid jargon)
- Role: "Friendly air quality assistant for Delhi residents"
- Knowledge scope: AQI basics, health advisories, what to do on bad air days, regional variation explanation
- Should NOT discuss policy mechanisms or technical model details in depth

**Example Capabilities:**
- "Is today's air safe to go outside in Dwarka?" → gives region-specific forecast + health advice
- "Why is North Delhi more polluted than South Delhi today?" → uses SHAP/Gemini explanation in plain language
- "What should I do to protect my child from pollution?" → health protective action advice
- "What does AQI 187 mean for me?" → explains health categories
- "Will air get better in the next 3 days?" → references the multi-day forecast

**Agent Architecture:**
```
User Message
    │
    ▼
Context Injection (predictions + simplified SHAP summary + Gemini explanation)
    │
    ▼
Gemini API Call (System: Public Agent prompt)
    │
    ▼
Response → Streamlit Chat UI
```

#### Step 7.3 — Policy Maker Agent
**Purpose:** Help government officials and policy makers understand pollution drivers and evaluate interventions

**System Prompt Key Characteristics:**
- Tone: Technical, precise, data-driven, policy-oriented
- Role: "Environmental policy intelligence assistant for Delhi government officials"
- Knowledge scope: Emission sources, regulatory frameworks, intervention effectiveness, counterfactual impact quantification, regional disparity analysis
- Should reference specific numbers, percentages, SHAP values, and counterfactual AQI deltas

**Example Capabilities:**
- "Which region needs emergency intervention in the next 3 days?" → cross-region comparison with highest AQI + trend
- "What's the most cost-effective pollution reduction policy?" → references counterfactual combined scenarios
- "How much can odd-even vehicle restriction improve AQI?" → uses Traffic Index counterfactual scenario
- "What are the top 3 emission sources driving today's spike in East Delhi?" → SHAP-driven answer
- "If we shut down industrial units in North Delhi for 24 hours, how much will AQI improve?" → SO2/PM2.5 counterfactual
- "Compare intervention efficiency across regions" → structured comparative analysis

**Agent Architecture:**
```
Policy Maker Message
    │
    ▼
Context Injection (full predictions + SHAP JSON + all counterfactual scenarios + Gemini scientific summary)
    │
    ▼
Gemini API Call (System: Policy Agent prompt — technical + quantitative mode)
    │
    ▼
Response → Streamlit Chat UI
```

#### Step 7.4 — Conversation Memory
- Maintain conversation history within session (list of message dicts)
- Pass full conversation history with each Gemini call for multi-turn coherence
- Clear/reset history on session start (no cross-session memory needed for research level)

---

### PHASE 8 — Streamlit Frontend

#### Step 8.1 — App Pages / Tabs Structure
```
Streamlit App
├── 🏠 Dashboard          ← AQI Forecast Overview (all regions, 3-day)
├── 📊 Model Insights     ← SHAP plots, model performance metrics
├── 🔄 What-If Scenarios  ← Counterfactual results + charts
├── 🤖 AI Explanation     ← Gemini-generated scientific summary
├── 💬 Public Agent       ← Chatbot for general public
└── 🏛️ Policy Agent       ← Chatbot for policy makers
```

#### Step 8.2 — Dashboard Page
- Upload CSV widget for live data input (or use pre-loaded sample)
- Trigger prediction pipeline on upload/button click
- Display: 
  - Region-wise AQI cards (1-day, 2-day, 3-day) with color coding by AQI category
  - Delhi Overall AQI summary prominently
  - Simple bar/line chart comparing regions across 3 days
  - AQI trend direction indicator (improving / worsening / stable)

#### Step 8.3 — Model Insights Page
- SHAP Summary Bar chart (global feature importance)
- Local SHAP Waterfall plot for selected region + day (user selects via dropdown)
- Model performance table: MAE / RMSE / R² per region (from training evaluation)
- Train/test split info with date boundaries

#### Step 8.4 — What-If Scenarios Page
- Dropdown to select region
- Display each counterfactual scenario as a card:
  - Feature(s) changed, original AQI, new AQI, improvement delta, new category
- Bar chart comparing original vs all counterfactual AQI values
- Highlight best-performing scenario (largest AQI reduction)

#### Step 8.5 — AI Explanation Page
- Display the full Gemini-generated scientific summary in formatted sections
- Sections: Forecast Explanation | SHAP Interpretation | Counterfactual Analysis | Health Impact | Recommended Intervention
- Re-generate button (calls Gemini API again if needed)

#### Step 8.6 — Public Agent Chat Page
- Clean chat interface with avatar
- System context: public-facing tone
- Suggested starter questions visible as clickable chips
- Examples: "Is it safe to jog outside tomorrow?", "Which area has best air quality?", "What AQI is dangerous for kids?"

#### Step 8.7 — Policy Agent Chat Page
- Professional chat interface with different color scheme
- System context: policy/technical tone
- Suggested starter questions:
  - "Which region needs priority intervention?"
  - "Quantify the benefit of reducing industrial emissions by 30%"
  - "Compare top pollution drivers across all 5 regions"
- Option to export conversation as text/PDF for records

#### Step 8.8 — Session State Management
- Use `st.session_state` to persist:
  - Uploaded CSV data
  - Prediction outputs
  - SHAP values
  - Counterfactual results
  - Gemini explanation
  - Conversation histories for both agents
- Pipeline runs once per session (not re-running on every UI interaction)

---

### PHASE 9 — Integration & Final Assembly

#### Step 9.1 — Pipeline Orchestration
Create a master `run_pipeline()` function that:
1. Loads and validates uploaded CSV
2. Runs feature engineering
3. Loads saved XGBoost models
4. Generates 1-3 day predictions per region
5. Runs SHAP analysis on predictions
6. Runs counterfactual scenarios
7. Calls Gemini API for scientific explanation
8. Stores all outputs in `st.session_state`
9. Triggers Streamlit re-render to populate all pages

#### Step 9.2 — Error Handling Plan
- CSV validation: check required columns present, no all-null rows
- Model loading: graceful error if model file missing
- Gemini API: retry with exponential backoff on rate limit errors
- SHAP computation: timeout guard for very large inputs
- Counterfactual: validate that feature value changes are within realistic bounds

#### Step 9.3 — Configuration File (`config.py`)
- Gemini API key (load from env variable)
- Region names list
- AQI category thresholds (Good: 0–50, Moderate: 51–100, etc.)
- Feature names for counterfactual scenarios
- Counterfactual percentage change values per scenario
- File paths for models, outputs

---

### PHASE 10 — Testing & Validation

#### Step 10.1 — Research-Level Validation Criteria
This is a proof-of-concept. Acceptance criteria:
- [ ] All 18 XGBoost models (6 regions × 3 horizons) train without errors as plain XGBRegressor instances
- [ ] 80-20 chronological split confirmed (no data leakage)
- [ ] Test set metrics are reasonable (R² > 0.6 is acceptable for research level)
- [ ] 1-3 day predictions generate valid AQI values (0–500 range)
- [ ] SHAP values sum to approximately (predicted - base value) ✓
- [ ] Counterfactual scenarios produce different AQI values than original
- [ ] Gemini API returns coherent scientific explanations
- [ ] Both chat agents respond in their respective tones/styles
- [ ] Streamlit app runs end-to-end without crashing

#### Step 10.2 — Sanity Checks
- Cross-check SHAP top features match domain knowledge (PM2.5 should be a top driver)
- Counterfactual "reduce pollution feature" should always lower AQI (sanity check direction)
- Day+2 and Day+3 predictions should show reasonable drift from Day+1
- Verify overall Delhi AQI is roughly the mean of the 5 region AQIs

---

## Technology Stack Summary

| Component | Technology |
|---|---|
| ML Model | XGBoost (`xgboost` library) — plain `XGBRegressor` per horizon |
| Hyperparameter Tuning | Optuna |
| Model Serialization | `joblib` or `pickle` |
| SHAP | `shap` library (TreeExplainer) |
| Counterfactual | DiCE — `dice_ml` library (Diverse Counterfactual Explanations) |
| LLM | Google Gemini API (`google-generativeai`) |
| Frontend | Streamlit |
| Data Processing | Pandas, NumPy |
| Visualization | Matplotlib, Plotly (in Streamlit) |
| Environment Config | `python-dotenv` |
| AQI Category Logic | Custom thresholds (CPCB standard) |

---

## Data Flow Summary

```
Final Dataset CSV (historical)
    → Feature Engineering → Lag Features → Rolling Features
    → 80% Train / 20% Test (chronological)
    → XGBoost Training (18 models: 6 regions × 3 day horizons) → Test Evaluation
    → Bundle all into single PKL nested dict → Save `delhi_aqi_all_regions.pkl`

Live Data CSV (recent) — via `load_live_data()` module (CSV now, API-swappable later)
    → Feature Engineering (same pipeline)
    → Load Single PKL (`delhi_aqi_all_regions.pkl`) → all_models nested dict
    → Predict Day+1/2/3 per region: `all_models[region]["day_N"].predict(X_live)` (no recursion)
    → SHAP TreeExplainer on Day+1 predictions → rank top 5 positive SHAP features per region
    → Predict Day+1, Day+2, Day+3
    → SHAP TreeExplainer → Global + Local SHAP values
    → Counterfactual Engine → 5 individual + 3 combined scenarios (features sourced from top 5 SHAP above)
    → All Outputs → Gemini API → Scientific Narrative
    → Streamlit App
        ├── Dashboard (predictions)
        ├── Insights (SHAP)
        ├── What-If (counterfactuals)
        ├── AI Explanation (Gemini output)
        ├── Public Chat Agent (Gemini)
        └── Policy Chat Agent (Gemini)
```

---

## Implementation Order (Recommended)

| Week | Focus |
|---|---|
| Day 1–2 | Phase 1 (Data pipeline, feature engineering, split) |
| Day 3–4 | Phase 2 (XGBoost training, evaluation, model saving) |
| Day 5 | Phase 3 (Prediction engine, multi-step logic, CSV input) |
| Day 6 | Phase 4 (SHAP analysis, plots, JSON output) |
| Day 7 | Phase 5 (Counterfactual scenarios, output formatting) |
| Day 8 | Phase 6 (Gemini integration, prompt engineering) |
| Day 9 | Phase 7 (Agent design, system prompts, conversation logic) |
| Day 10–11 | Phase 8 (Streamlit frontend, all pages) |
| Day 12 | Phase 9–10 (Integration, testing, sanity checks) |

---

## Key Design Decisions & Rationale

| Decision | Rationale |
|---|---|
| Direct Multi-Output training (3 models per region, 18 total in one PKL) | Eliminates recursive prediction at inference time — prediction code just loads PKL and calls `.predict(X)` for each horizon. Clean, simple, no lag updates needed when running predictions |
| CSV as live data source with API-ready abstraction layer | CSV works now for research; wrapping it in `load_live_data()` means swapping to a live API (CPCB, OpenWeatherMap) later requires changing only one function |
| Counterfactual features taken from top 5 positive SHAP values of the actual prediction | Ensures counterfactuals are grounded in what is driving *this specific prediction* rather than a fixed hardcoded list — makes the analysis more honest and data-driven |
| Chronological 80-20 split | Time series data has temporal dependency; random split would cause data leakage from future to past |
| Direct Multi-Output forecasting (3 separate XGBRegressor models per region per horizon) | Each horizon trained independently with its own shifted target — no recursive dependency at prediction time. Nested dict structure `all_models[region]["day_N"]` gives clean `.predict(X_live)` calls and works perfectly with `shap.TreeExplainer` since each model is a plain XGBRegressor |
| SHAP TreeExplainer | Exact SHAP values for tree models; faster and more accurate than model-agnostic methods |
| DiCE (`dice_ml`) for counterfactual generation | Research-standard library purpose-built for counterfactual explanations; generates realistic diverse alternatives by respecting feature constraints and `permitted_range` — more principled than manual feature perturbation |
| Two separate Gemini agents | Different user personas require different language registers, depth, and focus areas |
| Session-based pipeline | Prevents redundant computation in Streamlit; runs once per data upload |

---

*This plan covers proof-of-concept research-level implementation. Production hardening (model retraining pipeline, database storage, authentication, deployment) is out of scope for this phase.*
