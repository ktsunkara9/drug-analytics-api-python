"""
Dependency injection container for FastAPI.
Provides singleton-like behavior for services and repositories.
"""
from functools import lru_cache
from src.repositories.s3_repository import S3Repository
from src.repositories.dynamo_repository import DynamoRepository
from src.services.file_service import FileService
from src.services.drug_service import DrugService


@lru_cache()
def get_s3_repository() -> S3Repository:
    """Get S3Repository singleton instance."""
    return S3Repository()


@lru_cache()
def get_dynamo_repository() -> DynamoRepository:
    """Get DynamoRepository singleton instance."""
    return DynamoRepository()


@lru_cache()
def get_file_service() -> FileService:
    """Get FileService singleton instance."""
    return FileService()


@lru_cache()
def get_drug_service() -> DrugService:
    """Get DrugService singleton instance with injected dependencies."""
    return DrugService(
        s3_repository=get_s3_repository(),
        dynamo_repository=get_dynamo_repository(),
        file_service=get_file_service()
    )
