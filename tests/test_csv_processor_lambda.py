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


@pytest.fixture
def aws_resources(setup_env):
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
        s3_key = "uploads/abc123def456/test.csv"
        upload_id = _extract_upload_id(s3_key)
        assert upload_id == "abc123def456"

    @mock_aws
    def test_extract_upload_id_no_match(self):
        s3_key = "invalid/path/test.csv"
        upload_id = _extract_upload_id(s3_key)
        assert upload_id is None

    @mock_aws
    def test_handler_updates_status_to_processing(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = "drug_name,target,efficacy\nAspirin,COX,85.5\nIbuprofen,COX,90.0"
        s3.put_object(Bucket="test-bucket", Key="uploads/test123/data.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "test123",
            "status": "pending",
            "filename": "data.csv",
            "s3_key": "uploads/test123/data.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/test123/data.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "test123"})
        assert response["Item"]["status"] == "completed"
        assert response["Item"]["total_rows"] == 2
        assert response["Item"]["processed_rows"] == 2

    @mock_aws
    def test_handler_updates_status_to_completed(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = "drug_name,target,efficacy\nDrug1,Target1,75.0"
        s3.put_object(Bucket="test-bucket", Key="uploads/uuid456/test.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "uuid456",
            "status": "pending",
            "filename": "test.csv",
            "s3_key": "uploads/uuid456/test.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/uuid456/test.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "uuid456"})
        assert response["Item"]["status"] == "completed"
        assert response["Item"]["total_rows"] == 1
        assert response["Item"]["processed_rows"] == 1

    @mock_aws
    def test_handler_updates_status_to_failed_on_error(self, aws_resources):
        s3, dynamodb = aws_resources
        
        csv_content = "invalid,csv,format\nno,efficacy,column"
        s3.put_object(Bucket="test-bucket", Key="uploads/uuid789/bad.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "uuid789",
            "status": "pending",
            "filename": "bad.csv",
            "s3_key": "uploads/uuid789/bad.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/uuid789/bad.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "uuid789"})
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
        s3.put_object(Bucket="test-bucket", Key="uploads/multi123/drugs.csv", Body=csv_content)
        
        status_table = dynamodb.Table("UploadStatus-test")
        status_table.put_item(Item={
            "upload_id": "multi123",
            "status": "pending",
            "filename": "drugs.csv",
            "s3_key": "uploads/multi123/drugs.csv",
            "created_at": "2024-01-01T12:00:00"
        })
        
        event = {
            "Records": [{
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "uploads/multi123/drugs.csv"}
                }
            }]
        }
        
        handler(event, None)
        
        response = status_table.get_item(Key={"upload_id": "multi123"})
        assert response["Item"]["status"] == "completed"
        assert response["Item"]["total_rows"] == 4
        assert response["Item"]["processed_rows"] == 4
