"""
Tests for authentication service.
"""
import pytest
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from moto import mock_aws
import boto3
import importlib
from src.core import config


class TestAuthService:
    """Test suite for authentication service."""
    
    def test_create_access_token_success(self):
        """Test JWT token creation with valid username."""
        from src.services.auth_service import create_access_token
        username = "test_user"
        token = create_access_token(username)
        
        # Verify token is a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify payload
        jwt_secret = config.settings.jwt_secret
        jwt_algorithm = config.settings.jwt_algorithm
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        
        assert payload["sub"] == username
        assert "exp" in payload
        assert "iat" in payload
    
    def test_create_access_token_expiration(self):
        """Test token expiration is set correctly."""
        from src.services.auth_service import create_access_token
        username = "test_user"
        before_creation = datetime.utcnow()
        token = create_access_token(username)
        after_creation = datetime.utcnow()
        
        jwt_secret = config.settings.jwt_secret
        jwt_algorithm = config.settings.jwt_algorithm
        payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        
        exp_time = datetime.utcfromtimestamp(payload["exp"])
        expected_exp = before_creation + timedelta(hours=config.settings.jwt_expiration_hours)
        
        # Allow 1 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 1
    
    def test_verify_password_success(self):
        """Test password verification with matching password."""
        from src.services.auth_service import verify_password
        plain_password = "test_password_123"
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        result = verify_password(plain_password, hashed_password)
        assert result is True
    
    def test_verify_password_failure(self):
        """Test password verification with non-matching password."""
        from src.services.auth_service import verify_password
        plain_password = "test_password_123"
        wrong_password = "wrong_password"
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        result = verify_password(wrong_password, hashed_password)
        assert result is False
    
    @mock_aws
    def test_authenticate_user_success(self):
        """Test successful user authentication."""
        # Create DynamoDB table first
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='users-test',
            KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Add test user
        table = dynamodb.Table('users-test')
        password_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        table.put_item(Item={
            'username': 'alice',
            'password_hash': password_hash,
            'role': 'admin'
        })
        
        # Set environment and reload settings AFTER table creation
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['USERS_TABLE_NAME'] = 'users-test'
        config.settings = config.Settings()
        
        # Reload auth_service to pick up new settings
        from src.services import auth_service
        importlib.reload(auth_service)
        
        # Test authentication
        user = auth_service.authenticate_user('alice', 'password123')
        
        assert user is not None
        assert user['username'] == 'alice'
        assert user['role'] == 'admin'
        
        del os.environ['USERS_TABLE_NAME']
    
    @mock_aws
    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password."""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='users-test',
            KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        table = dynamodb.Table('users-test')
        password_hash = bcrypt.hashpw('password123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        table.put_item(Item={
            'username': 'alice',
            'password_hash': password_hash
        })
        
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['USERS_TABLE_NAME'] = 'users-test'
        config.settings = config.Settings()
        
        from src.services import auth_service
        importlib.reload(auth_service)
        
        user = auth_service.authenticate_user('alice', 'wrong_password')
        
        assert user is None
        
        del os.environ['USERS_TABLE_NAME']
    
    @mock_aws
    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user."""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='users-test',
            KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['USERS_TABLE_NAME'] = 'users-test'
        config.settings = config.Settings()
        
        from src.services import auth_service
        importlib.reload(auth_service)
        
        user = auth_service.authenticate_user('nonexistent', 'password123')
        
        assert user is None
        
        del os.environ['USERS_TABLE_NAME']
