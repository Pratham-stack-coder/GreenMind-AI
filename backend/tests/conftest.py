"""Shared test fixtures for authenticated API route coverage."""

from uuid import uuid4

import pytest
from cryptography.fernet import Fernet


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Ensure test database and all tables are initialized for the test suite."""
    import asyncio
    from app.database import init_db

    asyncio.run(init_db())


@pytest.fixture(autouse=True)
def authenticated_test_user(monkeypatch):
    """Give API tests a fresh auth identity and encryption key without Supabase."""
    from app.auth import _current_user_id, require_authenticated_user
    from app.config import get_settings
    from app.main import app

    user_id = f"pytest-{uuid4()}"
    monkeypatch.setattr(
        get_settings(),
        "credential_encryption_key",
        Fernet.generate_key().decode("ascii"),
    )

    async def override_authenticated_user():
        token = _current_user_id.set(user_id)
        try:
            yield {"sub": user_id, "role": "authenticated"}
        finally:
            _current_user_id.reset(token)

    app.dependency_overrides[require_authenticated_user] = override_authenticated_user
    try:
        yield user_id
    finally:
        app.dependency_overrides.pop(require_authenticated_user, None)
