from pydantic import BaseModel, Field


class CloudMetrics(BaseModel):
    timestamp: str
    region: str
    cpu: float
    memory: float
    storage: float
    network: float
    source: str = Field(description="DEMO or LIVE")


class PredictRequest(BaseModel):
    cpu: float
    hour: float = Field(ge=0, le=23.99, description="Hour of day, 0-23.99")
    day_of_week: int = Field(ge=0, le=6)
    cpu_rolling_avg_1h: float | None = None
    cpu_rolling_std_1h: float = 0.0


class PredictResponse(BaseModel):
    current_cpu: float
    predicted_cpu: float
    risk: str
    model_mae: float | None = None


class ScheduleRequest(BaseModel):
    predicted_cpu: float
    current_hour: int = Field(ge=0, le=23)
    region: str = "us-east"
    job_duration_hours: float = 1.0
    deferrable: bool = True
    max_defer_hours: int = 12


class ScheduleResponse(BaseModel):
    predicted_cpu: float
    risk: str
    region: str
    current_hour: int
    recommended_hour: int
    hours_to_wait: int
    cost_now_usd: float
    cost_at_recommended_time_usd: float
    carbon_now_gco2: float
    carbon_at_recommended_time_gco2: float
    carbon_reduction_pct: float
    baseline_carbon_gco2: float
    action: str
    reason: str
