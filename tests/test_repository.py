"""Tests for TenantRepository using SQLite in-memory."""

import asyncio
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from provisioning.db.database import Base
from provisioning.db.models import TenantModel
from provisioning.db.repository import TenantRepository
from provisioning.models.tenant import (
    TenantCreate, 
    TenantUpdate, 
    TenantStatus, 
    TenantTier,
    TenantConfig,
)


# Use SQLite for testing (no PostgreSQL required)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(engine):
    """Create test database session."""
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def repo(session):
    """Create repository with test session."""
    return TenantRepository(session)


@pytest.mark.asyncio
async def test_create_tenant(repo: TenantRepository, session: AsyncSession):
    """Test creating a new tenant."""
    data = TenantCreate(
        name="Test Corp",
        email="test@example.com",
        tier=TenantTier.PRO,
    )
    
    tenant = await repo.create(data, subdomain="test-corp-abc123")
    await session.commit()
    
    assert tenant.id is not None
    assert tenant.name == "Test Corp"
    assert tenant.email == "test@example.com"
    assert tenant.subdomain == "test-corp-abc123"
    assert tenant.tier == TenantTier.PRO.value
    assert tenant.status == TenantStatus.PENDING.value
    assert tenant.config.max_agents == 3  # PRO tier


@pytest.mark.asyncio
async def test_get_tenant(repo: TenantRepository, session: AsyncSession):
    """Test retrieving a tenant by ID."""
    data = TenantCreate(name="Get Test", email="get@test.com")
    tenant = await repo.create(data, subdomain="get-test-xyz")
    await session.commit()
    
    retrieved = await repo.get(tenant.id)
    
    assert retrieved is not None
    assert retrieved.id == tenant.id
    assert retrieved.name == "Get Test"


@pytest.mark.asyncio
async def test_get_by_subdomain(repo: TenantRepository, session: AsyncSession):
    """Test finding tenant by subdomain."""
    data = TenantCreate(name="Subdomain Test", email="sub@test.com")
    tenant = await repo.create(data, subdomain="unique-subdomain")
    await session.commit()
    
    found = await repo.get_by_subdomain("unique-subdomain")
    
    assert found is not None
    assert found.id == tenant.id


@pytest.mark.asyncio
async def test_update_tenant(repo: TenantRepository, session: AsyncSession):
    """Test updating tenant fields."""
    data = TenantCreate(name="Update Test", email="update@test.com")
    tenant = await repo.create(data, subdomain="update-test")
    await session.commit()
    
    update = TenantUpdate(name="Updated Name", tier=TenantTier.BUSINESS)
    updated = await repo.update(tenant.id, update)
    await session.commit()
    
    assert updated.name == "Updated Name"
    assert updated.tier == TenantTier.BUSINESS.value


@pytest.mark.asyncio
async def test_update_status(repo: TenantRepository, session: AsyncSession):
    """Test status transitions."""
    data = TenantCreate(name="Status Test", email="status@test.com")
    tenant = await repo.create(data, subdomain="status-test")
    await session.commit()
    
    # Transition to ACTIVE
    active = await repo.update_status(
        tenant.id, 
        TenantStatus.ACTIVE,
        container_id="abc123",
        gateway_url="https://status-test.openclaw.ai"
    )
    await session.commit()
    
    assert active.status == TenantStatus.ACTIVE.value
    assert active.container_id == "abc123"
    assert active.provisioned_at is not None


@pytest.mark.asyncio
async def test_list_all(repo: TenantRepository, session: AsyncSession):
    """Test listing tenants."""
    # Create multiple tenants
    for i in range(3):
        data = TenantCreate(name=f"List Test {i}", email=f"list{i}@test.com")
        await repo.create(data, subdomain=f"list-test-{i}")
    await session.commit()
    
    tenants = await repo.list_all()
    
    assert len(tenants) >= 3


@pytest.mark.asyncio
async def test_list_by_status(repo: TenantRepository, session: AsyncSession):
    """Test filtering by status."""
    # Create pending tenant
    data1 = TenantCreate(name="Pending Corp", email="pending@test.com")
    t1 = await repo.create(data1, subdomain="pending-corp")
    
    # Create and activate another
    data2 = TenantCreate(name="Active Corp", email="active@test.com")
    t2 = await repo.create(data2, subdomain="active-corp")
    await repo.update_status(t2.id, TenantStatus.ACTIVE)
    await session.commit()
    
    pending = await repo.list_all(status=TenantStatus.PENDING)
    active = await repo.list_all(status=TenantStatus.ACTIVE)
    
    assert any(t.id == t1.id for t in pending)
    assert any(t.id == t2.id for t in active)


@pytest.mark.asyncio
async def test_exists(repo: TenantRepository, session: AsyncSession):
    """Test subdomain existence check."""
    data = TenantCreate(name="Exists Test", email="exists@test.com")
    await repo.create(data, subdomain="taken-subdomain")
    await session.commit()
    
    assert await repo.exists("taken-subdomain") is True
    assert await repo.exists("available-subdomain") is False


@pytest.mark.asyncio
async def test_delete(repo: TenantRepository, session: AsyncSession):
    """Test hard delete."""
    data = TenantCreate(name="Delete Test", email="delete@test.com")
    tenant = await repo.create(data, subdomain="delete-test")
    await session.commit()
    
    deleted = await repo.delete(tenant.id)
    await session.commit()
    
    assert deleted is True
    assert await repo.get(tenant.id) is None
