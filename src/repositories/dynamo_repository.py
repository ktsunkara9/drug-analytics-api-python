"""
DynamoDB Repository for drug data storage.
Handles CRUD operations for drug data in DynamoDB.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple
import json
import base64
import boto3
from botocore.exceptions import ClientError
from src.core import config
from src.core.exceptions import DynamoDBException, DrugNotFoundException, ValidationException
from src.models.drug_model import Drug
from src.repositories.db_repository import DBRepository


class DynamoRepository(DBRepository):
    """Repository for DynamoDB operations."""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=config.settings.aws_region)
        self.table = self.dynamodb.Table(config.settings.dynamodb_table_name)
    
    def save(self, drug: Drug) -> None:
        """
        Save drug data to DynamoDB.
        
        Args:
            drug: Drug domain model
            
        Raises:
            DynamoDBException: If save operation fails
        """
        try:
            item = {
                'PK': self._create_pk(drug.drug_name),
                'SK': self._create_sk(drug.upload_timestamp),
                'drug_category': 'ALL',
                'drug_name': drug.drug_name,
                'target': drug.target,
                'efficacy': Decimal(str(drug.efficacy)),
                'upload_timestamp': drug.upload_timestamp.isoformat(),
                's3_key': drug.s3_key
            }
            
            self.table.put_item(Item=item)
            
        except ClientError as e:
            raise DynamoDBException(f"Failed to save drug data: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error saving drug data: {str(e)}") from e
    
    def find_by_drug_name(self, drug_name: str) -> List[Drug]:
        """
        Find all records for a specific drug.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            List of Drug objects
            
        Raises:
            DynamoDBException: If query fails
        """
        try:
            response = self.table.query(
                KeyConditionExpression='PK = :pk',
                ExpressionAttributeValues={
                    ':pk': self._create_pk(drug_name)
                }
            )
            
            items = response.get('Items', [])
            if not items:
                raise DrugNotFoundException(f"Drug '{drug_name}' not found")
            
            return [self._item_to_drug(item) for item in items]
            
        except DrugNotFoundException:
            raise
        except ClientError as e:
            raise DynamoDBException(f"Failed to query drug data: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error querying drug data: {str(e)}") from e
    
    def find_all(self) -> List[Drug]:
        """
        Retrieve all drug records.
        
        Returns:
            List of all Drug objects
            
        Raises:
            DynamoDBException: If scan fails
        """
        try:
            response = self.table.scan()
            items = response.get('Items', [])
            
            return [self._item_to_drug(item) for item in items]
            
        except ClientError as e:
            raise DynamoDBException(f"Failed to scan drug data: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error scanning drug data: {str(e)}") from e
    
    def find_all_paginated(self, limit: int = 10, next_token: Optional[str] = None) -> Tuple[List[Drug], Optional[str]]:
        """
        Retrieve all drug records with pagination using GSI.
        
        Args:
            limit: Maximum number of items to return (default 10, max 1000)
            next_token: Base64-encoded pagination token from previous request
            
        Returns:
            Tuple of (list of Drug objects, next_token or None)
            
        Raises:
            DynamoDBException: If query fails
            ValidationException: If next_token is invalid
        """
        try:
            query_kwargs = {
                'IndexName': 'DrugCategoryIndex',
                'KeyConditionExpression': 'drug_category = :cat',
                'ExpressionAttributeValues': {':cat': 'ALL'},
                'Limit': min(limit, 10),
                'ScanIndexForward': False
            }
            
            if next_token:
                try:
                    last_key = json.loads(base64.b64decode(next_token))
                    query_kwargs['ExclusiveStartKey'] = last_key
                except Exception:
                    raise ValidationException("Invalid pagination token")
            
            response = self.table.query(**query_kwargs)
            items = response.get('Items', [])
            drugs = [self._item_to_drug(item) for item in items]
            
            next_token = None
            if 'LastEvaluatedKey' in response:
                next_token = base64.b64encode(
                    json.dumps(response['LastEvaluatedKey']).encode()
                ).decode()
            
            return drugs, next_token
            
        except ValidationException:
            raise
        except ClientError as e:
            raise DynamoDBException(f"Failed to query drug data: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error querying drug data: {str(e)}") from e
    
    def batch_save(self, drugs: List[Drug]) -> None:
        """
        Save multiple drugs in batches.
        DynamoDB batch_writer automatically handles batching (25 items per batch).
        
        Args:
            drugs: List of Drug objects to save
            
        Raises:
            DynamoDBException: If batch save fails
        """
        try:
            with self.table.batch_writer() as batch:
                for drug in drugs:
                    item = {
                        'PK': self._create_pk(drug.drug_name),
                        'SK': self._create_sk(drug.upload_timestamp),
                        'drug_category': 'ALL',
                        'drug_name': drug.drug_name,
                        'target': drug.target,
                        'efficacy': Decimal(str(drug.efficacy)),
                        'upload_timestamp': drug.upload_timestamp.isoformat(),
                        's3_key': drug.s3_key
                    }
                    batch.put_item(Item=item)
        except ClientError as e:
            raise DynamoDBException(f"Failed to batch save drug data: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error during batch save: {str(e)}") from e
    
    def _create_pk(self, drug_name: str) -> str:
        """Create partition key for drug."""
        return f"DRUG#{drug_name}"
    
    def _create_sk(self, timestamp: datetime) -> str:
        """Create sort key with timestamp."""
        return f"METADATA#{timestamp.isoformat()}"
    
    def _item_to_drug(self, item: dict) -> Drug:
        """Convert DynamoDB item to Drug domain model."""
        return Drug(
            drug_name=item['drug_name'],
            target=item['target'],
            efficacy=float(item['efficacy']),
            upload_timestamp=datetime.fromisoformat(item['upload_timestamp']),
            s3_key=item.get('s3_key')
        )
