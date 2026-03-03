"""Tests for provisioning service."""

import pytest
from provisioning.models import TenantCreate, TenantTier, TenantStatus
from provisioning.services import Provisioner


@pytest.fixture
def provisioner():
    """Create fresh provisioner for each test."""
    return Provisioner()


@pytest.mark.asyncio
async def test_create_tenant(provisioner):
    """Test tenant creation."""
    request = TenantCreate(
        name="Test Company",
        email="test@example.com",
        tier=TenantTier.STARTER,
    )
    
    tenant = await provisioner.create_tenant(request)
    
    assert tenant.name == "Test Company"
    assert tenant.email == "test@example.com"
    assert tenant.tier == TenantTier.STARTER
    assert tenant.status == TenantStatus.PENDING
    assert tenant.subdomain is not None
    assert tenant.config.max_agents == 1


@pytest.mark.asyncio
async def test_subdomain_generation(provisioner):
    """Test subdomain is properly slugified."""
    request = TenantCreate(
        name="My Awesome Company!!!",
        email="test@example.com",
    )
    
    tenant = await provisioner.create_tenant(request)
    
    # Should be lowercase, no special chars
    assert tenant.subdomain.startswith("my-awesome-company-")
    assert "!" not in tenant.subdomain


@pytest.mark.asyncio
async def test_tier_affects_max_agents(provisioner):
    """Test that tier sets correct max_agents."""
    tiers = {
        TenantTier.STARTER: 1,
        TenantTier.PRO: 3,
        TenantTier.BUSINESS: 6,
        TenantTier.ENTERPRISE: 20,
    }
    
    for tier, expected_agents in tiers.items():
        request = TenantCreate(
            name=f"Test {tier}",
            email="test@example.com",
            tier=tier,
        )
        tenant = await provisioner.create_tenant(request)
        assert tenant.config.max_agents == expected_agents


@pytest.mark.asyncio
async def test_list_tenants_filter_by_status(provisioner):
    """Test listing tenants with status filter."""
    # Create tenants
    for i in range(3):
        await provisioner.create_tenant(TenantCreate(
            name=f"Test {i}",
            email=f"test{i}@example.com",
        ))
    
    # All should be PENDING
    pending = provisioner.list_tenants(status=TenantStatus.PENDING)
    assert len(pending) == 3
    
    active = provisioner.list_tenants(status=TenantStatus.ACTIVE)
    assert len(active) == 0


@pytest.mark.asyncio
async def test_get_tenant_by_subdomain(provisioner):
    """Test fetching tenant by subdomain."""
    request = TenantCreate(
        name="Findme Corp",
        email="find@example.com",
        subdomain="findme-corp",
    )
    
    created = await provisioner.create_tenant(request)
    found = provisioner.get_tenant_by_subdomain("findme-corp")
    
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_update_tenant_tier(provisioner):
    """Test upgrading tenant tier."""
    from provisioning.models import TenantUpdate
    
    tenant = await provisioner.create_tenant(TenantCreate(
        name="Upgrade Me",
        email="upgrade@example.com",
        tier=TenantTier.STARTER,
    ))
    
    assert tenant.config.max_agents == 1
    
    updated = await provisioner.update_tenant(
        tenant.id,
        TenantUpdate(tier=TenantTier.BUSINESS),
    )
    
    assert updated.tier == TenantTier.BUSINESS
    assert updated.config.max_agents == 6
