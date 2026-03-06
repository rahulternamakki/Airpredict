# PHASE 6 — Gemini LLM Integration
## Complete Combined Plan: Pre-Computation + Scientific Explanation + Output Validation
### Delhi AQI Prediction System

---

## Overview

This phase has **two distinct responsibilities** that must never be confused:

| Responsibility | Where it runs | When it runs | Who triggers it |
|---|---|---|---|
| **Gemini explanation generation** | Your local machine | Once per day, when new CSV data arrives | You (developer) |
| **Displaying the explanation** | Streamlit web app | Every time user opens the tab | User (instant load) |

Gemini is **never called by the web app**. The web app only reads a pre-saved JSON file.

---

## System Architecture

```
YOUR LOCAL MACHINE (runs once daily):
┌──────────────────────────────────────────────────────┐
│  New CSV arrives                                      │
│       ↓                                              │
│  run_daily_pipeline.py                               │
│  ├── Feature Engineering                             │
│  ├── XGBoost Predictions (18 models)                 │
│  ├── SHAP Analysis                                   │
│  ├── Counterfactual Scenarios (DiCE)                 │
│  ├── Serialize all outputs → clean text blocks       │
│  ├── Build Gemini prompt                             │
│  ├── Call Gemini API (gemini-1.5-pro)                │
│  ├── Validate output → retry if failed               │
│  └── Save → outputs/latest_result.json              │
└──────────────────────────────────────────────────────┘
                    ↓ (file deployed / updated)
STREAMLIT WEB APP (instant for user):
┌──────────────────────────────────────────────────────┐
│  User opens AI Explanation tab                       │
│  → Read outputs/latest_result.json                   │
│  → Display all 5 sections instantly                  │
│  → Show "Last updated: [timestamp]"                  │
│  → Show staleness warning if > 30 hours old          │
└──────────────────────────────────────────────────────┘
```

---

## Step 6.1 — Gemini API Setup

### 6.1a — Installation & Configuration

```python
# requirements.txt additions
google-generativeai>=0.5.0
python-dotenv>=1.0.0
```

```bash
# .env file (never commit this to git)
GEMINI_API_KEY=your_key_here
```

```python
# config.py
import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY     = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL       = "gemini-1.5-pro"        # Pro for explanation (quality over cost)
GEMINI_TEMPERATURE = 0.2                      # Low = factual, consistent, not creative
GEMINI_MAX_TOKENS  = 4096                     # Enough for detailed 5-section output
GEMINI_TOP_P       = 0.85

LATEST_RESULT_PATH = "outputs/latest_result.json"
MAX_RETRIES        = 3
STALENESS_HOURS    = 30                       # Warn user if data older than this
```

### 6.1b — Model Initialization

```python
# pipeline/gemini_explainer.py

import google.generativeai as genai
import time, json, os
from datetime import datetime
from config import (GEMINI_API_KEY, GEMINI_MODEL, GEMINI_TEMPERATURE,
                    GEMINI_MAX_TOKENS, GEMINI_TOP_P, MAX_RETRIES)

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    model_name=GEMINI_MODEL,
    generation_config=genai.types.GenerationConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_TOKENS,
        top_p=GEMINI_TOP_P
    )
)
```

### 6.1c — Retry Logic with Exponential Backoff

```python
def call_gemini_with_retry(prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """
    Calls Gemini API with exponential backoff on failure.
    Waits: 2s → 4s → 8s between retries.
    Raises exception if all retries exhausted.
    """
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            wait_time = 2 ** attempt
            if attempt < max_retries - 1:
                print(f"[Gemini] Attempt {attempt+1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"Gemini API failed after {max_retries} attempts: {e}")
```

---

## Step 6.2 — Pre-Prompt Data Serialization

**This is the most critical step for explanation quality.**
Raw JSON dumps are noisy, waste tokens, and confuse the model.
Every data source must be converted to clean, labeled, human-readable text before injection.

### 6.2a — Serialize Predictions

