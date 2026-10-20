"""
Root conftest.py — adds the backend directory to sys.path so that
`import app.*` works regardless of how pytest is invoked (pytest / python -m pytest).
"""
import os
import sys
from pathlib import Path

import pytest

# Test credentials are encrypted with an ephemeral, non-production key.
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")

# Ensure the backend/ directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    """Ensure test database and all tables are initialized for the test suite."""
    import asyncio
    from app.database import init_db

    asyncio.run(init_db())


@pytest.fixture(autouse=True)
def authenticate_api_requests_in_tests():
    """Keep existing endpoint tests focused on API behavior, not JWT plumbing."""
    from app.auth import _current_user_id, require_authenticated_user
    from app.main import app

    async def test_user_dependency():
        context_token = _current_user_id.set("test-user")
        try:
            yield {
                "sub": "test-user",
                "role": "authenticated",
            }
        finally:
            _current_user_id.reset(context_token)

    app.dependency_overrides[require_authenticated_user] = test_user_dependency
    yield
    app.dependency_overrides.pop(require_authenticated_user, None)
