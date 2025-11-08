"""
Drug Service for business logic.
Orchestrates drug data operations between API and repositories.
"""
import io
import uuid
from datetime import datetime
from typing import List, BinaryIO
from src.models.drug_model import Drug
from src.models.upload_status import UploadStatus
from src.models.dto.drug_dto import DrugUploadResponse, DrugResponse, DrugListResponse, UploadStatusResponse
from src.repositories.s3_repository import S3Repository
from src.repositories.dynamo_repository import DynamoRepository
from src.repositories.upload_status_repository import UploadStatusRepository
from src.services.file_service import FileService


class DrugService:
    """Service for drug-related business operations."""
    
    def __init__(
        self,
        s3_repository: S3Repository = None,
        dynamo_repository: DynamoRepository = None,
        file_service: FileService = None,
        upload_status_repository: UploadStatusRepository = None
    ):
        self.s3_repository = s3_repository or S3Repository()
        self.dynamo_repository = dynamo_repository or DynamoRepository()
        self.file_service = file_service or FileService()
        self.upload_status_repository = upload_status_repository or UploadStatusRepository()
    
    def upload_drug_data(self, file: BinaryIO, filename: str) -> DrugUploadResponse:
        """
        Handle drug data upload workflow.
        
        Args:
            file: CSV file containing drug data
            filename: Original filename
            
        Returns:
            DrugUploadResponse with upload details
            
        Raises:
            ValidationException: If CSV validation fails
            S3Exception: If S3 upload fails
        """
        # Validate CSV structure
        self.file_service.validate_csv_structure(file)
        
        # Generate upload ID
        upload_id = str(uuid.uuid4())
        
        # Upload file to S3
        upload_result = self.s3_repository.upload_file(file, filename)
        
        # Create upload status record
        upload_status = UploadStatus(
            upload_id=upload_id,
            status="pending",
            filename=filename,
            s3_key=upload_result['s3_key'],
            created_at=datetime.utcnow()
        )
        self.upload_status_repository.create(upload_status)
        
        return DrugUploadResponse(
            upload_id=upload_id,
            status="pending",
            message="File uploaded successfully. Processing in progress.",
            s3_location=upload_result['s3_location']
        )
    
    def get_drug_by_name(self, drug_name: str) -> DrugListResponse:
        """
        Retrieve all versions of a specific drug.
        
        Args:
            drug_name: Name of the drug
            
        Returns:
            DrugListResponse with drug data
            
        Raises:
            DrugNotFoundException: If drug not found
            DynamoDBException: If query fails
        """
        drugs = self.dynamo_repository.find_by_drug_name(drug_name)
        
        drug_responses = [
            DrugResponse(
                drug_name=drug.drug_name,
                target=drug.target,
                efficacy=drug.efficacy,
                upload_timestamp=drug.upload_timestamp
            )
            for drug in drugs
        ]
        
        return DrugListResponse(drugs=drug_responses, count=len(drug_responses))
    
    def get_all_drugs(self) -> DrugListResponse:
        """
        Retrieve all drug records.
        
        Returns:
            DrugListResponse with all drugs
            
        Raises:
            DynamoDBException: If scan fails
        """
        drugs = self.dynamo_repository.find_all()
        
        drug_responses = [
            DrugResponse(
                drug_name=drug.drug_name,
                target=drug.target,
                efficacy=drug.efficacy,
                upload_timestamp=drug.upload_timestamp
            )
            for drug in drugs
        ]
        
        return DrugListResponse(drugs=drug_responses, count=len(drug_responses))
    
    def process_csv_and_save(self, s3_key: str) -> int:
        """
        Process CSV from S3 and save to DynamoDB.
        Used by Lambda processor.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            Number of records processed
            
        Raises:
            S3Exception: If file retrieval fails
            CSVProcessingException: If parsing fails
            DynamoDBException: If save fails
        """
        # Get file from S3
        file_content = self.s3_repository.get_file(s3_key)
        
        # Wrap bytes in BytesIO to provide file-like interface
        file_obj = io.BytesIO(file_content)
        
        # Parse CSV
        drugs = self.file_service.parse_csv_to_drugs(file_obj)
        
        # Set s3_key for all drugs
        for drug in drugs:
            drug.s3_key = s3_key
        
        # Batch save to DynamoDB (efficient!)
        self.dynamo_repository.batch_save(drugs)
        
        return len(drugs)
    
    def get_upload_status(self, upload_id: str) -> UploadStatusResponse:
        """
        Get upload processing status.
        
        Args:
            upload_id: Upload identifier
            
        Returns:
            UploadStatusResponse with current status
            
        Raises:
            HTTPException: If upload_id not found
        """
        upload_status = self.upload_status_repository.get_by_id(upload_id)
        
        if not upload_status:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Upload ID '{upload_id}' not found"
            )
        
        return UploadStatusResponse(
            upload_id=upload_status.upload_id,
            status=upload_status.status,
            filename=upload_status.filename,
            s3_key=upload_status.s3_key,
            created_at=upload_status.created_at,
            total_rows=upload_status.total_rows,
            processed_rows=upload_status.processed_rows,
            error_message=upload_status.error_message
        )
