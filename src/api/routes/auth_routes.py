"""
Authentication API routes.
"""
from fastapi import APIRouter, HTTPException, status
from src.models.dto.auth_dto import LoginRequest, LoginResponse
from src.services.auth_service import authenticate_user, create_access_token

router = APIRouter(prefix="/v1/api/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT access token.
    
    - **username**: User's username
    - **password**: User's password
    
    Returns JWT token for accessing protected endpoints.
    """
    user = authenticate_user(request.username, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    access_token = create_access_token(user['username'])
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        username=user['username']
    )
