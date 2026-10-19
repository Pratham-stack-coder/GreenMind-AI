from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.routing import APIRoute

from app import auth
from app.auth import require_authenticated_user
from app.main import app, health


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

    token_default_iss = jwt.encode(
        {
            "sub": "user-456",
            "iss": "supabase",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    assert auth._verify_asymmetric_token(token_default_iss, supabase_url)["sub"] == "user-456"

    token_clean_iss = jwt.encode(
        {
            "sub": "user-789",
            "iss": supabase_url,
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    assert auth._verify_asymmetric_token(token_clean_iss, supabase_url)["sub"] == "user-789"

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


def test_normalize_supabase_issuer_handles_all_url_variants():
    base1, iss1 = auth._normalize_supabase_issuer("https://test.supabase.co")
    assert base1 == "https://test.supabase.co"
    assert iss1 == "https://test.supabase.co/auth/v1"

    base2, iss2 = auth._normalize_supabase_issuer("https://test.supabase.co/")
    assert base2 == "https://test.supabase.co"
    assert iss2 == "https://test.supabase.co/auth/v1"

    base3, iss3 = auth._normalize_supabase_issuer("https://test.supabase.co/auth/v1")
    assert base3 == "https://test.supabase.co"
    assert iss3 == "https://test.supabase.co/auth/v1"

    base4, iss4 = auth._normalize_supabase_issuer("https://test.supabase.co/auth/v1/")
    assert base4 == "https://test.supabase.co"
    assert iss4 == "https://test.supabase.co/auth/v1"


def test_asymmetric_token_refreshes_jwks_on_key_rotation(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    supabase_url = "https://project-ref.supabase.co"

    from jwt.exceptions import PyJWKClientError

    class StaleJwksClient:
        def get_signing_key_from_jwt(self, _token):
            raise PyJWKClientError("Key not in cached set")

    class FreshJwksClient:
        def __init__(self, *args, **kwargs):
            pass

        def get_signing_key_from_jwt(self, _token):
            return SimpleNamespace(key=public_key)

    monkeypatch.setattr(auth, "_jwks_client", lambda _url: StaleJwksClient())
    monkeypatch.setattr(auth, "PyJWKClient", FreshJwksClient)

    token = jwt.encode(
        {
            "sub": "user-rotated-key",
            "iss": f"{supabase_url}/auth/v1",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "newly-rotated-key"},
    )

    result = auth._verify_asymmetric_token(token, supabase_url)
    assert result["sub"] == "user-rotated-key"

