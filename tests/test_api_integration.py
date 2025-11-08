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


@mock_aws
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
        self.client = TestClient(app)
        
        yield
        
        for key in ['S3_BUCKET_NAME', 'DYNAMODB_TABLE_NAME', 'ENVIRONMENT']:
            if key in os.environ:
                del os.environ[key]
    
    def test_health_check(self):
        """Test health check endpoint."""
        response = self.client.get("/v1/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_hello_endpoint(self):
        """Test hello endpoint."""
        response = self.client.get("/v1/api/hello")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
    
    def test_upload_csv_success(self):
        """Test successful CSV file upload."""
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5\nIbuprofen,COX-1,90.0"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = self.client.post("/v1/api/drugs/upload", files=files)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "s3_key" in data
        assert data["drugs_processed"] == 2
    
    def test_upload_csv_invalid_file_type(self):
        """Test upload with invalid file type."""
        files = {"file": ("test.txt", io.BytesIO(b"invalid"), "text/plain")}
        
        response = self.client.post("/v1/api/drugs/upload", files=files)
        assert response.status_code == 400
        assert "CSV file" in response.json()["detail"]
    
    def test_upload_csv_missing_columns(self):
        """Test upload with missing required columns."""
        csv_content = b"drug_name,target\nAspirin,COX-2"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = self.client.post("/v1/api/drugs/upload", files=files)
        assert response.status_code == 400
        assert "Missing required columns" in response.json()["detail"]
    
    def test_upload_csv_invalid_data(self):
        """Test upload with invalid efficacy value."""
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,invalid"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        
        response = self.client.post("/v1/api/drugs/upload", files=files)
        assert response.status_code == 400
        assert "must be a number" in response.json()["detail"]
    
    def test_get_all_drugs_empty(self):
        """Test getting all drugs when database is empty."""
        response = self.client.get("/v1/api/drugs/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["drugs"] == []
    
    def test_get_all_drugs_with_data(self):
        """Test getting all drugs after uploading data."""
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        self.client.post("/v1/api/drugs/upload", files=files)
        
        response = self.client.get("/v1/api/drugs/")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["drugs"]) == 1
        assert data["drugs"][0]["drug_name"] == "Aspirin"
    
    def test_get_drug_by_name_success(self):
        """Test getting specific drug by name."""
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5"
        files = {"file": ("test.csv", io.BytesIO(csv_content), "text/csv")}
        self.client.post("/v1/api/drugs/upload", files=files)
        
        response = self.client.get("/v1/api/drugs/Aspirin")
        assert response.status_code == 200
        data = response.json()
        assert data["drug_name"] == "Aspirin"
        assert data["target"] == "COX-2"
        assert data["efficacy"] == 85.5
    
    def test_get_drug_by_name_not_found(self):
        """Test getting non-existent drug."""
        response = self.client.get("/v1/api/drugs/NonExistent")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
    
    def test_upload_multiple_versions_same_drug(self):
        """Test uploading same drug multiple times creates versions."""
        csv1 = b"drug_name,target,efficacy\nAspirin,COX-2,85.5"
        files1 = {"file": ("test1.csv", io.BytesIO(csv1), "text/csv")}
        self.client.post("/v1/api/drugs/upload", files=files1)
        
        csv2 = b"drug_name,target,efficacy\nAspirin,COX-2,90.0"
        files2 = {"file": ("test2.csv", io.BytesIO(csv2), "text/csv")}
        self.client.post("/v1/api/drugs/upload", files=files2)
        
        response = self.client.get("/v1/api/drugs/Aspirin")
        assert response.status_code == 200
        data = response.json()
        assert data["efficacy"] == 90.0
