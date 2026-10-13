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
from ..services.scoring import compute_optimization_scores


class DigitalTwinSimulator:
    """Non-destructive simulation engine for GreenMind AI infrastructure digital twin."""

    def run_simulation(self, req: SimulationScenarioRequest) -> ScenarioSimulationResult:
        sim_id = str(uuid.uuid4())[:8]

        # Use current state if provided, otherwise default realistic cloud state
        before = req.current_state or StateSnapshot(
            cpu=80.0,
            memory=65.0,
            cost=1.20,
            carbon=150.0,
            instance_count=4,
            monthly_cost=864.0,
            monthly_carbon_kg=108.0,
        )

        after, saving, carbon_red, perf_impact, risk, recommendation = apply_scenario(
            req.scenario,
            before,
            target_region=req.target_region or req.region,
        )

        # Recalculate baseline and projected optimization scores from actual snapshots
        baseline_score = compute_optimization_scores(
            cpu=before.cpu,
            memory=before.memory,
            cost_usd_per_hour=before.cost,
            carbon_gco2_per_hour=before.carbon,
            instance_count=before.instance_count,
            region=req.region,
            source="SIMULATED",
        )

        projected_score = compute_optimization_scores(
            cpu=after.cpu,
            memory=after.memory,
            cost_usd_per_hour=after.cost,
            carbon_gco2_per_hour=after.carbon,
            instance_count=after.instance_count,
            region=req.target_region or req.region,
            source="SIMULATED",
            is_simulated=True,
            baseline_overall=baseline_score.overall,
        )

        delta = projected_score.overall - baseline_score.overall
        if delta == 0:
            scoring_explanation = (
                f"Optimization score remains at {baseline_score.overall}/100: "
                "the simulated scenario metrics remain within baseline scoring brackets."
            )
        elif delta > 0:
            scoring_explanation = (
                f"Optimization score projected to improve from {baseline_score.overall}/100 "
                f"to {projected_score.overall}/100 (+{delta} pts) through improved efficiency."
            )
        else:
            scoring_explanation = (
                f"Optimization score projected to shift from {baseline_score.overall}/100 "
                f"to {projected_score.overall}/100 ({delta} pts) due to increased capacity cost."
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
            baseline_score=baseline_score.overall,
            projected_score=projected_score.overall,
            score_delta=delta,
            scoring_explanation=scoring_explanation,
            warnings=[
                "Simulation result only — no live cloud infrastructure was altered.",
                "Actual savings may vary based on spot market fluctuations and regional grid carbon intensity shifts.",
            ],
        )


simulator = DigitalTwinSimulator()