```python
def serialize_predictions(predictions: dict) -> str:
    lines = ["=== AQI PREDICTIONS (Next 3 Days) ==="]
    for region, vals in predictions["regions"].items():
        lines.append(
            f"• {region}: "
            f"Day+1 = {vals['day_1']} AQI ({vals['category'][0]}), "
            f"Day+2 = {vals['day_2']} AQI ({vals['category'][1]}), "
            f"Day+3 = {vals['day_3']} AQI ({vals['category'][2]})"
        )
    # Add trend direction per region
    for region, vals in predictions["regions"].items():
        d1, d2, d3 = vals['day_1'], vals['day_2'], vals['day_3']
        if d3 > d1 + 10:
            trend = "WORSENING over 3 days"
        elif d3 < d1 - 10:
            trend = "IMPROVING over 3 days"
        else:
            trend = "STABLE over 3 days"
        lines.append(f"  → {region} trend: {trend} ({d1} → {d2} → {d3})")
    lines.append(f"\nPrediction date: {predictions['prediction_date']}")
    return "\n".join(lines)
```

### 6.2b — Serialize SHAP Values

```python
def serialize_shap(shap_outputs: list) -> str:
    lines = ["=== SHAP FEATURE CONTRIBUTIONS (Day+1 Predictions) ==="]
    for entry in shap_outputs:
        lines.append(
            f"\nRegion: {entry['region']} | "
            f"Base AQI: {entry['base_value']:.1f} → Predicted: {entry['predicted_value']}"
        )
        lines.append("  Features driving AQI UP (positive SHAP):")
        pos = [f for f in entry['top_features'] if f['shap_value'] > 0]
        neg = [f for f in entry['top_features'] if f['shap_value'] <= 0]
        for feat in pos:
            lines.append(
                f"    ↑ {feat['feature']}: observed={feat['actual_value']}, "
                f"SHAP={feat['shap_value']:+.2f} (pushes AQI higher)"
            )
        lines.append("  Features reducing AQI (negative SHAP):")
        for feat in neg:
            lines.append(
                f"    ↓ {feat['feature']}: observed={feat['actual_value']}, "
                f"SHAP={feat['shap_value']:+.2f} (reduces AQI)"
            )
    return "\n".join(lines)
```

### 6.2c — Serialize Counterfactuals

```python
def serialize_counterfactuals(cf_outputs: list) -> str:
    lines = ["=== COUNTERFACTUAL (WHAT-IF) SCENARIOS ==="]
    for entry in cf_outputs:
        lines.append(
            f"\nRegion: {entry['region']} | "
            f"Original AQI: {entry['original_day1_aqi']} ({entry['original_category']})"
        )
        for s in entry['scenarios']:
            feat_changes = ", ".join([
                f"{k}: {entry.get('original_feature_values', {}).get(k, '?')} → {v}"
                for k, v in s['counterfactual_feature_values'].items()
            ])
            lines.append(
                f"  [{s['type'].upper()}] {s['name']}: "
                f"Change ({feat_changes}) → "
                f"New AQI = {s['new_aqi']} ({s['new_category']}) | "
                f"Reduction: {s['aqi_reduction']} pts ({s['percent_improvement']})"
            )
    return "\n".join(lines)
```

### 6.2d — Season Context Injection

Season dramatically affects atmospheric chemistry. Auto-detect it from the prediction date:

```python
def get_season_context(prediction_date: str) -> str:
    month = int(prediction_date.split("-")[1])
    season_map = {
        (10, 11, 12, 1): (
            "WINTER POLLUTION SEASON (Oct–Jan) — HIGHEST RISK PERIOD.\n"
            "Key drivers: Stubble burning in Punjab/Haryana (Oct–Nov), strong nocturnal boundary "
            "layer compression, thermal inversion trapping pollutants near ground level, "
            "low wind speeds, low mixing height (~200–400m vs ~1500m in summer), "
            "increased biomass burning and indoor heating. "
            "GRAP emergency thresholds frequently breached during this period."
        ),
        (2, 3): (
            "LATE WINTER / SPRING TRANSITION (Feb–Mar) — IMPROVING.\n"
            "Stubble burning largely ended, westerly winds improving dispersion, "
            "boundary layer height gradually increasing, AQI typically declining from winter peaks."
        ),
        (4, 5, 6): (
            "PRE-MONSOON / SUMMER (Apr–Jun) — DUST DOMINANT.\n"
            "Dust storms (andhi) from Rajasthan elevate PM10 significantly, "
            "high surface temperatures increase photochemical ozone formation, "
            "low relative humidity, occasional thunderstorms provide partial washout."
        ),
        (7, 8, 9): (
            "MONSOON SEASON (Jul–Sep) — LOWEST AQI PERIOD.\n"
            "Rainfall wet deposition removes particulate matter, high humidity, "
            "increased mixing, lowest PM2.5/PM10 of the year. "
            "If AQI is elevated during monsoon, likely localized emission source issue."
        ),
    }
    for months, desc in season_map.items():
        if month in months:
            return f"=== CURRENT SEASON CONTEXT ===\n{desc}"
    return ""
```

