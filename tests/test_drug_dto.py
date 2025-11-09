"""
Unit tests for Drug DTOs.
"""
import pytest
from datetime import datetime
from src.models.dto.drug_dto import DrugListResponse, DrugResponse


class TestDrugDTO:
    """Test Drug DTO models."""
    
    def test_drug_list_response_with_next_token(self):
        """Test DrugListResponse includes next_token field."""
        drugs = [
            DrugResponse(
                drug_name="Aspirin",
                target="COX-2",
                efficacy=85.5,
                upload_timestamp=datetime(2024, 1, 1)
            )
        ]
        
        response = DrugListResponse(
            drugs=drugs,
            count=1,
            next_token="token123"
        )
        
        assert response.drugs == drugs
        assert response.count == 1
        assert response.next_token == "token123"
    
    def test_drug_list_response_without_next_token(self):
        """Test DrugListResponse with None next_token."""
        drugs = [
            DrugResponse(
                drug_name="Aspirin",
                target="COX-2",
                efficacy=85.5,
                upload_timestamp=datetime(2024, 1, 1)
            )
        ]
        
        response = DrugListResponse(
            drugs=drugs,
            count=1
        )
        
        assert response.drugs == drugs
        assert response.count == 1
        assert response.next_token is None
    
    def test_drug_list_response_serialization(self):
        """Test DrugListResponse can be serialized to dict."""
        drugs = [
            DrugResponse(
                drug_name="Aspirin",
                target="COX-2",
                efficacy=85.5,
                upload_timestamp=datetime(2024, 1, 1)
            )
        ]
        
        response = DrugListResponse(
            drugs=drugs,
            count=1,
            next_token="token123"
        )
        
        data = response.model_dump()
        assert "drugs" in data
        assert "count" in data
        assert "next_token" in data
        assert data["next_token"] == "token123"
