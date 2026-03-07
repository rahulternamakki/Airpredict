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
    """Categorize AQI based on US EPA standard as referenced in the plan."""
    if aqi <= 50: return "Good"
    elif aqi <= 100: return "Moderate"
    elif aqi <= 150: return "Unhealthy for Sensitive Groups"
    elif aqi <= 200: return "Unhealthy"
    elif aqi <= 300: return "Very Unhealthy"
    else: return "Hazardous"

def get_reducible_features(features: list) -> list:
    """
    Filters features to only those that can be realistically reduced by human intervention.
    Excludes meteorological features.
    """
    # Allow pollutants, their lags and rolling variants, and human activity indicators
    reducible_keywords = [
        'pm25', 'pm10', 'no2', 'so2', 'co', 'no', 'nox', 'ozone', 
        'traffic_index', 'fire_count', 'stubble_burning', 'daily_frp',
        'is_festival', 'is_wedding_heavy', 'AQI_rolling'
    ]
    
    non_reducible_keywords = ['wind', 'msl', 'temp', 'humidity', 'precip', 'month', 'day', 'hour', 't2m', 'interaction', 'inversion', 'is_weekend', 'is_gazetted_holiday', 'is_restricted_holiday']
    
    valid_features = []
    for f in features:
        is_meteorological = any(kw.lower() in f.lower() for kw in non_reducible_keywords)
        is_reducible = any(kw.lower() in f.lower() for kw in reducible_keywords)
        
        if is_reducible and not is_meteorological:
            valid_features.append(f)
            
    return valid_features

