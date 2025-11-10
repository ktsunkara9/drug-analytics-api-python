"""
Tests for authentication dependencies.
"""
import pytest
import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException
from src.core.auth_dependencies import verify_token
from src.core import config


class TestAuthDependencies:
    """Test suite for authentication dependencies."""
    
    def test_verify_token_success(self):
        """Test token verification with valid token."""
        # Create valid token
        jwt_secret = config.settings.jwt_secret
        jwt_algorithm = config.settings.jwt_algorithm
        expiration = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "sub": "test_user",
            "exp": expiration,
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
        
        # Test verification
        authorization = f"Bearer {token}"
        username = verify_token(authorization)
        
        assert username == "test_user"
    
    def test_verify_token_missing_header(self):
        """Test token verification with missing authorization header."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token(None)
        
        assert exc_info.value.status_code == 401
        assert "Missing authorization header" in exc_info.value.detail
    
    def test_verify_token_invalid_format(self):
        """Test token verification with invalid header format."""
        with pytest.raises(HTTPException) as exc_info:
            verify_token("InvalidFormat token123")
        
        assert exc_info.value.status_code == 401
        assert "Invalid authorization header format" in exc_info.value.detail
    
    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        jwt_secret = config.settings.jwt_secret
        jwt_algorithm = config.settings.jwt_algorithm
        expiration = datetime.utcnow() - timedelta(hours=1)  # Expired 1 hour ago
        payload = {
            "sub": "test_user",
            "exp": expiration,
            "iat": datetime.utcnow() - timedelta(hours=2)
        }
        token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
        
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
    
    def test_verify_token_invalid_signature(self):
        """Test token verification with invalid signature."""
        # Create token with wrong secret
        wrong_secret = "wrong-secret-key"
        jwt_algorithm = config.settings.jwt_algorithm
        expiration = datetime.utcnow() + timedelta(hours=1)
        payload = {
            "sub": "test_user",
            "exp": expiration,
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, wrong_secret, algorithm=jwt_algorithm)
        
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
    
    def test_verify_token_missing_subject(self):
        """Test token verification with missing subject claim."""
        jwt_secret = config.settings.jwt_secret
        jwt_algorithm = config.settings.jwt_algorithm
        expiration = datetime.utcnow() + timedelta(hours=1)
        payload = {
            # Missing "sub" claim
            "exp": expiration,
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)
        
        authorization = f"Bearer {token}"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token payload" in exc_info.value.detail
    
    def test_verify_token_malformed(self):
        """Test token verification with malformed token."""
        authorization = "Bearer malformed.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(authorization)
        
        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
