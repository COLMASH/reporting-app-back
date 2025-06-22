"""
Comprehensive authentication tests.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from src.auth import models, service
from src.config import settings
from src.database.core import Base, get_db
from src.entities.user import User
from src.main import app

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for tests."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_database():
    """Create tables before each test and drop after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """Database session fixture."""
    session = TestingSessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(db_session: Session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=service.hash_password("TestPass123!"),
        name="Test User",
        company_name="Test Corp",
        role="user",
        emailVerified=datetime.now(UTC),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_admin(db_session: Session):
    """Create a test admin user."""
    admin = User(
        email="admin@example.com",
        password_hash=service.hash_password("AdminPass123!"),
        name="Admin User",
        company_name="Admin Corp",
        role="admin",
        emailVerified=datetime.now(UTC),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def user_token(test_user: User):
    """Generate a valid token for test user."""
    return service.create_access_token(test_user)


@pytest.fixture
def admin_token(test_admin: User):
    """Generate a valid token for admin user."""
    return service.create_access_token(test_admin)


@pytest.fixture
def expired_token(test_user: User):
    """Generate an expired token."""
    return service.create_access_token(test_user, expires_delta=timedelta(seconds=-1))


# ============================================================================
# Model Tests
# ============================================================================


def test_token_data_model():
    """Test TokenData model creation."""
    test_uuid = uuid.uuid4()
    token_data = models.TokenData(
        user_id=str(test_uuid),
        email="test@example.com",
        name="Test User",
        image="https://example.com/avatar.jpg",
    )
    assert token_data.user_id == str(test_uuid)
    assert token_data.email == "test@example.com"
    assert token_data.name == "Test User"
    assert token_data.image == "https://example.com/avatar.jpg"


def test_password_validation():
    """Test password validation rules."""
    # Valid password
    valid_request = models.SignupRequest(
        email="test@example.com",
        password="ValidPass123!",
        name="Test User",
    )
    assert valid_request.password == "ValidPass123!"

    # Invalid passwords
    with pytest.raises(ValueError, match="at least one lowercase"):
        models.SignupRequest(
            email="test@example.com",
            password="VALIDPASS123!",
            name="Test User",
        )

    with pytest.raises(ValueError, match="at least one uppercase"):
        models.SignupRequest(
            email="test@example.com",
            password="validpass123!",
            name="Test User",
        )

    with pytest.raises(ValueError, match="at least one number"):
        models.SignupRequest(
            email="test@example.com",
            password="ValidPass!",
            name="Test User",
        )

    with pytest.raises(ValueError, match="at least one special character"):
        models.SignupRequest(
            email="test@example.com",
            password="ValidPass123",
            name="Test User",
        )


# ============================================================================
# Signup Tests
# ============================================================================


def test_signup_first_user_becomes_admin(client: TestClient):
    """Test that the first user automatically becomes admin."""
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "first@example.com",
            "password": "FirstUser123!",
            "name": "First User",
            "company_name": "First Corp",
            "role": "user",  # Requesting user role
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "first@example.com"
    assert data["role"] == "admin"  # But gets admin role
    assert data["name"] == "First User"


def test_signup_duplicate_email(client: TestClient, test_admin: User, admin_token: str):
    """Test signup with duplicate email."""
    # Admin tries to create user with existing admin email
    response = client.post(
        "/api/v1/auth/signup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": test_admin.email,  # Using admin's email
            "password": "DupePass123!",
            "name": "Duplicate User",
        },
    )
    assert response.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in response.json()["detail"]


def test_signup_second_user_requires_admin(client: TestClient, test_user: User, admin_token: str):
    """Test that creating second user requires admin authentication."""
    # Without auth - should fail
    response = client.post(
        "/api/v1/auth/signup",
        json={
            "email": "second@example.com",
            "password": "SecondUser123!",
            "name": "Second User",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

    # With admin auth - should succeed
    response = client.post(
        "/api/v1/auth/signup",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "email": "second@example.com",
            "password": "SecondUser123!",
            "name": "Second User",
            "role": "user",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["role"] == "user"


def test_signup_non_admin_cannot_create_users(client: TestClient, test_user: User, user_token: str):
    """Test that regular users cannot create new users."""
    response = client.post(
        "/api/v1/auth/signup",
        headers={"Authorization": f"Bearer {user_token}"},
        json={
            "email": "newuser@example.com",
            "password": "NewUser123!",
            "name": "New User",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Admin access required" in response.json()["detail"]


# ============================================================================
# Login Tests
# ============================================================================


def test_login_success(client: TestClient, test_user: User):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "TestPass123!",
        },
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_invalid_email(client: TestClient):
    """Test login with non-existent email."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePass123!",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]


def test_login_invalid_password(client: TestClient, test_user: User):
    """Test login with wrong password."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "WrongPass123!",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid email or password" in response.json()["detail"]


def test_login_inactive_user(client: TestClient, db_session: Session):
    """Test login with inactive user."""
    # Create inactive user
    user = User(
        email="inactive@example.com",
        password_hash=service.hash_password("InactivePass123!"),
        name="Inactive User",
        role="user",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "InactivePass123!",
        },
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Account is disabled" in response.json()["detail"]


# ============================================================================
# Token Verification Tests
# ============================================================================


def test_verify_token_valid(client: TestClient, user_token: str):
    """Test token verification with valid token."""
    response = client.post(
        "/api/v1/auth/verify",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == "test@example.com"


def test_verify_token_expired(client: TestClient, expired_token: str):
    """Test token verification with expired token."""
    response = client.post(
        "/api/v1/auth/verify",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid or expired token" in response.json()["detail"]


def test_verify_token_invalid_signature(client: TestClient):
    """Test token verification with invalid signature."""
    # Create token with wrong secret
    payload = {
        "sub": "test@example.com",
        "email": "test@example.com",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    invalid_token = jwt.encode(payload, "wrong_secret", algorithm=settings.jwt_algorithm)

    response = client.post(
        "/api/v1/auth/verify",
        headers={"Authorization": f"Bearer {invalid_token}"},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ============================================================================
# Get Current User Tests
# ============================================================================


def test_get_me_success(client: TestClient, test_user: User, user_token: str):
    """Test getting current user info."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["email"] == test_user.email
    assert data["name"] == test_user.name
    assert data["role"] == "user"
    assert data["is_active"] is True


def test_get_me_no_token(client: TestClient):
    """Test getting current user without token."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "Not authenticated" in response.json()["detail"]


def test_get_me_inactive_user(client: TestClient, db_session: Session):
    """Test getting current user info for inactive user."""
    # Create inactive user with token
    user = User(
        email="inactive@example.com",
        password_hash=service.hash_password("InactivePass123!"),
        name="Inactive User",
        role="user",
        is_active=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Create token for inactive user
    token = service.create_access_token(user)

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert "User account is disabled" in response.json()["detail"]


# ============================================================================
# Service Function Tests
# ============================================================================


def test_hash_password():
    """Test password hashing."""
    password = "TestPassword123!"
    hashed = service.hash_password(password)

    # Hash should be different from original
    assert hashed != password

    # Should be able to verify
    assert service.verify_password(password, hashed) is True
    assert service.verify_password("WrongPassword", hashed) is False


def test_create_and_decode_token(test_user: User):
    """Test token creation and decoding."""
    # Create token
    token = service.create_access_token(test_user)

    # Decode token
    token_data = service.decode_token(token)

    assert token_data.email == test_user.email
    assert str(test_user.id) in str(token_data.user_id)
