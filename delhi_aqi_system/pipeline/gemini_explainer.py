import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import time, json, os
from datetime import datetime

# Configure standard path to import config
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import (GCP_PROJECT, GCP_LOCATION, GEMINI_MODEL, GEMINI_TEMPERATURE,
                    GEMINI_MAX_TOKENS, GEMINI_TOP_P, MAX_RETRIES)

# Initialize Vertex AI
vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)

model = GenerativeModel(
    model_name=GEMINI_MODEL,
    generation_config=GenerationConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_TOKENS,
        top_p=GEMINI_TOP_P
    )
)

def call_gemini_with_retry(prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """
    Calls Gemini API with exponential backoff on failure.
    Waits: 2s -> 4s -> 8s between retries.
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
        lines.append(f"  -> {region} trend: {trend} ({d1} -> {d2} -> {d3})")
    lines.append(f"\nPrediction date: {predictions.get('prediction_date', predictions.get('prediction_date_start', 'Unknown'))}")
    return "\n".join(lines)

def serialize_shap(shap_outputs: list) -> str:
    lines = ["=== SHAP FEATURE CONTRIBUTIONS (Day+1 Predictions) ==="]
    for entry in shap_outputs:
        lines.append(
            f"\nRegion: {entry['region']} | "
            f"Base AQI: {entry['base_value']:.1f} -> Predicted: {entry['predicted_value']}"
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

def serialize_counterfactuals(cf_outputs: list) -> str:
    lines = ["=== COUNTERFACTUAL (WHAT-IF) SCENARIOS ==="]
    for entry in cf_outputs:
        lines.append(
            f"\nRegion: {entry['region']} | "
            f"Original AQI: {entry['original_day1_aqi']} ({entry['original_category']})"
        )
        for s in entry['scenarios']:
            # Adjust to original phase 5 variable names
            feat_changes = ", ".join([
                f"{k}: {entry.get('original_feature_values', {}).get(k, '?')} -> {v}"
                for k, v in s.get('perturbed_feature_values', s.get('perturbed_feature_value', {})).items()
            ])
            if not feat_changes: # Fall back logic
                feat_changes = str(s.get('feature_changes', {}))
                
            lines.append(
                f"  [{s['type'].upper()}] {s['name']}: "
                f"Change ({feat_changes}) -> "
                f"New AQI = {s['new_aqi']} ({s['new_category']}) | "
                f"Reduction: {s['aqi_reduction']} pts ({s['percent_improvement']})"
            )
    return "\n".join(lines)

def get_season_context(prediction_date: str) -> str:
    try:
        month = int(prediction_date.split("-")[1])
    except Exception:
        # Default to January if parsing fails
        month = 1
        
    season_map = {
        (10, 11, 12, 1): (
            "WINTER POLLUTION SEASON (Oct-Jan) -- HIGHEST RISK PERIOD.\n"
            "Key drivers: Stubble burning in Punjab/Haryana (Oct-Nov), strong nocturnal boundary "
            "layer compression, thermal inversion trapping pollutants near ground level, "
            "low wind speeds, low mixing height (~200-400m vs ~1500m in summer), "
            "increased biomass burning and indoor heating. "
            "GRAP emergency thresholds frequently breached during this period."
        ),
        (2, 3): (
            "LATE WINTER / SPRING TRANSITION (Feb-Mar) -- IMPROVING.\n"
            "Stubble burning largely ended, westerly winds improving dispersion, "
            "boundary layer height gradually increasing, AQI typically declining from winter peaks."
        ),
        (4, 5, 6): (
            "PRE-MONSOON / SUMMER (Apr-Jun) -- DUST DOMINANT.\n"
            "Dust storms (andhi) from Rajasthan elevate PM10 significantly, "
            "high surface temperatures increase photochemical ozone formation, "
            "low relative humidity, occasional thunderstorms provide partial washout."
        ),
        (7, 8, 9): (
            "MONSOON SEASON (Jul-Sep) -- LOWEST AQI PERIOD.\n"
            "Rainfall wet deposition removes particulate matter, high humidity, "
            "increased mixing, lowest PM2.5/PM10 of the year. "
            "If AQI is elevated during monsoon, likely localized emission source issue."
        ),
    }
    for months, desc in season_map.items():
        if month in months:
            return f"=== CURRENT SEASON CONTEXT ===\n{desc}"
    return ""

SYSTEM_PROMPT = """
You are a senior atmospheric chemist and environmental scientist with 20 years of 
expertise in urban air quality in South Asian megacities, specializing in Delhi, India.

YOUR DEEP KNOWLEDGE INCLUDES:
- Delhi's emission sources: vehicular exhaust (NCR fleet ~12 million vehicles), 
  industrial zones (Anand Parbat, Bawana, Okhla, Patparganj), crop residue burning 
  in Punjab/Haryana (Oct-Nov), construction dust, waste burning at Bhalswa/Ghazipur, 
  road dust resuspension, secondary aerosol formation
- Atmospheric chemistry: PM2.5/PM10 nucleation and condensation, secondary organic 
  aerosol (SOA) formation, NOx-VOC photochemical cycles, SO2 oxidation to sulfate, 
  thermal inversion mechanics, nocturnal boundary layer compression, planetary 
  boundary layer (PBL) height effects on pollutant concentration
- India's CPCB AQI standard: Good (0-50), Satisfactory (51-100), Moderate (101-200), 
  Poor (201-300), Very Poor (301-400), Severe (401-500)
- GRAP (Graded Response Action Plan): Stage I (201-300), Stage II (301-400), 
  Stage III (401-450), Stage IV (>450) -- and what actions each stage triggers
- Delhi's geography: how Aravalli ridge affects South/West Delhi wind patterns, 
  how Yamuna floodplain affects East Delhi humidity and fog formation, 
  how Central Delhi's heat island effect elevates ozone
- Health impacts by AQI level and vulnerable populations: children (<14), elderly 
  (>65), cardiopulmonary patients, outdoor workers, pregnant women

YOUR TASK:
Analyze the AQI prediction data, SHAP feature attributions, and counterfactual 
scenarios provided. Generate a rigorous scientific report in EXACTLY the following 
5-section JSON format. Output ONLY valid JSON -- no preamble, no explanation, 
no markdown fences, no text outside the JSON object.

STRICT RULES:
1. Use simple, non-scientific language for the general public.
2. Always use a bulleted list for every section (starting with "- ").
3. Provide FEWER bullet points (3-4 per section).
4. Make each bullet point DETAILED and COMPREHENSIVE ("big explanation").
5. Use actual numbers from the data for credibility.
6. Avoid long technical jargon; explain concepts simply.

REQUIRED OUTPUT FORMAT (valid JSON, all 5 keys present, no extras):
{
  "prediction_explanation": "Detailed 3-day forecast summary. Explain the trend for all regions with depth. Use 3-4 detailed bullets. Max 150 words.",
  "shap_interpretation": "Detailed list of why AQI is what it is. Explain major factors (PM2.5, NO2, Weather) with simple depth. Use 3-4 detailed bullets. Max 150 words.",
  "counterfactual_analysis": "Detailed comparison of what-if scenarios. Explain the impact of different actions thoroughly. Use 3 detailed bullets. Max 120 words.",
  "health_impact_summary": "Detailed health advice for different groups. Explain risks and actions with clarity and depth. Use 3 detailed bullets. Max 100 words.",
  "recommended_intervention": "Detailed action plan. Explain exactly what steps to take and why. Use 2-3 detailed bullets. Max 80 words."
}
"""

def build_full_prompt(predictions: dict, shap_outputs: list,
                      cf_outputs: list) -> str:
    pred_date = predictions.get("prediction_date", predictions.get("prediction_date_start", ""))
    season_text = get_season_context(pred_date)
    pred_text   = serialize_predictions(predictions)
    shap_text   = serialize_shap(shap_outputs)
    cf_text     = serialize_counterfactuals(cf_outputs)

    user_data = f"""
{season_text}

{pred_text}

{shap_text}

{cf_text}

INSTRUCTIONS:
- Analyze ALL regions individually -- do not generalize
- Ground every claim in the numbers above
- Output only the JSON object as specified in your instructions
"""
    return SYSTEM_PROMPT + "\n\n" + user_data

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

REQUIRED_KEYS = [
    "prediction_explanation",
    "shap_interpretation",
    "counterfactual_analysis",
    "health_impact_summary",
    "recommended_intervention"
]

# Minimum character length per section (Adjusted for detailed bullets)
MIN_SECTION_LENGTH = {
    "prediction_explanation":  350,
    "shap_interpretation":     350,
    "counterfactual_analysis": 300,
    "health_impact_summary":   200,
    "recommended_intervention":150
}

def get_feature_variations(feature: str) -> list:
    """
    Returns a list of common variations of a feature name
    so validation is case-insensitive and format-flexible.
    e.g. 'pm25' -> ['pm25', 'PM25', 'PM2.5', 'pm2.5']
    """
    feature_map = {
        "pm25": ["pm25", "PM25", "PM2.5", "pm2.5", "PM 2.5"],
        "pm10": ["pm10", "PM10", "PM 10", "pm 10"],
        "no2":  ["no2",  "NO2",  "nitrogen dioxide"],
        "so2":  ["so2",  "SO2",  "sulphur dioxide", "sulfur dioxide"],
        "co":   ["co",   "CO",   "carbon monoxide"],
        "o3":   ["o3",   "O3",   "ozone"],
        "nox":  ["nox",  "NOx",  "NOX"],
    }
    key = feature.lower().replace(" ", "")
    if key in feature_map:
        return feature_map[key]
    # Fallback: return original + uppercase + lowercase
    return [feature, feature.upper(), feature.lower()]

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

    # Stop here if keys are missing -- further tests would crash
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
    if shap_outputs and len(shap_outputs) > 0 and len(shap_outputs[0].get("top_features", [])) > 0:
        top_feature = shap_outputs[0]["top_features"][0]["feature"]  # e.g. "pm25"
        variations = get_feature_variations(top_feature)
        shap_text = explanation["shap_interpretation"]
        if not any(v in shap_text for v in variations):
            failures.append(
                f"NOT_GROUNDED: 'shap_interpretation' does not mention "
                f"top SHAP feature '{top_feature}'"
            )

    # TEST 5: counterfactual_analysis must mention at least one scenario feature
    if cf_outputs and len(cf_outputs) > 0 and len(cf_outputs[0].get("scenarios", [])) > 0:
        scenario_name = cf_outputs[0]["scenarios"][0]["name"]

        # Get varied features. Handle original implementation names too
        s = cf_outputs[0]["scenarios"][0]
        first_feature = ""
        if "feature_changes" in s and s["feature_changes"]:
            first_feature = list(s["feature_changes"].keys())[0]
        elif "features_varied" in s and s["features_varied"]:
            first_feature = s["features_varied"][0]

        if first_feature:
            variations = get_feature_variations(first_feature)
            cf_text = explanation["counterfactual_analysis"]
            if not any(v in cf_text for v in variations):
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
    placeholder_indicators = ["[insert", "[add", "placeholder", "TODO"]
    for key in REQUIRED_KEYS:
        for indicator in placeholder_indicators:
            if indicator.lower() in explanation[key].lower():
                failures.append(
                    f"PLACEHOLDER_DETECTED: '{key}' contains '{indicator}'"
                )

    return failures

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

def generate_with_validation(predictions: dict, shap_outputs: list,
                              cf_outputs: list, max_attempts: int = 3) -> tuple:
    """
    Calls Gemini, validates output, retries with corrective prompt if needed.

    Returns:
        (explanation_dict, attempt_number, final_validation_failures)
    """
    base_prompt = build_full_prompt(predictions, shap_outputs, cf_outputs)
    
    previous_raw_output = ""
    previous_failures = []

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
                # Provide empty structure if failing fully to not crash
                return {}, attempt, previous_failures
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

def save_daily_result(predictions: dict, shap_outputs: list,
                      cf_outputs: list, explanation: dict,
                      attempt_count: int, validation_warnings: list,
                      output_path: str = "outputs/latest_result.json"):
    """
    Saves all pipeline outputs + Gemini explanation to a single JSON file.
    This is the ONLY file the Streamlit app reads.
    """
    # Ensure relative path works
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_output_path = os.path.join(base_dir, output_path)
    
    pred_date = predictions.get("prediction_date", predictions.get("prediction_date_start", "Unknown"))
    
    result = {
        "date":               pred_date,
        "pipeline_ran_at":    datetime.now().isoformat(),
        "gemini_model_used":  GEMINI_MODEL,
        "gemini_attempts":    attempt_count,
        "validation_warnings": validation_warnings,   # empty list = fully passed
        "predictions":        predictions,
        "shap":               shap_outputs,
        "counterfactuals":    cf_outputs,
        "explanation":        explanation
    }

    os.makedirs(os.path.dirname(full_output_path), exist_ok=True)
    with open(full_output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[Pipeline] Saved latest result to {full_output_path}")
    return full_output_path