import json
import warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

warnings.filterwarnings("ignore")

import sys
ML_DIR = Path(__file__).resolve().parent.parent / "backend" / "app" / "ml"
sys.path.insert(0, str(ML_DIR))
from generate_dataset import generate_series
from baseline import evaluate_temporal_persistence, evaluate_rolling_mean, compute_metrics

df = generate_series(days=60, seed=42)
print(f"Total rows in df: {len(df)}")
idx = int(len(df) * 0.8)
train, test = df.iloc[:idx], df.iloc[idx:]
print(f"Train len: {len(train)}, Test len: {len(test)}")

metrics_file = ML_DIR / "metrics.json"
if not metrics_file.exists():
    from train import main as train_main
    print("metrics.json not found, training models...")
    train_main()

with open(metrics_file) as f:
    saved_metrics = json.load(f)

targets = [
    ("cpu", ["cpu", "hour", "day_of_week", "cpu_rolling_avg_1h", "cpu_rolling_std_1h"], "future_cpu", "cpu"),
    ("memory", ["memory", "hour", "day_of_week", "memory_rolling_avg_1h", "memory_rolling_std_1h"], "future_memory", "memory"),
    ("network", ["network", "hour", "day_of_week", "network_rolling_avg_1h", "network_rolling_std_1h"], "future_network", "network"),
    ("cost", ["cpu", "memory", "cost_usd", "hour", "day_of_week"], "future_cost_usd", "cost_usd"),
    ("carbon", ["carbon_intensity_gco2_per_kwh", "hour", "day_of_week", "cpu"], "future_carbon_gco2", "carbon_gco2"),
]

for name, features, target_col, base_col in targets:
    y_test = test[target_col].values
    y_base = test[base_col].values
    
    # Load model with fallback to re-train if missing or incompatible with current scikit-learn
    model_path = ML_DIR / f"{name}_model.pkl"
    model = None
    if model_path.exists():
        try:
            model = joblib.load(model_path)
        except Exception:
            model = None

    if model is None:
        print(f"Note: Model for '{name}' missing or incompatible with active environment. Training now...")
        from train import train_model
        model, _ = train_model(df, features, target_col, base_col)
        joblib.dump(model, model_path)
        if name == "cpu":
            joblib.dump(model, ML_DIR / "model.pkl")

    X_test = test[features]
    preds = model.predict(X_test)
    
    mae = float(mean_absolute_error(y_test, preds))
    rmse = float(np.sqrt(np.mean((y_test - preds) ** 2)))
    r2 = float(r2_score(y_test, preds))
    
    pers = evaluate_temporal_persistence(y_test, y_base)
    roll = evaluate_rolling_mean(y_base, window=4)
    
    # Also evaluate true 4-step rolling mean from forecast origin t:
    # At time t, the rolling mean available is test[f"{base_col}_rolling_avg_1h"] if it exists
    # Or mean of 4 preceding values at time t:
    if f"{base_col}_rolling_avg_1h" in test.columns:
        roll_4step_origin = compute_metrics(y_test, test[f"{base_col}_rolling_avg_1h"].values)
    else:
        roll_4step_origin = None
        
    gain = 100 * (1 - mae / pers.mae)
    
    saved = saved_metrics[name]
    print(f"\n--- Target: {name} ---")
    print(f"Model MAE: calc={mae:.4f}, saved={saved['mae']}")
    print(f"Model RMSE: calc={rmse:.4f}, saved={saved['rmse']}")
    print(f"Model R2: calc={r2:.4f}, saved={saved['r2']}")
    print(f"Persistence MAE: calc={pers.mae:.4f}, saved={saved['naive_mae']}")
    print(f"Rolling MAE: calc={roll.mae:.4f}, saved={saved['rolling_mae']}")
    if roll_4step_origin:
        print(f"True 4-step rolling baseline MAE (from origin t): {roll_4step_origin.mae:.4f}")
    print(f"Gain (%): calc={gain:.2f}%, saved={saved['improvement_pct']}%")
