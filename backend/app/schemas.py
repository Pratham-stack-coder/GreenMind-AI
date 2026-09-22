"""
Expanded Pydantic schemas — request/response models for all API endpoints.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Telemetry ─────────────────────────────────────────────────────────────────

class CloudMetrics(BaseModel):
    timestamp: str
    provider: str = "aws"
    region: str
    cpu: float
    memory: float
    storage: float
    network: float
    cost_usd_per_hour: float = 0.0
    carbon_gco2_per_hour: float = 0.0
    instance_count: int = 1
    source: Literal["DEMO", "LIVE"] = "DEMO"


class TelemetryHistoryResponse(BaseModel):
    entries: list[CloudMetrics]
    count: int


# ── Predictions ───────────────────────────────────────────────────────────────

class PredictRequest(BaseModel):
    cpu: float = Field(ge=0, le=100)
    memory: float = Field(default=50.0, ge=0, le=100)
    network: float = Field(default=500.0, ge=0)
    hour: float | None = Field(default=None, ge=0, le=23.99, description="Hour of day, 0-23.99")
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    cpu_rolling_avg_1h: float | None = None
    cpu_rolling_std_1h: float = 0.0
    provider: str = "aws"
    region: str = "us-east"


class MetricForecast(BaseModel):
    current: float
    predicted: float
    delta_pct: float
    anomaly: bool = False
    confidence: float = 0.9


class PredictResponse(BaseModel):
    cpu: MetricForecast
    memory: MetricForecast
    network: MetricForecast
    cost_usd_per_hour: MetricForecast
    carbon_gco2_per_hour: MetricForecast
    risk: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    model_mae: float | None = None
    horizon_minutes: int = 60


# ── Schedule / Carbon ─────────────────────────────────────────────────────────

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


# ── Recommendations ───────────────────────────────────────────────────────────

class RecommendationItem(BaseModel):
    id: str
    category: Literal["cost", "performance", "sustainability", "security", "reliability"]
    priority: Literal["critical", "high", "medium", "low"]
    title: str
    description: str
    impact_summary: str
    estimated_monthly_savings_usd: float = 0.0
    estimated_carbon_reduction_pct: float = 0.0
    effort: Literal["low", "medium", "high"] = "medium"
    action: str
    evidence: list[str] = []
    confidence: float = 0.85


class RecommendationsResponse(BaseModel):
    recommendations: list[RecommendationItem]
    generated_at: str
    optimization_score: int  # 0-100


class ExplainRequest(BaseModel):
    recommendation_id: str


class ExplainResponse(BaseModel):
    recommendation_id: str
    title: str
    why_flagged: str
    data_evidence: list[dict[str, Any]]
    counterfactual: str
    steps_to_implement: list[str]
    expected_outcome: str


# ── Multi-Agent ───────────────────────────────────────────────────────────────

class AgentRunRequest(BaseModel):
    provider: str = "aws"
    region: str = "us-east"
    metrics: CloudMetrics | None = None  # if None, system fetches live


class AgentResult(BaseModel):
    agent: str
    status: Literal["completed", "skipped", "error"]
    findings: list[str]
    recommendations: list[RecommendationItem]
    score: int  # 0-100 domain score


class AgentRunResponse(BaseModel):
    run_id: str
    started_at: str
    completed_at: str
    agents: list[AgentResult]
    unified_recommendations: list[RecommendationItem]
    overall_score: int
    summary: str


# ── Digital Twin ──────────────────────────────────────────────────────────────

class InstanceChange(BaseModel):
    action: Literal["resize", "scale_out", "scale_in", "migrate", "consolidate", "terminate"]
    instance_type_from: str = "m5.large"
    instance_type_to: str | None = None
    scale_factor: float = 1.0  # for scale_out / scale_in
    target_region: str | None = None  # for migrate


class SimulationRequest(BaseModel):
    baseline_metrics: CloudMetrics
    changes: list[InstanceChange]
    simulation_hours: float = 24.0


class SimulationMetrics(BaseModel):
    cpu: float
    memory: float
    cost_usd_per_hour: float
    carbon_gco2_per_hour: float
    monthly_cost_usd: float
    monthly_carbon_kgco2: float


class SimulationResult(BaseModel):
    simulation_id: str
    before: SimulationMetrics
    after: SimulationMetrics
    delta: dict[str, float]  # % changes
    recommendation: str
    confidence: float
    warnings: list[str] = []


# ── Copilot ───────────────────────────────────────────────────────────────────

class CopilotMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class CopilotRequest(BaseModel):
    message: str
    history: list[CopilotMessage] = []
    context: dict[str, Any] = {}


class CopilotResponse(BaseModel):
    reply: str
    actions: list[dict[str, Any]] = []
    charts: list[dict[str, Any]] = []
    follow_up_suggestions: list[str] = []


# ── Analytics ─────────────────────────────────────────────────────────────────

class CostDataPoint(BaseModel):
    timestamp: str
    cost_usd: float
    provider: str
    region: str
    category: str = "compute"


class CarbonDataPoint(BaseModel):
    timestamp: str
    carbon_gco2: float
    provider: str
    region: str
    intensity_gco2_per_kwh: float


class OptimizationScores(BaseModel):
    overall: int
    cost: int
    performance: int
    sustainability: int
    security: int
    reliability: int
    trend: Literal["improving", "stable", "declining"] = "stable"


class CostAnalyticsResponse(BaseModel):
    period_days: int
    total_usd: float
    data_points: list[CostDataPoint]
    breakdown_by_provider: dict[str, float]
    top_cost_drivers: list[str]


class CarbonAnalyticsResponse(BaseModel):
    period_days: int
    total_gco2: float
    data_points: list[CarbonDataPoint]
    breakdown_by_region: dict[str, float]
    green_hours_pct: float
