"""
Core configuration for the Drug Analytics API.
Manages environment variables and AWS service settings.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # AWS Configuration
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "drug-analytics-bucket")
    dynamodb_table_name: str = os.getenv("DYNAMODB_TABLE_NAME", "DrugData")
    
    # API Configuration
    api_title: str = "Drug Analytics API"
    api_version: str = "1.0.0"
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
