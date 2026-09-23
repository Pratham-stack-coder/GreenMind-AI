"""
Cloud Provider package for GreenMind AI.
Provides factory function get_provider() to get the appropriate provider instance,
as well as status introspection and provider re-initialization.
"""

from __future__ import annotations

from typing import Any

from .base_provider import BaseCloudProvider, NormalizedCloudMetric
from .aws_provider import AWSCloudProvider
from .azure_provider import AzureCloudProvider
from .gcp_provider import GCPCloudProvider

_PROVIDERS: dict[str, BaseCloudProvider] = {}


def get_provider(name: str = "aws") -> BaseCloudProvider:
    """Return singleton instance of the requested cloud provider."""
    name_clean = name.lower().strip()
    if name_clean not in _PROVIDERS:
        if name_clean == "azure":
            _PROVIDERS[name_clean] = AzureCloudProvider()
        elif name_clean == "gcp":
            _PROVIDERS[name_clean] = GCPCloudProvider()
        else:
            _PROVIDERS[name_clean] = AWSCloudProvider()
    return _PROVIDERS[name_clean]


def reset_provider(name: str) -> None:
    """Reset provider singleton so credentials or modes can be refreshed."""
    name_clean = name.lower().strip()
    if name_clean in _PROVIDERS:
        del _PROVIDERS[name_clean]


def reset_all_providers() -> None:
    """Clear all provider singletons."""
    _PROVIDERS.clear()


def get_all_providers_status() -> dict[str, Any]:
    """Retrieve operational and connectivity status across AWS, Azure, and GCP."""
    return {
        "aws": get_provider("aws").get_status(),
        "azure": get_provider("azure").get_status(),
        "gcp": get_provider("gcp").get_status(),
    }
