"""
Unit tests for DynamoRepository.
Uses moto to mock AWS DynamoDB service.
"""
from datetime import datetime
from decimal import Decimal
import os
import pytest
from moto import mock_dynamodb
import boto3
from src.repositories.dynamo_repository import DynamoRepository
from src.models.drug_model import Drug
from src.core.exceptions import DrugNotFoundException


class TestDynamoRepository:
    """Test suite for DynamoRepository."""
    
    @pytest.fixture
    def aws_credentials(self):
        """Mock AWS credentials for moto."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
    
    def _create_table(self):
        """Helper to create DynamoDB table."""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-dev',
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
    
    @mock_dynamodb
    def test_save_drug_success(self, aws_credentials):
        """Test successful drug save to DynamoDB."""
        self._create_table()
        repo = DynamoRepository()
        
        drug = Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1")
        repo.save(drug)
        
        drugs = repo.find_by_drug_name("Aspirin")
        assert len(drugs) == 1
        assert drugs[0].drug_name == "Aspirin"
    
    @mock_dynamodb
    def test_find_by_drug_name_not_found(self, aws_credentials):
        """Test finding non-existent drug raises exception."""
        self._create_table()
        repo = DynamoRepository()
        
        with pytest.raises(DrugNotFoundException):
            repo.find_by_drug_name("NonExistent")
    
    @mock_dynamodb
    def test_find_all_success(self, aws_credentials):
        """Test retrieving all drugs."""
        self._create_table()
        repo = DynamoRepository()
        
        drug1 = Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1")
        drug2 = Drug("Ibuprofen", "COX-1", 90.0, datetime(2024, 1, 2), "key2")
        repo.save(drug1)
        repo.save(drug2)
        
        drugs = repo.find_all()
        assert len(drugs) == 2
    
    @mock_dynamodb
    def test_batch_save_success(self, aws_credentials):
        """Test batch saving multiple drugs."""
        self._create_table()
        repo = DynamoRepository()
        
        drugs = [
            Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1"),
            Drug("Ibuprofen", "COX-1", 90.0, datetime(2024, 1, 2), "key2"),
            Drug("Paracetamol", "COX-3", 75.0, datetime(2024, 1, 3), "key3")
        ]
        
        repo.batch_save(drugs)
        all_drugs = repo.find_all()
        assert len(all_drugs) == 3
