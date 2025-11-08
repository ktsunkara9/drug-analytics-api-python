import pytest
from fastapi.testclient import TestClient
from moto import mock_aws
import boto3
from src.main import app
from src.core import config
from src.api.dependencies import get_drug_service


@pytest.fixture
def setup_test_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "DrugData-test")
    monkeypatch.setenv("UPLOAD_STATUS_TABLE_NAME", "UploadStatus-test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    config.settings = config.Settings()
    yield
    app.dependency_overrides.clear()
    get_drug_service.cache_clear()
    config.settings = config.Settings()


@pytest.fixture
def aws_resources(setup_test_env):
    with mock_aws():
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
        
        yield s3, dynamodb


class TestUploadStatusAPI:
    @mock_aws
    def test_upload_returns_upload_id_and_pending_status(self, aws_resources):
        client = TestClient(app)
        csv_content = "drug_name,target,efficacy\nAspirin,COX,85.5"
        
        response = client.post(
            "/v1/api/drugs/upload",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data
        assert data["status"] == "pending"
        assert data["message"] == "File uploaded successfully"

    @mock_aws
    def test_get_upload_status_success(self, aws_resources):
        _, dynamodb = aws_resources
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
        
        client = TestClient(app)
        response = client.get("/v1/api/drugs/status/test-uuid-123")
        
        assert response.status_code == 200
        data = response.json()
        assert data["upload_id"] == "test-uuid-123"
        assert data["status"] == "completed"
        assert data["total_rows"] == 50
        assert data["processed_rows"] == 50

    @mock_aws
    def test_get_upload_status_not_found(self, aws_resources):
        client = TestClient(app)
        response = client.get("/v1/api/drugs/status/nonexistent-id")
        
        assert response.status_code == 404
        assert response.json()["detail"] == "Upload status not found"

    @mock_aws
    def test_get_upload_status_processing(self, aws_resources):
        _, dynamodb = aws_resources
        table = dynamodb.Table("UploadStatus-test")
        table.put_item(Item={
            "upload_id": "test-uuid-456",
            "status": "processing",
            "filename": "data.csv",
            "s3_key": "uploads/test-uuid-456/data.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        client = TestClient(app)
        response = client.get("/v1/api/drugs/status/test-uuid-456")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["total_rows"] is None
        assert data["processed_rows"] is None

    @mock_aws
    def test_get_upload_status_failed(self, aws_resources):
        _, dynamodb = aws_resources
        table = dynamodb.Table("UploadStatus-test")
        table.put_item(Item={
            "upload_id": "test-uuid-789",
            "status": "failed",
            "filename": "bad.csv",
            "s3_key": "uploads/test-uuid-789/bad.csv",
            "created_at": "2024-01-01T12:00:00",
            "error_message": "Invalid CSV format"
        })
        
        client = TestClient(app)
        response = client.get("/v1/api/drugs/status/test-uuid-789")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["error_message"] == "Invalid CSV format"
