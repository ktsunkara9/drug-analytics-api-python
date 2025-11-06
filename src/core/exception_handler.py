"""
Global exception handler for the Drug Analytics API.
Provides centralized error handling for all API exceptions.
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .exceptions import (
    DrugNotFoundException,
    ValidationException,
    S3UploadException,
    DynamoDBException,
    CSVProcessingException
)


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI application."""
    
    @app.exception_handler(DrugNotFoundException)
    async def handle_not_found(request: Request, exc: DrugNotFoundException):
        return JSONResponse(
            status_code=404,
            content={"error": "Not Found", "message": exc.message}
        )
    
    @app.exception_handler(ValidationException)
    async def handle_validation_error(request: Request, exc: ValidationException):
        return JSONResponse(
            status_code=400,
            content={"error": "Validation Error", "message": exc.message}
        )
    
    @app.exception_handler(S3UploadException)
    async def handle_s3_error(request: Request, exc: S3UploadException):
        return JSONResponse(
            status_code=500,
            content={"error": "S3 Upload Failed", "message": exc.message}
        )
    
    @app.exception_handler(DynamoDBException)
    async def handle_dynamodb_error(request: Request, exc: DynamoDBException):
        return JSONResponse(
            status_code=500,
            content={"error": "Database Error", "message": exc.message}
        )
    
    @app.exception_handler(CSVProcessingException)
    async def handle_csv_error(request: Request, exc: CSVProcessingException):
        return JSONResponse(
            status_code=400,
            content={"error": "CSV Processing Failed", "message": exc.message}
        )
    
    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "message": "An unexpected error occurred"}
        )