---

## Step 6.3 — System Prompt (Scientific Persona)

This prompt defines **who Gemini is** during this call. Precision here directly determines explanation quality.

```python
SYSTEM_PROMPT = """
You are a senior atmospheric chemist and environmental scientist with 20 years of 
expertise in urban air quality in South Asian megacities, specializing in Delhi, India.

YOUR DEEP KNOWLEDGE INCLUDES:
- Delhi's emission sources: vehicular exhaust (NCR fleet ~12 million vehicles), 
  industrial zones (Anand Parbat, Bawana, Okhla, Patparganj), crop residue burning 
  in Punjab/Haryana (Oct–Nov), construction dust, waste burning at Bhalswa/Ghazipur, 
  road dust resuspension, secondary aerosol formation
- Atmospheric chemistry: PM2.5/PM10 nucleation and condensation, secondary organic 
  aerosol (SOA) formation, NOx-VOC photochemical cycles, SO2 oxidation to sulfate, 
  thermal inversion mechanics, nocturnal boundary layer compression, planetary 
  boundary layer (PBL) height effects on pollutant concentration
- India's CPCB AQI standard: Good (0–50), Satisfactory (51–100), Moderate (101–200), 
  Poor (201–300), Very Poor (301–400), Severe (401–500)
- GRAP (Graded Response Action Plan): Stage I (201–300), Stage II (301–400), 
  Stage III (401–450), Stage IV (>450) — and what actions each stage triggers
- Delhi's geography: how Aravalli ridge affects South/West Delhi wind patterns, 
  how Yamuna floodplain affects East Delhi humidity and fog formation, 
  how Central Delhi's heat island effect elevates ozone
- Health impacts by AQI level and vulnerable populations: children (<14), elderly 
  (>65), cardiopulmonary patients, outdoor workers, pregnant women

YOUR TASK:
Analyze the AQI prediction data, SHAP feature attributions, and counterfactual 
scenarios provided. Generate a rigorous scientific report in EXACTLY the following 
5-section JSON format. Output ONLY valid JSON — no preamble, no explanation, 
no markdown fences, no text outside the JSON object.

STRICT RULES:
1. Reference actual numbers from the data — never invent or approximate figures
2. Cite specific SHAP values when explaining drivers (e.g., "PM2.5 SHAP=+28.4 indicates...")
3. Reference specific counterfactual scenarios by name and their AQI delta
4. Use correct atmospheric science terminology — avoid vague phrases like "pollution is high"
5. Assess counterfactual feasibility: is the required feature change physically achievable 
   in 24–72 hours, and what specific policy mechanism (GRAP action, odd-even, industrial 
   shutdown, construction ban) could produce it?
6. Explain inter-region differences using geographic and emission-source reasoning
7. If AQI trend is worsening Day+1→Day+3, explain the likely atmospheric mechanism

REQUIRED OUTPUT FORMAT (valid JSON, all 5 keys present, no extras):
{
  "prediction_explanation": "Scientific narrative of the 3-day AQI forecast for all regions. Explain the trend direction, atmospheric conditions driving it, and regional differences. Min 150 words.",
  "shap_interpretation": "For each region, explain what each top SHAP feature means atmospherically. Why is PM2.5/NO2/etc at this level? What emission sources explain it? What atmospheric condition explains the negative SHAP features? Min 150 words.",
  "counterfactual_analysis": "For each scenario, explain: (1) what the AQI reduction means in category terms, (2) whether the required feature change is physically realistic in 24-72 hours, (3) which specific GRAP action or policy could achieve it. Identify the single best intervention. Min 150 words.",
  "health_impact_summary": "For the predicted AQI levels, specify exact health risks using CPCB categories. List specific vulnerable groups, recommended protective actions, and whether GRAP emergency protocols should be triggered. Min 100 words.",
  "recommended_intervention": "Single clearest policy recommendation based on counterfactual results. Name the specific intervention, the expected AQI reduction in points and percentage, which region benefits most, and the GRAP stage it would help avoid or exit. Min 80 words."
}
"""
```

