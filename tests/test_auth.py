"""
Authentication tests.

TODO: Implement comprehensive authentication tests:
- JWT token validation
- User signup and login flows
- Permission checks (user vs admin)
- Token expiration handling
- Invalid token scenarios
"""

from src.auth.models import TokenData


def test_token_data_model():
    """Test TokenData model creation."""
    token_data = TokenData(
        user_id=1,
        email="test@example.com",
        name="Test User",
        image="https://example.com/avatar.jpg",
    )
    assert token_data.user_id == 1
    assert token_data.email == "test@example.com"
    assert token_data.get_user_id() == 1


def test_token_data_minimal():
    """Test TokenData with minimal fields."""
    token_data = TokenData(user_id=2, email="minimal@example.com")
    assert token_data.user_id == 2
    assert token_data.email == "minimal@example.com"
    assert token_data.name is None
    assert token_data.image is None


# TODO: Implement these critical auth tests
class TestAuthenticationFlow:
    """
    TODO: Implement comprehensive authentication flow tests.

    Test cases to implement:
    - Valid JWT token processing
    - Invalid JWT signature handling
    - Expired token rejection
    - Missing required claims (email, sub)
    - User signup flow (first user as admin)
    - User login with password
    - Admin role verification
    - Rate limiting on auth endpoints
    """

    pass
