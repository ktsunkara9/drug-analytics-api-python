"""
S3 Repository for file storage operations.
Handles CSV file uploads to Amazon S3.
"""
import uuid
from datetime import datetime
from typing import BinaryIO
import boto3
from botocore.exceptions import ClientError
from src.core import config
from src.core.exceptions import S3Exception


class S3Repository:
    """Repository for S3 file operations."""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=config.settings.aws_region)
        self.bucket_name = config.settings.s3_bucket_name
    
    def upload_file(self, file: BinaryIO, filename: str) -> dict:
        """
        Upload a file to S3.
        
        Args:
            file: File object to upload
            filename: Original filename
            
        Returns:
            dict: Upload metadata including s3_key and location
            
        Raises:
            S3Exception: If upload fails
        """
        try:
            # Generate unique S3 key
            s3_key = self._generate_s3_key(filename)
            
            # Upload to S3
            self.s3_client.upload_fileobj(
                file,
                self.bucket_name,
                s3_key,
                ExtraArgs={'ContentType': 'text/csv'}
            )
            
            # Generate S3 location URL
            s3_location = f"s3://{self.bucket_name}/{s3_key}"
            
            return {
                's3_key': s3_key,
                's3_location': s3_location,
                'bucket': self.bucket_name,
                'upload_timestamp': datetime.utcnow().isoformat()
            }
            
        except ClientError as e:
            raise S3Exception(f"Failed to upload file to S3: {str(e)}") from e
        except Exception as e:
            raise S3Exception(f"Unexpected error during S3 upload: {str(e)}") from e
    
    def _generate_s3_key(self, filename: str) -> str:
        """
        Generate unique S3 key for file.
        
        Format: uploads/YYYY/MM/DD/{uuid}_{filename}
        """
        now = datetime.utcnow()
        unique_id = uuid.uuid4().hex[:8]
        return f"uploads/{now.year}/{now.month:02d}/{now.day:02d}/{unique_id}_{filename}"
    
    def get_file(self, s3_key: str) -> bytes:
        """
        Retrieve file from S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            bytes: File content
            
        Raises:
            S3Exception: If retrieval fails
        """
        try:
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            return response['Body'].read()
        except ClientError as e:
            raise S3Exception(f"Failed to retrieve file from S3: {str(e)}") from e
