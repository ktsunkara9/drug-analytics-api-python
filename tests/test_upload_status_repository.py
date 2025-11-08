import pytest
from datetime import datetime
from moto import mock_aws
import boto3
from src.repositories.upload_status_repository import UploadStatusRepository
from src.models.upload_status import UploadStatus
from src.core import config
from src.core.exceptions import DynamoDBException


@pytest.fixture
def setup_test_env(monkeypatch):
    monkeypatch.setenv("UPLOAD_STATUS_TABLE_NAME", "UploadStatus-test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    config.settings = config.Settings()
    yield
    config.settings = config.Settings()


@pytest.fixture
def dynamodb_table(setup_test_env):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName="UploadStatus-test",
            KeySchema=[{"AttributeName": "upload_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "upload_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        yield table


class TestUploadStatusRepository:
    @mock_aws
    def test_create_success(self, dynamodb_table):
        repo = UploadStatusRepository()
        upload_status = UploadStatus(
            upload_id="test-uuid-123",
            status="pending",
            filename="test.csv",
            s3_key="uploads/test-uuid-123/test.csv",
            created_at=datetime.now()
        )
        
        repo.create(upload_status)
        
        response = dynamodb_table.get_item(Key={"upload_id": "test-uuid-123"})
        assert "Item" in response
        assert response["Item"]["upload_id"] == "test-uuid-123"
        assert response["Item"]["status"] == "pending"
        assert response["Item"]["filename"] == "test.csv"

    @mock_aws
    def test_get_by_id_success(self, dynamodb_table):
        dynamodb_table.put_item(Item={
            "upload_id": "test-uuid-456",
            "status": "completed",
            "filename": "data.csv",
            "s3_key": "uploads/test-uuid-456/data.csv",
            "created_at": "2024-01-01T12:00:00",
            "total_rows": 100,
            "processed_rows": 100
        })
        
        repo = UploadStatusRepository()
        result = repo.get_by_id("test-uuid-456")
        
        assert result is not None
        assert result.upload_id == "test-uuid-456"
        assert result.status == "completed"
        assert result.total_rows == 100

    @mock_aws
    def test_get_by_id_not_found(self, dynamodb_table):
        repo = UploadStatusRepository()
        result = repo.get_by_id("nonexistent-id")
        assert result is None

    @mock_aws
    def test_update_success(self, dynamodb_table):
        dynamodb_table.put_item(Item={
            "upload_id": "test-uuid-789",
            "status": "pending",
            "filename": "test.csv",
            "s3_key": "uploads/test-uuid-789/test.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        repo = UploadStatusRepository()
        repo.update("test-uuid-789", {"status": "processing"})
        
        response = dynamodb_table.get_item(Key={"upload_id": "test-uuid-789"})
        assert response["Item"]["status"] == "processing"

    @mock_aws
    def test_update_multiple_fields(self, dynamodb_table):
        dynamodb_table.put_item(Item={
            "upload_id": "test-uuid-999",
            "status": "processing",
            "filename": "test.csv",
            "s3_key": "uploads/test-uuid-999/test.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        repo = UploadStatusRepository()
        repo.update("test-uuid-999", {"status": "completed", "total_rows": 50, "processed_rows": 50})
        
        response = dynamodb_table.get_item(Key={"upload_id": "test-uuid-999"})
        assert response["Item"]["status"] == "completed"
        assert response["Item"]["total_rows"] == 50
        assert response["Item"]["processed_rows"] == 50

    @mock_aws
    def test_create_exception_handling(self, dynamodb_table):
        repo = UploadStatusRepository()
        upload_status = UploadStatus(
            upload_id="test-uuid-error",
            status="pending",
            filename="test.csv",
            s3_key="uploads/test.csv",
            created_at=datetime.now()
        )
        
        dynamodb_table.delete()
        
        with pytest.raises(DynamoDBException):
            repo.create(upload_status)

    @mock_aws
    def test_get_by_id_exception_handling(self, dynamodb_table):
        repo = UploadStatusRepository()
        dynamodb_table.delete()
        
        with pytest.raises(DynamoDBException):
            repo.get_by_id("test-uuid")

    @mock_aws
    def test_update_exception_handling(self, dynamodb_table):
        repo = UploadStatusRepository()
        dynamodb_table.delete()
        
        with pytest.raises(DynamoDBException):
            repo.update("test-uuid", {"status": "completed"})
