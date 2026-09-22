"""
Multi-metric synthetic cloud telemetry generator.
Produces CPU, memory, storage, network, cost, and carbon time series with
realistic daily patterns and provider/region variation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FORECAST_HORIZON = 4   # steps ahead (4 × 15 min = 1 h)
STEP_MINUTES = 15


def generate_series(
    days: int = 60,
    seed: int = 42,
    provider: str = "aws",
    region: str = "us-east",
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    steps_per_day = 24 * 60 // STEP_MINUTES
    n = days * steps_per_day

    timestamps = pd.date_range("2026-06-01", periods=n, freq=f"{STEP_MINUTES}min")
    hour = timestamps.hour + timestamps.minute / 60.0
    day_of_week = timestamps.dayofweek.to_numpy()

    # ── CPU ──────────────────────────────────────────────────────────────────
    daily_cpu = 35 + 30 * np.sin((hour - 7) / 24 * 2 * np.pi) ** 2
    weekend_damp = np.where(day_of_week >= 5, 0.7, 1.0)
    trend = np.linspace(0, 5, n)
    cpu = np.clip(daily_cpu * weekend_damp + trend + rng.normal(0, 4, n), 2, 98)

    # ── Memory ───────────────────────────────────────────────────────────────
    # Slightly flatter profile, slow upward drift (memory leaks build up)
    daily_mem = 45 + 15 * np.sin((hour - 8) / 24 * 2 * np.pi) ** 2
    mem_trend = np.linspace(0, 8, n)
    memory = np.clip(daily_mem + mem_trend + rng.normal(0, 3, n), 10, 95)

    # ── Storage ──────────────────────────────────────────────────────────────
    # Monotonic slow growth with occasional spikes
    storage_base = np.linspace(40, 65, n)
    storage_spikes = rng.choice([0, 5, 10], n, p=[0.97, 0.02, 0.01])
    storage = np.clip(storage_base + rng.normal(0, 1, n) + np.cumsum(storage_spikes) * 0.001, 20, 95)

    # ── Network ──────────────────────────────────────────────────────────────
    daily_net = 300 + 400 * np.sin((hour - 9) / 24 * 2 * np.pi) ** 2
    network = np.clip(daily_net * weekend_damp + rng.normal(0, 50, n), 50, 2000)

    # ── Cost (USD/hr) ─────────────────────────────────────────────────────────
    # Proportional to active instances; compute cost tracks cpu roughly
    base_cost = 0.192  # m5.xlarge on-demand
    cost_multiplier = 1 + (cpu / 100) * 0.5  # 1.0–1.5×
    cost_usd = np.clip(base_cost * cost_multiplier + rng.normal(0, 0.01, n), 0.05, 5.0)

    # ── Carbon intensity (gCO2/kWh) ───────────────────────────────────────────
    _REGION_INTENSITY: dict[str, list[float]] = {
        "us-east": [350, 340, 330, 325, 320, 330, 360, 400, 430, 440, 445, 440,
                    430, 425, 430, 440, 450, 460, 470, 460, 440, 410, 380, 360],
        "us-west": [280, 270, 265, 260, 258, 270, 300, 320, 290, 240, 200, 185,
                    175, 172, 185, 210, 250, 290, 310, 305, 295, 288, 283, 280],
        "eu-west": [220, 210, 205, 200, 198, 205, 230, 260, 275, 280, 278, 272,
                    268, 270, 275, 282, 285, 280, 265, 248, 235, 228, 222, 220],
        "in-north": [620, 600, 590, 585, 590, 610, 660, 700, 720, 715, 700, 690,
                     685, 690, 700, 715, 730, 740, 730, 710, 690, 670, 650, 635],
        "ap-southeast": [480, 470, 465, 460, 462, 475, 510, 540, 555, 560, 558, 552,
                         548, 550, 555, 560, 565, 562, 550, 535, 520, 510, 495, 485],
        "ca-central": [90, 85, 82, 80, 79, 82, 95, 110, 118, 120, 119, 116,
                       114, 115, 116, 118, 120, 118, 112, 105, 100, 96, 93, 91],
    }
    curve = _REGION_INTENSITY.get(region, _REGION_INTENSITY["us-east"])
    intensity_arr = np.array([curve[int(h) % 24] for h in hour.to_numpy()], dtype=float)
    kwh_per_step = 0.35 * (STEP_MINUTES / 60)
    carbon_gco2 = np.clip(intensity_arr * kwh_per_step + rng.normal(0, 5, n), 0, 500)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "hour": hour,
        "day_of_week": day_of_week,
        "cpu": cpu,
        "memory": memory,
        "storage": storage,
        "network": network,
        "cost_usd": cost_usd,
        "carbon_gco2": carbon_gco2,
        "carbon_intensity_gco2_per_kwh": intensity_arr,
    })

    # Rolling features (safe — no lookahead)
    for col in ["cpu", "memory", "network"]:
        df[f"{col}_rolling_avg_1h"] = df[col].rolling(4, min_periods=1).mean()
        df[f"{col}_rolling_std_1h"] = df[col].rolling(4, min_periods=1).std().fillna(0)

    # Targets: FORECAST_HORIZON steps ahead
    for col in ["cpu", "memory", "network", "cost_usd", "carbon_gco2"]:
        df[f"future_{col}"] = df[col].shift(-FORECAST_HORIZON)

    df = df.dropna().reset_index(drop=True)
    return df


if __name__ == "__main__":
    data = generate_series()
    out_path = "dataset.csv"
    data.to_csv(out_path, index=False)
    print(f"Wrote {len(data)} rows — columns: {list(data.columns)}")
