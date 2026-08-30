import json
import logging
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_FILE = os.path.join(os.path.dirname(__file__), "services", "api", "app", "eta", "xgboost_model.json")

def train_mock_model():
    logger.info("Generating mock dataset...")
    # Features: distance_to_next_km, section_speed_kmh, current_delay_min, time_of_day_hour, day_of_week
    np.random.seed(42)
    n_samples = 1000
    
    distance_to_next_km = np.random.uniform(5, 50, n_samples)
    section_speed_kmh = np.random.uniform(40, 110, n_samples)
    current_delay_min = np.random.uniform(0, 60, n_samples)
    time_of_day_hour = np.random.randint(0, 24, n_samples)
    day_of_week = np.random.randint(0, 7, n_samples)
    
    # Target: delay_residual
    # Let's create some simple relationships
    delay_residual = (
        0.1 * distance_to_next_km +
        (-0.05 * section_speed_kmh) +
        0.2 * current_delay_min +
        np.where(np.isin(time_of_day_hour, [8, 9, 17, 18]), 5, 0) + # rush hour penalty
        np.where(np.isin(day_of_week, [5, 6]), -2, 0) + # weekend bonus
        np.random.normal(0, 2, n_samples)
    )
    
    df = pd.DataFrame({
        "distance_to_next_km": distance_to_next_km,
        "section_speed_kmh": section_speed_kmh,
        "current_delay_min": current_delay_min,
        "time_of_day_hour": time_of_day_hour,
        "day_of_week": day_of_week
    })
    y = pd.Series(delay_residual)
    
    logger.info("Training XGBoost model...")
    model = xgb.XGBRegressor(
        n_estimators=50,
        learning_rate=0.1,
        max_depth=4,
        random_state=42
    )
    
    model.fit(df, y)
    
    # Save Model
    os.makedirs(os.path.dirname(MODEL_FILE), exist_ok=True)
    model.save_model(MODEL_FILE)
    logger.info(f"Model saved to {MODEL_FILE}")

if __name__ == "__main__":
    train_mock_model()