def generate_counterfactuals(live_data_path: str, models_path: str, shap_values_path: str, output_dir: str):
    """
    Generates Counterfactual ('What-If') scenarios using Feature Perturbation based on the top SHAP features.
    Reduces reducible features by 25%.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Load Data, Models, and SHAP values
    logging.info("Loading models...")
    all_models = joblib.load(models_path)
    
    if not os.path.exists(shap_values_path):
        raise FileNotFoundError(f"SHAP values not found at {shap_values_path}. Please run SHAP analysis first.")
    with open(shap_values_path, "r") as f:
        shap_outputs = json.load(f)
        
    logging.info(f"Loading live data context from {live_data_path}...")
    df_raw = load_live_data(live_data_path)
    
    # Check features from a reliable model key
    model_keys = list(all_models.keys())
    first_region = "North Delhi" if "North Delhi" in all_models else model_keys[0]
    model_ref = all_models[first_region]['day_1']
    if not hasattr(model_ref, 'feature_names_in_'):
        raise ValueError("Model missing feature_names_in_.")
    expected_features = list(model_ref.feature_names_in_)
    
    # Feature engineering for live data
    last_date = df_raw['datetime'].max()
    cutoff_date = last_date - pd.Timedelta(days=30)
    df_context = df_raw[df_raw['datetime'] >= cutoff_date].copy()
    df_feats = engineer_features(df_context)
    
    nan_cols = [col for col in expected_features if col in df_feats.columns and df_feats[col].isna().any()]
    if nan_cols:
        df_feats[nan_cols] = df_feats[nan_cols].fillna(0)
        
    latest_feats = df_feats[df_feats['datetime'] == last_date]
    
    final_output = []
    specific_regions = [r for r in df_raw['region_name'].unique() if r != 'Overall Delhi']
    
    for shap_data in shap_outputs:
        region = shap_data['region']
        day = shap_data['prediction_day']
        
        # We only do counterfactuals for Day+1
        if day != 1:
            continue
            
        original_aqi = shap_data['predicted_value']
        
        # Extract features driving AQI up
        all_candidate_features = [f['feature'] for f in shap_data['top_features']]
        # Filter to only reducible features
        reducible_features = get_reducible_features(all_candidate_features)
        
        top_features = reducible_features[:5]
        
        if not top_features:
            logging.warning(f"No top reducible features found for {region}. Skipping.")
            continue
            
        model_key = region
        if model_key not in all_models:
            alternative_keys = [k for k in all_models.keys() if region.replace(" Delhi", "").lower() in k.lower()]
            if alternative_keys:
                model_key = alternative_keys[0]
            else:
                logging.warning(f"No model found for region: {region}. Skipping.")
                continue
                
        model = all_models[model_key]['day_1']
        
        # 2. Extract latest query instance
        region_live = latest_feats[latest_feats['region_name'] == region.replace(" Delhi", "")].copy()
        if region_live.empty and region == 'Overall Delhi':
             region_live = latest_feats[latest_feats['region_name'].isin(specific_regions)].mean(numeric_only=True).to_frame().T
        elif region_live.empty:
            region_live = latest_feats[latest_feats['region_name'] == region].copy()
            
        if region_live.empty:
            logging.warning(f"No live features for {region}. Skipping counterfactuals.")
            continue
            
        X_live = region_live.copy()
        for col in expected_features:
            if col not in X_live.columns:
                X_live[col] = 0
        X_live = X_live[expected_features].astype(float)
        
        query_instance = X_live.iloc[[0]].copy()
        
        scenarios = []
        
        def run_scenario(name, type_val, features_to_vary, query_instance, reduction_factor):
            try:
                X_cf = query_instance.copy()
                orig_vals = {}
                new_vals = {}
                
                for f in features_to_vary:
                    orig_val = float(X_cf[f].iloc[0])
                    new_val = orig_val * (1 - reduction_factor)
                    X_cf[f] = new_val
                    orig_vals[f] = round(orig_val, 2)
                    new_vals[f] = round(new_val, 2)
                    
                new_aqi = float(model.predict(X_cf)[0])
                
                reduction = round(original_aqi - new_aqi, 2)
                # Ensure we only record valid reductions
                if reduction <= 0:
                    return None
                    
                pct_improvement = f"{round((reduction / original_aqi) * 100, 1)}%"
                
                scenario_res = {
                    "name": name,
                    "type": type_val,
                    "feature_changes": {f: -int(reduction_factor * 100) for f in features_to_vary},
                    "new_aqi": int(round(new_aqi)),
                    "new_category": get_aqi_category(new_aqi),
                    "aqi_reduction": int(round(reduction)),
                    "percent_improvement": pct_improvement
                }

                # Plan spec: singular key for individual, plural for combined
                if type_val == "individual":
                    scenario_res["original_feature_value"] = orig_vals
                    scenario_res["perturbed_feature_value"] = new_vals
                else:
                    scenario_res["original_feature_values"] = orig_vals
                    scenario_res["perturbed_feature_values"] = new_vals
                
                return scenario_res
            except Exception as e:
                logging.warning(f"Failed perturbation for {name}: {e}")
            return None

        # Individual Scenarios
        for feat in top_features:
            scen = run_scenario(f"{feat} reduced by 25%", "individual", [feat], query_instance, 0.25)
            if scen:
                scenarios.append(scen)
                
        # Combined Scenarios
        if len(top_features) >= 2:
            scen = run_scenario("Top 2 features reduced by 25%", "combined", top_features[:2], query_instance, 0.25)
            if scen:
                 scenarios.append(scen)
                 
        if len(top_features) >= 3:
            scen = run_scenario("Top 3 features reduced by 25%", "combined", top_features[:3], query_instance, 0.25)
            if scen:
                 scenarios.append(scen)
                 
        if len(top_features) >= 5:
            scen = run_scenario("Top 5 features reduced by 15%", "combined", top_features[:5], query_instance, 0.15)
            if scen:
                 scenarios.append(scen)
                 
        if scenarios:
            final_output.append({
                "region": region,
                "original_day1_aqi": int(round(original_aqi)),
                "original_category": get_aqi_category(original_aqi),
                "method": "Feature Perturbation",
                "scenarios": scenarios
            })
            
    out_file = os.path.join(output_dir, 'counterfactual_results.json')
    with open(out_file, 'w') as f:
        json.dump(final_output, f, indent=2)
        
    logging.info(f"✅ Counterfactual Analysis completed. Results saved to {out_file}")

if __name__ == "__main__":
    import warnings
    warnings.filterwarnings('ignore')
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    live_data_path = os.path.join(base_dir, 'data', 'raw', 'live_data.csv')
    if not os.path.exists(live_data_path):
        live_data_path = os.path.join(base_dir, 'Delhi_AQI_final.csv')
        
    models_path = os.path.join(base_dir, 'models', 'saved', 'delhi_aqi_all_regions.pkl')
    shap_dir = os.path.join(base_dir, 'outputs', 'shap', 'shap_candidates.json')
    output_dir = os.path.join(base_dir, 'outputs', 'counterfactual')
    
    logging.info("Starting Counterfactual Pipeline...")
    generate_counterfactuals(live_data_path, models_path, shap_dir, output_dir)
