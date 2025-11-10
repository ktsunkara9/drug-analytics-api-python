"""
Health check routes for monitoring.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/v1/api", tags=["Health"])


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "Drug Analytics API",
        "version": "1.0.0"
    }
