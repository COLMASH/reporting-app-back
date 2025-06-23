"""
Pytest configuration and fixtures.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.core.database.core import Base, get_db
from src.main import app
from src.modules.auth.models import User

# Test database URL (using SQLite for tests)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """Create test database session."""
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def client(test_db) -> Generator[TestClient, None, None]:
    """Create test client with overridden database."""

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user(test_db) -> User:
    """Create a test user."""
    user = User(email="test@example.com", name="Test User", is_active=True, role="user")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def admin_user(test_db) -> User:
    """Create a test admin user."""
    user = User(email="admin@example.com", name="Admin User", is_active=True, role="admin")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Create authentication headers for test user."""
    from src.modules.auth.service import create_access_token

    token = create_access_token(test_user)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers(admin_user) -> dict:
    """Create authentication headers for admin user."""
    from src.modules.auth.service import create_access_token

    token = create_access_token(admin_user)
    return {"Authorization": f"Bearer {token}"}


# Mock fixtures for external services
@pytest.fixture
def mock_supabase(mocker):
    """Mock Supabase client."""
    mock = mocker.patch("src.integrations.supabase.SupabaseService")
    return mock


@pytest.fixture
def mock_celery(mocker):
    """Mock Celery tasks."""
    mock = mocker.patch("src.integrations.celery_app.celery")
    return mock
