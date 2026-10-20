"""
Digital Twin Schemas.
Models for scenario-based simulation of infrastructure changes.
"""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


class StateSnapshot(BaseModel):
    cpu: float
    memory: float = 50.0
    cost: float
    carbon: float
    instance_count: int = 1
    monthly_cost: float = 0.0
    monthly_carbon_kg: float = 0.0


class SimulationScenarioRequest(BaseModel):
    scenario: Literal["RIGHT_SIZE", "SCALE_UP", "SCALE_DOWN", "CONSOLIDATE", "REGION_MIGRATION", "CUSTOM"] = "RIGHT_SIZE"
    current_state: StateSnapshot | None = None
    target_instance_type: str | None = None
    target_region: str | None = None
    scale_factor: float = 1.0
    provider: str = "aws"
    region: str = "us-east"
    simulation_hours: float = 24.0


class ScenarioSimulationResult(BaseModel):
    simulation_id: str
    scenario: str
    is_simulated: bool = True
    label: str = "SIMULATED / ESTIMATED"
    before: StateSnapshot
    after: StateSnapshot
    estimated_saving: float
    estimated_carbon_reduction: float
    performance_impact: str
    risk: Literal["LOW", "MEDIUM", "HIGH"]
    recommendation: str
    confidence: float = 0.85
    baseline_score: int | None = None
    projected_score: int | None = None
    score_delta: int | None = None
    scoring_explanation: str | None = None
    warnings: list[str] = Field(default_factory=list)
