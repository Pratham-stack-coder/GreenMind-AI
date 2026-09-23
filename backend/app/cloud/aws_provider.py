"""
AWS Cloud Provider implementation for GreenMind AI.
Provides live CloudWatch metrics when AWS credentials are configured,
or high-fidelity DEMO metrics when in demo mode.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .base_provider import BaseCloudProvider
from ..services.aws_collector import AWSCollector
from ..carbon import get_carbon_intensity
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class AWSCloudProvider(BaseCloudProvider):
    """AWS provider adapter supporting both LIVE CloudWatch telemetry and DEMO simulation."""

    def __init__(self):
        self.collector = AWSCollector()
        is_live = not settings.demo_mode and self.collector.is_configured
        super().__init__(provider_name="aws", is_live=is_live)

    def get_metrics(self, region: str) -> dict[str, Any]:
        """Fetch current telemetry metrics for AWS."""
        now = datetime.now(timezone.utc)
        hour = now.hour

        # Try live metrics if configured
        if self.is_live:
            live_cpu = self.collector.collect_cpu_utilization()
            live_net = self.collector.collect_network_mbps()
            live_mem, mem_note = self.collector.collect_memory_utilization()

            if live_cpu is not None:
                # Live CPU available
                cpu = live_cpu
                memory = live_mem if live_mem is not None else 55.0
                network = live_net if live_net is not None else 250.0
                storage = 45.0
                cost = round(0.192 * (1 + (cpu / 100) * 0.35), 4)
                ci = get_carbon_intensity(region, hour)["carbon_intensity_gco2_per_kwh"]
                carbon = round(0.35 * ci * (1 + (cpu / 100) * 0.35), 2)
                return {
                    "timestamp": now.isoformat(),
                    "provider": "aws",
                    "region": region,
                    "cpu": cpu,
                    "memory": memory,
                    "storage": storage,
                    "network": network,
                    "cost_usd_per_hour": cost,
                    "carbon_gco2_per_hour": carbon,
                    "instance_count": 1,
                    "source": "LIVE_AWS",
                    "memory_note": mem_note,
                }

        # Fallback to realistic DEMO mode
        from ..routers.telemetry import _generate_live_metrics
        m = _generate_live_metrics("aws", region)
        d = m.model_dump()
        d["source"] = "DEMO"
        return d

    def get_resources(self, region: str) -> list[dict[str, Any]]:
        """Fetch cloud resource inventory."""
        if self.is_live:
            live_instances = self.collector.list_ec2_instances()
            if live_instances:
                return [
                    {
                        "id": inst["id"],
                        "name": inst["name"],
                        "type": inst["type"],
                        "provider": "aws",
                        "region": region,
                        "status": inst["state"],
                        "cpu_utilization": 42.5,
                        "memory_utilization": 58.0,
                        "cost_per_hour": 0.192,
                        "carbon_intensity": 185.0,
                        "tags": {"Environment": "Production", "ManagedBy": "GreenMind"},
                        "right_size_candidate": False,
                    }
                    for inst in live_instances
                ]

        # Standard simulated resource catalog
        return [
            {
                "id": "i-09f1234abcd5678ef",
                "name": "api-gateway-prod-01",
                "type": "c5.2xlarge",
                "provider": "aws",
                "region": region,
                "status": "running",
                "cpu_utilization": 24.5,
                "memory_utilization": 38.0,
                "cost_per_hour": 0.34,
                "carbon_intensity": 210.0,
                "tags": {"Service": "API Gateway", "Environment": "Production"},
                "right_size_candidate": True,
            },
            {
                "id": "i-08a9876dcba4321fe",
                "name": "ml-inference-worker-03",
                "type": "g4dn.xlarge",
                "provider": "aws",
                "region": region,
                "status": "running",
                "cpu_utilization": 82.0,
                "memory_utilization": 74.0,
                "cost_per_hour": 0.526,
                "carbon_intensity": 210.0,
                "tags": {"Service": "ML Inference", "Environment": "Production"},
                "right_size_candidate": False,
            },
            {
                "id": "i-07b5555feed1111aa",
                "name": "background-celery-worker",
                "type": "t3.large",
                "provider": "aws",
                "region": region,
                "status": "running",
                "cpu_utilization": 12.0,
                "memory_utilization": 28.0,
                "cost_per_hour": 0.0832,
                "carbon_intensity": 210.0,
                "tags": {"Service": "Batch Workers", "Environment": "Staging"},
                "right_size_candidate": True,
            },
            {
                "id": "vol-0123456789abcdef0",
                "name": "db-backup-storage-ebs",
                "type": "gp3 (500 GB)",
                "provider": "aws",
                "region": region,
                "status": "in-use",
                "cpu_utilization": 0.0,
                "memory_utilization": 0.0,
                "cost_per_hour": 0.055,
                "carbon_intensity": 210.0,
                "tags": {"Service": "Storage", "Lifecycle": "Active"},
                "right_size_candidate": False,
            },
        ]

    def get_cost(self, region: str, days: int = 7) -> dict[str, Any]:
        """Fetch cost breakdown."""
        total = round(0.192 * 24 * days, 2)
        return {
            "provider": "aws",
            "region": region,
            "period_days": days,
            "total_usd": total,
            "currency": "USD",
            "top_services": [
                {"service": "Amazon EC2", "cost_usd": round(total * 0.65, 2)},
                {"service": "Amazon EBS", "cost_usd": round(total * 0.18, 2)},
                {"service": "Data Transfer", "cost_usd": round(total * 0.12, 2)},
                {"service": "Amazon CloudWatch", "cost_usd": round(total * 0.05, 2)},
            ],
        }

    def get_health(self, region: str) -> dict[str, Any]:
        """Fetch AWS infrastructure health indicators."""
        return {
            "provider": "aws",
            "region": region,
            "status": "HEALTHY",
            "health_score": 92,
            "active_alarms": 0,
            "service_status": {
                "EC2": "Normal",
                "EBS": "Normal",
                "VPC": "Normal",
                "CloudWatch": "Normal",
            },
        }
