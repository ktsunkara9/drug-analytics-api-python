"""
Unit tests for DynamoRepository.
Uses moto to mock AWS DynamoDB service.
"""
from datetime import datetime
from decimal import Decimal
import os
import pytest
from moto import mock_aws
import boto3
from src.repositories.dynamo_repository import DynamoRepository
from src.models.drug_model import Drug
from src.core.exceptions import DrugNotFoundException, DynamoDBException, ValidationException
import base64
import json


class TestDynamoRepository:
    """Test suite for DynamoRepository."""
    
    @pytest.fixture(autouse=True)
    def aws_credentials(self):
        """Mock AWS credentials for moto."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['DYNAMODB_TABLE_NAME'] = 'DrugData-test'
        
        yield
        
        if 'DYNAMODB_TABLE_NAME' in os.environ:
            del os.environ['DYNAMODB_TABLE_NAME']
    
    def _create_table(self):
        """Helper to create DynamoDB table with GSI."""
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        dynamodb.create_table(
            TableName='DrugData-test',
            KeySchema=[
                {'AttributeName': 'PK', 'KeyType': 'HASH'},
                {'AttributeName': 'SK', 'KeyType': 'RANGE'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'PK', 'AttributeType': 'S'},
                {'AttributeName': 'SK', 'AttributeType': 'S'},
                {'AttributeName': 'drug_category', 'AttributeType': 'S'},
                {'AttributeName': 'upload_timestamp', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'DrugCategoryIndex',
                    'KeySchema': [
                        {'AttributeName': 'drug_category', 'KeyType': 'HASH'},
                        {'AttributeName': 'upload_timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'}
                }
            ],
            BillingMode='PAY_PER_REQUEST'
        )
    
    @mock_aws
    def test_save_drug_success(self):
        """Test successful drug save to DynamoDB."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        drug = Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1")
        repo.save(drug)
        
        # Verify drug was saved with drug_category attribute
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('DrugData-test')
        response = table.get_item(Key={'PK': 'DRUG#Aspirin', 'SK': f'METADATA#{datetime(2024, 1, 1).isoformat()}'})
        assert 'Item' in response
        assert response['Item']['drug_category'] == 'ALL'
        
        drugs = repo.find_by_drug_name("Aspirin")
        assert len(drugs) == 1
        assert drugs[0].drug_name == "Aspirin"
    
    @mock_aws
    def test_find_by_drug_name_not_found(self):
        """Test finding non-existent drug raises exception."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        with pytest.raises(DrugNotFoundException):
            repo.find_by_drug_name("NonExistent")
    
    @mock_aws
    def test_find_all_success(self):
        """Test retrieving all drugs."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        drug1 = Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1")
        drug2 = Drug("Ibuprofen", "COX-1", 90.0, datetime(2024, 1, 2), "key2")
        repo.save(drug1)
        repo.save(drug2)
        
        drugs = repo.find_all()
        assert len(drugs) == 2
    
    @mock_aws
    def test_batch_save_success(self):
        """Test batch saving multiple drugs."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        drugs = [
            Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1"),
            Drug("Ibuprofen", "COX-1", 90.0, datetime(2024, 1, 2), "key2"),
            Drug("Paracetamol", "COX-3", 75.0, datetime(2024, 1, 3), "key3")
        ]
        
        repo.batch_save(drugs)
        
        # Verify all drugs were saved with drug_category attribute
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.Table('DrugData-test')
        for drug in drugs:
            response = table.get_item(Key={'PK': f'DRUG#{drug.drug_name}', 'SK': f'METADATA#{drug.upload_timestamp.isoformat()}'})
            assert 'Item' in response
            assert response['Item']['drug_category'] == 'ALL'
        
        all_drugs = repo.find_all()
        assert len(all_drugs) == 3
    
    @mock_aws
    def test_save_generic_exception(self):
        """Test save handles generic exceptions."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        # Create invalid drug that will cause exception during conversion
        from unittest.mock import patch
        with patch.object(repo.table, 'put_item', side_effect=Exception("Unexpected error")):
            drug = Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1")
            with pytest.raises(DynamoDBException) as exc_info:
                repo.save(drug)
            assert "Unexpected error saving drug data" in str(exc_info.value)
    
    @mock_aws
    def test_find_by_drug_name_generic_exception(self):
        """Test find_by_drug_name handles generic exceptions."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        from unittest.mock import patch
        with patch.object(repo.table, 'query', side_effect=Exception("Unexpected error")):
            with pytest.raises(DynamoDBException) as exc_info:
                repo.find_by_drug_name("Aspirin")
            assert "Unexpected error querying drug data" in str(exc_info.value)
    
    @mock_aws
    def test_find_all_generic_exception(self):
        """Test find_all handles generic exceptions."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        from unittest.mock import patch
        with patch.object(repo.table, 'scan', side_effect=Exception("Unexpected error")):
            with pytest.raises(DynamoDBException) as exc_info:
                repo.find_all()
            assert "Unexpected error scanning drug data" in str(exc_info.value)
    
    @mock_aws
    def test_batch_save_generic_exception(self):
        """Test batch_save handles generic exceptions."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        drugs = [Drug("Aspirin", "COX-2", 85.5, datetime(2024, 1, 1), "key1")]
        
        from unittest.mock import patch, MagicMock
        mock_batch = MagicMock()
        mock_batch.__enter__.return_value.put_item.side_effect = Exception("Unexpected error")
        
        with patch.object(repo.table, 'batch_writer', return_value=mock_batch):
            with pytest.raises(DynamoDBException) as exc_info:
                repo.batch_save(drugs)
            assert "Unexpected error during batch save" in str(exc_info.value)
    
    @mock_aws
    def test_find_all_paginated_first_page(self):
        """Test paginated query returns first page with token."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        # Create 15 drugs
        drugs = [Drug(f"Drug{i}", f"Target{i}", 80.0 + i, datetime(2024, 1, i+1), f"key{i}") for i in range(15)]
        repo.batch_save(drugs)
        
        # Get first page (limit 10)
        result_drugs, next_token = repo.find_all_paginated(limit=10)
        
        assert len(result_drugs) == 10
        assert next_token is not None
    
    @mock_aws
    def test_find_all_paginated_with_token(self):
        """Test paginated query with token returns next page."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        drugs = [Drug(f"Drug{i}", f"Target{i}", 80.0 + i, datetime(2024, 1, i+1), f"key{i}") for i in range(15)]
        repo.batch_save(drugs)
        
        # Get first page
        _, next_token = repo.find_all_paginated(limit=10)
        
        # Get second page
        result_drugs, next_token2 = repo.find_all_paginated(limit=10, next_token=next_token)
        
        assert len(result_drugs) == 5
        assert next_token2 is None
    
    @mock_aws
    def test_find_all_paginated_invalid_token(self):
        """Test invalid pagination token raises ValidationException."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        with pytest.raises(ValidationException) as exc_info:
            repo.find_all_paginated(limit=10, next_token="invalid_token")
        
        assert "Invalid pagination token" in str(exc_info.value)
    
    @mock_aws
    def test_find_all_paginated_respects_max_limit(self):
        """Test pagination caps limit at 1000."""
        from src.core import config
        config.settings = config.Settings()
        
        self._create_table()
        repo = DynamoRepository()
        
        drugs = [Drug(f"Drug{i}", f"Target{i}", 80.0, datetime(2024, 1, 1), f"key{i}") for i in range(5)]
        repo.batch_save(drugs)
        
        # Request 5000 but should be capped at 1000
        result_drugs, _ = repo.find_all_paginated(limit=5000)
        
        # Should return all 5 drugs (less than limit)
        assert len(result_drugs) == 5
