"""
Cloud Provider package for GreenMind AI.
Provides factory function get_provider() to get the appropriate provider instance.
"""

from .base_provider import BaseCloudProvider
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
