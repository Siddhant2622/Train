"""Train the XGBoost delay residual model and SHAP explainer."""

import json
import logging
import pandas as pd
import xgboost as xgb
import shap
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_FILE = "/app/ml/train_data.csv"
MODEL_FILE = "/app/app/eta/xgboost_model.json"

def train():
    logger.info("Loading dataset...")
    try:
        df = pd.read_csv(DATA_FILE)
    except FileNotFoundError:
        logger.error(f"Data file {DATA_FILE} not found. Run generate_data.py first.")
        return

    if df.empty:
        logger.error("Dataset is empty.")
        return

    # Feature engineering: Categorical encoding
    # In a real pipeline, we'd save the encoders. Here we'll use simple mapping or let XGBoost handle categoricals (if using enable_categorical).
    # For simplicity in this demo, we'll convert train_type to numerical or drop it, and target the numerical features.
    
    # We will use simple numerical features for the baseline XGBoost
    features = [
        "distance_to_next_km",
        "section_speed_kmh",
        "current_delay_min",
        "time_of_day_hour",
        "day_of_week"
    ]
    
    X = df[features]
    y = df["delay_residual"]
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    logger.info("Training XGBoost model...")
    model = xgb.XGBRegressor(
        n_estimators=100,
        learning_rate=0.1,
        max_depth=6,
        random_state=42
    )
    
    model.fit(X_train, y_train)
    
    # Evaluate
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = mean_squared_error(y_test, preds, squared=False)
    logger.info(f"Evaluation - MAE: {mae:.2f} min, RMSE: {rmse:.2f} min")
    
    # Save Model
    model.save_model(MODEL_FILE)
    logger.info(f"Model saved to {MODEL_FILE}")
    
    # Test SHAP explainer
    logger.info("Testing SHAP Explainer...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test.iloc[:1])
    logger.info(f"SHAP values computed successfully. Sample: {shap_values[0]}")

if __name__ == "__main__":
    train()
