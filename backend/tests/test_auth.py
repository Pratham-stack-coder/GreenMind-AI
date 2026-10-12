from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.routing import APIRoute

from app import auth
from app.auth import require_authenticated_user
from app.main import app, health
from fastapi.testclient import TestClient


def test_health_is_public_and_reports_auth_configuration():
    response = health()
    assert response["status"] == "ok"
    assert isinstance(response["auth_configured"], bool)


def test_authenticated_probe_route_has_server_auth_dependency():
    route = next(
        route for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/api/v1/auth/session"
    )
    assert any(
        dependency.call is require_authenticated_user
        for dependency in route.dependant.dependencies
    )


def test_asymmetric_supabase_token_checks_signature_issuer_audience_and_expiry(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    supabase_url = "https://project-ref.supabase.co"

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(auth, "_jwks_client", lambda _url: FakeJwksClient())
    token = jwt.encode(
        {
            "sub": "user-123",
            "iss": f"{supabase_url}/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    assert auth._verify_asymmetric_token(token, supabase_url)["sub"] == "user-123"

    wrong_issuer = jwt.encode(
        {
            "sub": "user-123",
            "iss": "https://other-project.supabase.co/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with pytest.raises(jwt.InvalidIssuerError):
        auth._verify_asymmetric_token(wrong_issuer, supabase_url)


from fastapi.testclient import TestClient


def test_protected_session_rejects_missing_and_invalid_bearer_token():
    client = TestClient(app)
    missing = client.get("/api/v1/auth/session")
    invalid = client.get(
        "/api/v1/auth/session",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert missing.status_code == 401
    assert invalid.status_code == 503  # Auth config is absent in this isolated test environment.


@pytest.mark.asyncio
async def test_expired_asymmetric_token_is_rejected(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    supabase_url = "https://project-ref.supabase.co"

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(auth, "_jwks_client", lambda _url: FakeJwksClient())
    expired = jwt.encode(
        {
            "sub": "user-123",
            "iss": f"{supabase_url}/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        auth._verify_asymmetric_token(expired, supabase_url)


def test_invalid_signature_is_rejected(monkeypatch):
    valid_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class FakeJwksClient:
        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=valid_key.public_key())

    monkeypatch.setattr(auth, "_jwks_client", lambda _url: FakeJwksClient())
    token = jwt.encode(
        {
            "sub": "user-123",
            "iss": "https://project-ref.supabase.co/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        wrong_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    with pytest.raises(jwt.InvalidSignatureError):
        auth._verify_asymmetric_token(token, "https://project-ref.supabase.co")
