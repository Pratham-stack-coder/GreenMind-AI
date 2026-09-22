"""
Carbon intensity lookup — extended to 6 regions across AWS / Azure / GCP.

DEMO MODE: illustrative hourly gCO2/kWh curves shaped after publicly reported
day/night carbon-intensity patterns. Not live measurements.

REAL MODE: replace get_carbon_intensity() with a call to Electricity Maps or
WattTime. Nothing else needs to change.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

# gCO2/kWh, illustrative 24-hour curves (hour 0-23)
_DEMO_CURVES: dict[str, list[float]] = {
    # US East Coast — moderate renewables, higher peaks on hot evenings
    "us-east": [
        350, 340, 330, 325, 320, 330, 360, 400, 430, 440, 445, 440,
        430, 425, 430, 440, 450, 460, 470, 460, 440, 410, 380, 360,
    ],
    # US West Coast — high solar midday, very clean overnight
    "us-west": [
        280, 270, 265, 260, 258, 270, 300, 320, 290, 240, 200, 185,
        175, 172, 185, 210, 250, 290, 310, 305, 295, 288, 283, 280,
    ],
    # EU West (Ireland / Germany mix) — strong wind, cleaner overnight
    "eu-west": [
        220, 210, 205, 200, 198, 205, 230, 260, 275, 280, 278, 272,
        268, 270, 275, 282, 285, 280, 265, 248, 235, 228, 222, 220,
    ],
    # India North — coal-heavy grid, high throughout
    "in-north": [
        620, 600, 590, 585, 590, 610, 660, 700, 720, 715, 700, 690,
        685, 690, 700, 715, 730, 740, 730, 710, 690, 670, 650, 635,
    ],
    # Asia Pacific (Singapore) — mix of gas/coal
    "ap-southeast": [
        480, 470, 465, 460, 462, 475, 510, 540, 555, 560, 558, 552,
        548, 550, 555, 560, 565, 562, 550, 535, 520, 510, 495, 485,
    ],
    # Canada Central — very clean (hydro-dominant)
    "ca-central": [
        90, 85, 82, 80, 79, 82, 95, 110, 118, 120, 119, 116,
        114, 115, 116, 118, 120, 118, 112, 105, 100, 96, 93, 91,
    ],
}

# Map provider+region labels to curve keys
_REGION_MAP: dict[str, str] = {
    # AWS
    "us-east-1": "us-east",
    "us-west-2": "us-west",
    "eu-west-1": "eu-west",
    "ap-south-1": "in-north",
    "ap-southeast-1": "ap-southeast",
    "ca-central-1": "ca-central",
    # Azure
    "eastus": "us-east",
    "westus2": "us-west",
    "westeurope": "eu-west",
    "centralindia": "in-north",
    "southeastasia": "ap-southeast",
    "canadacentral": "ca-central",
    # GCP
    "us-east4": "us-east",
    "us-west1": "us-west",
    "europe-west1": "eu-west",
    "asia-south1": "in-north",
    "asia-southeast1": "ap-southeast",
    "northamerica-northeast1": "ca-central",
    # Short names (demo)
    "us-east": "us-east",
    "us-west": "us-west",
    "eu-west": "eu-west",
    "in-north": "in-north",
    "ap-southeast": "ap-southeast",
    "ca-central": "ca-central",
}

DEFAULT_REGION = "us-east"

# Instance type power draw estimates (kWh per instance-hour)
_INSTANCE_KWH: dict[str, float] = {
    "t3.micro": 0.04,
    "t3.small": 0.08,
    "t3.medium": 0.15,
    "m5.large": 0.35,
    "m5.xlarge": 0.65,
    "m5.2xlarge": 1.2,
    "c5.large": 0.30,
    "c5.xlarge": 0.55,
    "r5.large": 0.40,
    "r5.xlarge": 0.75,
    "default": 0.35,
}


class DataSource(str, Enum):
    DEMO = "DEMO"
    LIVE = "LIVE"


def available_regions() -> list[str]:
    return list(_DEMO_CURVES.keys())


def _resolve_region(region: str) -> str:
    return _REGION_MAP.get(region, DEFAULT_REGION)


def get_carbon_intensity(region: str, hour: int) -> dict:
    key = _resolve_region(region)
    curve = _DEMO_CURVES[key]
    hour = hour % 24
    return {
        "region": key,
        "hour": hour,
        "carbon_intensity_gco2_per_kwh": curve[hour],
        "source": DataSource.DEMO,
    }


def get_intensity_curve(region: str) -> list[dict]:
    return [get_carbon_intensity(region, h) for h in range(24)]


def find_greenest_window(region: str, start_hour: int, window_hours: int = 12) -> dict:
    candidates = [
        get_carbon_intensity(region, (start_hour + offset) % 24)
        for offset in range(window_hours)
    ]
    best = min(candidates, key=lambda c: c["carbon_intensity_gco2_per_kwh"])
    now = candidates[0]
    reduction_pct = 0.0
    if now["carbon_intensity_gco2_per_kwh"] > 0:
        reduction_pct = 100 * (
            1 - best["carbon_intensity_gco2_per_kwh"] / now["carbon_intensity_gco2_per_kwh"]
        )
    return {
        "current_hour_intensity": now,
        "best_hour_intensity": best,
        "hours_from_now": (best["hour"] - start_hour) % 24,
        "estimated_carbon_reduction_pct": round(reduction_pct, 1),
    }


def instance_kwh(instance_type: str) -> float:
    return _INSTANCE_KWH.get(instance_type, _INSTANCE_KWH["default"])


def estimate_carbon_gco2(
    region: str,
    hour: int,
    duration_hours: float,
    instance_type: str = "m5.large",
) -> float:
    intensity = get_carbon_intensity(region, hour)["carbon_intensity_gco2_per_kwh"]
    kwh = instance_kwh(instance_type) * duration_hours
    return round(kwh * intensity, 2)


def region_green_score(region: str) -> float:
    """0-100 score where 100 = cleanest. Based on average daily intensity."""
    key = _resolve_region(region)
    avg = sum(_DEMO_CURVES[key]) / 24
    # Normalize: best ~79 gCO2 (ca-central avg), worst ~685 (in-north avg)
    worst, best = 720, 79
    score = 100 * (1 - (avg - best) / (worst - best))
    return round(max(0, min(100, score)), 1)
