"""Predictions router — multi-metric ML forecasting."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from .. import carbon
from ..decision_engine import classify_risk_multi
from ..ml import predictor
from ..schemas import MetricForecast, PredictRequest, PredictResponse

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post("/forecast", response_model=PredictResponse)
def forecast(req: PredictRequest):
    """Multi-metric forecast: CPU, memory, network, cost, carbon."""
    try:
        now = datetime.now(timezone.utc)
        hour = req.hour if req.hour is not None else (now.hour + now.minute / 60.0)
        dow = req.day_of_week if req.day_of_week is not None else now.weekday()

        # Carbon intensity for the current region/hour
        intensity = carbon.get_carbon_intensity(req.region, int(hour))["carbon_intensity_gco2_per_kwh"]
        cost_usd = req.cpu / 100 * 0.35 + 0.05  # rough demo estimate

        forecasts = predictor.predict_all(
            cpu=req.cpu,
            memory=req.memory,
            network=req.network,
            cost_usd=cost_usd,
            carbon_intensity=intensity,
            hour=hour,
            day_of_week=dow,
        )

        def to_schema(fc: predictor.Forecast) -> MetricForecast:
            return MetricForecast(
                current=fc.current,
                predicted=fc.predicted,
                delta_pct=fc.delta_pct,
                anomaly=fc.anomaly,
                confidence=fc.confidence,
            )

        risk = classify_risk_multi(forecasts["cpu"].predicted, forecasts["memory"].predicted)
        info = predictor.model_info()
        mae = info.get("cpu", {}).get("mae") if info else None

        return PredictResponse(
            cpu=to_schema(forecasts["cpu"]),
            memory=to_schema(forecasts["memory"]),
            network=to_schema(forecasts["network"]),
            cost_usd_per_hour=to_schema(forecasts["cost"]),
            carbon_gco2_per_hour=to_schema(forecasts["carbon"]),
            risk=risk,
            model_mae=mae,
            horizon_minutes=60,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/model-info")
def model_info():
    """Return ML model evaluation metrics."""
    info = predictor.model_info()
    return {"models": info, "status": "loaded" if info else "not_trained"}
