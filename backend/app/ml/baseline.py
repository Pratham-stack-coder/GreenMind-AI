r"""
Temporal Baselines for Time-Series Forecasting.

DATA TRUTH & SOUNDNESS:
Baselines evaluate temporal persistence on each metric's OWN historical observations:
1. Last-Value (Persistence) Baseline: \hat{y}_t = y_{t-1}
2. Rolling Mean Baseline: \hat{y}_t = (1/k) \sum_{i=1}^k y_{t-i}
3. Hourly Seasonal Baseline: \hat{y}_t = y_{t-24h}

Cross-metric comparisons (e.g. comparing future cost to current CPU) are strictly forbidden.
"""

from __future__ import annotations

from typing import NamedTuple
import numpy as np
import pandas as pd


class BaselineMetrics(NamedTuple):
    mae: float
    rmse: float
    mape: float


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> BaselineMetrics:
    """Calculate MAE, RMSE, and MAPE between ground truth and predictions."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    denom = np.where(np.abs(y_true) < 1e-4, 1.0, np.abs(y_true))
    mape = float(np.mean(np.abs((y_true - y_pred) / denom)) * 100.0)
    return BaselineMetrics(round(mae, 4), round(rmse, 4), round(mape, 2))


def evaluate_temporal_persistence(y_true: np.ndarray, y_prev: np.ndarray) -> BaselineMetrics:
    r"""Evaluates 1-step ahead temporal persistence baseline: \hat{y}_t = y_{t-1}."""
    return compute_metrics(y_true, y_prev)


def evaluate_rolling_mean(series: pd.Series | np.ndarray, window: int = 4) -> BaselineMetrics:
    """Evaluates rolling average baseline of preceding k time steps."""
    arr = np.asarray(series, dtype=float)
    if len(arr) <= window:
        if len(arr) < 2:
            return BaselineMetrics(0.0, 0.0, 0.0)
        return compute_metrics(arr[1:], arr[:-1])
    y_true = arr[window:]
    y_pred = np.array([np.mean(arr[i : i + window]) for i in range(len(arr) - window)])
    return compute_metrics(y_true, y_pred)


def evaluate_seasonal(series: pd.Series | np.ndarray, period: int = 24) -> BaselineMetrics:
    """Evaluates seasonal lag baseline (e.g., 24 steps back)."""
    arr = np.asarray(series, dtype=float)
    if len(arr) <= period:
        if len(arr) < 2:
            return BaselineMetrics(0.0, 0.0, 0.0)
        return compute_metrics(arr[1:], arr[:-1])
    y_true = arr[period:]
    y_pred = arr[:-period]
    return compute_metrics(y_true, y_pred)
