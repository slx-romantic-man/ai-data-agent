"""Pytest fixtures and configuration."""
import os
import pytest
from fastapi.testclient import TestClient

# Set test environment variables before importing app
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault("API_AUTH_ENCRYPTION_KEY", "test-encryption-key")
os.environ.setdefault("LLM_API_KEY", "test-llm-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DEBUG", "true")


@pytest.fixture
def client():
    """Create a FastAPI TestClient."""
    from app.main import app
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Generate a valid admin JWT token for testing."""
    from app.api.v1.auth import create_access_token
    return create_access_token(
        data={"sub": "admin", "username": "管理员", "login_id": "admin"}
    )


@pytest.fixture
def user_token():
    """Generate a valid user JWT token for testing."""
    from app.api.v1.auth import create_access_token
    return create_access_token(
        data={"sub": "user_001", "username": "张三", "login_id": "user1"}
    )


@pytest.fixture
def admin_headers(admin_token):
    """Return headers with admin authentication."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def user_headers(user_token):
    """Return headers with user authentication."""
    return {"Authorization": f"Bearer {user_token}"}
