"""Shared test fixtures for authenticated API route coverage."""

from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def authenticated_test_user():
    """Give API tests a fresh authenticated identity without calling Supabase."""
    from app.auth import _current_user_id, require_authenticated_user
    from app.main import app

    user_id = f"pytest-{uuid4()}"

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
