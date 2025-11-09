"""
Upload Status Repository for DynamoDB operations.
Handles CRUD operations for upload status tracking.
"""
from datetime import datetime
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from src.core import config
from src.core.exceptions import DynamoDBException
from src.models.upload_status import UploadStatus


class UploadStatusRepository:
    """Repository for upload status DynamoDB operations."""
    
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb', region_name=config.settings.aws_region)
        self.table = self.dynamodb.Table(config.settings.upload_status_table_name)
    
    def create(self, upload_status: UploadStatus) -> None:
        """
        Create new upload status record.
        
        Args:
            upload_status: UploadStatus domain model
            
        Raises:
            DynamoDBException: If create operation fails
        """
        try:
            item = {
                'upload_id': upload_status.upload_id,
                'status': upload_status.status,
                'filename': upload_status.filename,
                's3_key': upload_status.s3_key,
                'created_at': upload_status.created_at.isoformat(),
                'total_rows': upload_status.total_rows,
                'processed_rows': upload_status.processed_rows
            }
            
            if upload_status.error_message:
                item['error_message'] = upload_status.error_message
            
            self.table.put_item(Item=item)
            
        except ClientError as e:
            raise DynamoDBException(f"Failed to create upload status: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error creating upload status: {str(e)}") from e
    
    def get_by_id(self, upload_id: str) -> Optional[UploadStatus]:
        """
        Retrieve upload status by ID.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            UploadStatus object or None if not found
            
        Raises:
            DynamoDBException: If query fails
        """
        try:
            response = self.table.get_item(Key={'upload_id': upload_id})
            
            if 'Item' not in response:
                return None
            
            item = response['Item']
            return self._item_to_upload_status(item)
            
        except ClientError as e:
            raise DynamoDBException(f"Failed to get upload status: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error getting upload status: {str(e)}") from e
    
    def update(self, upload_id: str, updates: dict) -> None:
        """
        Update upload status fields.
        
        Args:
            upload_id: Upload identifier
            updates: Dictionary of fields to update
            
        Raises:
            DynamoDBException: If update operation fails
        """
        try:
            update_expression = "SET "
            expression_values = {}
            expression_names = {}
            
            for key, value in updates.items():
                update_expression += f"#{key} = :{key}, "
                expression_values[f":{key}"] = value
                expression_names[f"#{key}"] = key
            
            update_expression = update_expression.rstrip(", ")
            
            self.table.update_item(
                Key={'upload_id': upload_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_names,
                ExpressionAttributeValues=expression_values
            )
            
        except ClientError as e:
            raise DynamoDBException(f"Failed to update upload status: {str(e)}") from e
        except Exception as e:
            raise DynamoDBException(f"Unexpected error updating upload status: {str(e)}") from e
    
    def _item_to_upload_status(self, item: dict) -> UploadStatus:
        """Convert DynamoDB item to UploadStatus domain model."""
        return UploadStatus(
            upload_id=item['upload_id'],
            status=item['status'],
            filename=item['filename'],
            s3_key=item['s3_key'],
            created_at=datetime.fromisoformat(item['created_at']),
            total_rows=int(item.get('total_rows', 0)),
            processed_rows=int(item.get('processed_rows', 0)),
            error_message=item.get('error_message')
        )
