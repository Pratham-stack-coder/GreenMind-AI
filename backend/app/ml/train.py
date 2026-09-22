"""
Multi-metric ML training — trains separate GradientBoosting models for
CPU, memory, network, cost, and carbon forecasting.
All models use chronological train/test split to prevent data leakage.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

from generate_dataset import generate_series

HERE = Path(__file__).resolve().parent

# Feature sets per target
CPU_FEATURES = ["cpu", "hour", "day_of_week", "cpu_rolling_avg_1h", "cpu_rolling_std_1h"]
MEMORY_FEATURES = ["memory", "hour", "day_of_week", "memory_rolling_avg_1h", "memory_rolling_std_1h"]
NETWORK_FEATURES = ["network", "hour", "day_of_week", "network_rolling_avg_1h", "network_rolling_std_1h"]
COST_FEATURES = ["cpu", "memory", "cost_usd", "hour", "day_of_week"]
CARBON_FEATURES = ["carbon_intensity_gco2_per_kwh", "hour", "day_of_week", "cpu"]

TARGETS = {
    "cpu": (CPU_FEATURES, "future_cpu"),
    "memory": (MEMORY_FEATURES, "future_memory"),
    "network": (NETWORK_FEATURES, "future_network"),
    "cost": (COST_FEATURES, "future_cost_usd"),
    "carbon": (CARBON_FEATURES, "future_carbon_gco2"),
}


def chronological_split(df, test_frac: float = 0.2):
    idx = int(len(df) * (1 - test_frac))
    return df.iloc[:idx], df.iloc[idx:]


def train_model(df, features: list[str], target: str) -> tuple:
    train, test = chronological_split(df)
    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]

    model = GradientBoostingRegressor(
        n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))
    naive_mae = float(mean_absolute_error(y_test, X_test[features[0]].values))
    improvement = round(100 * (1 - mae / naive_mae), 1) if naive_mae > 0 else 0.0

    return model, {
        "mae": round(mae, 3),
        "naive_mae": round(naive_mae, 3),
        "improvement_pct": improvement,
        "n_train": len(train),
        "n_test": len(test),
    }


def main():
    print("Generating synthetic multi-metric dataset (60 days)…")
    df = generate_series(days=60)

    all_metrics = {}
    for name, (features, target) in TARGETS.items():
        print(f"  Training {name} forecaster…")
        model, metrics = train_model(df, features, target)
        joblib.dump(model, HERE / f"{name}_model.pkl")
        all_metrics[name] = metrics
        beat = metrics["improvement_pct"]
        sign = "OK" if beat > 0 else "--"
        print(f"    MAE={metrics['mae']:.3f}  naive={metrics['naive_mae']:.3f}  "
              f"[{sign}] beats baseline by {beat:.1f}%")

    with open(HERE / "metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2)

    print(f"\nSaved models to {HERE}")
    print("Training complete.")


if __name__ == "__main__":
    main()
