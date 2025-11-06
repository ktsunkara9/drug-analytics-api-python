"""
Drug Service for business logic.
Orchestrates drug data operations between API and repositories.
"""
import uuid
from typing import List, BinaryIO
from src.models.drug_model import Drug
from src.models.dto.drug_dto import DrugUploadResponse, DrugResponse, DrugListResponse
from src.repositories.s3_repository import S3Repository
from src.repositories.dynamo_repository import DynamoRepository
from src.services.file_service import FileService


class DrugService:
    """Service for drug-related business operations."""
    
    def __init__(
        self,
        s3_repository: S3Repository = None,
        dynamo_repository: DynamoRepository = None,
        file_service: FileService = None
    ):
        self.s3_repository = s3_repository or S3Repository()
        self.dynamo_repository = dynamo_repository or DynamoRepository()
        self.file_service = file_service or FileService()
    
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
        
        # Upload file to S3
        upload_result = self.s3_repository.upload_file(file, filename)
        
        # Generate upload ID
        upload_id = str(uuid.uuid4())
        
        return DrugUploadResponse(
            upload_id=upload_id,
            status="uploaded",
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
        
        # Parse CSV
        drugs = self.file_service.parse_csv_to_drugs(file_content)
        
        # Set s3_key for all drugs
        for drug in drugs:
            drug.s3_key = s3_key
        
        # Batch save to DynamoDB (efficient!)
        self.dynamo_repository.batch_save(drugs)
        
        return len(drugs)
