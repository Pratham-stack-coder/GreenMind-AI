"""
Multi-metric ML predictor — loads all trained models and exposes a unified
predict_all() function with anomaly detection.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import NamedTuple

import joblib

HERE = Path(__file__).resolve().parent

CPU_FEATURES = ["cpu", "hour", "day_of_week", "cpu_rolling_avg_1h", "cpu_rolling_std_1h"]
MEMORY_FEATURES = ["memory", "hour", "day_of_week", "memory_rolling_avg_1h", "memory_rolling_std_1h"]
NETWORK_FEATURES = ["network", "hour", "day_of_week", "network_rolling_avg_1h", "network_rolling_std_1h"]
COST_FEATURES = ["cpu", "memory", "cost_usd", "hour", "day_of_week"]
CARBON_FEATURES = ["carbon_intensity_gco2_per_kwh", "hour", "day_of_week", "cpu"]

_MODELS: dict[str, object] = {}
_METRICS: dict = {}

# Anomaly z-score threshold
ANOMALY_THRESHOLD = 2.5
_ROLLING_STATS: dict[str, dict] = {
    "cpu":     {"mean": 50, "std": 15},
    "memory":  {"mean": 55, "std": 12},
    "network": {"mean": 500, "std": 200},
    "cost":    {"mean": 0.25, "std": 0.08},
    "carbon":  {"mean": 100, "std": 40},
}


def _load(name: str):
    if name not in _MODELS:
        path = HERE / f"{name}_model.pkl"
        if not path.exists():
            # Fall back to legacy cpu model.pkl during first run
            if name == "cpu":
                legacy = HERE / "model.pkl"
                if legacy.exists():
                    _MODELS[name] = joblib.load(legacy)
                    return _MODELS[name]
            raise FileNotFoundError(
                f"{name}_model.pkl not found — run `python train.py` inside backend/app/ml/"
            )
        _MODELS[name] = joblib.load(path)
        metrics_path = HERE / "metrics.json"
        if metrics_path.exists() and not _METRICS:
            _METRICS.update(json.loads(metrics_path.read_text()))
    return _MODELS[name]


class Forecast(NamedTuple):
    current: float
    predicted: float
    delta_pct: float
    anomaly: bool
    confidence: float


def _detect_anomaly(name: str, value: float) -> bool:
    stats = _ROLLING_STATS.get(name, {"mean": 50, "std": 20})
    z = abs(value - stats["mean"]) / max(stats["std"], 1)
    return z > ANOMALY_THRESHOLD


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def predict_cpu(cpu: float, hour: float, day_of_week: int,
                cpu_rolling_avg_1h: float | None = None,
                cpu_rolling_std_1h: float = 0.0) -> Forecast:
    model = _load("cpu")
    if cpu_rolling_avg_1h is None:
        cpu_rolling_avg_1h = cpu
    row = [[cpu, hour, day_of_week, cpu_rolling_avg_1h, cpu_rolling_std_1h]]
    pred = _clip(float(model.predict(row)[0]), 0, 100)
    delta = round((pred - cpu) / max(cpu, 1) * 100, 1)
    mae = _METRICS.get("cpu", {}).get("mae", 4.0)
    confidence = round(_clip(1.0 - mae / 100, 0.5, 0.99), 2)
    return Forecast(round(cpu, 2), round(pred, 2), delta, _detect_anomaly("cpu", pred), confidence)


def predict_memory(memory: float, hour: float, day_of_week: int,
                   memory_rolling_avg_1h: float | None = None,
                   memory_rolling_std_1h: float = 0.0) -> Forecast:
    try:
        model = _load("memory")
        if memory_rolling_avg_1h is None:
            memory_rolling_avg_1h = memory
        row = [[memory, hour, day_of_week, memory_rolling_avg_1h, memory_rolling_std_1h]]
        pred = _clip(float(model.predict(row)[0]), 0, 100)
    except FileNotFoundError:
        pred = memory * 1.02  # graceful fallback
    delta = round((pred - memory) / max(memory, 1) * 100, 1)
    return Forecast(round(memory, 2), round(pred, 2), delta, _detect_anomaly("memory", pred), 0.88)


def predict_network(network: float, hour: float, day_of_week: int,
                    network_rolling_avg_1h: float | None = None,
                    network_rolling_std_1h: float = 0.0) -> Forecast:
    try:
        model = _load("network")
        if network_rolling_avg_1h is None:
            network_rolling_avg_1h = network
        row = [[network, hour, day_of_week, network_rolling_avg_1h, network_rolling_std_1h]]
        pred = _clip(float(model.predict(row)[0]), 0, 5000)
    except FileNotFoundError:
        pred = network * 1.01
    delta = round((pred - network) / max(network, 1) * 100, 1)
    return Forecast(round(network, 2), round(pred, 2), delta, _detect_anomaly("network", pred), 0.85)


def predict_cost(cpu: float, memory: float, cost_usd: float,
                 hour: float, day_of_week: int) -> Forecast:
    try:
        model = _load("cost")
        row = [[cpu, memory, cost_usd, hour, day_of_week]]
        pred = _clip(float(model.predict(row)[0]), 0, 50)
    except FileNotFoundError:
        pred = cost_usd * (1 + (cpu / 100) * 0.1)
    delta = round((pred - cost_usd) / max(cost_usd, 0.001) * 100, 1)
    return Forecast(round(cost_usd, 4), round(pred, 4), delta, _detect_anomaly("cost", pred), 0.87)


def predict_carbon(intensity: float, hour: float, day_of_week: int, cpu: float) -> Forecast:
    try:
        model = _load("carbon")
        row = [[intensity, hour, day_of_week, cpu]]
        pred = _clip(float(model.predict(row)[0]), 0, 2000)
    except FileNotFoundError:
        pred = intensity * 0.35 * 0.25  # kwh estimate
    delta = round((pred - intensity * 0.35 * 0.25) / max(intensity * 0.35 * 0.25, 0.1) * 100, 1)
    return Forecast(round(intensity * 0.35 * 0.25, 2), round(pred, 2), delta, _detect_anomaly("carbon", pred), 0.86)


def model_info() -> dict:
    try:
        _load("cpu")
    except FileNotFoundError:
        pass
    return _METRICS


def predict_all(
    cpu: float,
    memory: float = 50.0,
    network: float = 500.0,
    cost_usd: float = 0.25,
    carbon_intensity: float = 350.0,
    hour: float = 12.0,
    day_of_week: int = 0,
) -> dict[str, Forecast]:
    return {
        "cpu": predict_cpu(cpu, hour, day_of_week),
        "memory": predict_memory(memory, hour, day_of_week),
        "network": predict_network(network, hour, day_of_week),
        "cost": predict_cost(cpu, memory, cost_usd, hour, day_of_week),
        "carbon": predict_carbon(carbon_intensity, hour, day_of_week, cpu),
    }
