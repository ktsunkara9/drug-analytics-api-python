"""
Authentication service for user login and JWT token management.
"""
import jwt
import bcrypt
import boto3
from datetime import datetime, timedelta
from typing import Optional
from src.core.config import settings


def create_access_token(username: str) -> str:
    """
    Generate a JWT access token for authenticated user.
    
    Args:
        username: The username to encode in the token
        
    Returns:
        Encoded JWT token string
    """
    expiration = datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours)
    
    payload = {
        "sub": username,
        "exp": expiration,
        "iat": datetime.utcnow()
    }
    
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt hashed password.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password from database
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate user by verifying credentials against DynamoDB.
    
    Args:
        username: Username to authenticate
        password: Plain text password to verify
        
    Returns:
        User dict if authentication successful, None otherwise
    """
    dynamodb = boto3.resource('dynamodb', region_name=settings.aws_region)
    table = dynamodb.Table(settings.users_table_name)
    
    response = table.get_item(Key={'username': username})
    
    if 'Item' not in response:
        return None
    
    user = response['Item']
    
    if not verify_password(password, user['password_hash']):
        return None
    
    return user
