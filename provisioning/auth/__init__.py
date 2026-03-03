"""Authentication module."""

from .models import UserModel, APIKeyModel
from .service import AuthService, get_auth_service
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_api_key,
    require_auth,
    require_admin,
)

__all__ = [
    "UserModel",
    "APIKeyModel", 
    "AuthService",
    "get_auth_service",
    "get_current_user",
    "get_current_active_user",
    "get_api_key",
    "require_auth",
    "require_admin",
]