---

## Step 6.4 — Full Prompt Construction

```python
def build_full_prompt(predictions: dict, shap_outputs: list,
                      cf_outputs: list) -> str:
    season_text = get_season_context(predictions["prediction_date"])
    pred_text   = serialize_predictions(predictions)
    shap_text   = serialize_shap(shap_outputs)
    cf_text     = serialize_counterfactuals(cf_outputs)

    user_data = f"""
{season_text}

{pred_text}

{shap_text}

{cf_text}

INSTRUCTIONS:
- Analyze ALL regions individually — do not generalize
- Ground every claim in the numbers above
- Output only the JSON object as specified in your instructions
"""
    # Combine system prompt + user data in a single string
    # (gemini-1.5-pro handles system+user combined as one prompt)
    return SYSTEM_PROMPT + "\n\n" + user_data
```

---

## Step 6.5 — Output Parsing

```python
def parse_gemini_response(raw_text: str) -> dict:
    """
    Parses Gemini's raw text response into a clean Python dict.
    Handles accidental markdown fences and whitespace.
    """
    cleaned = raw_text.strip()

    # Strip markdown fences if Gemini accidentally added them
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()

    # Parse JSON
    explanation = json.loads(cleaned)
    return explanation
```

---

## Step 6.6 — Output Validation & Auto-Retry (The Key New Addition)

This is the layer that guarantees quality. After every Gemini call, run structured tests.
If tests fail, automatically regenerate with a corrective prompt. Max 3 attempts total.

### Validation Rules

```python
REQUIRED_KEYS = [
    "prediction_explanation",
    "shap_interpretation",
    "counterfactual_analysis",
    "health_impact_summary",
    "recommended_intervention"
]

# Minimum character length per section (too short = hallucination or truncation)
MIN_SECTION_LENGTH = {
    "prediction_explanation":  400,
    "shap_interpretation":     400,
    "counterfactual_analysis": 400,
    "health_impact_summary":   250,
    "recommended_intervention":200
}

def validate_gemini_output(explanation: dict, predictions: dict,
                            shap_outputs: list, cf_outputs: list) -> list:
    """
    Returns a list of validation failure strings.
    Empty list = all tests passed.
    """
    failures = []

    # TEST 1: All 5 required keys present
    for key in REQUIRED_KEYS:
        if key not in explanation:
            failures.append(f"MISSING_KEY: '{key}' not found in output")

    # Stop here if keys are missing — further tests would crash
    if failures:
        return failures

    # TEST 2: No section is empty or below minimum length
    for key, min_len in MIN_SECTION_LENGTH.items():
        actual_len = len(explanation.get(key, ""))
        if actual_len < min_len:
            failures.append(
                f"TOO_SHORT: '{key}' is {actual_len} chars, minimum is {min_len}"
            )

    # TEST 3: prediction_explanation must reference actual AQI numbers from the data
    overall_d1 = str(predictions["regions"]["Overall Delhi"]["day_1"])
    if overall_d1 not in explanation["prediction_explanation"]:
        failures.append(
            f"NOT_GROUNDED: 'prediction_explanation' does not reference "
            f"Overall Delhi Day+1 AQI value ({overall_d1})"
        )

    # TEST 4: shap_interpretation must mention at least one feature name from SHAP data
    if shap_outputs:
        top_feature = shap_outputs[0]["top_features"][0]["feature"]  # e.g. "PM2.5"
        if top_feature not in explanation["shap_interpretation"]:
            failures.append(
                f"NOT_GROUNDED: 'shap_interpretation' does not mention "
                f"top SHAP feature '{top_feature}'"
            )

    # TEST 5: counterfactual_analysis must mention at least one scenario
    if cf_outputs and cf_outputs[0]["scenarios"]:
        scenario_name = cf_outputs[0]["scenarios"][0]["name"]
        # Check for key feature name from first scenario instead of exact name
        first_feature = cf_outputs[0]["scenarios"][0]["features_varied"][0]
        if first_feature not in explanation["counterfactual_analysis"]:
            failures.append(
                f"NOT_GROUNDED: 'counterfactual_analysis' does not reference "
                f"counterfactual feature '{first_feature}'"
            )

    # TEST 6: recommended_intervention must not be generic filler
    generic_phrases = [
        "reduce pollution", "improve air quality", "take action",
        "further analysis needed", "consult experts"
    ]
    rec = explanation["recommended_intervention"].lower()
    generic_count = sum(1 for phrase in generic_phrases if phrase in rec)
    if generic_count >= 2:
        failures.append(
            "GENERIC_OUTPUT: 'recommended_intervention' appears to be generic "
            "filler rather than data-grounded recommendation"
        )

    # TEST 7: No section should contain placeholder text
    placeholder_indicators = ["[insert", "[add", "...", "placeholder", "TODO"]
    for key in REQUIRED_KEYS:
        for indicator in placeholder_indicators:
            if indicator.lower() in explanation[key].lower():
                failures.append(
                    f"PLACEHOLDER_DETECTED: '{key}' contains '{indicator}'"
                )

    return failures
```

