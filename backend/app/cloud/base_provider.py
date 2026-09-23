"""
Base Cloud Provider Interface for GreenMind AI.
Defines common telemetry, resource inventory, cost, and health reporting interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseCloudProvider(ABC):
    """Abstract interface that all cloud provider adapters (AWS, Azure, GCP) must implement."""

    def __init__(self, provider_name: str, is_live: bool = False):
        self.provider_name = provider_name
        self.is_live = is_live

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
