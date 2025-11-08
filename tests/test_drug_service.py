"""
Unit tests for DrugService.
Tests business logic orchestration with mocked dependencies.
"""
import io
from unittest.mock import Mock, MagicMock
import pytest
from src.services.drug_service import DrugService
from src.models.drug_model import Drug
from src.models.dto.drug_dto import DrugUploadResponse, DrugListResponse
from datetime import datetime


class TestDrugService:
    """Test suite for DrugService."""
    
    @pytest.fixture
    def mock_s3_repo(self):
        """Mock S3Repository."""
        return Mock()
    
    @pytest.fixture
    def mock_dynamo_repo(self):
        """Mock DynamoRepository."""
        return Mock()
    
    @pytest.fixture
    def mock_file_service(self):
        """Mock FileService."""
        return Mock()
    
    @pytest.fixture
    def mock_upload_status_repo(self):
        """Mock UploadStatusRepository."""
        return Mock()
    
    @pytest.fixture
    def drug_service(self, mock_s3_repo, mock_dynamo_repo, mock_upload_status_repo, mock_file_service):
        """Create DrugService with mocked dependencies."""
        return DrugService(
            s3_repository=mock_s3_repo,
            dynamo_repository=mock_dynamo_repo,
            upload_status_repository=mock_upload_status_repo,
            file_service=mock_file_service
        )
    
    @pytest.fixture
    def sample_drug(self):
        """Sample Drug object."""
        return Drug(
            drug_name="Aspirin",
            target="COX-2",
            efficacy=85.5,
            upload_timestamp=datetime(2024, 1, 1, 12, 0, 0),
            s3_key="uploads/2024/01/01/abc123_test.csv"
        )
    
    def test_upload_drug_data_success(self, drug_service, mock_s3_repo, mock_file_service, mock_upload_status_repo):
        """Test successful drug data upload."""
        # Setup
        file = io.BytesIO(b"drug_name,target,efficacy\nAspirin,COX-2,85.5")
        filename = "test.csv"
        mock_file_service.validate_csv_structure.return_value = None
        mock_s3_repo.upload_file.return_value = {
            's3_key': 'uploads/2024/01/01/abc123_test.csv',
            's3_location': 's3://bucket/uploads/2024/01/01/abc123_test.csv'
        }
        
        # Execute
        result = drug_service.upload_drug_data(file, filename)
        
        # Assert
        assert isinstance(result, DrugUploadResponse)
        assert result.upload_id is not None
        assert result.status == "pending"
        assert "successfully" in result.message.lower()
        assert result.s3_location == 's3://bucket/uploads/2024/01/01/abc123_test.csv'
        mock_file_service.validate_csv_structure.assert_called_once_with(file)
        mock_s3_repo.upload_file.assert_called_once()
        mock_upload_status_repo.create.assert_called_once()
    
    def test_get_drug_by_name_success(self, drug_service, mock_dynamo_repo, sample_drug):
        """Test retrieving drug by name."""
        # Setup
        mock_dynamo_repo.find_by_drug_name.return_value = [sample_drug]
        
        # Execute
        result = drug_service.get_drug_by_name("Aspirin")
        
        # Assert
        assert isinstance(result, DrugListResponse)
        assert result.count == 1
        assert len(result.drugs) == 1
        assert result.drugs[0].drug_name == "Aspirin"
        assert result.drugs[0].target == "COX-2"
        assert result.drugs[0].efficacy == 85.5
        mock_dynamo_repo.find_by_drug_name.assert_called_once_with("Aspirin")
    
    def test_get_drug_by_name_multiple_versions(self, drug_service, mock_dynamo_repo):
        """Test retrieving multiple versions of same drug."""
        # Setup
        drugs = [
            Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1"),
            Drug("Aspirin", "COX-2", 90.0, datetime(2024, 1, 2), "key2")
        ]
        mock_dynamo_repo.find_by_drug_name.return_value = drugs
        
        # Execute
        result = drug_service.get_drug_by_name("Aspirin")
        
        # Assert
        assert result.count == 2
        assert len(result.drugs) == 2
        assert result.drugs[0].efficacy == 85.5
        assert result.drugs[1].efficacy == 90.0
    
    def test_get_all_drugs_success(self, drug_service, mock_dynamo_repo, sample_drug):
        """Test retrieving all drugs."""
        # Setup
        drug2 = Drug("Ibuprofen", "COX-1", 90.0, datetime(2024, 1, 1), "key2")
        mock_dynamo_repo.find_all.return_value = [sample_drug, drug2]
        
        # Execute
        result = drug_service.get_all_drugs()
        
        # Assert
        assert isinstance(result, DrugListResponse)
        assert result.count == 2
        assert len(result.drugs) == 2
        assert result.drugs[0].drug_name == "Aspirin"
        assert result.drugs[1].drug_name == "Ibuprofen"
        mock_dynamo_repo.find_all.assert_called_once()
    
    def test_get_all_drugs_empty(self, drug_service, mock_dynamo_repo):
        """Test retrieving all drugs when none exist."""
        # Setup
        mock_dynamo_repo.find_all.return_value = []
        
        # Execute
        result = drug_service.get_all_drugs()
        
        # Assert
        assert result.count == 0
        assert len(result.drugs) == 0
    
    def test_process_csv_and_save_success(self, drug_service, mock_s3_repo, mock_file_service, mock_dynamo_repo):
        """Test CSV processing and saving to DynamoDB."""
        # Setup
        s3_key = "uploads/2024/01/01/abc123_test.csv"
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5"
        drugs = [Drug("Aspirin", "COX-2", 85.5)]
        
        mock_s3_repo.get_file.return_value = csv_content
        mock_file_service.parse_csv_to_drugs.return_value = drugs
        mock_dynamo_repo.batch_save.return_value = None
        
        # Execute
        count = drug_service.process_csv_and_save(s3_key)
        
        # Assert
        assert count == 1
        mock_s3_repo.get_file.assert_called_once_with(s3_key)
        mock_file_service.parse_csv_to_drugs.assert_called_once()
        mock_dynamo_repo.batch_save.assert_called_once()
        # Verify s3_key was set on drugs
        saved_drugs = mock_dynamo_repo.batch_save.call_args[0][0]
        assert saved_drugs[0].s3_key == s3_key
    
    def test_process_csv_and_save_multiple_records(self, drug_service, mock_s3_repo, mock_file_service, mock_dynamo_repo):
        """Test processing CSV with multiple records."""
        # Setup
        s3_key = "uploads/2024/01/01/abc123_test.csv"
        drugs = [
            Drug("Aspirin", "COX-2", 85.5),
            Drug("Ibuprofen", "COX-1", 90.0),
            Drug("Paracetamol", "COX-3", 75.0)
        ]
        
        mock_s3_repo.get_file.return_value = b"csv_content"
        mock_file_service.parse_csv_to_drugs.return_value = drugs
        
        # Execute
        count = drug_service.process_csv_and_save(s3_key)
        
        # Assert
        assert count == 3
        saved_drugs = mock_dynamo_repo.batch_save.call_args[0][0]
        assert len(saved_drugs) == 3
        assert all(drug.s3_key == s3_key for drug in saved_drugs)
