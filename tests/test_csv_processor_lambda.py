import pytest
from unittest.mock import Mock, patch, MagicMock
from moto import mock_aws
import boto3
from lambda_functions.csv_processor import handler, _extract_upload_id


@pytest.fixture
def setup_env(monkeypatch):
    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("DYNAMODB_TABLE_NAME", "DrugData-test")
    monkeypatch.setenv("UPLOAD_STATUS_TABLE_NAME", "UploadStatus-test")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    from src.core import config
    config.settings = config.Settings()


@pytest.fixture
def aws_resources(setup_env):
    from src.core import config
    config.settings = config.Settings()
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


class TestCsvProcessorLambda:
    @mock_aws
    def test_extract_upload_id_success(self):
        s3_key = "uploads/a1b2c3d4-e5f6-4789-abcd-123456789012/test.csv"
        upload_id = _extract_upload_id(s3_key)
        assert upload_id == "a1b2c3d4-e5f6-4789-abcd-123456789012"

    @mock_aws
    def test_extract_upload_id_no_match(self):
        s3_key = "invalid/path/test.csv"
        upload_id = _extract_upload_id(s3_key)
        assert upload_id is None

    @mock_aws
    def test_handler_updates_status_to_processing(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = "drug_name,target,efficacy\nAspirin,COX,85.5\nIbuprofen,COX,90.0"
        s3.put_object(Bucket="test-bucket", Key="uploads/a1b2c3d4-5678-9abc-def0-123456789012/data.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "a1b2c3d4-5678-9abc-def0-123456789012",
            "status": "pending",
            "filename": "data.csv",
            "s3_key": "uploads/a1b2c3d4-5678-9abc-def0-123456789012/data.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/a1b2c3d4-5678-9abc-def0-123456789012/data.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "a1b2c3d4-5678-9abc-def0-123456789012"})
        assert response["Item"]["status"] == "completed"
        assert response["Item"]["total_rows"] == 2
        assert response["Item"]["processed_rows"] == 2

    @mock_aws
    def test_handler_updates_status_to_completed(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = "drug_name,target,efficacy\nDrug1,Target1,75.0"
        s3.put_object(Bucket="test-bucket", Key="uploads/b2c3d4e5-7890-abcd-ef12-345678901234/test.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "b2c3d4e5-7890-abcd-ef12-345678901234",
            "status": "pending",
            "filename": "test.csv",
            "s3_key": "uploads/b2c3d4e5-7890-abcd-ef12-345678901234/test.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/b2c3d4e5-7890-abcd-ef12-345678901234/test.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "b2c3d4e5-7890-abcd-ef12-345678901234"})
        assert response["Item"]["status"] == "completed"
        assert response["Item"]["total_rows"] == 1
        assert response["Item"]["processed_rows"] == 1

    @mock_aws
    def test_handler_updates_status_to_failed_on_error(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = "invalid,csv,format\nno,efficacy,column"
        s3.put_object(Bucket="test-bucket", Key="uploads/c3d4e5f6-abcd-ef12-3456-789012345678/bad.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "c3d4e5f6-abcd-ef12-3456-789012345678",
            "status": "pending",
            "filename": "bad.csv",
            "s3_key": "uploads/c3d4e5f6-abcd-ef12-3456-789012345678/bad.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/c3d4e5f6-abcd-ef12-3456-789012345678/bad.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "c3d4e5f6-abcd-ef12-3456-789012345678"})
        assert response["Item"]["status"] == "failed"
        assert "error_message" in response["Item"]

    @mock_aws
    def test_handler_without_upload_id_in_key(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = "drug_name,target,efficacy\nDrug1,Target1,80.0"
        s3.put_object(Bucket="test-bucket", Key="legacy/test.csv", Body=csv_content)
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "legacy/test.csv"}
                }
            }]
        }
        
        result = handler(event, None)
        assert result["statusCode"] == 200

    @mock_aws
    def test_handler_processes_multiple_rows(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = """drug_name,target,efficacy
Aspirin,COX,85.5
Ibuprofen,COX,90.0
Paracetamol,COX,75.0
Naproxen,COX,88.0"""
        s3.put_object(Bucket="test-bucket", Key="uploads/d4e5f6a7-4567-89ab-cdef-012345678901/drugs.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "d4e5f6a7-4567-89ab-cdef-012345678901",
            "status": "pending",
            "filename": "drugs.csv",
            "s3_key": "uploads/d4e5f6a7-4567-89ab-cdef-012345678901/drugs.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/d4e5f6a7-4567-89ab-cdef-012345678901/drugs.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "d4e5f6a7-4567-89ab-cdef-012345678901"})
        assert response["Item"]["status"] == "completed"
        assert response["Item"]["total_rows"] == 4
        assert response["Item"]["processed_rows"] == 4