### Auto-Retry with Corrective Prompt

```python
def generate_with_validation(predictions: dict, shap_outputs: list,
                              cf_outputs: list, max_attempts: int = 3) -> tuple:
    """
    Calls Gemini, validates output, retries with corrective prompt if needed.

    Returns:
        (explanation_dict, attempt_number, final_validation_failures)
    """
    base_prompt = build_full_prompt(predictions, shap_outputs, cf_outputs)

    for attempt in range(1, max_attempts + 1):
        print(f"[Gemini] Generation attempt {attempt}/{max_attempts}...")

        try:
            if attempt == 1:
                prompt = base_prompt
            else:
                # Corrective prompt: tell Gemini exactly what it did wrong
                prompt = build_corrective_prompt(
                    base_prompt, previous_failures, previous_raw_output
                )

            raw_output = call_gemini_with_retry(prompt)
            previous_raw_output = raw_output

        except RuntimeError as e:
            print(f"[Gemini] API call failed on attempt {attempt}: {e}")
            if attempt == max_attempts:
                raise
            continue

        # Parse JSON
        try:
            explanation = parse_gemini_response(raw_output)
        except json.JSONDecodeError as e:
            previous_failures = [f"JSON_PARSE_ERROR: {e}. Raw output was not valid JSON."]
            print(f"[Gemini] JSON parse failed: {e}")
            if attempt == max_attempts:
                raise ValueError(f"Gemini failed to produce valid JSON after {max_attempts} attempts")
            continue

        # Validate
        failures = validate_gemini_output(
            explanation, predictions, shap_outputs, cf_outputs
        )

        if not failures:
            print(f"[Gemini] ✓ All validation tests passed on attempt {attempt}")
            return explanation, attempt, []
        else:
            previous_failures = failures
            print(f"[Gemini] ✗ Attempt {attempt} failed {len(failures)} validation test(s):")
            for f in failures:
                print(f"    - {f}")
            if attempt == max_attempts:
                print(f"[Gemini] WARNING: Returning best attempt despite {len(failures)} failure(s)")
                return explanation, attempt, failures

    # Should never reach here
    raise RuntimeError("Unexpected exit from retry loop")
```

### Corrective Prompt Builder

```python
def build_corrective_prompt(base_prompt: str, failures: list,
                             previous_output: str) -> str:
    failure_text = "\n".join([f"  - {f}" for f in failures])
    return f"""
{base_prompt}

---
CORRECTION REQUIRED:
Your previous response failed the following quality checks:
{failure_text}

Your previous response was:
{previous_output}

Please regenerate the complete JSON response, fixing all the issues listed above.
Remember: output ONLY the JSON object. No preamble, no markdown, no explanation.
Ground every section in the actual numbers provided in the data above.
"""
```

