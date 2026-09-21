"""
Generates a synthetic cloud CPU utilization time series for training/testing
the CPU forecasting model.

Why synthetic: this project runs in DEMO mode until AWS CloudWatch (or another
real telemetry source) is wired in. The synthetic series still has realistic
structure (daily seasonality + business-hours load + noise) so the model has
something genuine to learn, rather than pure random data.

No data leakage: each row's target (`future_cpu`) is the CPU value
FORECAST_HORIZON steps ahead of that row's own features. The split in train.py
is chronological (train on the past, test on the future) rather than random,
because random splitting on a time series lets the model "see the future"
through neighboring rows.
"""

import numpy as np
import pandas as pd

FORECAST_HORIZON = 4  # steps ahead to predict (e.g. 4 x 15min = 1 hour)
STEP_MINUTES = 15


def generate_series(days: int = 30, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps_per_day = 24 * 60 // STEP_MINUTES
    n = days * steps_per_day

    timestamps = pd.date_range("2026-06-01", periods=n, freq=f"{STEP_MINUTES}min")
    hour = timestamps.hour + timestamps.minute / 60.0
    day_of_week = timestamps.dayofweek

    # Daily seasonality: low overnight, ramps up during business hours,
    # slightly lower on weekends.
    daily_pattern = 35 + 30 * np.sin((hour - 7) / 24 * 2 * np.pi) ** 2
    weekend_damp = np.where(day_of_week >= 5, 0.7, 1.0)
    trend = np.linspace(0, 5, n)  # slow upward drift, mimics growing load
    noise = rng.normal(0, 4, n)

    cpu = daily_pattern * weekend_damp + trend + noise
    cpu = np.clip(cpu, 2, 98)

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "hour": hour,
            "day_of_week": day_of_week,
            "cpu": cpu,
        }
    )

    # Rolling features computed only from past values (safe: no lookahead)
    df["cpu_rolling_avg_1h"] = df["cpu"].rolling(4, min_periods=1).mean()
    df["cpu_rolling_std_1h"] = df["cpu"].rolling(4, min_periods=1).std().fillna(0)

    # Target: CPU FORECAST_HORIZON steps in the future. Rows at the end of the
    # series have no future value yet and are dropped.
    df["future_cpu"] = df["cpu"].shift(-FORECAST_HORIZON)
    df = df.dropna().reset_index(drop=True)

    return df


if __name__ == "__main__":
    data = generate_series()
    out_path = "backend/app/ml/dataset.csv"
    data.to_csv(out_path, index=False)
    print(f"Wrote {len(data)} rows to {out_path}")
    print(data.head())
