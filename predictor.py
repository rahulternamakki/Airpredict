"""
predictor.py — Core ML Inference

build_feature_vector(region, input_features) → 42-element dict (with region one-hot set)
predict_aqi(region, input_features)          → {day1, day2, day3} predictions

Handles:
  - Single region prediction (Central, East, North, South, West)
  - "Overall" → runs all 5 regions, returns averaged predictions
"""

import logging
import numpy as np
import pandas as pd

from app.ml.features import M3_FEATURES, CONTINUOUS_FEATURES, REGION_NAMES
from app.utils.model_loader import get_model, get_scaler
from app.utils.aqi_categories import get_category

logger = logging.getLogger(__name__)


def build_feature_vector(region: str, input_features: dict) -> pd.DataFrame:
    """
    Build a 42-column feature DataFrame ready for scaling + prediction.

    Steps:
    1. Start from input_features dict (all M3 features except region one-hots).
    2. Set region one-hot columns (region_Central, region_East, etc.).
    3. Fill any missing M3 columns with 0.0.
    4. Return as a single-row DataFrame in M3_FEATURES column order.
    """
    row = {}

    # Copy all provided features
    for feat in M3_FEATURES:
        row[feat] = float(input_features.get(feat, 0.0))

    # Override region one-hots
    for r in REGION_NAMES:
        row[f"region_{r}"] = 1.0 if r == region else 0.0

    df = pd.DataFrame([row], columns=M3_FEATURES)
    return df


def _predict_single(region: str, input_features: dict) -> dict:
    """Run prediction for a single region. Returns {day1, day2, day3}."""
    model = get_model()
    scaler = get_scaler()

    df = build_feature_vector(region, input_features)

    # Scale only continuous features
    df_scaled = df.copy()
    continuous_cols = [c for c in CONTINUOUS_FEATURES if c in df_scaled.columns]
    df_scaled[continuous_cols] = scaler.transform(df_scaled[continuous_cols])

    # Predict → shape (1, 3) for [day1, day2, day3]
    preds = model.predict(df_scaled[M3_FEATURES])
    
    result = {}
    for i, day in enumerate(["day1", "day2", "day3"]):
        aqi_val = max(0, int(round(float(preds[0][i]))))
        cat = get_category(aqi_val)
        result[day] = {
            "aqi": aqi_val,
            "category": cat["label"],
            "color": cat["color"],
        }

    return result


def predict_aqi(region: str, input_features: dict) -> dict:
    """
    Predict AQI for day+1, day+2, day+3.

    If region == "Overall":
        Run prediction for all 5 regions independently using the same input_features
        (feature values treated as city-wide averages).
        Returns per-region predictions AND overall averaged predictions.

    Otherwise:
        Returns predictions for the specified region.
    """
    if region == "Overall":
        all_preds = {}
        day1_aqis, day2_aqis, day3_aqis = [], [], []

        for r in REGION_NAMES:
            preds = _predict_single(r, input_features)
            all_preds[r] = preds
            day1_aqis.append(preds["day1"]["aqi"])
            day2_aqis.append(preds["day2"]["aqi"])
            day3_aqis.append(preds["day3"]["aqi"])

        def avg_day(aqis):
            aqi_val = max(0, int(round(float(np.mean(aqis)))))
            cat = get_category(aqi_val)
            return {"aqi": aqi_val, "category": cat["label"], "color": cat["color"]}

        overall_preds = {
            "day1": avg_day(day1_aqis),
            "day2": avg_day(day2_aqis),
            "day3": avg_day(day3_aqis),
        }

        return {
            "region": "Overall",
            "predictions": overall_preds,
            "region_predictions": all_preds,
        }

    else:
        preds = _predict_single(region, input_features)
        return {
            "region": region,
            "predictions": preds,
        }
