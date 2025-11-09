"""
Drug API routes.
Handles HTTP endpoints for drug data operations.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from src.services.drug_service import DrugService
from src.core.dependencies import get_drug_service
from src.models.dto.drug_dto import DrugUploadResponse, DrugListResponse, UploadStatusResponse
from src.core import config

router = APIRouter(prefix="/v1/api/drugs", tags=["Drugs"])


@router.post("/upload", response_model=DrugUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_drug_csv(
    file: UploadFile = File(..., description="CSV file containing drug data"),
    drug_service: DrugService = Depends(get_drug_service)
):
    """
    Upload CSV file with drug discovery data.
    
    The file will be uploaded to S3 and processed asynchronously.
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files are allowed"
        )
    
    # Validate file size
    content = await file.read()
    file_size = len(content)
    max_size_bytes = config.settings.max_file_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size ({file_size / (1024 * 1024):.2f}MB) exceeds maximum allowed size of {config.settings.max_file_size_mb}MB"
        )
    
    # Reset file pointer for processing
    await file.seek(0)
    
    # Upload and process
    result = drug_service.upload_drug_data(file.file, file.filename)
    return result


@router.get("", response_model=DrugListResponse)
async def get_all_drugs(
    drug_service: DrugService = Depends(get_drug_service)
):
    """
    Retrieve all drug records from the database.
    """
    return drug_service.get_all_drugs()


@router.get("/{drug_name}", response_model=DrugListResponse)
async def get_drug_by_name(
    drug_name: str,
    drug_service: DrugService = Depends(get_drug_service)
):
    """
    Retrieve all versions of a specific drug by name.
    """
    return drug_service.get_drug_by_name(drug_name)


@router.get("/status/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    drug_service: DrugService = Depends(get_drug_service)
):
    """
    Get the processing status of an uploaded CSV file.
    """
    return drug_service.get_upload_status(upload_id)
