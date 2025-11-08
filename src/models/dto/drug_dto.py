"""
Data Transfer Objects for Drug API.
Defines request and response schemas for API endpoints.
"""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class DrugUploadRequest(BaseModel):
    """Request schema for uploading drug data via CSV."""
    drug_name: str = Field(..., min_length=1, max_length=100, description="Name of the drug")
    target: str = Field(..., min_length=1, max_length=100, description="Target protein or pathway")
    efficacy: float = Field(..., ge=0, le=100, description="Efficacy percentage (0-100)")
    
    @field_validator('drug_name', 'target')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Field cannot be empty")
        return v.strip()


class DrugUploadResponse(BaseModel):
    """Response schema for successful drug data upload."""
    upload_id: str = Field(..., description="Unique identifier for the upload")
    status: str = Field(..., description="Upload status")
    message: str = Field(..., description="Status message")
    s3_location: str = Field(..., description="S3 location of uploaded file")


class DrugResponse(BaseModel):
    """Response schema for drug data retrieval."""
    drug_name: str
    target: str
    efficacy: float
    upload_timestamp: datetime
    
    class Config:
        from_attributes = True


class DrugListResponse(BaseModel):
    """Response schema for listing multiple drugs."""
    drugs: list[DrugResponse]
    count: int


class UploadStatusResponse(BaseModel):
    """Response schema for upload status query."""
    upload_id: str
    status: str
    filename: str
    s3_key: str
    created_at: datetime
    total_rows: int = 0
    processed_rows: int = 0
    error_message: str = None
