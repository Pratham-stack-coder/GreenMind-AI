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
from ..auth import get_current_user_id

_PROVIDERS: dict[tuple[str | None, str], BaseCloudProvider] = {}
_USER_CREDENTIALS: dict[tuple[str, str], dict[str, str]] = {}


def update_provider_credentials(name: str, credentials: dict[str, str]) -> None:
    """Update the active user's in-memory cloud credentials and provider instance."""
    user_id = get_current_user_id()
    if not user_id:
        raise RuntimeError("Provider credentials require an authenticated user.")
    provider_name = name.lower().strip()
    key = (user_id, provider_name)
    _USER_CREDENTIALS[key] = {**_USER_CREDENTIALS.get(key, {}), **credentials}
    _PROVIDERS.pop((user_id, provider_name), None)


def clear_provider_credentials(name: str) -> None:
    """Clear only the active user's credentials and provider instance."""
    user_id = get_current_user_id()
    if not user_id:
        raise RuntimeError("Provider credentials require an authenticated user.")
    provider_name = name.lower().strip()
    key = (user_id, provider_name)
    _USER_CREDENTIALS.pop(key, None)
    _PROVIDERS.pop((user_id, provider_name), None)


def sync_user_provider_credentials(user_id: str, credentials: dict[str, dict[str, str]]) -> None:
    """Refresh this user's provider credentials and invalidate changed clients."""
    for provider_name in ("aws", "azure", "gcp", "llm", "openai", "gemini"):
        key = (user_id, provider_name)
        value = credentials.get(provider_name, {})
        if _USER_CREDENTIALS.get(key, {}) != value:
            if value:
                _USER_CREDENTIALS[key] = dict(value)
            else:
                _USER_CREDENTIALS.pop(key, None)
            _PROVIDERS.pop(key, None)


def get_user_credentials(name: str) -> dict[str, str]:
    """Return credentials for a provider belonging to the active user."""
    user_id = get_current_user_id()
    if not user_id:
        return {}
    return dict(_USER_CREDENTIALS.get((user_id, name.lower().strip()), {}))


def get_provider(name: Any = "aws") -> BaseCloudProvider:
    """Return a provider instance scoped to the active authenticated user."""
    if hasattr(name, "default"):
        name = name.default
    if not isinstance(name, str):
        name = str(name) if name is not None else "aws"
    name_clean = name.lower().strip()
    user_id = get_current_user_id()
    key = (user_id, name_clean)
    if key not in _PROVIDERS:
        credentials = _USER_CREDENTIALS.get((user_id, name_clean), {}) if user_id else None
        if name_clean == "azure":
            _PROVIDERS[key] = AzureCloudProvider(credentials=credentials)
        elif name_clean == "gcp":
            _PROVIDERS[key] = GCPCloudProvider(credentials=credentials)
        else:
            _PROVIDERS[key] = AWSCloudProvider(credentials=credentials)
    return _PROVIDERS[key]


def reset_provider(name: str) -> None:
    """Reset the active user's provider instance."""
    name_clean = name.lower().strip()
    key = (get_current_user_id(), name_clean)
    _PROVIDERS.pop(key, None)


def reset_all_providers() -> None:
    """Clear all provider instances and in-memory user credentials."""
    _PROVIDERS.clear()
    _USER_CREDENTIALS.clear()


def get_all_providers_status() -> dict[str, Any]:
    """Retrieve operational and connectivity status across AWS, Azure, and GCP."""
    return {
        "aws": get_provider("aws").get_status(),
        "azure": get_provider("azure").get_status(),
        "gcp": get_provider("gcp").get_status(),
    }
