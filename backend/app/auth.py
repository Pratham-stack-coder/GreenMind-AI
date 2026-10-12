"""Supabase access-token validation for protected FastAPI routes."""

from __future__ import annotations

import asyncio
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


@lru_cache(maxsize=8)
def _jwks_client(jwks_url: str) -> PyJWKClient:
    # Supabase rotates asymmetric signing keys through this public JWKS endpoint.
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300, timeout=10)


def _verify_asymmetric_token(token: str, supabase_url: str) -> dict[str, Any]:
    issuer = f"{supabase_url.rstrip('/')}/auth/v1"
    client = _jwks_client(f"{issuer}/.well-known/jwks.json")
    signing_key = client.get_signing_key_from_jwt(token)
    header = jwt.get_unverified_header(token)
    algorithm = header.get("alg")
    if algorithm not in {"ES256", "RS256"}:
        raise jwt.InvalidAlgorithmError("Unsupported Supabase signing algorithm")

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=[algorithm],
        audience="authenticated",
        issuer=issuer,
        options={"require": ["exp", "sub", "iss", "aud"]},
    )


async def _verify_legacy_hs256_token(
    token: str,
    supabase_url: str,
    publishable_key: str,
) -> dict[str, Any]:
    """Ask Supabase Auth to validate legacy shared-secret tokens."""
    if not publishable_key:
        raise HTTPException(
            status_code=503,
            detail=(
                "Backend authentication is not fully configured. Set "
                "SUPABASE_PUBLISHABLE_KEY when the Supabase project uses HS256 tokens."
            ),
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{supabase_url.rstrip('/')}/auth/v1/user",
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

    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if algorithm == "HS256":
        return await _verify_legacy_hs256_token(
            token,
            supabase_url,
            settings.supabase_publishable_key.strip(),
        )

    if algorithm not in {"ES256", "RS256"}:
        raise HTTPException(
            status_code=401,
            detail="Unsupported access-token signing algorithm.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return await asyncio.to_thread(_verify_asymmetric_token, token, supabase_url)
    except PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Supabase signing keys could not be reached to validate this session.",
        ) from exc
    except (jwt.PyJWTError, PyJWKClientError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """FastAPI dependency for endpoints that require a valid Supabase session."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="A Supabase bearer access token is required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await verify_supabase_access_token(credentials.credentials)
