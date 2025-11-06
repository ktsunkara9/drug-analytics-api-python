"""
Drug API routes.
Handles HTTP endpoints for drug data operations.
"""
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from src.services.drug_service import DrugService
from src.core.dependencies import get_drug_service
from src.models.dto.drug_dto import DrugUploadResponse, DrugListResponse

router = APIRouter(prefix="/api/drugs", tags=["Drugs"])


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
