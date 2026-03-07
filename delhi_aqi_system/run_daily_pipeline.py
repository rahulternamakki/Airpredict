import os
import sys
import json
import logging
from datetime import datetime

# Adjust sys.path so modules inside pipeline/ can import each other (e.g., data_loader)
base_dir = os.path.dirname(os.path.abspath(__file__))
pipeline_dir = os.path.join(base_dir, "pipeline")
if pipeline_dir not in sys.path:
    sys.path.insert(0, pipeline_dir)

from pipeline.model_predict import predict_future_days
from pipeline.shap_analysis import perform_shap_analysis
from pipeline.counterfactual import generate_counterfactuals
from pipeline.gemini_explainer import generate_with_validation, save_daily_result

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_daily_pipeline(new_csv_path: str):
    print(f"\n{'='*60}")
    print(f"DAILY PIPELINE START — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Input: {new_csv_path}")
    print(f"{'='*60}\n")

    models_path = os.path.join(base_dir, 'models', 'saved', 'delhi_aqi_all_regions.pkl')
    output_dir_predictions = os.path.join(base_dir, 'outputs', 'predictions')
    output_dir_shap = os.path.join(base_dir, 'outputs', 'shap')
    output_dir_cf = os.path.join(base_dir, 'outputs', 'counterfactual')
    
    # Paths for generated JSONs
    predictions_file = os.path.join(output_dir_predictions, 'predictions_3day.json')
    shap_explain_file = os.path.join(output_dir_shap, 'shap_values.json')
    shap_cand_file = os.path.join(output_dir_shap, 'shap_candidates.json')
    cf_file = os.path.join(output_dir_cf, 'counterfactual_results.json')

    # Step 1: Predictions
    print("[1/5] Generating 1-3 day predictions (18 models)...")
    predict_future_days(new_csv_path, models_path, output_dir_predictions)

    # Step 2: SHAP
    print("[2/5] Running SHAP analysis...")
    perform_shap_analysis(new_csv_path, models_path, output_dir_shap)

    # Step 3: Counterfactuals
    print("[3/5] Running Counterfactual scenarios...")
    generate_counterfactuals(new_csv_path, models_path, shap_cand_file, output_dir_cf)

    # Read generated JSON files to pass to Gemini
    print("[4/5] Reading outputs for Gemini explanation...")
    with open(predictions_file, 'r', encoding='utf-8') as f:
        predictions = json.load(f)
    with open(shap_explain_file, 'r', encoding='utf-8') as f:
        shap_outputs = json.load(f)
    with open(cf_file, 'r', encoding='utf-8') as f:
        cf_outputs = json.load(f)

    # Step 4: Gemini (with validation + auto-retry)
    print("[5/5] Calling Gemini API for scientific explanation...")
    explanation, attempts, warnings = generate_with_validation(
        predictions, shap_outputs, cf_outputs, max_attempts=3
    )

    # Step 5: Save
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
    # Use live_data.csv if exists, else fallback to main dataset
    default_csv_path = os.path.join(base_dir, 'data', 'raw', 'live_data.csv')
    if not os.path.exists(default_csv_path):
        default_csv_path = os.path.join(base_dir, 'Delhi_AQI_final.csv')
        
    csv_path = sys.argv[1] if len(sys.argv) > 1 else default_csv_path
    
    run_daily_pipeline(csv_path)
