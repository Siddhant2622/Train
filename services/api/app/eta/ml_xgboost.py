"""XGBoost ML Layer + SHAP Explainer.

Loads the trained XGBoost model and uses it to predict `delay_residual` 
on top of the physics baseline. Computes SHAP values for explainability.
"""

import logging
import os
import pandas as pd
import xgboost as xgb
import shap
from datetime import datetime
from typing import Any

from app.eta.baseline import EtaResult

logger = logging.getLogger(__name__)

MODEL_FILE = os.path.join(os.path.dirname(__file__), "xgboost_model.json")

_model: xgb.XGBRegressor | None = None
_explainer: shap.TreeExplainer | None = None

def _load_model():
    global _model, _explainer
    if _model is not None:
        return
        
    if not os.path.exists(MODEL_FILE):
        logger.warning(f"ML model {MODEL_FILE} not found. Running in physics-only mode.")
        return
        
    try:
        _model = xgb.XGBRegressor()
        _model.load_model(MODEL_FILE)
        _explainer = shap.TreeExplainer(_model)
        logger.info("XGBoost ML Layer loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load XGBoost model: {e}")
        _model = None
        _explainer = None


def apply_ml_layer(
    eta_result: EtaResult, 
    current_speed_kmph: float, 
    time_of_day_hour: int, 
    day_of_week: int
) -> EtaResult:
    """Enhance the physics ETA result with ML predictions and SHAP explanations."""
    _load_model()
    
    if _model is None or _explainer is None:
        return eta_result  # Fallback to physics-only
        
    # Prepare features for all stops
    features_list = []
    for stop in eta_result.stops:
        features_list.append({
            "distance_to_next_km": stop.__dict__.get("_dist_from_src", 0), # Approx
            "section_speed_kmh": stop.explanation.get("section_speed_kmph", 80),
            "current_delay_min": stop.explanation.get("current_delay_min", 0),
            "time_of_day_hour": time_of_day_hour,
            "day_of_week": day_of_week
        })
        
    df = pd.DataFrame(features_list)
    
    # Predict residuals
    residuals = _model.predict(df)
    
    # Compute SHAP values
    shap_values = _explainer.shap_values(df)
    
    feature_names = df.columns.tolist()
    
    # Apply residuals and append explanations
    from datetime import timedelta
    for i, stop in enumerate(eta_result.stops):
        residual_min = float(residuals[i])
        
        # Adjust bounds and ETA
        stop.predicted_eta += timedelta(minutes=residual_min)
        stop.lower_bound += timedelta(minutes=residual_min)
        stop.upper_bound += timedelta(minutes=residual_min)
        stop.delay_at_stop_min += residual_min
        
        # Generate human-readable SHAP explanation
        stop_shap = shap_values[i]
        
        # Find top 2 factors contributing to delay (positive SHAP) or recovery (negative SHAP)
        factors = sorted(zip(feature_names, stop_shap), key=lambda x: abs(x[1]), reverse=True)
        top_factors = []
        for name, val in factors[:2]:
            direction = "increased" if val > 0 else "decreased"
            
            # Human readable names
            hr_name = name.replace("_", " ").title()
            if name == "current_delay_min":
                hr_name = "Current Delay Cascade"
            elif name == "time_of_day_hour":
                hr_name = "Time of Day Traffic"
                
            top_factors.append(f"{hr_name} {direction} ETA by {abs(val):.1f} min")
            
        stop.explanation["ml_residual_min"] = round(residual_min, 1)
        stop.explanation["shap_factors"] = top_factors
        stop.explanation["engine"] = "xgboost_ensemble_v1"
        
    eta_result.model_version = "xgboost_ensemble_v1"
    return eta_result
