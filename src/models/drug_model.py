"""
Domain model for Drug entity.
Database-agnostic representation of drug data.
"""
from datetime import datetime
from typing import Optional


class Drug:
    """Domain model representing drug discovery data."""
    
    def __init__(
        self,
        drug_name: str,
        target: str,
        efficacy: float,
        upload_timestamp: Optional[datetime] = None,
        s3_key: Optional[str] = None
    ):
        self.drug_name = drug_name
        self.target = target
        self.efficacy = efficacy
        self.upload_timestamp = upload_timestamp or datetime.utcnow()
        self.s3_key = s3_key
    
    def __repr__(self):
        return f"Drug(drug_name={self.drug_name}, target={self.target}, efficacy={self.efficacy})"
