import pytest
import os
from fastapi.testclient import TestClient
from moto import mock_aws
import boto3
from src.core import config


@pytest.fixture
def setup_test_env():
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_REGION'] = 'us-east-1'
    os.environ['S3_BUCKET_NAME'] = 'test-bucket'
    os.environ['DYNAMODB_TABLE_NAME'] = 'DrugData-test'
    os.environ['UPLOAD_STATUS_TABLE_NAME'] = 'UploadStatus-test'
    os.environ['ENVIRONMENT'] = 'test'
    
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





class TestUploadStatusAPI:
    @mock_aws
    def test_upload_returns_upload_id_and_pending_status(self, setup_test_env):
        config.settings = config.Settings()
        
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="DrugData-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        dynamodb.create_table(
            TableName="UploadStatus-test",
            KeySchema=[{"AttributeName": "upload_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "upload_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        from src.main import app
        client = TestClient(app)
        csv_content = "drug_name,target,efficacy\nAspirin,COX,85.5"
        
        response = client.post(
            "/v1/api/uploads",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "upload_id" in data
        assert data["status"] == "pending"
        assert "successfully" in data["message"].lower()

    @mock_aws
    def test_get_upload_status_success(self, setup_test_env):
        config.settings = config.Settings()
        
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="DrugData-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        dynamodb.create_table(
            TableName="UploadStatus-test",
            KeySchema=[{"AttributeName": "upload_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "upload_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        table = dynamodb.Table("UploadStatus-test")
        table.put_item(Item={
            "upload_id": "test-uuid-123",
            "status": "completed",
            "filename": "test.csv",
            "s3_key": "uploads/test-uuid-123/test.csv",
            "created_at": "2024-01-01T12:00:00",
            "total_rows": 50,
            "processed_rows": 50
        })
        
        from src.main import app
        client = TestClient(app)
        response = client.get("/v1/api/uploads/test-uuid-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["upload_id"] == "test-uuid-123"
        assert data["status"] == "completed"
        assert data["total_rows"] == 50
        assert data["processed_rows"] == 50

    @mock_aws
    def test_get_upload_status_not_found(self, setup_test_env):
        config.settings = config.Settings()
        
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="DrugData-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        dynamodb.create_table(
            TableName="UploadStatus-test",
            KeySchema=[{"AttributeName": "upload_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "upload_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        from src.main import app
        client = TestClient(app)
        response = client.get("/v1/api/uploads/nonexistent-id")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @mock_aws
    def test_get_upload_status_processing(self, setup_test_env):
        config.settings = config.Settings()
        
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="DrugData-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        dynamodb.create_table(
            TableName="UploadStatus-test",
            KeySchema=[{"AttributeName": "upload_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "upload_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        table = dynamodb.Table("UploadStatus-test")
        table.put_item(Item={
            "upload_id": "test-uuid-456",
            "status": "processing",
            "filename": "data.csv",
            "s3_key": "uploads/test-uuid-456/data.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        from src.main import app
        client = TestClient(app)
        response = client.get("/v1/api/uploads/test-uuid-456")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["total_rows"] == 0
        assert data["processed_rows"] == 0

    @mock_aws
    def test_get_upload_status_failed(self, setup_test_env):
        config.settings = config.Settings()
        
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="DrugData-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        dynamodb.create_table(
            TableName="UploadStatus-test",
            KeySchema=[{"AttributeName": "upload_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "upload_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        table = dynamodb.Table("UploadStatus-test")
        table.put_item(Item={
            "upload_id": "test-uuid-789",
            "status": "failed",
            "filename": "bad.csv",
            "s3_key": "uploads/test-uuid-789/bad.csv",
            "created_at": "2024-01-01T12:00:00",
            "error_message": "Invalid CSV format"
        })
        
        from src.main import app
        client = TestClient(app)
        response = client.get("/v1/api/uploads/test-uuid-789")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Invalid CSV format"

    @mock_aws
    def test_upload_file_exceeds_size_limit(self, setup_test_env):
        config.settings = config.Settings()
        
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-bucket")
        
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        dynamodb.create_table(
            TableName="DrugData-test",
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"}
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"}
            ],
            BillingMode="PAY_PER_REQUEST"
        )
        dynamodb.create_table(
            TableName="UploadStatus-test",
            KeySchema=[{"AttributeName": "upload_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "upload_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        from src.main import app
        client = TestClient(app)
        
        # Create file larger than limit (default 10MB)
        max_size_bytes = config.settings.max_file_size_mb * 1024 * 1024
        large_content = "x" * (max_size_bytes + 1024)
        
        response = client.post(
            "/v1/api/uploads",
            files={"file": ("large.csv", large_content, "text/csv")}
        )
        
        assert response.status_code == 413
        assert "exceeds maximum allowed size" in response.json()["detail"]
        assert f"{config.settings.max_file_size_mb}MB" in response.json()["detail"]
