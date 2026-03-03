"""Data models for ClawGeeks API."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from datetime import datetime


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""
    PENDING = "PENDING"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class TenantTier(str, Enum):
    """Subscription tier."""
    STARTER = "STARTER"
    PRO = "PRO"
    BUSINESS = "BUSINESS"
    ENTERPRISE = "ENTERPRISE"
    
    @property
    def max_agents(self) -> int:
        """Maximum agents for this tier."""
        limits = {
            TenantTier.STARTER: 1,
            TenantTier.PRO: 3,
            TenantTier.BUSINESS: 6,
            TenantTier.ENTERPRISE: 20,
        }
        return limits.get(self, 1)
    
    @property
    def price_cents(self) -> int:
        """Monthly price in cents."""
        prices = {
            TenantTier.STARTER: 4900,
            TenantTier.PRO: 14900,
            TenantTier.BUSINESS: 29900,
            TenantTier.ENTERPRISE: 0,  # Custom pricing
        }
        return prices.get(self, 0)


@dataclass
class Tenant:
    """Tenant data model."""
    id: str
    name: str
    email: str
    subdomain: str
    tier: TenantTier
    status: TenantStatus
    ship_os_enabled: bool = True
    agent_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    coolify_app_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "Tenant":
        """Create Tenant from API response dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            email=data["email"],
            subdomain=data["subdomain"],
            tier=TenantTier(data["tier"]),
            status=TenantStatus(data["status"]),
            ship_os_enabled=data.get("ship_os_enabled", True),
            agent_count=data.get("agent_count", 0),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            stripe_customer_id=data.get("stripe_customer_id"),
            stripe_subscription_id=data.get("stripe_subscription_id"),
            coolify_app_id=data.get("coolify_app_id"),
        )


@dataclass
class User:
    """User data model."""
    id: str
    email: str
    is_admin: bool = False
    is_active: bool = True
    tenant_id: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Create User from API response dict."""
        return cls(
            id=data["id"],
            email=data["email"],
            is_admin=data.get("is_admin", False),
            is_active=data.get("is_active", True),
            tenant_id=data.get("tenant_id"),
        )


@dataclass
class TokenResponse:
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    
    @classmethod
    def from_dict(cls, data: dict) -> "TokenResponse":
        """Create TokenResponse from API response dict."""
        return cls(
            access_token=data["access_token"],
            token_type=data.get("token_type", "bearer"),
            expires_in=data.get("expires_in", 3600),
        )


@dataclass
class APIKey:
    """API key data model."""
    id: str
    name: str
    prefix: str
    is_active: bool = True
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    use_count: int = 0
    
    @classmethod
    def from_dict(cls, data: dict) -> "APIKey":
        """Create APIKey from API response dict."""
        return cls(
            id=data["id"],
            name=data["name"],
            prefix=data["prefix"],
            is_active=data.get("is_active", True),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
            use_count=data.get("use_count", 0),
        )
