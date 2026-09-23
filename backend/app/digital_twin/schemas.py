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
    scenario: Literal["RIGHT_SIZE", "SCALE_UP", "SCALE_DOWN", "CONSOLIDATE", "CUSTOM"] = "RIGHT_SIZE"
    current_state: StateSnapshot | None = None
    target_instance_type: str | None = None
    scale_factor: float = 1.0
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
    warnings: list[str] = Field(default_factory=list)
