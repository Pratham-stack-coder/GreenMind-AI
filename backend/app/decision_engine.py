"""
Expanded decision engine — right-sizing, scaling, workload scheduling, and
carbon-aware recommendations with baseline comparisons.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import carbon

# ── Thresholds ────────────────────────────────────────────────────────────────

RISK_THRESHOLDS = {"low": 70, "medium": 85}   # CPU %
MEMORY_RISK_THRESHOLDS = {"low": 75, "medium": 90}

# On-demand cost per instance-hour (USD) — demo values
INSTANCE_COSTS: dict[str, float] = {
    "t3.micro": 0.0104,
    "t3.small": 0.0208,
    "t3.medium": 0.0416,
    "m5.large": 0.096,
    "m5.xlarge": 0.192,
    "m5.2xlarge": 0.384,
    "c5.large": 0.085,
    "c5.xlarge": 0.170,
    "r5.large": 0.126,
    "r5.xlarge": 0.252,
}

DEFAULT_INSTANCE = "m5.xlarge"


# ── Dataclasses ───────────────────────────────────────────────────────────────

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


@dataclass
class RightSizeRecommendation:
    current_instance: str
    recommended_instance: str
    reason: str
    monthly_savings_usd: float
    monthly_carbon_reduction_kgco2: float
    risk: str


@dataclass
class ScalingRecommendation:
    action: str  # "scale_out" | "scale_in" | "maintain"
    current_count: int
    recommended_count: int
    reason: str
    estimated_cost_delta_usd_hr: float


# ── Core functions ────────────────────────────────────────────────────────────

def classify_risk(predicted_cpu: float) -> str:
    if predicted_cpu < RISK_THRESHOLDS["low"]:
        return "LOW"
    if predicted_cpu < RISK_THRESHOLDS["medium"]:
        return "MEDIUM"
    return "HIGH"


def classify_risk_multi(cpu: float, memory: float) -> str:
    cpu_risk = classify_risk(cpu)
    mem_risk = "LOW" if memory < 75 else ("MEDIUM" if memory < 90 else "HIGH")
    priority = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
    worse = max(cpu_risk, mem_risk, key=lambda r: priority[r])
    if cpu > 95 and memory > 95:
        return "CRITICAL"
    return worse


def estimate_emissions_gco2(hours: float, carbon_intensity: float, instance: str = DEFAULT_INSTANCE) -> float:
    kwh = carbon.instance_kwh(instance) * hours
    return round(kwh * carbon_intensity, 2)


def recommend(
    predicted_cpu: float,
    current_hour: int,
    region: str = carbon.DEFAULT_REGION,
    job_duration_hours: float = 1.0,
    deferrable: bool = True,
    max_defer_hours: int = 12,
    instance_type: str = DEFAULT_INSTANCE,
) -> ScheduleRecommendation:
    """Carbon + cost aware scheduling recommendation."""
    risk = classify_risk(predicted_cpu)
    now_intensity = carbon.get_carbon_intensity(region, current_hour)
    carbon_now = estimate_emissions_gco2(
        job_duration_hours, now_intensity["carbon_intensity_gco2_per_kwh"], instance_type
    )
    cost_now = round(job_duration_hours * INSTANCE_COSTS.get(instance_type, 0.192), 3)
    baseline_carbon = carbon_now

    if not deferrable or risk == "HIGH":
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
            reason="Workload not deferrable or predicted load is HIGH — scheduling for reliability.",
        )

    window = carbon.find_greenest_window(region, current_hour, max_defer_hours)
    best = window["best_hour_intensity"]
    carbon_later = estimate_emissions_gco2(
        job_duration_hours, best["carbon_intensity_gco2_per_kwh"], instance_type
    )
    cost_later = cost_now  # on-demand price doesn't vary by hour in demo

    action = "RUN_NOW" if window["hours_from_now"] == 0 else "DEFER"
    reason = (
        "Current hour is already the greenest in the window."
        if action == "RUN_NOW"
        else (
            f"Deferring {window['hours_from_now']}h reduces estimated emissions "
            f"by {window['estimated_carbon_reduction_pct']}% with no cost change."
        )
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


def right_size(
    cpu_avg: float,
    memory_avg: float,
    current_instance: str = "m5.xlarge",
) -> RightSizeRecommendation:
    """Recommend a smaller or larger instance based on observed utilization."""
    instances_ordered = [
        "t3.micro", "t3.small", "t3.medium",
        "m5.large", "m5.xlarge", "m5.2xlarge",
    ]
    current_idx = instances_ordered.index(current_instance) if current_instance in instances_ordered else 3

    if cpu_avg < 20 and memory_avg < 40 and current_idx > 0:
        recommended = instances_ordered[current_idx - 1]
        reason = f"Average CPU {cpu_avg:.0f}% and memory {memory_avg:.0f}% — significantly under-utilized."
        risk = "LOW"
    elif cpu_avg > 80 or memory_avg > 85:
        recommended = instances_ordered[min(current_idx + 1, len(instances_ordered) - 1)]
        reason = f"CPU {cpu_avg:.0f}% or memory {memory_avg:.0f}% consistently high — risk of performance degradation."
        risk = "HIGH"
    else:
        recommended = current_instance
        reason = f"CPU {cpu_avg:.0f}% and memory {memory_avg:.0f}% within acceptable range."
        risk = "LOW"

    curr_cost = INSTANCE_COSTS.get(current_instance, 0.192)
    rec_cost = INSTANCE_COSTS.get(recommended, 0.192)
    monthly_savings = round((curr_cost - rec_cost) * 24 * 30, 2)
    monthly_carbon_reduction = round(
        (carbon.instance_kwh(current_instance) - carbon.instance_kwh(recommended)) * 24 * 30 * 400 / 1000, 2
    )

    return RightSizeRecommendation(
        current_instance=current_instance,
        recommended_instance=recommended,
        reason=reason,
        monthly_savings_usd=max(monthly_savings, 0.0),
        monthly_carbon_reduction_kgco2=max(monthly_carbon_reduction, 0.0),
        risk=risk,
    )


def scaling_advice(
    predicted_cpu: float,
    current_instance_count: int = 1,
    instance_type: str = DEFAULT_INSTANCE,
) -> ScalingRecommendation:
    """Auto-scaling trigger recommendation."""
    cost_per = INSTANCE_COSTS.get(instance_type, 0.192)
    if predicted_cpu > 80 and current_instance_count < 10:
        new_count = min(current_instance_count + 2, 10)
        return ScalingRecommendation(
            action="scale_out",
            current_count=current_instance_count,
            recommended_count=new_count,
            reason=f"Predicted CPU {predicted_cpu:.0f}% — proactively scaling out to maintain SLO.",
            estimated_cost_delta_usd_hr=round((new_count - current_instance_count) * cost_per, 3),
        )
    elif predicted_cpu < 25 and current_instance_count > 1:
        new_count = max(current_instance_count - 1, 1)
        return ScalingRecommendation(
            action="scale_in",
            current_count=current_instance_count,
            recommended_count=new_count,
            reason=f"Predicted CPU {predicted_cpu:.0f}% — safely scaling in to reduce cost.",
            estimated_cost_delta_usd_hr=round((current_instance_count - new_count) * cost_per * -1, 3),
        )
    return ScalingRecommendation(
        action="maintain",
        current_count=current_instance_count,
        recommended_count=current_instance_count,
        reason="Current capacity is appropriately sized.",
        estimated_cost_delta_usd_hr=0.0,
    )