---

## Step 6.7 — Save Daily Result

```python
def save_daily_result(predictions: dict, shap_outputs: list,
                      cf_outputs: list, explanation: dict,
                      attempt_count: int, validation_warnings: list,
                      output_path: str = "outputs/latest_result.json"):
    """
    Saves all pipeline outputs + Gemini explanation to a single JSON file.
    This is the ONLY file the Streamlit app reads.
    """
    result = {
        "date":               predictions["prediction_date"],
        "pipeline_ran_at":    datetime.now().isoformat(),
        "gemini_model_used":  GEMINI_MODEL,
        "gemini_attempts":    attempt_count,
        "validation_warnings": validation_warnings,   # empty list = fully passed
        "predictions":        predictions,
        "shap":               shap_outputs,
        "counterfactuals":    cf_outputs,
        "explanation":        explanation
    }

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[Pipeline] Saved latest result to {output_path}")
    return output_path
```

---

## Step 6.8 — Master Daily Pipeline Orchestrator

This is the single function you run every time new CSV data arrives.

```python
# run_daily_pipeline.py

from pipeline.data_loader         import load_live_data
from pipeline.feature_engineering import run_feature_engineering
from pipeline.model_predict        import generate_predictions
from pipeline.shap_analysis        import run_shap_analysis
from pipeline.counterfactual       import run_counterfactuals
from pipeline.gemini_explainer     import (generate_with_validation,
                                            save_daily_result)

def run_daily_pipeline(new_csv_path: str):
    print(f"\n{'='*60}")
    print(f"DAILY PIPELINE START — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input: {new_csv_path}")
    print(f"{'='*60}\n")

    # Step 1: Data
    print("[1/6] Loading and engineering features...")
    live_data = load_live_data(new_csv_path)
    features  = run_feature_engineering(live_data)

    # Step 2: Predictions
    print("[2/6] Generating 1-3 day predictions (18 models)...")
    predictions = generate_predictions(features)

    # Step 3: SHAP
    print("[3/6] Running SHAP analysis...")
    shap_outputs = run_shap_analysis(features, predictions)

    # Step 4: Counterfactuals
    print("[4/6] Running DiCE counterfactual scenarios...")
    cf_outputs = run_counterfactuals(features, shap_outputs)

    # Step 5: Gemini (with validation + auto-retry)
    print("[5/6] Calling Gemini API for scientific explanation...")
    explanation, attempts, warnings = generate_with_validation(
        predictions, shap_outputs, cf_outputs, max_attempts=3
    )

    # Step 6: Save
    print("[6/6] Saving all outputs to latest_result.json...")
    output_path = save_daily_result(
        predictions, shap_outputs, cf_outputs,
        explanation, attempts, warnings
    )

    # Final status report
    print(f"\n{'='*60}")
    print(f"PIPELINE COMPLETE")
    print(f"  Gemini attempts used:   {attempts}/3")
    print(f"  Validation warnings:    {len(warnings)}")
    if warnings:
        for w in warnings:
            print(f"    ⚠  {w}")
    else:
        print(f"    ✓ All validation tests passed")
    print(f"  Output saved to:        {output_path}")
    print(f"  Web app will now serve fresh data instantly.")
    print(f"{'='*60}\n")

    return output_path


if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "data/raw/latest_live_data.csv"
    run_daily_pipeline(csv_path)
```

**Run it:**
```bash
python run_daily_pipeline.py data/raw/2024_01_15_live.csv
```

---

## Step 6.9 — Streamlit App: Instant Read (Zero Latency)

The web app **never calls Gemini**. It only reads the JSON file saved by Step 6.8.

