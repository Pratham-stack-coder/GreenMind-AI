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

CredentialsStatus = Literal["CONFIGURED", "NOT_CONFIGURED"]
AuthenticationStatus = Literal["SUCCESS", "FAILED", "NOT_CONFIGURED"]
ReachabilityStatus = Literal["REACHABLE", "UNREACHABLE", "NOT_CONFIGURED"]
TelemetryStatus = Literal["OPERATIONAL", "DEGRADED", "UNAVAILABLE", "ERROR", "DEMO"]


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
    def get_account_info(self) -> dict[str, Any]:
        """Fetch safe account / subscription / project metadata (no secrets)."""
        pass

    @abstractmethod
    def get_regions(self) -> list[dict[str, Any]]:
        """Fetch list of available cloud regions for this provider."""
        pass

    @abstractmethod
    def test_connection(self, credentials: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Validate live credentials and connectivity against the cloud provider API.
        Must distinguish the 4-tier model:
        - credentials_status: CONFIGURED / NOT_CONFIGURED
        - authentication_status: SUCCESS / FAILED / NOT_CONFIGURED
        - api_reachability: REACHABLE / UNREACHABLE / NOT_CONFIGURED
        - telemetry_status: OPERATIONAL / DEGRADED / UNAVAILABLE / ERROR / DEMO
        """
        pass

    def validate_credentials(self, credentials: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate credentials dictionary without permanently modifying current provider state."""
        return self.test_connection(credentials=credentials)

    def get_status(self) -> dict[str, Any]:
        """Return cached or active 4-tier status summary for the provider."""
        if self._last_test_result:
            return self._last_test_result

        mode = "LIVE" if self.is_live else "DEMO"
        status = "connected" if self.is_live else "demo"
        msg = (
            f"{self.provider_name.upper()} active in Live mode"
            if self.is_live
            else f"{self.provider_name.upper()} operating in safe Demo mode"
        )
        return {
            "provider": self.provider_name,
            "success": True,
            "status": status,
            "mode": mode,
            "credentials_status": "CONFIGURED" if self.is_live else "NOT_CONFIGURED",
            "authentication_status": "SUCCESS" if self.is_live else "NOT_CONFIGURED",
            "api_reachability": "REACHABLE" if self.is_live else "NOT_CONFIGURED",
            "telemetry_status": "OPERATIONAL" if self.is_live else "DEMO",
            "message": msg,
            "account_info": self.get_account_info(),
            "last_tested": datetime.now(timezone.utc).isoformat(),
        }
