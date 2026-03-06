import pandas as pd
import numpy as np
import joblib
import os
import json
import logging
from datetime import datetime
from data_loader import load_and_validate_data
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
    Predicts Day+1, Day+2, Day+3 AQI for each region and Overall Delhi.
    Updates historical context dynamically by persisting features and predicting AQI.
    Uses `live_data_path` as the source of the recent data context (e.g. from an API).
    """
    os.makedirs(output_dir, exist_ok=True)
    logging.info("Loading models...")
    all_models = joblib.load(models_path)
    
    logging.info(f"Loading live data context from {live_data_path}...")
    df_raw = load_and_validate_data(live_data_path)
    
    regions = [r for r in df_raw['region_name'].unique() if r != 'Overall Delhi']
    
    # Take the last 14 days of data to provide enough context for rolling means and lags
    last_date = df_raw['datetime'].max()
    cutoff_date = last_date - pd.Timedelta(days=14)
    df_context = df_raw[df_raw['datetime'] >= cutoff_date].copy()
    
    # We use North Delhi to get the list of expected features as all specific regional models share the structure
    expected_features = all_models['North Delhi'].feature_names_in_
    
    # Initialize output structure
    predictions = {}
    for r in regions:
        display_name = f"{r} Delhi"
        predictions[display_name] = {"day_1": 0, "day_2": 0, "day_3": 0, "category": []}
    predictions["Overall Delhi"] = {"day_1": 0, "day_2": 0, "day_3": 0, "category": []}
    
    current_context = df_context.copy()
    
    # Predict recursively for 3 days
    for step in range(1, 4):
        next_date = last_date + pd.Timedelta(days=step)
        logging.info(f"Generating features and predicting for Day {step}: {next_date.strftime('%Y-%m-%d')}")
        
        new_rows = []
        for r in regions:
            # We copy weather/pollutants from the last available step for this region (Persistence forecasting)
            last_row = current_context[current_context['region_name'] == r].iloc[-1].copy()
            last_row['datetime'] = next_date
            last_row['AQI'] = np.nan # Must be predicted
            new_rows.append(last_row.to_frame().T)
            
        current_context = pd.concat([current_context] + new_rows, ignore_index=True)
        current_context['datetime'] = pd.to_datetime(current_context['datetime'])
        
        # Ensure sorting before running feature engineering
        current_context.sort_values(by=['region_name', 'datetime'], ascending=True, inplace=True)
        current_context.reset_index(drop=True, inplace=True)
        
        # Run feature engineering on the updated context
        df_feats = engineer_features(current_context.copy())
        
        # Extract the exact row for `next_date` which has all lag features populated
        day_df = df_feats[df_feats['datetime'] == next_date]
        
        for r in regions:
            display_name = f"{r} Delhi"
            region_df = day_df[day_df['region_name'] == r].copy()
            
            if region_df.empty:
                logging.warning(f"No features generated for {r} on {next_date}. Skipping.")
                continue
                
            X = region_df[[col for col in expected_features if col in region_df.columns]].copy()
            for col in expected_features:
                if col not in X.columns:
                    X[col] = 0
            
            X = X[expected_features].astype(float)
            pred_aqi = float(all_models[display_name].predict(X)[0])
            
            predictions[display_name][f"day_{step}"] = round(pred_aqi, 2)
            predictions[display_name]["category"].append(get_aqi_category(pred_aqi))
            
            # Write prediction back to current context so next day can use it as lag
            mask = (current_context['region_name'] == r) & (current_context['datetime'] == next_date)
            current_context.loc[mask, 'AQI'] = pred_aqi
            
        # Predict Overall Delhi (by averaging the engineered feature vectors of all regions)
        overall_features_df = day_df[day_df['region_name'].isin(regions)].mean(numeric_only=True).to_frame().T
        X_overall = overall_features_df[[col for col in expected_features if col in overall_features_df.columns]].copy()
        
        for col in expected_features:
            if col not in X_overall.columns:
                X_overall[col] = 0
                
        X_overall = X_overall[expected_features].astype(float)
        pred_overall_aqi = float(all_models["Overall Delhi"].predict(X_overall)[0])
        
        predictions["Overall Delhi"][f"day_{step}"] = round(pred_overall_aqi, 2)
        predictions["Overall Delhi"]["category"].append(get_aqi_category(pred_overall_aqi))
        
    output = {
        "prediction_date": (last_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "regions": predictions
    }
    
    out_file = os.path.join(output_dir, 'predictions_3day.json')
    with open(out_file, 'w') as f:
        json.dump(output, f, indent=2)
        
    logging.info(f"✅ Multi-step Prediction successfully generated and saved to {out_file}")
    
    # Print sample of the JSON object directly to the console
    print("\n--- 3-Day Forecast JSON Output ---")
    print(json.dumps(output, indent=2))

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    live_data_path = os.path.join(base_dir, 'data', 'raw', 'live_data.csv')
    models_path = os.path.join(base_dir, 'models', 'saved', 'delhi_aqi_all_regions.pkl')
    output_dir = os.path.join(base_dir, 'outputs', 'predictions')
    
    # Suppress print output of sub-functions if desired
    import sys, io
    logging.info("Starting recursive 3-day forecasting...")
    predict_future_days(live_data_path, models_path, output_dir)
