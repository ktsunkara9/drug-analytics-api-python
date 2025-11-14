"""
Abstract base class for database repositories.
Defines the contract for drug data storage operations.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.models.drug_model import Drug


class DBRepository(ABC):
    """Abstract repository interface for drug data operations."""
    
    @abstractmethod
    def save(self, drug: Drug) -> None:
        """Save a single drug record."""
        pass
    
    @abstractmethod
    def find_by_drug_name(self, drug_name: str) -> List[Drug]:
        """Find all records for a specific drug."""
        pass
    
    @abstractmethod
    def find_all_paginated(self, limit: int = 10, next_token: Optional[str] = None) -> Tuple[List[Drug], Optional[str]]:
        """Retrieve all drug records with pagination."""
        pass
    
    @abstractmethod
    def batch_save(self, drugs: List[Drug]) -> None:
        """Save multiple drugs in batches."""
        pass
