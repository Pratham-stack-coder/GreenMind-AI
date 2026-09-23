"""
Base Cloud Provider Interface for GreenMind AI.
Defines common telemetry, resource inventory, cost, health reporting, and connection testing interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Literal

ProviderStatus = Literal[
    "connected",
    "not_configured",
    "authentication_failed",
    "permission_denied",
    "service_unavailable",
    "demo",
]


@dataclass
class NormalizedCloudMetric:
    """Normalized multi-cloud telemetry record for GreenMind AI engines."""
    provider: str
    resource_id: str
    resource_name: str
    resource_type: str
    timestamp: str
    cpu: float
    memory: float
    storage: float
    network: float
    cost_usd_per_hour: float
    carbon_gco2_per_hour: float
    region: str
    status: str
    mode: Literal["LIVE", "DEMO"]
    source: str
    memory_note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BaseCloudProvider(ABC):
    """Abstract interface that all cloud provider adapters (AWS, Azure, GCP, Demo) must implement."""

    def __init__(self, provider_name: str, is_live: bool = False):
        self.provider_name = provider_name
        self.is_live = is_live
        self._last_test_result: dict[str, Any] | None = None

    @abstractmethod
    def get_metrics(self, region: str) -> dict[str, Any]:
        """Fetch current telemetry metrics (CPU, Memory, Storage, Network, Cost, Carbon)."""
        pass

    @abstractmethod
    def get_resources(self, region: str) -> list[dict[str, Any]]:
        """Fetch cloud resource inventory (VMs/instances, storage volumes, databases)."""
        pass

    @abstractmethod
    def get_cost(self, region: str, days: int = 7) -> dict[str, Any]:
        """Fetch historical and current cost breakdown."""
        pass

    @abstractmethod
    def get_health(self, region: str) -> dict[str, Any]:
        """Fetch cloud infrastructure health score, anomalies, and active alerts."""
        pass

    @abstractmethod
    def test_connection(self) -> dict[str, Any]:
        """
        Validate live credentials and connectivity against the cloud provider API.
        Returns:
            dict containing:
            - success: bool
            - status: ProviderStatus ('connected', 'not_configured', 'authentication_failed', etc.)
            - mode: 'LIVE' or 'DEMO'
            - message: human-readable status explanation (safe, no secret exposure)
            - last_tested: ISO-8601 timestamp
        """
        pass

    def get_status(self) -> dict[str, Any]:
        """Return cached or active status summary for the provider."""
        if self._last_test_result:
            return self._last_test_result

        mode = "LIVE" if self.is_live else "DEMO"
        status = "connected" if self.is_live else "demo"
        msg = f"{self.provider_name.upper()} active in Live mode" if self.is_live else f"{self.provider_name.upper()} operating in safe Demo mode"
        return {
            "provider": self.provider_name,
            "success": True,
            "status": status,
            "mode": mode,
            "message": msg,
            "last_tested": datetime.now(timezone.utc).isoformat(),
        }
