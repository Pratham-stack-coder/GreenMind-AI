"""
Digital Twin Simulation Scenarios.
Defines calculation logic for standard cloud optimization scenarios.
"""

from __future__ import annotations

from typing import Any
from .schemas import StateSnapshot


def apply_scenario(scenario: str, before: StateSnapshot) -> tuple[StateSnapshot, float, float, str, str, str]:
    """
    Applies standard simulation scenario.
    Returns:
    (after_snapshot, estimated_saving, estimated_carbon_reduction, performance_impact, risk, recommendation)
    """
    scenario_clean = scenario.upper().replace("-", "_").strip()

    if scenario_clean == "RIGHT_SIZE":
        # Right sizing: modern instance family reduces cost & carbon by 25-30% while maintaining healthy ~65-72% CPU
        after_cpu = round(min(85.0, max(25.0, before.cpu * 0.90)), 1)
        after_mem = round(min(80.0, max(30.0, before.memory * 0.88)), 1)
        after_cost = round(before.cost * 0.75, 2)
        after_carbon = round(before.carbon * 0.80, 2)
        monthly_saving = round(before.cost * 0.25 * 24 * 30, 2)
        monthly_carbon_red = round(before.carbon * 0.20 * 24 * 30 / 1000, 3)

        after = StateSnapshot(
            cpu=after_cpu,
            memory=after_mem,
            cost=after_cost,
            carbon=after_carbon,
            instance_count=before.instance_count,
            monthly_cost=round(after_cost * 24 * 30, 2),
            monthly_carbon_kg=round(after_carbon * 24 * 30 / 1000, 3),
        )
        return (
            after,
            monthly_saving,
            monthly_carbon_red,
            "Stable — workload stays comfortably within memory headroom with negligible latency delta",
            "LOW",
            "Recommended for immediate execution: 25% cost reduction and 20% carbon emissions cut.",
        )

    elif scenario_clean == "SCALE_UP":
        # Scale up: add capacity; CPU and memory utilization decrease, cost and carbon increase
        after_cpu = round(max(15.0, before.cpu * 0.55), 1)
        after_mem = round(max(20.0, before.memory * 0.60), 1)
        after_cost = round(before.cost * 1.60, 2)
        after_carbon = round(before.carbon * 1.55, 2)
        monthly_saving = round(-before.cost * 0.60 * 24 * 30, 2)  # negative = increased cost
        monthly_carbon_red = round(-before.carbon * 0.55 * 24 * 30 / 1000, 3)

        after = StateSnapshot(
            cpu=after_cpu,
            memory=after_mem,
            cost=after_cost,
            carbon=after_carbon,
            instance_count=before.instance_count + 1,
            monthly_cost=round(after_cost * 24 * 30, 2),
            monthly_carbon_kg=round(after_carbon * 24 * 30 / 1000, 3),
        )
        return (
            after,
            monthly_saving,
            monthly_carbon_red,
            "High performance — p99 latency decreases by estimated 35%, headroom doubled",
            "LOW",
            "Provides maximum headroom for bursty traffic; costs $ " + f"{abs(monthly_saving):.0f}" + "/month more.",
        )

    elif scenario_clean == "SCALE_DOWN":
        # Scale down: terminate or reduce instance size; CPU increases, cost and carbon drop
        after_cpu = round(min(96.0, before.cpu * 1.65), 1)
        after_mem = round(min(92.0, before.memory * 1.50), 1)
        after_cost = round(before.cost * 0.55, 2)
        after_carbon = round(before.carbon * 0.60, 2)
        monthly_saving = round(before.cost * 0.45 * 24 * 30, 2)
        monthly_carbon_red = round(before.carbon * 0.40 * 24 * 30 / 1000, 3)
        risk = "HIGH" if after_cpu > 85 else "MEDIUM"

        after = StateSnapshot(
            cpu=after_cpu,
            memory=after_mem,
            cost=after_cost,
            carbon=after_carbon,
            instance_count=max(1, before.instance_count - 1),
            monthly_cost=round(after_cost * 24 * 30, 2),
            monthly_carbon_kg=round(after_carbon * 24 * 30 / 1000, 3),
        )
        return (
            after,
            monthly_saving,
            monthly_carbon_red,
            f"Tighter headroom — CPU load rises to {after_cpu}%; monitoring and autoscaling required",
            risk,
            f"Maximizes savings (${monthly_saving:.0f}/mo), but monitor CPU headroom during peak hours.",
        )

    elif scenario_clean == "CONSOLIDATE":
        # Consolidate: merge multiple low-utilization nodes into denser instances
        after_cpu = round(min(80.0, max(45.0, before.cpu * 1.35)), 1)
        after_mem = round(min(75.0, max(40.0, before.memory * 1.25)), 1)
        after_cost = round(before.cost * 0.65, 2)
        after_carbon = round(before.carbon * 0.68, 2)
        monthly_saving = round(before.cost * 0.35 * 24 * 30, 2)
        monthly_carbon_red = round(before.carbon * 0.32 * 24 * 30 / 1000, 3)

        after = StateSnapshot(
            cpu=after_cpu,
            memory=after_mem,
            cost=after_cost,
            carbon=after_carbon,
            instance_count=max(1, before.instance_count // 2 or 1),
            monthly_cost=round(after_cost * 24 * 30, 2),
            monthly_carbon_kg=round(after_carbon * 24 * 30 / 1000, 3),
        )
        return (
            after,
            monthly_saving,
            monthly_carbon_red,
            "Optimal density — higher bin-packing efficiency with balanced failure domain redundancy",
            "LOW",
            f"Consolidation saves ${monthly_saving:.0f}/mo and trims Scope 2 carbon by 32%.",
        )

    elif scenario_clean in ["REGION_MIGRATION", "REGION_MIGRATE"]:
        # Region Migration: e.g. shifting workload to hydro/nuclear green grid (e.g. eu-north-1 / us-west-2)
        # Slashes carbon emissions by 75% with negligible compute cost difference (~5% savings in cold climate regions)
        after_cpu = before.cpu
        after_mem = before.memory
        after_cost = round(before.cost * 0.95, 2)
        after_carbon = round(before.carbon * 0.25, 2)
        monthly_saving = round(before.cost * 0.05 * 24 * 30, 2)
        monthly_carbon_red = round(before.carbon * 0.75 * 24 * 30 / 1000, 3)

        after = StateSnapshot(
            cpu=after_cpu,
            memory=after_mem,
            cost=after_cost,
            carbon=after_carbon,
            instance_count=before.instance_count,
            monthly_cost=round(after_cost * 24 * 30, 2),
            monthly_carbon_kg=round(after_carbon * 24 * 30 / 1000, 3),
        )
        return (
            after,
            monthly_saving,
            monthly_carbon_red,
            "Clean energy grid — 75% Scope 2 carbon drop with +18ms ingress latency for North American users",
            "LOW",
            f"Region migration cuts carbon footprint by {monthly_carbon_red:.2f} kgCO2/mo with minor egress considerations.",
        )

    # Fallback / Custom
    after = StateSnapshot(
        cpu=round(before.cpu * 0.85, 1),
        memory=round(before.memory * 0.85, 1),
        cost=round(before.cost * 0.85, 2),
        carbon=round(before.carbon * 0.85, 2),
        instance_count=before.instance_count,
        monthly_cost=round(before.cost * 0.85 * 24 * 30, 2),
        monthly_carbon_kg=round(before.carbon * 0.85 * 24 * 30 / 1000, 3),
    )
    return (
        after,
        round(before.cost * 0.15 * 24 * 30, 2),
        round(before.carbon * 0.15 * 24 * 30 / 1000, 3),
        "Estimated moderate reduction across dimensions",
        "LOW",
        "Custom scenario simulation completed.",
    )

