"""FastAPI authentication dependencies."""

from typing import Optional, Annotated

from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from .service import AuthService
from .models import UserModel
from .schemas import TokenPayload


# Security schemes
bearer_scheme = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_token_payload(
    credentials: Annotated[
        Optional[HTTPAuthorizationCredentials], 
        Depends(bearer_scheme)
    ],
) -> Optional[TokenPayload]:
    """Extract and validate JWT token from Authorization header."""
    if not credentials:
        return None
    
    payload = AuthService.decode_token(credentials.credentials)
    return payload


async def get_current_user(
    session: Annotated[AsyncSession, Depends(get_db)],
    token_payload: Annotated[Optional[TokenPayload], Depends(get_token_payload)],
) -> Optional[UserModel]:
    """
    Get current user from JWT token.
    
    Returns None if no valid token is provided.
    """
    if not token_payload:
        return None
    
    auth_service = AuthService(session)
    user = await auth_service.get_user_by_id(token_payload.sub)
    
    if not user or not user.is_active:
        return None
    
    return user


async def get_current_active_user(
    user: Annotated[Optional[UserModel], Depends(get_current_user)],
) -> UserModel:
    """
    Get current active user (required).
    
    Raises 401 if no valid user.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_api_key(
    session: Annotated[AsyncSession, Depends(get_db)],
    api_key: Annotated[Optional[str], Security(api_key_header)],
) -> Optional[UserModel]:
    """
    Validate API key from X-API-Key header.
    
    Returns the user associated with the API key.
    """
    if not api_key:
        return None
    
    auth_service = AuthService(session)
    result = await auth_service.validate_api_key(api_key)
    
    if not result:
        return None
    
    _, user = result
    return user


async def require_auth(
    session: Annotated[AsyncSession, Depends(get_db)],
    jwt_user: Annotated[Optional[UserModel], Depends(get_current_user)],
    api_key_user: Annotated[Optional[UserModel], Depends(get_api_key)],
) -> UserModel:
    """
    Require authentication via JWT OR API key.
    
    Use this for routes that accept both authentication methods.
    Raises 401 if neither is provided.
    """
    user = jwt_user or api_key_user
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def require_admin(
    user: Annotated[UserModel, Depends(require_auth)],
) -> UserModel:
    """
    Require admin role.
    
    Use this for admin-only routes.
    Raises 403 if user is not admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    
    return user


def require_tenant_access(tenant_id: str):
    """
    Factory for tenant-scoped access check.
    
    Returns a dependency that verifies the user can access the tenant.
    Admins can access any tenant.
    Non-admins can only access their own tenant.
    """
    async def check_tenant_access(
        user: Annotated[UserModel, Depends(require_auth)],
    ) -> UserModel:
        if user.is_admin:
            return user
        
        if user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )
        
        return user
    
    return check_tenant_access


class TenantScopedDependency:
    """
    Dependency class for tenant-scoped access.
    
    Usage:
        @app.get("/tenants/{tenant_id}/resources")
        async def get_resources(
            tenant_id: str,
            user: UserModel = Depends(TenantScopedDependency())
        ):
            ...
    """
    
    async def __call__(
        self,
        tenant_id: str,
        user: Annotated[UserModel, Depends(require_auth)],
    ) -> UserModel:
        if user.is_admin:
            return user
        
        if user.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )
        
        return user
