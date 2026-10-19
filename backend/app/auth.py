"""Supabase access-token validation for protected FastAPI routes."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextvars import ContextVar
from functools import lru_cache
from typing import Any

import httpx
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from .config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)
_current_user_id: ContextVar[str | None] = ContextVar("greenmind_user_id", default=None)


def get_current_user_id() -> str | None:
    """Return the verified Supabase subject for the active request, if any."""
    return _current_user_id.get()


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    # Supabase rotates asymmetric signing keys through this public JWKS endpoint.
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=120, timeout=10)


def _normalize_supabase_issuer(supabase_url: str) -> tuple[str, str]:
    """Return (clean_base_url, issuer_url) handling inputs with or without trailing /auth/v1."""
    clean = supabase_url.strip().rstrip("/")
    if clean.endswith("/auth/v1"):
        clean = clean[:-8].rstrip("/")
    return clean, f"{clean}/auth/v1"


def _verify_asymmetric_token(token: str, supabase_url: str) -> dict[str, Any]:
    clean, issuer = _normalize_supabase_issuer(supabase_url)
    jwks_url = f"{issuer}/.well-known/jwks.json"
    client = _jwks_client(jwks_url)
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except PyJWKClientError:
        # Key may have been newly rotated or not in current cache; force refresh
        fresh_client = PyJWKClient(jwks_url, cache_jwk_set=False, timeout=10)
        signing_key = fresh_client.get_signing_key_from_jwt(token)

    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg")
    if algorithm not in {"ES256", "RS256"}:
        raise jwt.InvalidAlgorithmError(f"Unsupported Supabase signing algorithm: {algorithm}")

    allowed_issuers = [
        "supabase",
        issuer,
        clean,
        f"{issuer}/",
        f"{clean}/",
    ]

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[algorithm],
        audience="authenticated",
        issuer=allowed_issuers,
        options={"require": ["exp", "sub", "iss", "aud"]},
    )


async def _verify_token_via_supabase_api(
    token: str,
    supabase_url: str,
    publishable_key: str,
) -> dict[str, Any]:
    """Ask Supabase Auth to validate tokens directly via its /user endpoint."""
    if not publishable_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Backend authentication is not fully configured. Set "
                "SUPABASE_PUBLISHABLE_KEY when the Supabase project uses API token validation."
            ),
        )

    clean_base, _ = _normalize_supabase_issuer(supabase_url)
    user_endpoint = f"{clean_base}/auth/v1/user"

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                user_endpoint,
                headers={
                    "apikey": publishable_key,
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth could not be reached to validate this session.",
        ) from exc

    if response.status_code in {401, 403}:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=503,
            detail="Supabase Auth returned an error while validating this session.",
        )

    user = response.json()
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Supabase returned no user for this session.")
    return {"sub": user_id, "email": user.get("email"), "role": "authenticated"}


_verify_legacy_hs256_token = _verify_token_via_supabase_api


async def verify_supabase_access_token(
    token: str,
    config: Settings | None = None,
) -> dict[str, Any]:
    """Verify a Supabase JWT signature, issuer, audience, and expiry."""
    settings = config or get_settings()
    supabase_url = settings.supabase_url.strip().rstrip("/")
    if not supabase_url:
        raise HTTPException(
            status_code=503,
            detail="Backend authentication is not configured. Set SUPABASE_URL on the backend.",
        )

    pub_key = settings.supabase_publishable_key.strip()

    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError as exc:
        # If unverified header parsing fails, try authoritative Supabase API before rejecting
        if pub_key:
            return await _verify_token_via_supabase_api(token, supabase_url, pub_key)
        raise HTTPException(
            status_code=401,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if algorithm == "HS256":
        return await _verify_token_via_supabase_api(
            token,
            supabase_url,
            pub_key,
        )

    if algorithm not in {"ES256", "RS256"}:
        if pub_key:
            return await _verify_token_via_supabase_api(
                token,
                supabase_url,
                pub_key,
            )
        raise HTTPException(
            status_code=401,
            detail="Unsupported access-token signing algorithm.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await asyncio.to_thread(_verify_asymmetric_token, token, supabase_url)
    except PyJWKClientConnectionError as exc:
        if pub_key:
            try:
                return await _verify_token_via_supabase_api(token, supabase_url, pub_key)
            except Exception:
                pass
        raise HTTPException(
            status_code=503,
            detail="Supabase signing keys could not be reached to validate this session.",
        ) from exc
    except (jwt.PyJWTError, PyJWKClientError) as exc:
        if pub_key:
            try:
                return await _verify_token_via_supabase_api(token, supabase_url, pub_key)
            except HTTPException as sub_exc:
                if sub_exc.status_code == 401:
                    raise sub_exc
            except Exception:
                pass
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AsyncIterator[dict[str, Any]]:
    """FastAPI dependency for endpoints that require a valid Supabase session."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="A Supabase bearer access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    claims = await verify_supabase_access_token(credentials.credentials)
    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(status_code=401, detail="Supabase access token has no valid user subject.")

    context_token = _current_user_id.set(user_id)
    try:
        try:
            from .database import get_user_provider_credentials
            from .cloud import sync_user_provider_credentials

            user_credentials = await get_user_provider_credentials(user_id)
            sync_user_provider_credentials(user_id, user_credentials)
        except Exception:
            # If credential storage is unavailable, fail closed for provider access.
            from .cloud import sync_user_provider_credentials

            sync_user_provider_credentials(user_id, {})
        yield claims
    finally:
        _current_user_id.reset(context_token)
