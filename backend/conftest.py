"""Pytest setup for backend tests; protected endpoints remain authenticated by default."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))


@pytest.fixture
def authenticated_client():
    """Explicit opt-in auth mock for tests focused on non-auth API behavior."""
    from fastapi.testclient import TestClient
    from app.auth import require_authenticated_user
    from app.main import app

    previous = app.dependency_overrides.get(require_authenticated_user)
    app.dependency_overrides[require_authenticated_user] = lambda: {
        "sub": "test-user",
        "role": "authenticated",
    }
    try:
        with TestClient(app) as client:
            yield client
    finally:
        if previous is None:
            app.dependency_overrides.pop(require_authenticated_user, None)
        else:
            app.dependency_overrides[require_authenticated_user] = previous
