"""
Root conftest.py — adds the backend directory to sys.path so that
`import app.*` works regardless of how pytest is invoked (pytest / python -m pytest).
"""
import sys
from pathlib import Path

import pytest

# Ensure the backend/ directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture(autouse=True)
def authenticate_api_requests_in_tests():
    """Keep existing endpoint tests focused on API behavior, not JWT plumbing."""
    from app.auth import require_authenticated_user
    from app.main import app

    app.dependency_overrides[require_authenticated_user] = lambda: {
        "sub": "test-user",
        "role": "authenticated",
    }
    yield
    app.dependency_overrides.pop(require_authenticated_user, None)
