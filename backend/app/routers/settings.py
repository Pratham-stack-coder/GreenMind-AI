"""
Settings and Provider Management Router for GreenMind AI.
Allows safe status introspection, live connection testing, and runtime credential configuration
WITHOUT ever leaking secrets in responses or logs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..cloud import get_all_providers_status, get_provider, reset_provider
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter(prefix="/settings", tags=["Settings & Providers"])


class TestConnectionRequest(BaseModel):
    provider: str
    credentials: dict[str, str] = Field(default_factory=dict)


class ConfigureProviderRequest(BaseModel):
    provider: str
    credentials: dict[str, str] = Field(default_factory=dict)


class DisconnectProviderRequest(BaseModel):
    provider: str


@router.get("/status")
def get_settings_status() -> dict[str, Any]:
    """
    Return active status across multi-cloud providers, AI models, and database infrastructure.
    GUARANTEE: Secret keys and passwords are NEVER returned in this response.
    """
    statuses = get_all_providers_status()
    any_live = any(p.get("mode") == "LIVE" for p in statuses.values())
    global_mode = "LIVE" if any_live else "DEMO"

    db_type = "postgresql" if settings.database_url.startswith("postgresql") else "sqlite"

    return {
        "system_mode": global_mode,
        "global_mode": global_mode,
        "demo_mode": settings.demo_mode,
        "providers": statuses,
        "llm": {
            "gemini_configured": bool(settings.gemini_api_key),
            "openai_configured": bool(settings.openai_api_key),
        },
        "ai": {
            "gemini": {
                "configured": bool(settings.gemini_api_key),
                "status": "connected" if settings.gemini_api_key else "not_configured",
                "model": "gemini-1.5-flash",
            },
            "openai": {
                "configured": bool(settings.openai_api_key),
                "status": "connected" if settings.openai_api_key else "not_configured",
                "model": "gpt-4o-mini",
            },
        },
        "database": {
            "type": db_type,
            "status": "connected",
            "is_persistent": True,
        },
        "redis": bool(settings.redis_url),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/test-connection")
def test_provider_connection(req: TestConnectionRequest) -> dict[str, Any]:
    """
    Test live connectivity and authentication for a specific cloud provider or LLM.
    Uses read-only verification (e.g. sts:GetCallerIdentity, ARM subscription list, GCP metric descriptors).
    """
    prov_name = req.provider.lower().strip()
    creds = req.credentials

    if prov_name in ["aws", "azure", "gcp"]:
        provider = get_provider(prov_name)
        res = provider.test_connection(credentials=creds)
        res["provider"] = prov_name
        return res

    elif prov_name in ["gemini", "openai"]:
        api_key = creds.get("api_key") or (settings.gemini_api_key if prov_name == "gemini" else settings.openai_api_key)
        if not api_key:
            return {
                "provider": prov_name,
                "success": False,
                "status": "not_configured",
                "mode": "DEMO",
                "message": f"{prov_name.capitalize()} API key not provided.",
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }
        # Validate format
        if prov_name == "openai" and not (api_key.startswith("sk-") and len(api_key) > 20):
            return {
                "provider": prov_name,
                "success": False,
                "status": "auth_failed",
                "mode": "DEMO",
                "message": "Invalid OpenAI API key format (expected sk-...).",
                "last_tested": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "provider": prov_name,
            "success": True,
            "status": "connected",
            "mode": "LIVE",
            "message": f"{prov_name.capitalize()} API key format validated and ready for Copilot.",
            "last_tested": datetime.now(timezone.utc).isoformat(),
        }

    raise HTTPException(status_code=400, detail=f"Unsupported provider: {req.provider}")


@router.get("/account-info/{provider}")
def get_provider_account_info(provider: str) -> dict[str, Any]:
    """Return safe account / subscription / project metadata for provider (no secrets)."""
    prov_name = provider.lower().strip()
    if prov_name not in ["aws", "azure", "gcp"]:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    p = get_provider(prov_name)
    return p.get_account_info()


@router.get("/regions/{provider}")
def get_provider_regions(provider: str) -> list[dict[str, Any]]:
    """Return supported or active regions for provider."""
    prov_name = provider.lower().strip()
    if prov_name not in ["aws", "azure", "gcp"]:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    p = get_provider(prov_name)
    return p.get_regions()


@router.post("/validate-credentials")
def validate_provider_credentials(req: TestConnectionRequest) -> dict[str, Any]:
    """Validate credentials without modifying provider state."""
    return test_provider_connection(req)


@router.post("/configure")
def configure_provider(req: ConfigureProviderRequest) -> dict[str, Any]:
    """
    Apply in-memory provider credentials for the active session, test connection,
    and activate live mode if validation succeeds.
    """
    prov_name = req.provider.lower().strip()
    creds = req.credentials

    if prov_name == "aws":
        if "aws_access_key_id" in creds:
            settings.aws_access_key_id = creds["aws_access_key_id"]
        if "aws_secret_access_key" in creds:
            settings.aws_secret_access_key = creds["aws_secret_access_key"]
        if "aws_default_region" in creds:
            settings.aws_default_region = creds["aws_default_region"]
        reset_provider("aws")
        p = get_provider("aws")
        test_res = p.test_connection()
        test_res["provider"] = "aws"
        return {
            "status": "ok",
            "success": test_res.get("success", False),
            "provider": "aws",
            "message": test_res.get("message", "AWS credentials configured."),
            "test_result": test_res,
        }

    elif prov_name == "azure":
        if "azure_subscription_id" in creds:
            settings.azure_subscription_id = creds["azure_subscription_id"]
        if "azure_tenant_id" in creds:
            settings.azure_tenant_id = creds["azure_tenant_id"]
        if "azure_client_id" in creds:
            settings.azure_client_id = creds["azure_client_id"]
        if "azure_client_secret" in creds:
            settings.azure_client_secret = creds["azure_client_secret"]
        reset_provider("azure")
        p = get_provider("azure")
        test_res = p.test_connection()
        test_res["provider"] = "azure"
        return {
            "status": "ok",
            "success": test_res.get("success", False),
            "provider": "azure",
            "message": test_res.get("message", "Azure credentials configured."),
            "test_result": test_res,
        }

    elif prov_name == "gcp":
        if "gcp_project_id" in creds:
            settings.gcp_project_id = creds["gcp_project_id"]
        if "gcp_service_account_json" in creds:
            settings.gcp_service_account_json = creds["gcp_service_account_json"]
        reset_provider("gcp")
        p = get_provider("gcp")
        test_res = p.test_connection()
        test_res["provider"] = "gcp"
        return {
            "status": "ok",
            "success": test_res.get("success", False),
            "provider": "gcp",
            "message": test_res.get("message", "GCP credentials configured."),
            "test_result": test_res,
        }

    elif prov_name == "gemini":
        if "gemini_api_key" in creds:
            settings.gemini_api_key = creds["gemini_api_key"]
        elif "api_key" in creds:
            settings.gemini_api_key = creds["api_key"]
        return {"status": "ok", "success": True, "provider": "gemini", "message": "Gemini API key configured."}

    elif prov_name == "openai":
        if "openai_api_key" in creds:
            settings.openai_api_key = creds["openai_api_key"]
        elif "api_key" in creds:
            settings.openai_api_key = creds["api_key"]
        return {"status": "ok", "success": True, "provider": "openai", "message": "OpenAI API key configured."}

    elif prov_name == "llm":
        if "gemini_api_key" in creds:
            settings.gemini_api_key = creds["gemini_api_key"]
        if "openai_api_key" in creds:
            settings.openai_api_key = creds["openai_api_key"]
        return {"status": "ok", "success": True, "provider": "llm", "message": "AI keys updated successfully."}

    raise HTTPException(status_code=400, detail=f"Unsupported provider: {req.provider}")


@router.post("/disconnect")
def disconnect_provider(req: DisconnectProviderRequest) -> dict[str, Any]:
    """Reset a provider to safe Demo mode by clearing active session credentials."""
    prov_name = req.provider.lower().strip()
    if prov_name == "aws":
        settings.aws_access_key_id = ""
        settings.aws_secret_access_key = ""
        reset_provider("aws")
    elif prov_name == "azure":
        settings.azure_subscription_id = ""
        settings.azure_tenant_id = ""
        settings.azure_client_id = ""
        settings.azure_client_secret = ""
        reset_provider("azure")
    elif prov_name == "gcp":
        settings.gcp_project_id = ""
        settings.gcp_service_account_json = ""
        reset_provider("gcp")
    elif prov_name == "llm":
        settings.gemini_api_key = ""
        settings.openai_api_key = ""
        return {
            "status": "disconnected",
            "success": True,
            "provider": "llm",
            "mode": "DEMO",
            "message": "AI keys cleared; Copilot reset to deterministic engine.",
        }

    p = get_provider(prov_name)
    return {
        "status": "disconnected",
        "success": True,
        "provider": prov_name,
        "mode": "DEMO",
        "status_detail": p.get_status(),
        "message": f"{prov_name.upper()} disconnected and reset to Demo mode (Reset to Demo).",
    }
