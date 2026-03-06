import pandas as pd
import numpy as np
import joblib
import os
import json
import logging
import shap
import matplotlib.pyplot as plt
from datetime import datetime
from data_loader import load_live_data
from feature_engineering import engineer_features

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def perform_shap_analysis(live_data_path: str, models_path: str, output_dir: str):
    """
    Generates Global and Local SHAP explanations for Day 1-3 predictions.
    Outputs:
    - Global Summary & Beeswarm plots per region per day.
    - Local Waterfall plots for the latest prediction per region per day.
    - JSON structured payloads: 
        - shap_values.json (top 5 for explain)
        - shap_candidates.json (top 15 for counterfactual)
    """
    os.makedirs(output_dir, exist_ok=True)
    logging.info("Loading models for SHAP analysis...")
    all_models = joblib.load(models_path)
    
    logging.info(f"Loading live data context from {live_data_path}...")
    df_raw = load_live_data(live_data_path)
    
    regions = [r for r in df_raw['region_name'].unique()]
    specific_regions = [r for r in regions if r != 'Overall Delhi']
    
    if "Overall Delhi" in all_models and "Overall Delhi" not in regions:
        regions.append("Overall Delhi")
    
    # Check features from a reliable model key
    model_keys = list(all_models.keys())
    first_region = "North Delhi" if "North Delhi" in all_models else model_keys[0]
    
    model_ref = all_models[first_region]['day_1']
    if not hasattr(model_ref, 'feature_names_in_'):
        raise ValueError("Model missing feature_names_in_.")
    expected_features = model_ref.feature_names_in_
    
    last_date = df_raw['datetime'].max()
    
    # We take enough trailing data to get some context for the explainer's background
    cutoff_date = last_date - pd.Timedelta(days=30) 
    df_context = df_raw[df_raw['datetime'] >= cutoff_date].copy()
    df_feats = engineer_features(df_context)
    
    # Fill any NaNs
    nan_cols = [col for col in expected_features if col in df_feats.columns and df_feats[col].isna().any()]
    if nan_cols:
        df_feats[nan_cols] = df_feats[nan_cols].fillna(0)
        
    latest_feats = df_feats[df_feats['datetime'] == last_date]
    
    explain_output = []
    candidate_output = []
    
    for r in regions:
        display_name = r if "Delhi" in r else f"{r} Delhi"
        model_key = display_name
        
        if model_key not in all_models:
            alternative_keys = [k for k in all_models.keys() if r.lower() in k.lower()]
            if alternative_keys:
                model_key = alternative_keys[0]
            else:
                logging.warning(f"No model found for region: {r}. Skipping.")
                continue
                
        # Get background data for global analysis
        region_bg = df_feats[df_feats['region_name'] == r].copy()
        if region_bg.empty and r == 'Overall Delhi':
             region_bg = df_feats[df_feats['region_name'].isin(specific_regions)].groupby('datetime').mean(numeric_only=True).reset_index()
             
        X_bg = region_bg[[col for col in expected_features if col in region_bg.columns]].copy()
        for col in expected_features:
            if col not in X_bg.columns:
                X_bg[col] = 0
        X_bg = X_bg[expected_features].astype(float)
        
        # Latest prediction row
        region_live = latest_feats[latest_feats['region_name'] == r].copy()
        if region_live.empty and r == 'Overall Delhi':
            region_live = latest_feats[latest_feats['region_name'].isin(specific_regions)].mean(numeric_only=True).to_frame().T
            
        if region_live.empty:
            continue
            
        X_live = region_live[[col for col in expected_features if col in region_live.columns]].copy()
        for col in expected_features:
            if col not in X_live.columns:
                X_live[col] = 0
        X_live = X_live[expected_features].astype(float)

        for step in range(1, 4):
            day_str = f"day_{step}"
            model = all_models[model_key][day_str]
            explainer = shap.TreeExplainer(model)
            
            # Global SHAP
            if len(X_bg) > 10:
                X_bg_sample = shap.sample(X_bg, min(50, len(X_bg)))
                shap_values_global = explainer(X_bg_sample)
                plt.figure()
                shap.summary_plot(shap_values_global, X_bg_sample, plot_type="bar", show=False)
                plt.title(f"Global SHAP Summary - {display_name} (Day+{step})")
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, f"{display_name.replace(' ', '_')}_Day{step}_global_summary.png"))
                plt.close()
                
                plt.figure()
                shap.summary_plot(shap_values_global, X_bg_sample, show=False)
                plt.title(f"Global SHAP Beeswarm - {display_name} (Day+{step})")
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, f"{display_name.replace(' ', '_')}_Day{step}_global_beeswarm.png"))
                plt.close()

            # Local SHAP
            shap_values_local = explainer(X_live)
            
            plt.figure(figsize=(10, 6))
            shap.plots.waterfall(shap_values_local[0], show=False)
            plt.title(f"Local SHAP Waterfall - {display_name} (Day+{step})")
            plt.tight_layout()
            plt.savefig(os.path.join(output_dir, f"{display_name.replace(' ', '_')}_Day{step}_local_waterfall.png"))
            plt.close()
            
            vals = shap_values_local.values[0]
            base_val = float(shap_values_local.base_values[0])
            pred_val = float(model.predict(X_live)[0])
            
            feature_impacts = []
            for i, feature in enumerate(expected_features):
                feature_impacts.append({
                    "feature": feature,
                    "shap_value": round(float(vals[i]), 2),
                    "actual_value": round(float(X_live.iloc[0, i]), 2)
                })
                
            feature_impacts_sorted = sorted(feature_impacts, key=lambda x: x['shap_value'], reverse=True)

            # Prepare outputs
            explain_output.append({
                "region": display_name,
                "prediction_day": step,
                "base_value": round(base_val, 2),
                "predicted_value": round(pred_val, 2),
                "top_features": feature_impacts_sorted[:5] # Top 5 for SHAP Explanation
            })

            candidate_output.append({
                "region": display_name,
                "prediction_day": step,
                "base_value": round(base_val, 2),
                "predicted_value": round(pred_val, 2),
                "top_features": feature_impacts_sorted[:15] # Top 15 for Counterfactual Candidates
            })
            
            logging.info(f"Processed SHAP for {display_name} Day+{step}")

    # Save outputs
    explain_file = os.path.join(output_dir, 'shap_values.json')
    with open(explain_file, 'w') as f:
        json.dump(explain_output, f, indent=2)

    candidate_file = os.path.join(output_dir, 'shap_candidates.json')
    with open(candidate_file, 'w') as f:
        json.dump(candidate_output, f, indent=2)

    logging.info(f"✅ SHAP analysis completed. Explanation (Top 5) saved to {explain_file}. Candidates (Top 15) saved to {candidate_file}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    models_path = os.path.join(base_dir, 'models', 'saved', 'delhi_aqi_all_regions.pkl')
    live_data_path = os.path.join(base_dir, 'data', 'raw', 'live_data.csv')
    if not os.path.exists(live_data_path):
        live_data_path = os.path.join(base_dir, 'Delhi_AQI_final.csv')
    output_dir = os.path.join(base_dir, 'outputs', 'shap')

    logging.info("Starting SHAP Analysis Pipeline...")
    perform_shap_analysis(live_data_path, models_path, output_dir)
