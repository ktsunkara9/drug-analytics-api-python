"""
Unit tests for S3Repository.
Uses moto to mock AWS S3 service.
"""
import io
import os
import pytest
from moto import mock_aws
import boto3
from src.repositories.s3_repository import S3Repository
from src.core.exceptions import S3Exception


class TestS3Repository:
    """Test suite for S3Repository."""
    
    @pytest.fixture(autouse=True)
    def setup_aws(self):
        """Setup mock AWS credentials."""
        os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
        os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
        os.environ['AWS_SECURITY_TOKEN'] = 'testing'
        os.environ['AWS_SESSION_TOKEN'] = 'testing'
        os.environ['S3_BUCKET_NAME'] = 'test-bucket'
        
        yield
        
        # Cleanup
        if 'S3_BUCKET_NAME' in os.environ:
            del os.environ['S3_BUCKET_NAME']
    
    @mock_aws
    def test_upload_file_success(self):
        """Test successful file upload to S3."""
        # Reload settings inside mock context
        from src.core import config
        config.settings = config.Settings()
        
        # Create test bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        # Create repository
        repo = S3Repository()
        
        file_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5"
        file = io.BytesIO(file_content)
        filename = "test.csv"
        
        result = repo.upload_file(file, filename)
        
        assert 's3_key' in result
        assert 's3_location' in result
        assert filename in result['s3_key']
    
    @mock_aws
    def test_upload_file_generates_unique_keys(self):
        """Test that multiple uploads generate unique S3 keys."""
        # Reload settings inside mock context
        from src.core import config
        config.settings = config.Settings()
        
        # Create test bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        # Create repository
        repo = S3Repository()
        
        file1 = io.BytesIO(b"content1")
        file2 = io.BytesIO(b"content2")
        
        result1 = repo.upload_file(file1, "test.csv")
        result2 = repo.upload_file(file2, "test.csv")
        
        assert result1['s3_key'] != result2['s3_key']
    
    @mock_aws
    def test_get_file_success(self):
        """Test successful file retrieval from S3."""
        # Reload settings inside mock context
        from src.core import config
        config.settings = config.Settings()
        
        # Create test bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        # Create repository
        repo = S3Repository()
        
        file_content = b"drug_name,target,efficacy\nAspirin,COX-2,85.5"
        file = io.BytesIO(file_content)
        
        upload_result = repo.upload_file(file, "test.csv")
        retrieved_content = repo.get_file(upload_result['s3_key'])
        
        assert retrieved_content == file_content
    
    @mock_aws
    def test_get_file_not_found(self):
        """Test get_file raises exception for non-existent file."""
        # Reload settings inside mock context
        from src.core import config
        config.settings = config.Settings()
        
        # Create test bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        s3.create_bucket(Bucket='test-bucket')
        
        # Create repository
        repo = S3Repository()
        
        with pytest.raises(S3Exception) as exc_info:
            repo.get_file("non-existent-key")
        assert "Failed to retrieve file from S3" in str(exc_info.value)
