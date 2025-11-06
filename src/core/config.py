"""
Core configuration for the Drug Analytics API.
Manages environment variables and AWS service settings.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""
    
    # AWS Configuration
    aws_region: str
    s3_bucket_name: str
    dynamodb_table_name: str
    
    # API Configuration
    api_title: str
    api_version: str
    
    # Environment
    environment: str
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
