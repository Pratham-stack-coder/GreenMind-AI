"""
Trains the CPU forecasting model and reports honest, held-out evaluation
metrics.

Chronological split (not random): the model trains on the first ~80% of the
timeline and is tested on the last ~20%. This matches how it will actually be
used in production -- forecasting CPU it hasn't seen yet -- and avoids the
inflated accuracy you get from randomly splitting a time series (where the
model effectively gets to "peek" at neighbors of its test rows during
training).
"""

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error

from generate_dataset import generate_series

FEATURES = ["cpu", "hour", "day_of_week", "cpu_rolling_avg_1h", "cpu_rolling_std_1h"]
TARGET = "future_cpu"

HERE = Path(__file__).resolve().parent


def chronological_split(df: pd.DataFrame, test_frac: float = 0.2):
    split_idx = int(len(df) * (1 - test_frac))
    return df.iloc[:split_idx], df.iloc[split_idx:]


def evaluate(model, X_test, y_test) -> dict:
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
    return {"mae": round(mae, 3), "rmse": round(rmse, 3)}


def main():
    df = generate_series(days=60)
    train_df, test_df = chronological_split(df)

    X_train, y_train = train_df[FEATURES], train_df[TARGET]
    X_test, y_test = test_df[FEATURES], test_df[TARGET]

    # Baseline: "predict no change" (naive persistence model). Any real model
    # we ship needs to beat this, or it isn't adding value.
    naive_preds = X_test["cpu"].values
    naive_mae = mean_absolute_error(y_test, naive_preds)

    # Candidate model
    model = GradientBoostingRegressor(
        n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X_train, y_train)
    metrics = evaluate(model, X_test, y_test)

    # Simple linear model as a second baseline, for context in the README
    linreg = LinearRegression()
    linreg.fit(X_train, y_train)
    linreg_metrics = evaluate(linreg, X_test, y_test)

    results = {
        "n_train": len(train_df),
        "n_test": len(test_df),
        "features": FEATURES,
        "forecast_horizon_steps": 4,
        "naive_persistence_mae": round(naive_mae, 3),
        "linear_regression": linreg_metrics,
        "gradient_boosting": metrics,
    }

    print(json.dumps(results, indent=2))

    if metrics["mae"] >= naive_mae:
        print(
            "\nWARNING: model does not beat the naive persistence baseline. "
            "Do not ship this -- investigate features or model choice first."
        )
    else:
        improvement = 100 * (1 - metrics["mae"] / naive_mae)
        print(f"\nModel beats naive baseline by {improvement:.1f}% (lower MAE).")

    joblib.dump(model, HERE / "model.pkl")
    with open(HERE / "metrics.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved model to {HERE / 'model.pkl'}")


if __name__ == "__main__":
    main()
