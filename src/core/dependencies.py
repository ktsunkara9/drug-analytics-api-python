"""
Dependency injection container for FastAPI.
Provides singleton-like behavior for services and repositories.
"""
from functools import lru_cache
from src.repositories.s3_repository import S3Repository
from src.repositories.db_repository import DBRepository
from src.repositories.dynamo_repository import DynamoRepository
from src.repositories.upload_status_repository import UploadStatusRepository
from src.services.file_service import FileService
from src.services.drug_service import DrugService


@lru_cache()
def get_s3_repository() -> S3Repository:
    """Get S3Repository singleton instance."""
    return S3Repository()


@lru_cache()
def get_dynamo_repository() -> DBRepository:
    """Get DBRepository singleton instance."""
    return DynamoRepository()


@lru_cache()
def get_upload_status_repository() -> UploadStatusRepository:
    """Get UploadStatusRepository singleton instance."""
    return UploadStatusRepository()


@lru_cache()
def get_file_service() -> FileService:
    """Get FileService singleton instance."""
    return FileService()


@lru_cache()
def get_drug_service() -> DrugService:
    """Get DrugService singleton instance with injected dependencies."""
    return DrugService(
        s3_repository=get_s3_repository(),
        db_repository=get_dynamo_repository(),
        upload_status_repository=get_upload_status_repository(),
        file_service=get_file_service()
    )
