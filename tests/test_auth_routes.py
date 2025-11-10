"""
Tests for authentication API routes.
"""
import pytest
import os
import bcrypt
import importlib
from fastapi.testclient import TestClient
from moto import mock_aws
import boto3
from src.core import config


class TestAuthRoutes:
    """Test suite for authentication routes."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['S3_BUCKET_NAME'] = 'test-bucket'
        os.environ['DYNAMODB_TABLE_NAME'] = 'DrugData-test'
        os.environ['UPLOAD_STATUS_TABLE_NAME'] = 'UploadStatus-test'
        os.environ['USERS_TABLE_NAME'] = 'users-test'
        os.environ['ENVIRONMENT'] = 'test'
        
        from src.core import dependencies
        dependencies.get_s3_repository.cache_clear()
        dependencies.get_dynamo_repository.cache_clear()
        dependencies.get_upload_status_repository.cache_clear()
        dependencies.get_file_service.cache_clear()
        dependencies.get_drug_service.cache_clear()
        
        yield
        
        for key in ['S3_BUCKET_NAME', 'DYNAMODB_TABLE_NAME', 'UPLOAD_STATUS_TABLE_NAME', 'USERS_TABLE_NAME', 'ENVIRONMENT']:
            if key in os.environ:
                del os.environ[key]
    
    @mock_aws
    def test_login_success(self):
        """Test successful login with valid credentials."""
        # Create DynamoDB tables
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        dynamodb.create_table(
            TableName='UploadStatus-test',
            KeySchema=[{'AttributeName': 'upload_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'upload_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
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
        
        # Reload settings after tables are created
        config.settings = config.Settings()
        
        # Reload auth_service to pick up new settings
        from src.services import auth_service
        importlib.reload(auth_service)
        
        from src.main import app
        client = TestClient(app)
        
        response = client.post(
            "/v1/api/auth/login",
            json={"username": "alice", "password": "password123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "alice"
        assert len(data["access_token"]) > 0
    
    @mock_aws
    def test_login_wrong_password(self):
        """Test login with wrong password."""
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        dynamodb.create_table(
            TableName='UploadStatus-test',
            KeySchema=[{'AttributeName': 'upload_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'upload_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
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
        
        config.settings = config.Settings()
        
        from src.services import auth_service
        importlib.reload(auth_service)
        
        from src.main import app
        client = TestClient(app)
        
        response = client.post(
            "/v1/api/auth/login",
            json={"username": "alice", "password": "wrong_password"}
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    @mock_aws
    def test_login_user_not_found(self):
        """Test login with non-existent user."""
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        dynamodb.create_table(
            TableName='UploadStatus-test',
            KeySchema=[{'AttributeName': 'upload_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'upload_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        dynamodb.create_table(
            TableName='users-test',
            KeySchema=[{'AttributeName': 'username', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'username', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        config.settings = config.Settings()
        
        from src.services import auth_service
        importlib.reload(auth_service)
        
        from src.main import app
        client = TestClient(app)
        
        response = client.post(
            "/v1/api/auth/login",
            json={"username": "nonexistent", "password": "password123"}
        )
        
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]
    
    @mock_aws
    def test_login_missing_username(self):
        """Test login with missing username."""
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        from src.main import app
        
        config.settings = config.Settings()
        client = TestClient(app)
        
        response = client.post(
            "/v1/api/auth/login",
            json={"password": "password123"}
        )
        
        assert response.status_code == 422  # Validation error
    
    @mock_aws
    def test_login_missing_password(self):
        """Test login with missing password."""
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        from src.main import app
        
        config.settings = config.Settings()
        client = TestClient(app)
        
        response = client.post(
            "/v1/api/auth/login",
            json={"username": "alice"}
        )
        
        assert response.status_code == 422  # Validation error
