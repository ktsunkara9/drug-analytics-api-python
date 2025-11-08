"""
Integration tests for API endpoints.
Tests the full request/response cycle including routes, dependencies, and exception handlers.
"""
import io
import os
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
import boto3


class TestAPIIntegration:
    """Integration test suite for API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment with mocked AWS services."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_REGION'] = 'us-east-1'
        os.environ['S3_BUCKET_NAME'] = 'test-bucket'
        os.environ['DYNAMODB_TABLE_NAME'] = 'DrugData-test'
        os.environ['ENVIRONMENT'] = 'test'
        
        yield
        
        for key in ['S3_BUCKET_NAME', 'DYNAMODB_TABLE_NAME', 'ENVIRONMENT']:
            if key in os.environ:
                del os.environ[key]
    
    @mock_aws
    def test_health_check(self):
        """Test health check endpoint."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        response = client.get("/v1/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Drug Analytics API"
        assert data["version"] == "1.0.0"
    
    @mock_aws
    def test_hello_endpoint(self):
        """Test hello endpoint."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        response = client.get("/v1/api/hello")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    @mock_aws
    def test_upload_csv_success(self):
        """Test successful CSV file upload."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5\nIbuprofen,COX-1,90.0"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = client.post("/v1/api/drugs/upload", files=files)
        assert response.status_code == 202
        data = response.json()
        assert "message" in data
        assert "s3_location" in data
        assert data["status"] == "uploaded"
    
    @mock_aws
    def test_upload_csv_invalid_file_type(self):
        """Test upload with invalid file type."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        files = {"file": ("test.txt", io.BytesIO(b"invalid"), "text/plain")}
        
        response = client.post("/v1/api/drugs/upload", files=files)
        assert response.status_code == 400
        assert "CSV" in response.text
    
    @mock_aws
    def test_upload_csv_missing_columns(self):
        """Test upload with missing required columns."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        csv_content = b"drug_name,target\nAspirin,COX-2"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = client.post("/v1/api/drugs/upload", files=files)
        assert response.status_code == 400
        assert "Missing required columns" in response.text
    
    @mock_aws
    def test_upload_csv_invalid_data(self):
        """Test upload with invalid efficacy value."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,invalid"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = client.post("/v1/api/drugs/upload", files=files)
        # File is uploaded successfully (202), validation happens async
        assert response.status_code == 202
        data = response.json()
        assert "s3_location" in data
    
    @mock_aws
    def test_get_all_drugs_empty(self):
        """Test getting all drugs when database is empty."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        response = client.get("/v1/api/drugs/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["drugs"] == []
    
    @mock_aws
    def test_get_drug_by_name_not_found(self):
        """Test getting non-existent drug."""
        from src.core import config
        config.settings = config.Settings()
        
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
        client = TestClient(app)
        
        response = client.get("/v1/api/drugs/NonExistent")
        assert response.status_code == 404
        assert "not found" in response.text.lower()
