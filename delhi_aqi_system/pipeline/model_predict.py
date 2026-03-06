import pandas as pd
import numpy as np
import joblib
import os
import json
import logging
from datetime import datetime
from data_loader import load_live_data
from feature_engineering import engineer_features

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_aqi_category(aqi: float) -> str:
    """Categorize AQI based on standard thresholds."""
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Satisfactory"
    elif aqi <= 200: return "Moderate"
    elif aqi <= 300: return "Poor"
    elif aqi <= 400: return "Very Poor"
    else: return "Severe"

def predict_future_days(live_data_path: str, models_path: str, output_dir: str):
    """
    Predicts Day+1, Day+2, Day+3 AQI for each region and Overall Delhi using the Direct Multi-Output strategy.
    Loads 18 individual models and applies them to the current live data feature snapshot.
    """
    os.makedirs(output_dir, exist_ok=True)
    logging.info("Loading models...")
    all_models = joblib.load(models_path)
    
    logging.info(f"Loading live data context from {live_data_path}...")
    df_raw = load_live_data(live_data_path)
    
    # Identify unique regions
    regions = [r for r in df_raw['region_name'].unique()]
    specific_regions = [r for r in regions if r != 'Overall Delhi']
    
    # Ensure "Overall Delhi" is in the loop if models exist for it
    if "Overall Delhi" in all_models and "Overall Delhi" not in regions:
        regions.append("Overall Delhi")
    
    # Determine feature names from one of the models
    # Check "North Delhi" specifically as it's a reliable key name in your training script
    model_keys = list(all_models.keys())
    first_region = "North Delhi" if "North Delhi" in all_models else model_keys[0]
    
    model_ref = all_models[first_region]['day_1']
    if not hasattr(model_ref, 'feature_names_in_'):
        raise ValueError("Model missing feature_names_in_. Retrain with named DataFrame.")
    expected_features = model_ref.feature_names_in_
    
    # Prepare features for the most recent timestamp available
    last_date = df_raw['datetime'].max()
    df_recent = df_raw[df_raw['datetime'] == last_date].copy()
    
    # Run feature engineering on the recent window to get latest lags/rolling means
    # We take enough trailing data to compute features correctly
    cutoff_date = last_date - pd.Timedelta(days=14)
    df_context = df_raw[df_raw['datetime'] >= cutoff_date].copy()
    df_feats = engineer_features(df_context)
    
    # NaN check after feature engineering
    nan_cols = [col for col in expected_features if col in df_feats.columns and df_feats[col].isna().any()]
    if nan_cols:
        logging.warning(f"NaN in features: {nan_cols} — filling with 0")
        df_feats[nan_cols] = df_feats[nan_cols].fillna(0)
    
    # Get the feature rows for the very last date
    latest_feats = df_feats[df_feats['datetime'] == last_date]
    
    # Initialize output structure
    predictions_output = {}
    
    for r in regions:
        display_name = r if "Delhi" in r else f"{r} Delhi"
        # The trained model dict keys are usually "North Delhi", "South Delhi", etc.
        # Check against available keys in all_models
        model_key = display_name
        if model_key not in all_models:
            # Fallback for name variations
            alternative_keys = [k for k in all_models.keys() if r.lower() in k.lower()]
            if alternative_keys:
                model_key = alternative_keys[0]
            else:
                logging.warning(f"No model found for region: {r}. Skipping.")
                continue

        predictions_output[display_name] = {"day_1": 0, "day_2": 0, "day_3": 0, "category": []}
        
        # Get features for this specific region
        region_feat_row = latest_feats[latest_feats['region_name'] == r].copy()
        
        if region_feat_row.empty and r == 'Overall Delhi':
            # Compute Overall Delhi features as average of all specific regions
            region_feat_row = latest_feats[latest_feats['region_name'].isin(specific_regions)].mean(numeric_only=True).to_frame().T
        
        if region_feat_row.empty:
            logging.warning(f"No features found for region {r} at {last_date}")
            continue

        # Prepare X vector
        X = region_feat_row[[col for col in expected_features if col in region_feat_row.columns]].copy()
        for col in expected_features:
            if col not in X.columns:
                X[col] = 0
        X = X[expected_features].astype(float)
        
        # Predict for each of the 3 independent horizons
        for step in range(1, 4):
            model = all_models[model_key][f"day_{step}"]
            pred_aqi = float(model.predict(X)[0])
            
            predictions_output[display_name][f"day_{step}"] = round(pred_aqi, 2)
            predictions_output[display_name]["category"].append(get_aqi_category(pred_aqi))
            
    output = {
        "prediction_date_start": (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "regions": predictions_output
    }
    
    out_file = os.path.join(output_dir, 'predictions_3day.json')
    with open(out_file, 'w') as f:
        json.dump(output, f, indent=2)
        
    logging.info(f"✅ 3-Day Forecast JSON successfully generated (Direct Multi-Output) and saved to {out_file}")
    print("\n--- 3-Day Forecast JSON Output ---")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Use live_data.csv if exists, else fallback to main dataset last row
    live_data_path = os.path.join(base_dir, 'data', 'raw', 'live_data.csv')
    if not os.path.exists(live_data_path):
        live_data_path = os.path.join(base_dir, 'Delhi_AQI_final.csv')
        
    models_path = os.path.join(base_dir, 'models', 'saved', 'delhi_aqi_all_regions.pkl')
    output_dir = os.path.join(base_dir, 'outputs', 'predictions')
    
    logging.info("Starting Direct 3-day forecasting...")
    predict_future_days(live_data_path, models_path, output_dir)
