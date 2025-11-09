"""
Data Transfer Objects for authentication endpoints.
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request model for user login."""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Response model for successful login."""
    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    username: str = Field(..., description="Authenticated username")
