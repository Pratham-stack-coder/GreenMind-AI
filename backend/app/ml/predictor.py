"""Loads the trained model and exposes a single predict() function."""

import json
from pathlib import Path

import joblib

HERE = Path(__file__).resolve().parent
_model = None
_metrics = None

FEATURES = ["cpu", "hour", "day_of_week", "cpu_rolling_avg_1h", "cpu_rolling_std_1h"]


def _load():
    global _model, _metrics
    if _model is None:
        model_path = HERE / "model.pkl"
        if not model_path.exists():
            raise FileNotFoundError(
                "model.pkl not found -- run `python train.py` inside "
                "backend/app/ml/ first."
            )
        _model = joblib.load(model_path)
        metrics_path = HERE / "metrics.json"
        _metrics = json.loads(metrics_path.read_text()) if metrics_path.exists() else {}
    return _model


def model_info() -> dict:
    _load()
    return _metrics


def predict_future_cpu(
    cpu: float,
    hour: float,
    day_of_week: int,
    cpu_rolling_avg_1h: float | None = None,
    cpu_rolling_std_1h: float = 0.0,
) -> float:
    model = _load()
    if cpu_rolling_avg_1h is None:
        cpu_rolling_avg_1h = cpu  # reasonable fallback with no history yet
    row = [[cpu, hour, day_of_week, cpu_rolling_avg_1h, cpu_rolling_std_1h]]
    pred = model.predict(row)[0]
    return float(max(0.0, min(100.0, pred)))
