"""Regression coverage for Supabase user scoping and tenant data isolation."""

import asyncio
from uuid import uuid4

from fastapi.security import HTTPAuthorizationCredentials
from types import SimpleNamespace
import sys

from app import auth, database
from app.cloud.aws_provider import AWSCloudProvider
from app.database import (
    delete_user_provider_credentials,
    get_telemetry_history,
    get_user_provider_credentials,
    record_telemetry,
    store_user_provider_credentials,
)
from app.routers import recommendations


def test_auth_dependency_sets_user_scope_and_resets_it(monkeypatch):
    async def fake_verify(_token):
        return {"sub": "scope-user", "role": "authenticated"}

    async def fake_load(user_id):
        assert user_id == "scope-user"
        return {"aws": {"aws_access_key_id": "user-key"}}

    synchronized = []
    monkeypatch.setattr(auth, "verify_supabase_access_token", fake_verify)
    monkeypatch.setattr(database, "get_user_provider_credentials", fake_load)
    monkeypatch.setattr(
        "app.cloud.sync_user_provider_credentials",
        lambda user_id, credentials: synchronized.append((user_id, credentials)),
    )

    async def exercise_dependency():
        dependency = auth.require_authenticated_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token")
        )
        claims = await anext(dependency)
        assert claims["sub"] == "scope-user"
        assert auth.get_current_user_id() == "scope-user"
        await dependency.aclose()
        assert auth.get_current_user_id() is None

    asyncio.run(exercise_dependency())
    assert synchronized == [("scope-user", {"aws": {"aws_access_key_id": "user-key"}})]


def test_recommendation_and_telemetry_state_are_isolated_by_user():
    user_a = f"isolation-a-{uuid4()}"
    user_b = f"isolation-b-{uuid4()}"

    token_a = auth._current_user_id.set(user_a)
    try:
        recommendations._user_states.pop(user_a, None)
        state_a = recommendations._user_state()
        state_a["score"] = 91
        record_telemetry({"provider": "aws", "region": "test", "cpu": 11})
        assert get_telemetry_history(1)[0]["cpu"] == 11

        token_b = auth._current_user_id.set(user_b)
        try:
            state_b = recommendations._user_state()
            assert state_b["score"] == 80
            assert state_b["recommendations"] == []
            assert get_telemetry_history(1) == []

            state_b["score"] = 65
            record_telemetry({"provider": "aws", "region": "test", "cpu": 72})
            assert get_telemetry_history(1)[0]["cpu"] == 72
        finally:
            auth._current_user_id.reset(token_b)

        assert recommendations._user_state()["score"] == 91
        assert get_telemetry_history(1)[0]["cpu"] == 11
    finally:
        auth._current_user_id.reset(token_a)
        recommendations._user_states.pop(user_a, None)
        recommendations._user_states.pop(user_b, None)


def test_saved_credentials_are_encrypted_and_scoped_to_owner():
    owner_a = f"credential-a-{uuid4()}"
    owner_b = f"credential-b-{uuid4()}"
    secret = f"private-secret-{uuid4()}"

    async def exercise_storage():
        await database.init_db()
        try:
            await store_user_provider_credentials(
                owner_a,
                "aws",
                {"aws_access_key_id": "AKIAUSERA", "aws_secret_access_key": secret},
            )
            loaded_a = await get_user_provider_credentials(owner_a)
            loaded_b = await get_user_provider_credentials(owner_b)
            assert loaded_a["aws"]["aws_secret_access_key"] == secret
            assert loaded_b == {}

            async with database._async_session_maker() as session:
                row = await session.get(database.UserProviderCredentialRecord, (owner_a, "aws"))
                assert row is not None
                assert secret not in row.encrypted_credentials
        finally:
            await delete_user_provider_credentials(owner_a, "aws")
            await delete_user_provider_credentials(owner_b, "aws")

    asyncio.run(exercise_storage())


def test_user_scoped_aws_connection_test_does_not_fall_back_to_server_credentials(monkeypatch):
    from app.services import aws_collector

    monkeypatch.setattr(aws_collector.settings, "aws_access_key_id", "SERVER_ACCESS_KEY")
    monkeypatch.setattr(aws_collector.settings, "aws_secret_access_key", "SERVER_SECRET_KEY")
    sessions = []

    class FakeClient:
        def get_caller_identity(self):
            return {"Account": "server-account", "Arn": "arn:aws:iam::server-account:user/server"}

        def describe_regions(self):
            return {}

        def list_metrics(self, **_kwargs):
            return {}

    class FakeSession:
        def __init__(self, **kwargs):
            sessions.append(kwargs)

        def client(self, *_args, **_kwargs):
            return FakeClient()

    monkeypatch.setitem(sys.modules, "boto3", SimpleNamespace(Session=FakeSession))
    provider = AWSCloudProvider(credentials={})
    result = provider.test_connection(credentials={})

    assert result["status"] == "not_configured"
    assert result["credentials_status"] == "NOT_CONFIGURED"
    assert sessions == []

def test_demo_mode_remains_synthetic_after_successful_aws_verification(monkeypatch):
    from app.cloud import aws_provider

    monkeypatch.setattr(aws_provider.settings, "demo_mode", True)
    provider = AWSCloudProvider(credentials={})
    provider.collector.test_connection = lambda **_kwargs: {
        "success": True,
        "status": "connected",
        "mode": "LIVE",
        "telemetry_status": "OPERATIONAL",
        "message": "Connected.",
        "account_info": {"mode": "LIVE"},
    }

    result = provider.test_connection(credentials={"aws_access_key_id": "user-key"})

    assert result["success"] is True
    assert result["mode"] == "DEMO"
    assert result["telemetry_status"] == "DEMO"
    assert provider.is_live is False
    assert result["account_info"]["mode"] == "DEMO"
