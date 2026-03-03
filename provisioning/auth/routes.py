"""Authentication API routes."""

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from .service import AuthService
from .models import UserModel
from .dependencies import (
    get_current_active_user,
    require_auth,
    require_admin,
)
from .schemas import (
    LoginRequest,
    TokenResponse,
    UserCreate,
    UserUpdate,
    UserResponse,
    PasswordChangeRequest,
    APIKeyCreate,
    APIKeyResponse,
    APIKeyCreated,
    APIKeyUpdate,
)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# =============================================================================
# Authentication
# =============================================================================

@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Authenticate with email/password and receive JWT token.
    
    Account locks after 5 failed attempts for 15 minutes.
    """
    auth_service = AuthService(session)
    user = await auth_service.authenticate(request.email, request.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token, expires_in = auth_service.create_access_token(user)
    
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user.to_dict()),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    """
    Refresh JWT token.
    
    Requires valid (non-expired) token.
    """
    auth_service = AuthService(session)
    token, expires_in = auth_service.create_access_token(user)
    
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user.to_dict()),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    """Get current authenticated user info."""
    return UserResponse.model_validate(user.to_dict())


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserModel, Depends(get_current_active_user)],
):
    """Change password for current user."""
    auth_service = AuthService(session)
    success = await auth_service.change_password(
        user.id,
        request.current_password,
        request.new_password,
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    return {"message": "Password changed successfully"}


# =============================================================================
# User Management (Admin)
# =============================================================================

@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    request: UserCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[UserModel, Depends(require_admin)],
):
    """
    Create a new user (admin only).
    
    Set is_admin=True to create admin users.
    Set tenant_id to scope user to a specific tenant.
    """
    auth_service = AuthService(session)
    
    # Check if email already exists
    existing = await auth_service.get_user_by_email(request.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    
    user = await auth_service.create_user(request)
    return UserResponse.model_validate(user.to_dict())


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[UserModel, Depends(require_admin)],
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List all users (admin only)."""
    auth_service = AuthService(session)
    users = await auth_service.list_users(
        limit=limit,
        offset=offset,
        is_active=is_active,
    )
    return [UserResponse.model_validate(u.to_dict()) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[UserModel, Depends(require_admin)],
):
    """Get user by ID (admin only)."""
    auth_service = AuthService(session)
    user = await auth_service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user.to_dict())


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[UserModel, Depends(require_admin)],
):
    """Update user (admin only)."""
    auth_service = AuthService(session)
    user = await auth_service.update_user(user_id, request)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user.to_dict())


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[UserModel, Depends(require_admin)],
):
    """Delete user (admin only)."""
    auth_service = AuthService(session)
    
    # Prevent self-deletion
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )
    
    success = await auth_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return {"message": "User deleted"}


# =============================================================================
# API Key Management
# =============================================================================

@router.post("/api-keys", response_model=APIKeyCreated, status_code=201)
async def create_api_key(
    request: APIKeyCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserModel, Depends(require_auth)],
):
    """
    Create a new API key.
    
    The API key is only shown once in the response.
    Store it securely — it cannot be retrieved again.
    """
    auth_service = AuthService(session)
    
    # Non-admins can only create keys for their own tenant
    if not user.is_admin and request.tenant_id and request.tenant_id != user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create key for other tenants",
        )
    
    api_key, raw_key = await auth_service.create_api_key(user.id, request)
    
    response_data = api_key.to_dict()
    response_data["key"] = raw_key
    
    return APIKeyCreated.model_validate(response_data)


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserModel, Depends(require_auth)],
    include_inactive: bool = False,
):
    """List API keys for current user."""
    auth_service = AuthService(session)
    keys = await auth_service.list_api_keys(
        user.id,
        include_inactive=include_inactive,
    )
    return [APIKeyResponse.model_validate(k.to_dict()) for k in keys]


@router.get("/api-keys/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserModel, Depends(require_auth)],
):
    """Get API key by ID."""
    auth_service = AuthService(session)
    api_key = await auth_service.get_api_key_by_id(key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Check ownership (non-admins can only see their own keys)
    if not user.is_admin and api_key.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    return APIKeyResponse.model_validate(api_key.to_dict())


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserModel, Depends(require_auth)],
):
    """
    Revoke (deactivate) an API key.
    
    The key remains in the database but becomes unusable.
    """
    auth_service = AuthService(session)
    api_key = await auth_service.get_api_key_by_id(key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Check ownership
    if not user.is_admin and api_key.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    await auth_service.revoke_api_key(key_id)
    return {"message": "API key revoked"}


@router.delete("/api-keys/{key_id}/permanent")
async def delete_api_key(
    key_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[UserModel, Depends(require_auth)],
):
    """
    Permanently delete an API key.
    
    This action cannot be undone.
    """
    auth_service = AuthService(session)
    api_key = await auth_service.get_api_key_by_id(key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )
    
    # Check ownership
    if not user.is_admin and api_key.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )
    
    await auth_service.delete_api_key(key_id)
    return {"message": "API key deleted"}
