"""SQLAlchemy ORM models."""

from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import String, Text, DateTime, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from ..models.tenant import TenantStatus, TenantTier


def generate_uuid() -> str:
    """Generate UUID string."""
    return str(uuid.uuid4())


class TenantModel(Base):
    """Tenant database table."""
    
    __tablename__ = "tenants"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=generate_uuid
    )
    
    # Core fields
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    subdomain: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    
    # Status and tier
    tier: Mapped[str] = mapped_column(
        SAEnum(TenantTier, name="tenant_tier", create_type=False),
        nullable=False,
        default=TenantTier.STARTER.value
    )
    status: Mapped[str] = mapped_column(
        SAEnum(TenantStatus, name="tenant_status", create_type=False),
        nullable=False,
        default=TenantStatus.PENDING.value
    )
    
    # Configuration (JSON)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    
    # Infrastructure
    container_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    gateway_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gateway_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Encrypted
    
    # Billing
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
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
    provisioned_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Tenant {self.subdomain} ({self.status})>"
    
    def to_dict(self) -> dict:
        """Convert to dictionary (for Pydantic serialization)."""
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "subdomain": self.subdomain,
            "tier": self.tier,
            "status": self.status,
            "config": self.config,
            "container_id": self.container_id,
            "gateway_url": self.gateway_url,
            "gateway_token": self.gateway_token,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provisioned_at": self.provisioned_at,
        }