```python
# streamlit_app.py — AI Explanation page

import json, streamlit as st
from datetime import datetime
from config import LATEST_RESULT_PATH, STALENESS_HOURS

@st.cache_data(ttl=300)  # Cache for 5 minutes, then re-read file
def load_latest_result():
    try:
        with open(LATEST_RESULT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def render_explanation_page():
    result = load_latest_result()

    if result is None:
        st.error("No explanation data found. Run the daily pipeline first.")
        st.code("python run_daily_pipeline.py data/raw/latest.csv")
        return

    explanation = result["explanation"]

    # ── Header with freshness indicator ──────────────────────────
    ran_at    = datetime.fromisoformat(result["pipeline_ran_at"])
    age_hours = (datetime.now() - ran_at).total_seconds() / 3600
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🤖 AI Scientific Explanation")
        st.caption(
            f"Generated: {ran_at.strftime('%d %b %Y, %I:%M %p')} | "
            f"Model: {result.get('gemini_model_used', 'gemini-1.5-pro')} | "
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
    st.write(explanation["prediction_explanation"])
    st.divider()

    # ── Section 2: SHAP Interpretation ───────────────────────────
    st.subheader("🔍 Why These Predictions? (SHAP Analysis)")
    st.write(explanation["shap_interpretation"])
    st.divider()

    # ── Section 3: Counterfactual Analysis ───────────────────────
    st.subheader("🔄 What-If Scenario Analysis")
    st.write(explanation["counterfactual_analysis"])
    st.divider()

    # ── Section 4: Health Impact ──────────────────────────────────
    st.subheader("🏥 Health Impact Summary")
    st.write(explanation["health_impact_summary"])
    st.divider()

    # ── Section 5: Recommended Intervention ──────────────────────
    st.subheader("✅ Recommended Intervention")
    st.info(explanation["recommended_intervention"])
```

---

## Step 6.10 — Validation Test Matrix (Complete Reference)

| Test ID | What it checks | Failure means | Action on failure |
|---|---|---|---|
| `MISSING_KEY` | All 5 JSON keys present | JSON structure wrong | Auto-retry with corrective prompt |
| `TOO_SHORT` | Each section ≥ min length | Truncated or empty response | Auto-retry |
| `NOT_GROUNDED_PRED` | prediction_explanation contains actual AQI number | Hallucinating numbers | Auto-retry |
| `NOT_GROUNDED_SHAP` | shap_interpretation mentions top feature name | Ignoring SHAP data | Auto-retry |
| `NOT_GROUNDED_CF` | counterfactual_analysis mentions feature from first scenario | Ignoring CF data | Auto-retry |
| `GENERIC_OUTPUT` | recommended_intervention is specific, not filler | Generic useless output | Auto-retry |
| `PLACEHOLDER_DETECTED` | No `[insert...]` or `TODO` patterns | Incomplete generation | Auto-retry |
| `JSON_PARSE_ERROR` | Response is valid JSON | Markdown fences or text outside JSON | Auto-retry with explicit reminder |

**Maximum 3 attempts. On 3rd attempt, save best result with warnings logged.**

---

## File Structure for Phase 6

```
delhi_aqi_system/
├── pipeline/
│   └── gemini_explainer.py      ← All Step 6.1–6.7 code lives here
├── run_daily_pipeline.py        ← Step 6.8 master orchestrator (you run this)
├── streamlit_app.py             ← Step 6.9 reads latest_result.json (users see this)
├── config.py                    ← API key, model name, paths, thresholds
├── .env                         ← GEMINI_API_KEY (never commit to git)
└── outputs/
    └── latest_result.json       ← The single file connecting pipeline to web app
```

---

## Summary of Design Decisions

| Decision | Reason |
|---|---|
| Pre-computation (run daily, not on user request) | Zero latency for users; single API call per day |
| `gemini-1.5-pro` for explanation (not Flash) | This is complex multi-data synthesis — quality matters here |
| `temperature=0.2` | Forces factual, reproducible outputs; prevents creative drift |
| Serialization before prompt injection | Clean labeled text produces far better explanations than raw JSON |
| Season context auto-injection | Month-aware context dramatically improves atmospheric reasoning quality |
| 7 structured validation tests | Catches missing keys, truncation, hallucination, and generic outputs |
| Auto-retry with corrective prompt | Tells Gemini exactly what it did wrong so it can fix it specifically |
| `latest_result.json` as single source of truth | One file, one read, instant display — clean separation of concerns |
| Staleness detection in Streamlit | Users always know if they're seeing today's or yesterday's data |
