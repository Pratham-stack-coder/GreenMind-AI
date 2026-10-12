"""Authenticated encryption for per-user cloud provider credentials."""

from __future__ import annotations

import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from .config import get_settings


def _cipher() -> Fernet:
    key = get_settings().credential_encryption_key.strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Per-user cloud credentials are disabled until CREDENTIAL_ENCRYPTION_KEY is configured.",
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="CREDENTIAL_ENCRYPTION_KEY must be a valid Fernet key.",
        ) from exc


def encrypt_credentials(credentials: dict[str, Any]) -> str:
    payload = json.dumps(credentials, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _cipher().encrypt(payload).decode("ascii")


def decrypt_credentials(ciphertext: str) -> dict[str, Any]:
    try:
        payload = _cipher().decrypt(ciphertext.encode("ascii"))
        value = json.loads(payload)
    except (InvalidToken, UnicodeEncodeError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Stored cloud credentials could not be decrypted. Check the configured encryption key.",
        ) from exc
    if not isinstance(value, dict):
        raise HTTPException(status_code=503, detail="Stored cloud credentials have an invalid format.")
    return value
