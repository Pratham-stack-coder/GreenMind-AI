"""
Digital Twin Simulator Engine for GreenMind AI.
Runs safe, non-destructive simulations of cloud infrastructure changes.
DOES NOT touch or modify real cloud infrastructure.
"""

from __future__ import annotations

import uuid
from typing import Any

from .scenarios import apply_scenario
from .schemas import ScenarioSimulationResult, SimulationScenarioRequest, StateSnapshot


class DigitalTwinSimulator:
    """Non-destructive simulation engine for GreenMind AI infrastructure digital twin."""

    def run_simulation(self, req: SimulationScenarioRequest) -> ScenarioSimulationResult:
        sim_id = str(uuid.uuid4())[:8]

        # Use current state if provided, otherwise default realistic cloud state
        before = req.current_state or StateSnapshot(
            cpu=80.0,
            memory=65.0,
            cost=1000.0,
            carbon=6.2,
            instance_count=4,
            monthly_cost=1000.0,
            monthly_carbon_kg=6.2,
        )

        after, saving, carbon_red, perf_impact, risk, recommendation = apply_scenario(
            req.scenario, before
        )

        return ScenarioSimulationResult(
            simulation_id=sim_id,
            scenario=req.scenario,
            is_simulated=True,
            label="SIMULATED / ESTIMATED",
            before=before,
            after=after,
            estimated_saving=saving,
            estimated_carbon_reduction=carbon_red,
            performance_impact=perf_impact,
            risk=risk,
            recommendation=recommendation,
            confidence=0.88,
            warnings=[
                "Simulation result only — no live cloud infrastructure was altered.",
                "Actual savings may vary based on spot market fluctuations and regional grid carbon intensity shifts.",
            ],
        )


simulator = DigitalTwinSimulator()
