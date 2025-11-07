"""
Core configuration for the Drug Analytics API.
Manages environment variables and AWS service settings.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""
    
    # AWS Configuration
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    s3_bucket_name: str = os.getenv("S3_BUCKET_NAME", "drug-analytics-dev")
    dynamodb_table_name: str = os.getenv("DYNAMODB_TABLE_NAME", "DrugData-dev")
    
    # API Configuration
    api_title: str = os.getenv("API_TITLE", "Drug Analytics API")
    api_version: str = os.getenv("API_VERSION", "1.0.0")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "dev")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
