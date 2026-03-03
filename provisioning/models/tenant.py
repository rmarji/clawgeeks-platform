"""Tenant database models."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""
    PENDING = "pending"          # Created, awaiting provisioning
    PROVISIONING = "provisioning"  # Container being created
    ACTIVE = "active"            # Running and healthy
    SUSPENDED = "suspended"      # Billing/policy suspension
    TERMINATED = "terminated"    # Deleted


class TenantTier(str, Enum):
    """Subscription tier."""
    STARTER = "starter"      # $49/mo - 1 agent
    PRO = "pro"              # $149/mo - 3 agents
    BUSINESS = "business"    # $299/mo - 6 agents
    ENTERPRISE = "enterprise"  # Custom


class TenantCreate(BaseModel):
    """Request to create a new tenant."""
    name: str = Field(..., min_length=3, max_length=50)
    email: str
    tier: TenantTier = TenantTier.STARTER
    subdomain: Optional[str] = None  # Auto-generated if not provided


class TenantConfig(BaseModel):
    """Tenant OpenClaw configuration."""
    model: str = "anthropic/claude-sonnet-4-20250514"
    channels: list[str] = ["telegram"]
    shipos_enabled: bool = True
    max_agents: int = 1


class Tenant(BaseModel):
    """Full tenant record."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    subdomain: str
    tier: TenantTier
    status: TenantStatus = TenantStatus.PENDING
    config: TenantConfig = Field(default_factory=TenantConfig)
    
    # Infrastructure
    container_id: Optional[str] = None
    gateway_url: Optional[str] = None
    gateway_token: Optional[str] = None  # Encrypted in DB
    
    # Billing
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    provisioned_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class TenantUpdate(BaseModel):
    """Tenant update request."""
    name: Optional[str] = None
    tier: Optional[TenantTier] = None
    config: Optional[TenantConfig] = None
