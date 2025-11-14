import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from src.services.drug_service import DrugService
from src.models.upload_status import UploadStatus


class TestDrugServiceUploadStatus:
    @pytest.fixture
    def mock_repositories(self):
        s3_repo = Mock()
        dynamo_repo = Mock()
        upload_status_repo = Mock()
        return s3_repo, dynamo_repo, upload_status_repo

    @pytest.fixture
    def drug_service(self, mock_repositories):
        s3_repo, dynamo_repo, upload_status_repo = mock_repositories
        return DrugService(
            s3_repository=s3_repo,
            db_repository=dynamo_repo,
            upload_status_repository=upload_status_repo,
            file_service=Mock()
        )

    @patch('uuid.uuid4')
    def test_upload_drug_data_creates_status_record(self, mock_uuid, drug_service, mock_repositories):
        s3_repo, dynamo_repo, upload_status_repo = mock_repositories
        mock_uuid.return_value = "abc123"
        s3_repo.upload_file.return_value = {
            's3_key': 'uploads/abc123/test.csv',
            's3_location': 's3://bucket/uploads/abc123/test.csv'
        }
        
        csv_content = b"drug_name,target,efficacy\nAspirin,COX,85.5"
        filename = "test.csv"
        
        result = drug_service.upload_drug_data(csv_content, filename)
        
        assert result.upload_id == "abc123"
        assert result.status == "pending"
        s3_repo.upload_file.assert_called_once()
        upload_status_repo.create.assert_called_once()
        
        created_status = upload_status_repo.create.call_args[0][0]
        assert created_status.upload_id == "abc123"
        assert created_status.status == "pending"
        assert created_status.filename == filename

    def test_get_upload_status_success(self, mock_repositories):
        s3_repo, dynamo_repo, upload_status_repo = mock_repositories
        service = DrugService(
            s3_repository=s3_repo,
            db_repository=dynamo_repo,
            upload_status_repository=upload_status_repo,
            file_service=Mock()
        )
        
        mock_status = UploadStatus(
            upload_id="test-123",
            status="completed",
            filename="test.csv",
            s3_key="uploads/test-123/test.csv",
            created_at=datetime.now(),
            total_rows=100,
            processed_rows=100
        )
        upload_status_repo.get_by_id.return_value = mock_status
        
        result = service.get_upload_status("test-123")
        
        assert result.upload_id == "test-123"
        assert result.status == "completed"
        assert result.total_rows == 100

    def test_get_upload_status_not_found(self, mock_repositories):
        from fastapi import HTTPException
        s3_repo, dynamo_repo, upload_status_repo = mock_repositories
        service = DrugService(
            s3_repository=s3_repo,
            db_repository=dynamo_repo,
            upload_status_repository=upload_status_repo,
            file_service=Mock()
        )
        upload_status_repo.get_by_id.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            service.get_upload_status("nonexistent")
        
        assert exc_info.value.status_code == 404

    @patch('uuid.uuid4')
    def test_upload_creates_correct_s3_key(self, mock_uuid, drug_service, mock_repositories):
        s3_repo, _, upload_status_repo = mock_repositories
        mock_uuid.return_value = "xyz789"
        s3_repo.upload_file.return_value = {
            's3_key': 'uploads/xyz789/data.csv',
            's3_location': 's3://bucket/uploads/xyz789/data.csv'
        }
        
        csv_content = b"drug_name,target,efficacy\nDrug1,Target1,90.0"
        filename = "data.csv"
        
        drug_service.upload_drug_data(csv_content, filename)
        
        s3_repo.upload_file.assert_called_once()
        
        created_status = upload_status_repo.create.call_args[0][0]
        assert created_status.s3_key == "uploads/xyz789/data.csv"
