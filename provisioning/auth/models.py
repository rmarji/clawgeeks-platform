"""Authentication database models."""

from datetime import datetime
from typing import Optional
import uuid
import secrets

from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.database import Base


def generate_uuid() -> str:
    """Generate UUID string."""
    return str(uuid.uuid4())


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"cg_{secrets.token_urlsafe(32)}"


class UserModel(Base):
    """User account for admin dashboard access."""
    
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid
    )
    
    # Credentials
    email: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True, 
        index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Profile
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Permissions
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Optional: Link to tenant (for tenant-scoped users)
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Sessions & Security
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    # Relationships
    api_keys: Mapped[list["APIKeyModel"]] = relationship(
        "APIKeyModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User {self.email}>"
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert to dictionary."""
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "is_admin": self.is_admin,
            "is_active": self.is_active,
            "tenant_id": self.tenant_id,
            "last_login": self.last_login,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_sensitive:
            data["failed_attempts"] = self.failed_attempts
            data["locked_until"] = self.locked_until
        return data


class APIKeyModel(Base):
    """API key for programmatic access."""
    
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid
    )
    
    # The key itself (hashed for storage, shown once on creation)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    key_prefix: Mapped[str] = mapped_column(String(10), nullable=False)  # "cg_xxxx" for display
    
    # Metadata
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Owner
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Optional: Scope to specific tenant
    tenant_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Expiration
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Usage tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    use_count: Mapped[int] = mapped_column(default=0, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationships
    user: Mapped["UserModel"] = relationship("UserModel", back_populates="api_keys")
    
    def __repr__(self) -> str:
        return f"<APIKey {self.key_prefix}... ({self.name})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "key_prefix": self.key_prefix,
            "name": self.name,
            "description": self.description,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "is_active": self.is_active,
            "expires_at": self.expires_at,
            "last_used_at": self.last_used_at,
            "use_count": self.use_count,
            "created_at": self.created_at,
        }
