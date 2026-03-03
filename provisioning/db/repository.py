"""Repository pattern for tenant CRUD operations."""

from datetime import datetime
from typing import Optional, Sequence, AsyncGenerator

from fastapi import Depends
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import TenantModel
from .database import get_db
from ..models.tenant import (
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantConfig,
    TenantStatus,
)


async def get_repository(
    session: AsyncSession = Depends(get_db),
) -> "TenantRepository":
    """FastAPI dependency: get TenantRepository with session."""
    return TenantRepository(session)


class TenantRepository:
    """Repository for Tenant CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, data: TenantCreate, subdomain: str) -> Tenant:
        """Create a new tenant."""
        # Build config based on tier
        config = TenantConfig(
            max_agents=self._max_agents_for_tier(data.tier)
        )
        
        tenant = TenantModel(
            name=data.name,
            email=data.email,
            subdomain=subdomain,
            tier=data.tier.value,
            status=TenantStatus.PENDING.value,
            config=config.model_dump(),
        )
        
        self.session.add(tenant)
        await self.session.flush()  # Get ID before commit
        
        return self._to_pydantic(tenant)
    
    async def get(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()
        return self._to_pydantic(tenant) if tenant else None
    
    async def get_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        """Get tenant by subdomain."""
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.subdomain == subdomain)
        )
        tenant = result.scalar_one_or_none()
        return self._to_pydantic(tenant) if tenant else None
    
    async def get_by_email(self, email: str) -> Optional[Tenant]:
        """Get tenant by email."""
        result = await self.session.execute(
            select(TenantModel).where(TenantModel.email == email)
        )
        tenant = result.scalar_one_or_none()
        return self._to_pydantic(tenant) if tenant else None
    
    async def get_by_subscription(self, subscription_id: str) -> Optional[Tenant]:
        """Get tenant by Stripe subscription ID."""
        result = await self.session.execute(
            select(TenantModel).where(
                TenantModel.stripe_subscription_id == subscription_id
            )
        )
        tenant = result.scalar_one_or_none()
        return self._to_pydantic(tenant) if tenant else None
    
    async def get_by_customer(self, customer_id: str) -> Optional[Tenant]:
        """Get tenant by Stripe customer ID."""
        result = await self.session.execute(
            select(TenantModel).where(
                TenantModel.stripe_customer_id == customer_id
            )
        )
        tenant = result.scalar_one_or_none()
        return self._to_pydantic(tenant) if tenant else None
    
    async def list_all(
        self,
        status: Optional[TenantStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[Tenant]:
        """List all tenants with optional status filter."""
        query = select(TenantModel).offset(offset).limit(limit)
        
        if status:
            query = query.where(TenantModel.status == status.value)
        
        result = await self.session.execute(query)
        tenants = result.scalars().all()
        return [self._to_pydantic(t) for t in tenants]
    
    async def update(
        self, 
        tenant_id: str, 
        data: TenantUpdate | dict
    ) -> Optional[Tenant]:
        """Update tenant fields.
        
        Args:
            tenant_id: Tenant ID
            data: TenantUpdate model or dict of fields to update
        """
        if isinstance(data, dict):
            update_data = {k: v for k, v in data.items() if v is not None}
        else:
            update_data = data.model_dump(exclude_unset=True)
        
        if not update_data:
            return await self.get(tenant_id)
        
        # Handle nested config
        if "config" in update_data and update_data["config"]:
            if hasattr(update_data["config"], "model_dump"):
                update_data["config"] = update_data["config"].model_dump()
        
        update_data["updated_at"] = datetime.utcnow()
        
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant_id)
            .values(**update_data)
        )
        
        return await self.get(tenant_id)
    
    async def update_status(
        self, 
        tenant_id: str, 
        status: TenantStatus,
        **kwargs
    ) -> Optional[Tenant]:
        """Update tenant status with optional extra fields."""
        values = {
            "status": status.value,
            "updated_at": datetime.utcnow(),
            **kwargs,
        }
        
        # Set provisioned_at timestamp when transitioning to ACTIVE
        if status == TenantStatus.ACTIVE and "provisioned_at" not in kwargs:
            values["provisioned_at"] = datetime.utcnow()
        
        await self.session.execute(
            update(TenantModel)
            .where(TenantModel.id == tenant_id)
            .values(**values)
        )
        
        return await self.get(tenant_id)
    
    async def delete(self, tenant_id: str) -> bool:
        """Hard delete a tenant (use update_status for soft delete)."""
        result = await self.session.execute(
            delete(TenantModel).where(TenantModel.id == tenant_id)
        )
        return result.rowcount > 0
    
    async def exists(self, subdomain: str) -> bool:
        """Check if subdomain is already taken."""
        result = await self.session.execute(
            select(TenantModel.id).where(TenantModel.subdomain == subdomain)
        )
        return result.scalar_one_or_none() is not None
    
    def _max_agents_for_tier(self, tier: str) -> int:
        """Get max agents for tier."""
        return {
            "starter": 1,
            "pro": 3,
            "business": 6,
            "enterprise": 20,
        }.get(tier, 1)
    
    def _to_pydantic(self, model: TenantModel) -> Tenant:
        """Convert SQLAlchemy model to Pydantic model."""
        return Tenant(
            id=model.id,
            name=model.name,
            email=model.email,
            subdomain=model.subdomain,
            tier=model.tier,
            status=model.status,
            config=TenantConfig(**model.config),
            container_id=model.container_id,
            gateway_url=model.gateway_url,
            gateway_token=model.gateway_token,
            stripe_customer_id=model.stripe_customer_id,
            stripe_subscription_id=model.stripe_subscription_id,
            created_at=model.created_at,
            updated_at=model.updated_at,
            provisioned_at=model.provisioned_at,
        )
