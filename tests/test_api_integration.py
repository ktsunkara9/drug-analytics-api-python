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
        os.environ['UPLOAD_STATUS_TABLE_NAME'] = 'UploadStatus-test'
        os.environ['ENVIRONMENT'] = 'test'
        
        # Clear dependency injection cache
        from src.core import dependencies
        dependencies.get_s3_repository.cache_clear()
        dependencies.get_dynamo_repository.cache_clear()
        dependencies.get_upload_status_repository.cache_clear()
        dependencies.get_file_service.cache_clear()
        dependencies.get_drug_service.cache_clear()
        
        yield
        
        for key in ['S3_BUCKET_NAME', 'DYNAMODB_TABLE_NAME', 'UPLOAD_STATUS_TABLE_NAME', 'ENVIRONMENT']:
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
    def test_upload_csv_success(self, auth_headers):
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
        dynamodb.create_table(
            TableName='UploadStatus-test',
            KeySchema=[{'AttributeName': 'upload_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'upload_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        from src.main import app
        client = TestClient(app)
        
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5\nIbuprofen,COX-1,90.0"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = client.post("/v1/api/uploads", files=files, headers=auth_headers)
        assert response.status_code == 202
        data = response.json()
        assert "message" in data
        assert "s3_location" in data
        assert "upload_id" in data
        assert data["status"] == "pending"
    
    @mock_aws
    def test_upload_csv_invalid_file_type(self, auth_headers):
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
        
        response = client.post("/v1/api/uploads", files=files, headers=auth_headers)
        assert response.status_code == 400
        assert "CSV" in response.text
    
    @mock_aws
    def test_upload_csv_missing_columns(self, auth_headers):
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
        
        response = client.post("/v1/api/uploads", files=files, headers=auth_headers)
        assert response.status_code == 400
        assert "Missing required columns" in response.text
    
    @mock_aws
    def test_upload_csv_invalid_data(self, auth_headers):
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
        dynamodb.create_table(
            TableName='UploadStatus-test',
            KeySchema=[{'AttributeName': 'upload_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'upload_id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        from src.main import app
        client = TestClient(app)
        
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,invalid"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = client.post("/v1/api/uploads", files=files, headers=auth_headers)
        # File is uploaded successfully (202), validation happens async
        assert response.status_code == 202
        data = response.json()
        assert "upload_id" in data
        assert data["status"] == "pending"
    
    @mock_aws
    def test_get_all_drugs_empty(self, auth_headers):
        """Test getting all drugs when database is empty."""
        from src.core import config
        config.settings = config.Settings()
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        self._create_table_with_gsi()
        
        from src.main import app
        client = TestClient(app)
        
        response = client.get("/v1/api/drugs", headers=auth_headers)
        if response.status_code != 200:
            print(f"\nError response: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["drugs"] == []
        assert "next_token" in data
        assert data["next_token"] is None
    
    @mock_aws
    def test_get_drug_by_name_not_found(self, auth_headers):
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
        
        response = client.get("/v1/api/drugs/NonExistent", headers=auth_headers)
        if response.status_code not in [404, 200]:
            print(f"\nError response: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 404
        assert "not found" in response.text.lower()
    
    def _create_table_with_gsi(self):
        """Helper to create DynamoDB table with GSI."""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'drug_category', 'AttributeType': 'S'},
                {'AttributeName': 'upload_timestamp', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'DrugCategoryIndex',
                    'KeySchema': [
                        {'AttributeName': 'drug_category', 'KeyType': 'HASH'},
                        {'AttributeName': 'upload_timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    
    @mock_aws
    def test_get_all_drugs_pagination_response_structure(self, auth_headers):
        """Test that pagination response includes next_token field."""
        from src.core import config
        config.settings = config.Settings()
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        self._create_table_with_gsi()
        
        from src.main import app
        client = TestClient(app)
        
        response = client.get("/v1/api/drugs", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "drugs" in data
        assert "count" in data
        assert "next_token" in data
        assert data["next_token"] is None
    
    @mock_aws
    def test_get_all_drugs_with_limit_parameter(self, auth_headers):
        """Test pagination with custom limit."""
        from src.core import config
        config.settings = config.Settings()
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        self._create_table_with_gsi()
        
        from src.main import app
        client = TestClient(app)
        
        response = client.get("/v1/api/drugs?limit=5", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "next_token" in data
    
    @mock_aws
    def test_get_all_drugs_limit_validation(self, auth_headers):
        """Test limit parameter validation."""
        from src.core import config
        config.settings = config.Settings()
        
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        self._create_table_with_gsi()
        
        from src.main import app
        client = TestClient(app)
        
        # Test limit > 1000
        response = client.get("/v1/api/drugs?limit=5000", headers=auth_headers)
        assert response.status_code == 422
        
        # Test limit < 1
        response = client.get("/v1/api/drugs?limit=0", headers=auth_headers)
        assert response.status_code == 422
