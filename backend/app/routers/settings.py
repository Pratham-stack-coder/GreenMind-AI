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
from sqlalchemy import text

from ..auth import get_current_user_id
from ..cloud import clear_provider_credentials, get_all_providers_status, get_provider, get_user_credentials, update_provider_credentials
from ..database import delete_user_provider_credentials, store_user_provider_credentials
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
async def get_settings_status() -> dict[str, Any]:
    """
    Return active status across multi-cloud providers, AI models, and database infrastructure.
    GUARANTEE: Secret keys and passwords are NEVER returned in this response.
    """
    statuses = get_all_providers_status()
    any_live = any(p.get("mode") == "LIVE" for p in statuses.values())
    global_mode = "LIVE" if any_live else "DEMO"
    llm_credentials = {
        **get_user_credentials("gemini"),
        **get_user_credentials("openai"),
        **get_user_credentials("llm"),
    }
    gemini_configured = bool(llm_credentials.get("gemini_api_key"))
    openai_configured = bool(llm_credentials.get("openai_api_key"))
    llm_status = "configured_unverified"

    db_type = "postgresql" if settings.database_url.startswith("postgresql") else "sqlite"
    from ..database import _engine

    try:
        async with _engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
        database_status = "connected"
    except Exception:
        database_status = "unavailable"

    return {
        "system_mode": global_mode,
        "global_mode": global_mode,
        "demo_mode": settings.demo_mode,
        "providers": statuses,
        "llm": {
            "gemini_configured": gemini_configured,
            "openai_configured": openai_configured,
        },
        "ai": {
            "gemini": {
                "configured": gemini_configured,
                "status": llm_status if gemini_configured else "not_configured",
                "model": "gemini-1.5-flash",
            },
            "openai": {
                "configured": openai_configured,
                "status": llm_status if openai_configured else "not_configured",
                "model": "gpt-4o-mini",
            },
        },
        "database": {
            "type": db_type,
            "status": database_status,
            "is_persistent": db_type == "postgresql",
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
        res = provider.test_connection(credentials=creds or None)
        res["provider"] = prov_name
        return res

    elif prov_name in ["gemini", "openai"]:
        stored = {
            **get_user_credentials(prov_name),
            **get_user_credentials("llm"),
        }
        api_key = creds.get("api_key") or creds.get(f"{prov_name}_api_key") or stored.get(f"{prov_name}_api_key", "")
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
            "success": False,
            "status": "configured_unverified",
            "mode": "DEMO",
            "message": "Key format looks plausible, but live LLM API verification is not implemented.",
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
async def configure_provider(req: ConfigureProviderRequest) -> dict[str, Any]:
    """Validate and configure cloud credentials for the authenticated user only."""
    prov_name = req.provider.lower().strip()
    creds = req.credentials

    if prov_name in {"aws", "azure", "gcp"}:
        user_id = get_current_user_id()
        if not user_id:
            raise HTTPException(status_code=401, detail="An authenticated user is required.")
        stored_credentials = await store_user_provider_credentials(user_id, prov_name, creds)
        update_provider_credentials(prov_name, stored_credentials)
        provider = get_provider(prov_name)
        test_res = provider.test_connection()
        test_res["provider"] = prov_name
        return {
            "status": "ok",
            "success": True,
            "connection_verified": test_res.get("success", False),
            "provider": prov_name,
            "message": test_res.get("message", "Cloud credentials were saved."),
            "test_result": test_res,
        }

    if prov_name in {"gemini", "openai", "llm"}:
        user_id = get_current_user_id()
        if not user_id:
            raise HTTPException(status_code=401, detail="An authenticated user is required.")
        stored_credentials = await store_user_provider_credentials(user_id, prov_name, creds)
        update_provider_credentials(prov_name, stored_credentials)
        return {
            "status": "configured_unverified",
            "success": True,
            "connection_verified": False,
            "provider": prov_name,
            "message": "AI credentials were saved for your account. Live provider verification is not implemented.",
        }

    raise HTTPException(status_code=400, detail=f"Unsupported provider: {req.provider}")


@router.post("/disconnect")
async def disconnect_provider(req: DisconnectProviderRequest) -> dict[str, Any]:
    """Reset a provider to safe Demo mode by clearing active session credentials."""
    prov_name = req.provider.lower().strip()
    if prov_name in {"aws", "azure", "gcp"}:
        user_id = get_current_user_id()
        if not user_id:
            raise HTTPException(status_code=401, detail="An authenticated user is required.")
        await delete_user_provider_credentials(user_id, prov_name)
        clear_provider_credentials(prov_name)
    elif prov_name == "llm":
        user_id = get_current_user_id()
        if not user_id:
            raise HTTPException(status_code=401, detail="An authenticated user is required.")
        for credential_provider in ("llm", "gemini", "openai"):
            await delete_user_provider_credentials(user_id, credential_provider)
            clear_provider_credentials(credential_provider)
        return {
            "status": "disconnected",
            "success": True,
            "provider": "llm",
            "mode": "DEMO",
            "message": "Your AI keys were deleted; Copilot uses the deterministic engine.",
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
