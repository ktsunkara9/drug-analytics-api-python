"""
Custom exceptions for the Drug Analytics API.
Provides specific error types for different failure scenarios.
"""


class DrugAnalyticsException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ValidationException(DrugAnalyticsException):
    """Raised when data validation fails."""
    pass


class DrugNotFoundException(DrugAnalyticsException):
    """Raised when a drug is not found in the database."""
    pass


class S3Exception(DrugAnalyticsException):
    """Raised when S3 operation fails."""
    pass


class DynamoDBException(DrugAnalyticsException):
    """Raised when DynamoDB operation fails."""
    pass


class CSVProcessingException(DrugAnalyticsException):
    """Raised when CSV file processing fails."""
    pass
