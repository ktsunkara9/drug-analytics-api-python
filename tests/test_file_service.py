"""
Unit tests for FileService.
Tests CSV validation, parsing, and error handling.
"""
import io
from unittest.mock import Mock, patch
import pytest
from src.services.file_service import FileService
from src.core.exceptions import ValidationException, CSVProcessingException


class TestFileService:
    """Test suite for FileService."""
    
    @pytest.fixture
    def file_service(self):
        """Create FileService instance."""
        return FileService()
    
    @pytest.fixture
    def valid_csv(self):
        """Valid CSV content."""
        return b"drug_name,target,efficacy\nAspirin,COX-2,85.5\nIbuprofen,COX-1,90.0"
    
    def test_validate_csv_structure_success(self, file_service, valid_csv):
        """Test successful CSV validation."""
        file = io.BytesIO(valid_csv)
        file_service.validate_csv_structure(file)
        # No exception means success
    
    def test_validate_csv_missing_columns(self, file_service):
        """Test validation fails with missing columns."""
        csv_content = b"drug_name,target\nAspirin,COX-2"
        file = io.BytesIO(csv_content)
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.validate_csv_structure(file)
        assert "Missing required columns" in str(exc_info.value)
        assert "efficacy" in str(exc_info.value)
    
    def test_validate_csv_invalid_encoding(self, file_service):
        """Test validation fails with invalid encoding."""
        file = io.BytesIO(b"\xff\xfe")  # Invalid UTF-8
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.validate_csv_structure(file)
        assert "UTF-8" in str(exc_info.value)
    
    def test_validate_csv_generic_exception(self, file_service):
        """Test validation handles generic exceptions."""
        mock_file = Mock()
        mock_file.read.side_effect = IOError("Disk error")
        
        with pytest.raises(CSVProcessingException) as exc_info:
            file_service.validate_csv_structure(mock_file)
        assert "Failed to validate CSV structure" in str(exc_info.value)
    
    def test_parse_csv_success(self, file_service, valid_csv):
        """Test successful CSV parsing."""
        file = io.BytesIO(valid_csv)
        drugs = file_service.parse_csv_to_drugs(file)
        
        assert len(drugs) == 2
        assert drugs[0].drug_name == "Aspirin"
        assert drugs[0].target == "COX-2"
        assert drugs[0].efficacy == 85.5
        assert drugs[1].drug_name == "Ibuprofen"
        assert drugs[1].target == "COX-1"
        assert drugs[1].efficacy == 90.0
    
    def test_parse_csv_empty_file(self, file_service):
        """Test parsing fails with empty CSV."""
        csv_content = b"drug_name,target,efficacy\n"
        file = io.BytesIO(csv_content)
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.parse_csv_to_drugs(file)
        assert "empty" in str(exc_info.value).lower()
    
    def test_parse_csv_empty_drug_name(self, file_service):
        """Test parsing fails with empty drug_name."""
        csv_content = b"drug_name,target,efficacy\n,COX-2,85.5"
        file = io.BytesIO(csv_content)
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.parse_csv_to_drugs(file)
        assert "drug_name cannot be empty" in str(exc_info.value)
    
    def test_parse_csv_empty_target(self, file_service):
        """Test parsing fails with empty target."""
        csv_content = b"drug_name,target,efficacy\nAspirin,,85.5"
        file = io.BytesIO(csv_content)
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.parse_csv_to_drugs(file)
        assert "target cannot be empty" in str(exc_info.value)
    
    def test_parse_csv_invalid_efficacy_format(self, file_service):
        """Test parsing fails with non-numeric efficacy."""
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,invalid"
        file = io.BytesIO(csv_content)
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.parse_csv_to_drugs(file)
        assert "must be a number" in str(exc_info.value)
    
    def test_parse_csv_efficacy_out_of_range_low(self, file_service):
        """Test parsing fails with efficacy < 0."""
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,-5.0"
        file = io.BytesIO(csv_content)
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.parse_csv_to_drugs(file)
        assert "between 0 and 100" in str(exc_info.value)
    
    def test_parse_csv_efficacy_out_of_range_high(self, file_service):
        """Test parsing fails with efficacy > 100."""
        csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,150.0"
        file = io.BytesIO(csv_content)
        
        with pytest.raises(ValidationException) as exc_info:
            file_service.parse_csv_to_drugs(file)
        assert "between 0 and 100" in str(exc_info.value)
    
    def test_parse_csv_boundary_values(self, file_service):
        """Test parsing with boundary efficacy values (0 and 100)."""
        csv_content = b"drug_name,target,efficacy\nDrug1,Target1,0\nDrug2,Target2,100"
        file = io.BytesIO(csv_content)
        
        drugs = file_service.parse_csv_to_drugs(file)
        assert len(drugs) == 2
        assert drugs[0].efficacy == 0.0
        assert drugs[1].efficacy == 100.0
    
    def test_parse_csv_strips_whitespace(self, file_service):
        """Test parsing strips whitespace from fields."""
        csv_content = b"drug_name,target,efficacy\n  Aspirin  ,  COX-2  ,85.5"
        file = io.BytesIO(csv_content)
        
        drugs = file_service.parse_csv_to_drugs(file)
        assert drugs[0].drug_name == "Aspirin"
        assert drugs[0].target == "COX-2"
    
    def test_parse_csv_generic_exception(self, file_service):
        """Test parsing handles generic exceptions."""
        mock_file = Mock()
        mock_file.read.side_effect = IOError("Disk error")
        
        with pytest.raises(CSVProcessingException) as exc_info:
            file_service.parse_csv_to_drugs(mock_file)
        assert "Failed to parse CSV file" in str(exc_info.value)
    
    def test_row_to_drug_generic_exception(self, file_service):
        """Test _row_to_drug handles unexpected exceptions."""
        # Create a mock Drug class that raises exception
        with patch('src.services.file_service.Drug') as mock_drug:
            mock_drug.side_effect = RuntimeError("Unexpected error")
            
            csv_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5"
            file = io.BytesIO(csv_content)
            
            with pytest.raises(ValidationException) as exc_info:
                file_service.parse_csv_to_drugs(file)
            assert "Invalid data" in str(exc_info.value)
