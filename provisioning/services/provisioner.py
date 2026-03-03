"""Core provisioning service — orchestrates tenant lifecycle."""

import re
import secrets
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from ..models import (
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantStatus,
    TenantConfig,
    TenantTier,
)
from .coolify import CoolifyClient

if TYPE_CHECKING:
    from ..db import TenantRepository


class ProvisioningError(Exception):
    """Provisioning operation failed."""
    pass


class TenantNotFoundError(Exception):
    """Tenant does not exist."""
    pass


class Provisioner:
    """
    Manages tenant lifecycle:
    - Create → Provision → Active → Suspend/Terminate
    
    Supports both:
    - Database-backed mode (production): pass repository= 
    - In-memory mode (testing/dev): no repository, uses _tenants dict
    """
    
    def __init__(
        self,
        coolify: CoolifyClient = None,
        repository: "TenantRepository" = None,
    ):
        self.coolify = coolify or CoolifyClient()
        self.repository = repository
        
        # In-memory fallback when no repository provided
        self._tenants: dict[str, Tenant] = {}
    
    @property
    def _use_db(self) -> bool:
        """Check if using database mode."""
        return self.repository is not None
    
    def _generate_subdomain(self, name: str) -> str:
        """Generate unique subdomain from tenant name."""
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        suffix = secrets.token_hex(3)
        return f"{slug}-{suffix}"
    
    async def create_tenant(self, request: TenantCreate) -> Tenant:
        """
        Create new tenant record (does not provision yet).
        
        Flow:
        1. Validate request
        2. Generate subdomain if not provided
        3. Create tenant record (PENDING)
        4. Return tenant (caller should trigger provisioning)
        """
        subdomain = request.subdomain or self._generate_subdomain(request.name)
        
        # Check subdomain availability
        if self._use_db:
            if await self.repository.exists(subdomain):
                raise ProvisioningError(f"Subdomain '{subdomain}' already taken")
            tenant = await self.repository.create(request, subdomain)
        else:
            # In-memory mode
            config = TenantConfig(
                max_agents=self._get_max_agents(request.tier),
                shipos_enabled=True,
            )
            tenant = Tenant(
                name=request.name,
                email=request.email,
                subdomain=subdomain,
                tier=request.tier,
                status=TenantStatus.PENDING,
                config=config,
            )
            self._tenants[tenant.id] = tenant
        
        return tenant
    
    def _get_max_agents(self, tier: TenantTier) -> int:
        """Get max agents for tier."""
        return {
            TenantTier.STARTER: 1,
            TenantTier.PRO: 3,
            TenantTier.BUSINESS: 6,
            TenantTier.ENTERPRISE: 20,
        }.get(tier, 1)
    
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID."""
        if self._use_db:
            return await self.repository.get(tenant_id)
        return self._tenants.get(tenant_id)
    
    async def provision_tenant(self, tenant_id: str) -> Tenant:
        """
        Provision infrastructure for tenant.
        
        Flow:
        1. Update status → PROVISIONING
        2. Deploy OpenClaw container via Coolify
        3. Wait for container to be healthy
        4. Update status → ACTIVE
        """
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        
        if tenant.status not in [TenantStatus.PENDING, TenantStatus.SUSPENDED]:
            raise ProvisioningError(f"Cannot provision tenant in {tenant.status} status")
        
        # Update status to PROVISIONING
        if self._use_db:
            await self.repository.update_status(tenant_id, TenantStatus.PROVISIONING)
        else:
            tenant.status = TenantStatus.PROVISIONING
            tenant.updated_at = datetime.utcnow()
        
        try:
            # Deploy via Coolify
            result = await self.coolify.deploy_openclaw(tenant)
            
            # Update tenant with infrastructure details
            if self._use_db:
                tenant = await self.repository.update_status(
                    tenant_id,
                    TenantStatus.ACTIVE,
                    container_id=result["application_uuid"],
                    gateway_url=result["gateway_url"],
                    gateway_token=result["gateway_token"],
                )
            else:
                tenant.container_id = result["application_uuid"]
                tenant.gateway_url = result["gateway_url"]
                tenant.gateway_token = result["gateway_token"]
                tenant.status = TenantStatus.ACTIVE
                tenant.provisioned_at = datetime.utcnow()
                tenant.updated_at = datetime.utcnow()
            
            return tenant
            
        except Exception as e:
            # Rollback status on failure
            if self._use_db:
                await self.repository.update_status(tenant_id, TenantStatus.PENDING)
            else:
                tenant.status = TenantStatus.PENDING
                tenant.updated_at = datetime.utcnow()
            raise ProvisioningError(f"Failed to provision: {e}")
    
    async def get_tenant_by_subdomain(self, subdomain: str) -> Optional[Tenant]:
        """Get tenant by subdomain."""
        if self._use_db:
            return await self.repository.get_by_subdomain(subdomain)
        for tenant in self._tenants.values():
            if tenant.subdomain == subdomain:
                return tenant
        return None
    
    async def list_tenants(
        self,
        status: Optional[TenantStatus] = None,
        tier: Optional[TenantTier] = None,
    ) -> list[Tenant]:
        """List tenants with optional filters."""
        if self._use_db:
            return list(await self.repository.list_all(status=status))
        
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        if tier:
            tenants = [t for t in tenants if t.tier == tier]
        return tenants
    
    async def suspend_tenant(self, tenant_id: str, reason: str = None) -> Tenant:
        """Suspend tenant (stop container, keep data)."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        
        if tenant.container_id:
            await self.coolify.stop_application(tenant.container_id)
        
        if self._use_db:
            tenant = await self.repository.update_status(tenant_id, TenantStatus.SUSPENDED)
        else:
            tenant.status = TenantStatus.SUSPENDED
            tenant.updated_at = datetime.utcnow()
        
        return tenant
    
    async def reactivate_tenant(self, tenant_id: str) -> Tenant:
        """Reactivate suspended tenant."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        
        if tenant.status != TenantStatus.SUSPENDED:
            raise ProvisioningError(f"Tenant is not suspended (status: {tenant.status})")
        
        if tenant.container_id:
            await self.coolify.start_application(tenant.container_id)
        
        if self._use_db:
            tenant = await self.repository.update_status(tenant_id, TenantStatus.ACTIVE)
        else:
            tenant.status = TenantStatus.ACTIVE
            tenant.updated_at = datetime.utcnow()
        
        return tenant
    
    async def terminate_tenant(self, tenant_id: str) -> Tenant:
        """Terminate tenant (delete container and data)."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        
        if tenant.container_id:
            await self.coolify.delete_application(tenant.container_id)
        
        if self._use_db:
            tenant = await self.repository.update_status(
                tenant_id,
                TenantStatus.TERMINATED,
                container_id=None,
                gateway_url=None,
            )
        else:
            tenant.status = TenantStatus.TERMINATED
            tenant.container_id = None
            tenant.gateway_url = None
            tenant.updated_at = datetime.utcnow()
        
        return tenant
    
    async def update_tenant(self, tenant_id: str, update: TenantUpdate) -> Tenant:
        """Update tenant settings."""
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise TenantNotFoundError(f"Tenant {tenant_id} not found")
        
        if self._use_db:
            tenant = await self.repository.update(tenant_id, update)
        else:
            if update.name is not None:
                tenant.name = update.name
            if update.tier is not None:
                tenant.tier = update.tier
                tenant.config.max_agents = self._get_max_agents(update.tier)
            if update.config is not None:
                tenant.config = update.config
            tenant.updated_at = datetime.utcnow()
        
        return tenant
