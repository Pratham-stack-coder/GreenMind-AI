"""
Multi-metric ML training — trains separate GradientBoosting models for
CPU, memory, network, cost, and carbon forecasting.
All models use chronological train/test split to prevent data leakage.
Computes and reports MAE, RMSE, and R² metrics alongside feature importances.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

from generate_dataset import generate_series
try:
    from .baseline import evaluate_temporal_persistence, evaluate_rolling_mean
except ImportError:
    from baseline import evaluate_temporal_persistence, evaluate_rolling_mean

HERE = Path(__file__).resolve().parent

# Feature sets per target
CPU_FEATURES = ["cpu", "hour", "day_of_week", "cpu_rolling_avg_1h", "cpu_rolling_std_1h"]
MEMORY_FEATURES = ["memory", "hour", "day_of_week", "memory_rolling_avg_1h", "memory_rolling_std_1h"]
NETWORK_FEATURES = ["network", "hour", "day_of_week", "network_rolling_avg_1h", "network_rolling_std_1h"]
COST_FEATURES = ["cpu", "memory", "cost_usd", "hour", "day_of_week"]
CARBON_FEATURES = ["carbon_intensity_gco2_per_kwh", "hour", "day_of_week", "cpu"]

# (features, target_col, baseline_persistence_col)
TARGETS = {
    "cpu": (CPU_FEATURES, "future_cpu", "cpu"),
    "memory": (MEMORY_FEATURES, "future_memory", "memory"),
    "network": (NETWORK_FEATURES, "future_network", "network"),
    "cost": (COST_FEATURES, "future_cost_usd", "cost_usd"),
    "carbon": (CARBON_FEATURES, "future_carbon_gco2", "carbon_gco2"),
}


def chronological_split(df, test_frac: float = 0.2):
    idx = int(len(df) * (1 - test_frac))
    return df.iloc[:idx], df.iloc[idx:]


def train_model(df, features: list[str], target: str, baseline_col: str) -> tuple:
    train, test = chronological_split(df)
    X_train, y_train = train[features], train[target]
    X_test, y_test = test[features], test[target]

    model = GradientBoostingRegressor(
        n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = float(mean_absolute_error(y_test, preds))

    # True temporal persistence baseline: \hat{y}_t = y_{t-1} on the target's own historical values
    persistence_baseline = evaluate_temporal_persistence(y_test.values, test[baseline_col].values)
    rolling_baseline = evaluate_rolling_mean(test[baseline_col].values, window=4)
    naive_mae = persistence_baseline.mae
    improvement = round(100 * (1 - mae / naive_mae), 1) if naive_mae > 0 else 0.0

    # Calculate RMSE & R²
    rmse = float(np.sqrt(np.mean((y_test - preds) ** 2)))
    r2 = float(r2_score(y_test, preds))

    # Feature importance mapping
    feature_imp = {
        feat: round(float(imp), 4)
        for feat, imp in zip(features, model.feature_importances_)
    }

    metrics = {
        "mae": round(mae, 3),
        "rmse": round(rmse, 3),
        "r2": round(r2, 3),
        "naive_mae": round(naive_mae, 3),
        "rolling_mae": round(rolling_baseline.mae, 3),
        "improvement_pct": improvement,
        "n_train": len(train),
        "n_test": len(test),
        "feature_importance": feature_imp,
    }

    return model, metrics


def main():
    print("Generating synthetic multi-metric dataset (60 days)…")
    df = generate_series(days=60)

    all_metrics = {}
    feature_importances = {}

    for name, (features, target, baseline_col) in TARGETS.items():
        print(f"  Training {name} forecaster…")
        model, metrics = train_model(df, features, target, baseline_col)
        joblib.dump(model, HERE / f"{name}_model.pkl")
        if name == "cpu":
            joblib.dump(model, HERE / "model.pkl")  # legacy compatibility

        feature_importances[name] = metrics["feature_importance"]
        all_metrics[name] = metrics

        beat = metrics["improvement_pct"]
        sign = "OK" if beat > 0 else "--"
        print(
            f"    MAE={metrics['mae']:.3f}  RMSE={metrics['rmse']:.3f}  R²={metrics['r2']:.3f}  "
            f"naive={metrics['naive_mae']:.3f}  [{sign}] beats baseline by {beat:.1f}%"
        )

    with open(HERE / "metrics.json", "w") as f:
        json.dump(all_metrics, f, indent=2)

    with open(HERE / "feature_importance.json", "w") as f:
        json.dump(feature_importances, f, indent=2)

    print(f"\nSaved models and metrics to {HERE}")
    print("Training complete.")


if __name__ == "__main__":
    main()

