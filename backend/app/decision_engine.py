"""
Decision engine: turns a CPU forecast + carbon curve + cost model into one
recommendation -- what size to run, and when.

This is the core "unique" piece of GreenMind AI: instead of only recommending
an instance size (what most cost-optimizer projects do), it also recommends a
WHEN, using time-of-day carbon intensity, and it reports its recommendation
against an explicit baseline so the improvement claim is checkable rather than
asserted.

RISK_THRESHOLDS and COST_PER_INSTANCE_HOUR are deliberately simple and
centralized here -- swap them for real billing/instance data when wiring up a
live cloud account.
"""

from dataclasses import dataclass

from . import carbon

RISK_THRESHOLDS = {"low": 70, "medium": 85}  # predicted CPU % boundaries

# Illustrative on-demand cost per instance-hour, USD. Deferring a workload a
# few hours does not change this in the demo model -- only the carbon
# intensity changes with time. (A real model could also fold in spot-price
# variation by hour; left out here to keep the recommendation logic legible.)
COST_PER_INSTANCE_HOUR = 0.192
ESTIMATED_KWH_PER_INSTANCE_HOUR = 0.35  # rough draw for a mid-size instance


@dataclass
class ScheduleRecommendation:
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


def classify_risk(predicted_cpu: float) -> str:
    if predicted_cpu < RISK_THRESHOLDS["low"]:
        return "LOW"
    if predicted_cpu < RISK_THRESHOLDS["medium"]:
        return "MEDIUM"
    return "HIGH"


def estimate_emissions_gco2(hours: float, carbon_intensity_gco2_per_kwh: float) -> float:
    return round(hours * ESTIMATED_KWH_PER_INSTANCE_HOUR * carbon_intensity_gco2_per_kwh, 2)


def recommend(
    predicted_cpu: float,
    current_hour: int,
    region: str = carbon.DEFAULT_REGION,
    job_duration_hours: float = 1.0,
    deferrable: bool = True,
    max_defer_hours: int = 12,
) -> ScheduleRecommendation:
    """
    `deferrable` matters: not every workload can wait (e.g. a live user-facing
    request can't be scheduled for 2am). GreenMind should never suggest
    deferring latency-sensitive work -- that's a correctness bug, not just a
    UX detail.
    """
    risk = classify_risk(predicted_cpu)
    now_intensity = carbon.get_carbon_intensity(region, current_hour)
    carbon_now = estimate_emissions_gco2(
        job_duration_hours, now_intensity["carbon_intensity_gco2_per_kwh"]
    )
    cost_now = round(job_duration_hours * COST_PER_INSTANCE_HOUR, 3)

    # Baseline for comparison: "run it now, always" -- the naive approach most
    # cost-optimizer tools default to.
    baseline_carbon = carbon_now

    if not deferrable or risk == "HIGH":
        # HIGH risk workloads should scale/run now for reliability, not be
        # deferred for a carbon saving -- correctness before optimization.
        return ScheduleRecommendation(
            predicted_cpu=predicted_cpu,
            risk=risk,
            region=now_intensity["region"],
            current_hour=current_hour,
            recommended_hour=current_hour,
            hours_to_wait=0,
            cost_now_usd=cost_now,
            cost_at_recommended_time_usd=cost_now,
            carbon_now_gco2=carbon_now,
            carbon_at_recommended_time_gco2=carbon_now,
            carbon_reduction_pct=0.0,
            baseline_carbon_gco2=baseline_carbon,
            action="RUN_NOW",
            reason=(
                "Workload is not deferrable or predicted load is HIGH risk -- "
                "scheduling for reliability rather than carbon savings."
            ),
        )

    window = carbon.find_greenest_window(region, current_hour, max_defer_hours)
    best = window["best_hour_intensity"]
    carbon_later = estimate_emissions_gco2(
        job_duration_hours, best["carbon_intensity_gco2_per_kwh"]
    )
    cost_later = cost_now  # demo cost model: on-demand price doesn't shift by hour

    if window["hours_from_now"] == 0:
        action = "RUN_NOW"
        reason = "Current hour is already the greenest point in the window."
    else:
        action = "DEFER"
        reason = (
            f"Deferring {window['hours_from_now']}h reduces estimated emissions "
            f"by {window['estimated_carbon_reduction_pct']}% for this job, "
            "with no change to on-demand cost."
        )

    return ScheduleRecommendation(
        predicted_cpu=predicted_cpu,
        risk=risk,
        region=now_intensity["region"],
        current_hour=current_hour,
        recommended_hour=best["hour"],
        hours_to_wait=window["hours_from_now"],
        cost_now_usd=cost_now,
        cost_at_recommended_time_usd=cost_later,
        carbon_now_gco2=carbon_now,
        carbon_at_recommended_time_gco2=carbon_later,
        carbon_reduction_pct=window["estimated_carbon_reduction_pct"],
        baseline_carbon_gco2=baseline_carbon,
        action=action,
        reason=reason,
    )
