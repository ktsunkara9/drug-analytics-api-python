"""
Shared test fixtures and utilities.
"""
import pytest
import jwt
from datetime import datetime, timedelta


@pytest.fixture
def auth_headers():
    """Generate valid JWT token and return authorization headers."""
    # Use same secret as in config
    jwt_secret = "dev-secret-change-in-production"
    jwt_algorithm = "HS256"
    
    # Create token with 1 hour expiration
    expiration = datetime.utcnow() + timedelta(hours=1)
    payload = {
        "sub": "test_user",
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
    
    return {"Authorization": f"Bearer {token}"}
