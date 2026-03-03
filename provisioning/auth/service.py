"""Authentication service."""

import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Tuple
import uuid

import bcrypt
import jwt
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import UserModel, APIKeyModel, generate_api_key
from .schemas import (
    UserCreate, 
    UserUpdate, 
    APIKeyCreate, 
    TokenPayload,
    UserResponse,
)


# Configuration from environment
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-in-production-" + secrets.token_hex(16))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", "60"))
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # =========================================================================
    # Password Hashing
    # =========================================================================
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using bcrypt."""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    
    @staticmethod
    def hash_api_key(key: str) -> str:
        """Hash API key using SHA-256 (faster than bcrypt for lookup)."""
        return hashlib.sha256(key.encode()).hexdigest()
    
    # =========================================================================
    # JWT Tokens
    # =========================================================================
    
    def create_access_token(
        self,
        user: UserModel,
        expires_delta: Optional[timedelta] = None,
    ) -> Tuple[str, int]:
        """
        Create JWT access token.
        
        Returns (token, expires_in_seconds).
        """
        now = datetime.utcnow()
        expires = expires_delta or timedelta(minutes=JWT_EXPIRY_MINUTES)
        exp = now + expires
        
        payload = {
            "sub": user.id,
            "email": user.email,
            "is_admin": user.is_admin,
            "tenant_id": user.tenant_id,
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
        }
        
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token, int(expires.total_seconds())
    
    @staticmethod
    def decode_token(token: str) -> Optional[TokenPayload]:
        """Decode and validate JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    # =========================================================================
    # User Management
    # =========================================================================
    
    async def create_user(self, data: UserCreate) -> UserModel:
        """Create a new user."""
        user = UserModel(
            email=data.email,
            name=data.name,
            password_hash=self.hash_password(data.password),
            is_admin=data.is_admin,
            tenant_id=data.tenant_id,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def get_user_by_id(self, user_id: str) -> Optional[UserModel]:
        """Get user by ID."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """Get user by email."""
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_user(
        self, 
        user_id: str, 
        data: UserUpdate
    ) -> Optional[UserModel]:
        """Update user fields."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        
        await self.session.commit()
        await self.session.refresh(user)
        return user
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Change user password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        if not self.verify_password(current_password, user.password_hash):
            return False
        
        user.password_hash = self.hash_password(new_password)
        await self.session.commit()
        return True
    
    async def delete_user(self, user_id: str) -> bool:
        """Delete user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False
        
        await self.session.delete(user)
        await self.session.commit()
        return True
    
    async def list_users(
        self,
        limit: int = 100,
        offset: int = 0,
        is_active: Optional[bool] = None,
    ) -> list[UserModel]:
        """List users with optional filters."""
        query = select(UserModel)
        if is_active is not None:
            query = query.where(UserModel.is_active == is_active)
        query = query.order_by(UserModel.created_at.desc())
        query = query.limit(limit).offset(offset)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    # =========================================================================
    # Authentication
    # =========================================================================
    
    async def authenticate(
        self, 
        email: str, 
        password: str
    ) -> Optional[UserModel]:
        """
        Authenticate user by email/password.
        
        Handles account lockout after failed attempts.
        """
        user = await self.get_user_by_email(email)
        if not user:
            return None
        
        # Check if account is locked
        if user.locked_until and user.locked_until > datetime.utcnow():
            return None
        
        # Check if account is active
        if not user.is_active:
            return None
        
        # Verify password
        if not self.verify_password(password, user.password_hash):
            # Increment failed attempts
            user.failed_attempts += 1
            if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
                user.locked_until = datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
            await self.session.commit()
            return None
        
        # Success: reset failed attempts, update last_login
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login = datetime.utcnow()
        await self.session.commit()
        
        return user
    
    # =========================================================================
    # API Key Management
    # =========================================================================
    
    async def create_api_key(
        self,
        user_id: str,
        data: APIKeyCreate,
    ) -> Tuple[APIKeyModel, str]:
        """
        Create a new API key.
        
        Returns (model, raw_key). The raw key is only available at creation.
        """
        raw_key = generate_api_key()
        key_hash = self.hash_api_key(raw_key)
        key_prefix = raw_key[:10]  # "cg_xxxxxx"
        
        expires_at = None
        if data.expires_in_days:
            expires_at = datetime.utcnow() + timedelta(days=data.expires_in_days)
        
        api_key = APIKeyModel(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=data.name,
            description=data.description,
            user_id=user_id,
            tenant_id=data.tenant_id,
            expires_at=expires_at,
        )
        
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)
        
        return api_key, raw_key
    
    async def get_api_key_by_id(self, key_id: str) -> Optional[APIKeyModel]:
        """Get API key by ID."""
        result = await self.session.execute(
            select(APIKeyModel).where(APIKeyModel.id == key_id)
        )
        return result.scalar_one_or_none()
    
    async def validate_api_key(self, raw_key: str) -> Optional[Tuple[APIKeyModel, UserModel]]:
        """
        Validate API key and return (api_key, user) if valid.
        
        Updates usage tracking on successful validation.
        """
        key_hash = self.hash_api_key(raw_key)
        
        result = await self.session.execute(
            select(APIKeyModel)
            .where(APIKeyModel.key_hash == key_hash)
            .where(APIKeyModel.is_active == True)
        )
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            return None
        
        # Check expiration
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None
        
        # Get associated user
        user = await self.get_user_by_id(api_key.user_id)
        if not user or not user.is_active:
            return None
        
        # Update usage tracking
        api_key.last_used_at = datetime.utcnow()
        api_key.use_count += 1
        await self.session.commit()
        
        return api_key, user
    
    async def revoke_api_key(self, key_id: str) -> bool:
        """Revoke (deactivate) an API key."""
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return False
        
        api_key.is_active = False
        await self.session.commit()
        return True
    
    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key."""
        api_key = await self.get_api_key_by_id(key_id)
        if not api_key:
            return False
        
        await self.session.delete(api_key)
        await self.session.commit()
        return True
    
    async def list_api_keys(
        self,
        user_id: str,
        include_inactive: bool = False,
    ) -> list[APIKeyModel]:
        """List API keys for a user."""
        query = select(APIKeyModel).where(APIKeyModel.user_id == user_id)
        if not include_inactive:
            query = query.where(APIKeyModel.is_active == True)
        query = query.order_by(APIKeyModel.created_at.desc())
        
        result = await self.session.execute(query)
        return list(result.scalars().all())


# Dependency helper
async def get_auth_service(session: AsyncSession) -> AuthService:
    """Get auth service instance."""
    return AuthService(session)
