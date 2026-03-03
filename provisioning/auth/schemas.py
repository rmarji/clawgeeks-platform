"""Authentication Pydantic schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user fields."""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)


class UserCreate(UserBase):
    """User creation request."""
    password: str = Field(..., min_length=8, max_length=128)
    is_admin: bool = False
    tenant_id: Optional[str] = None


class UserUpdate(BaseModel):
    """User update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserResponse(UserBase):
    """User response (public fields)."""
    id: str
    is_admin: bool
    is_active: bool
    tenant_id: Optional[str]
    last_login: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# Alias for backward compatibility
UserRead = UserResponse


class UserWithToken(UserResponse):
    """User response with JWT token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# =============================================================================
# Auth Schemas
# =============================================================================

class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """JWT token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasswordChangeRequest(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


# =============================================================================
# API Key Schemas
# =============================================================================

class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    tenant_id: Optional[str] = None  # Scope to tenant
    expires_in_days: Optional[int] = None  # None = never expires


class APIKeyResponse(BaseModel):
    """API key response (without the actual key)."""
    id: str
    key_prefix: str
    name: str
    description: Optional[str]
    user_id: str
    tenant_id: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    use_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class APIKeyCreated(APIKeyResponse):
    """API key creation response (includes the full key, shown once)."""
    key: str  # Full API key, only shown on creation


class APIKeyUpdate(BaseModel):
    """API key update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


# =============================================================================
# Token Payload
# =============================================================================

class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    email: str
    is_admin: bool
    tenant_id: Optional[str]
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    jti: str  # JWT ID (for revocation)
