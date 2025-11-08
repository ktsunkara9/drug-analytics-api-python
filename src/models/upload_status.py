"""
Upload Status domain model.
Represents the status of a CSV file upload and processing.
"""
from datetime import datetime
from typing import Optional


class UploadStatus:
    """Domain model for upload status tracking."""
    
    def __init__(
        self,
        upload_id: str,
        status: str,
        filename: str,
        s3_key: str,
        created_at: datetime,
        total_rows: int = 0,
        processed_rows: int = 0,
        error_message: Optional[str] = None
    ):
        self.upload_id = upload_id
        self.status = status
        self.filename = filename
        self.s3_key = s3_key
        self.created_at = created_at
        self.total_rows = total_rows
        self.processed_rows = processed_rows
        self.error_message = error_message
    
    def __repr__(self):
        return f"UploadStatus(upload_id={self.upload_id}, status={self.status}, filename={self.filename})"
