"""
Main FastAPI application entry point.
Configures and initializes the Drug Analytics API.
"""
from fastapi import FastAPI
from mangum import Mangum
from src.core.config import settings
from src.core.exception_handler import register_exception_handlers
from src.api.routes import health_routes, drug_routes

# Create FastAPI application
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="A cloud-based analytics service for drug discovery data"
)

# Register exception handlers
register_exception_handlers(app)

# Register routes
app.include_router(health_routes.router)
app.include_router(drug_routes.router)

# Lambda handler for AWS
handler = Mangum(app)


# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
