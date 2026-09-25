"""Comprehensive ML Model validation tests for GreenMind AI.
Validates that all five independent Gradient Boosting models exist, load properly,
achieve documented benchmark criteria (CPU MAE < 4%), and produce valid forecasts.
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pytest

from app.ml.predictor import (
    MODEL_DIR,
    METRICS_FILE,
    FEATURE_IMPORTANCE_FILE,
    get_multi_predictor,
    predict_next_cpu,
)


def test_ml_artifacts_exist():
    """Verify all 5 trained models and metadata files exist on disk."""
    required_files = [
        "cpu_model.pkl",
        "memory_model.pkl",
        "network_model.pkl",
        "cost_model.pkl",
        "carbon_model.pkl",
        "metrics.json",
        "feature_importance.json",
    ]
    for filename in required_files:
        filepath = MODEL_DIR / filename
        assert filepath.exists(), f"Missing required ML artifact: {filename}"
        assert filepath.stat().st_size > 0, f"Artifact {filename} is empty"


def test_metrics_evaluation_criteria():
    """Verify evaluation metrics meet documented specifications."""
    assert METRICS_FILE.exists()
    with open(METRICS_FILE, "r") as f:
        metrics = json.load(f)

    for target in ["cpu", "memory", "network", "cost", "carbon"]:
        assert target in metrics, f"Missing target {target} in metrics.json"
        m = metrics[target]
        assert "mae" in m and "rmse" in m and "r2" in m
        assert m["n_train"] > 0
        assert m["n_test"] > 0
        assert m["mae"] > 0

    # Explicit requirement: CPU MAE < 4.0%
    assert metrics["cpu"]["mae"] < 4.0, f"CPU MAE was {metrics['cpu']['mae']}%, expected < 4.0%"
    # Verify R2 score is positive and predictive
    assert metrics["cpu"]["r2"] > 0.80, f"CPU R2 was {metrics['cpu']['r2']}, expected > 0.80"


def test_feature_importance_metadata():
    """Verify feature importances are recorded for all targets."""
    assert FEATURE_IMPORTANCE_FILE.exists()
    with open(FEATURE_IMPORTANCE_FILE, "r") as f:
        fi = json.load(f)

    for target in ["cpu", "memory", "network", "cost", "carbon"]:
        assert target in fi, f"Missing feature importance for {target}"
        assert len(fi[target]) > 0
        total_importance = sum(fi[target].values())
        assert 0.95 <= total_importance <= 1.05, f"Feature importances for {target} do not sum to ~1.0"


def test_all_models_load_and_predict():
    """Load each of the 5 model pkl files and test direct inference."""
    targets = {
        "cpu": 5,      # cpu, hour, day_of_week, rolling_avg, rolling_std
        "memory": 5,   # memory, hour, day_of_week, rolling_avg, rolling_std
        "network": 5,  # network, hour, day_of_week, rolling_avg, rolling_std
        "cost": 5,     # cpu, memory, cost_usd, hour, day_of_week
        "carbon": 4,   # carbon_intensity, hour, day_of_week, cpu
    }

    for target, n_features in targets.items():
        model_path = MODEL_DIR / f"{target}_model.pkl"
        model = joblib.load(model_path)
        assert hasattr(model, "predict"), f"Model for {target} missing predict method"

        # Create dummy sample feature vector
        sample = np.ones((1, n_features), dtype=float)
        pred = model.predict(sample)
        assert len(pred) == 1
        assert not np.isnan(pred[0])


def test_multi_predictor_instance():
    """Verify MultiMetricPredictor loads all 5 models and runs 60-min multi-step forecast."""
    predictor = get_multi_predictor()
    assert predictor.is_loaded is True

    # Test single-step prediction
    preds = predictor.predict_all(
        cpu=50.0,
        memory=60.0,
        network=200.0,
        cost=0.19,
        carbon=40.0,
        hour=14,
        day_of_week=2,
    )
    for target in ["cpu", "memory", "network", "cost", "carbon"]:
        assert target in preds
        assert isinstance(preds[target], float)
        assert preds[target] > 0

    # Test 60-minute forecast (12 x 5-minute steps)
    forecasts = predictor.forecast_multi_step(
        current_metrics={
            "cpu": 55.0,
            "memory": 62.0,
            "network": 250.0,
            "cost": 0.20,
            "carbon": 45.0,
        },
        steps=12,
        current_hour=14,
        current_day=2,
    )
    for target in ["cpu", "memory", "network", "cost", "carbon"]:
        assert target in forecasts
        assert len(forecasts[target]) == 12
        for point in forecasts[target]:
            assert "step" in point
            assert "predicted" in point
            assert "timestamp" in point


def test_legacy_predictor_compatibility():
    """Verify legacy single-metric predictor function remains fully functional."""
    result = predict_next_cpu(current_cpu=55.0, hour=14.0, day_of_week=2.0)
    assert "current_cpu" in result
    assert "predicted_cpu" in result
    assert "risk" in result
    assert result["risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


def test_temporal_persistence_baselines():
    """Verify temporal persistence baseline calculations in baseline.py."""
    from app.ml.baseline import (
        evaluate_temporal_persistence,
        evaluate_rolling_mean,
        evaluate_seasonal,
    )
    series = np.array([10.0, 12.0, 15.0, 14.0, 16.0, 18.0, 20.0, 19.0])
    y_true = series[1:]
    y_prev = series[:-1]

    persistence = evaluate_temporal_persistence(y_true, y_prev)
    assert persistence.mae > 0
    assert persistence.rmse >= persistence.mae

    rolling = evaluate_rolling_mean(series, window=3)
    assert rolling.mae > 0

    seasonal = evaluate_seasonal(series, period=2)
    assert seasonal.mae > 0

