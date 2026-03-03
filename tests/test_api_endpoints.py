"""
API Endpoint Tests for ClawGeeks Platform.

Tests all API routes using FastAPI TestClient:
- HR Department endpoints
- Board of Mentors endpoints
- Board of Advisors endpoints
- Core tenant & billing endpoints

Uses SQLite in-memory for fast isolated tests.
"""

import asyncio
import os
import pytest
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

# MUST set environment variables BEFORE any provisioning imports
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-key-for-api-tests"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_fake"
os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test_fake"
os.environ["COOLIFY_API_URL"] = "http://localhost:3000"
os.environ["COOLIFY_API_KEY"] = "fake-coolify-key"

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from provisioning.api.main import app
from provisioning.db import Base, get_db
from provisioning.auth.models import UserModel
from provisioning.auth.service import AuthService
from provisioning.auth.schemas import UserCreate


# =============================================================================
# Test Database Setup
# =============================================================================

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def auth_service(db_session: AsyncSession) -> AuthService:
    return AuthService(db_session)


@pytest.fixture
async def admin_user(db_session: AsyncSession, auth_service: AuthService) -> UserModel:
    user_data = UserCreate(
        email="admin@test.com",
        name="Admin User",
        password="AdminPass123!",
        is_admin=True,
    )
    user = await auth_service.create_user(user_data)
    return user


@pytest.fixture
async def regular_user(db_session: AsyncSession, auth_service: AuthService) -> UserModel:
    user_data = UserCreate(
        email="user@test.com",
        name="Regular User",
        password="UserPass123!",
        is_admin=False,
    )
    user = await auth_service.create_user(user_data)
    return user


@pytest.fixture
async def admin_token(client: AsyncClient, admin_user: UserModel) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def user_token(client: AsyncClient, regular_user: UserModel) -> str:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@test.com", "password": "UserPass123!"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# HR Department API Tests
# =============================================================================

class TestHRDepartmentAPI:
    """Test /api/v1/hr endpoints."""

    # -------------------------------------------------------------------------
    # Public Endpoints
    # -------------------------------------------------------------------------

    async def test_get_questionnaire(self, client: AsyncClient):
        """GET /api/v1/hr/questionnaire returns prompts."""
        response = await client.get("/api/v1/hr/questionnaire")
        assert response.status_code == 200
        data = response.json()
        assert "prompts" in data
        assert len(data["prompts"]) > 0
        # Check structure of first prompt
        prompt = data["prompts"][0]
        assert "key" in prompt
        assert "prompt" in prompt

    async def test_list_industries(self, client: AsyncClient):
        """GET /api/v1/hr/industries returns all industries."""
        response = await client.get("/api/v1/hr/industries")
        assert response.status_code == 200
        data = response.json()
        assert "industries" in data
        assert len(data["industries"]) > 0
        # Check structure
        industry = data["industries"][0]
        assert "id" in industry
        assert "name" in industry
        assert "description" in industry

    async def test_list_stages(self, client: AsyncClient):
        """GET /api/v1/hr/stages returns business stages."""
        response = await client.get("/api/v1/hr/stages")
        assert response.status_code == 200
        data = response.json()
        assert "stages" in data
        assert len(data["stages"]) > 0

    async def test_list_goals(self, client: AsyncClient):
        """GET /api/v1/hr/goals returns business goals."""
        response = await client.get("/api/v1/hr/goals")
        assert response.status_code == 200
        data = response.json()
        assert "goals" in data
        assert len(data["goals"]) > 0

    # -------------------------------------------------------------------------
    # Authenticated Endpoints
    # -------------------------------------------------------------------------

    async def test_analyze_business_requires_auth(self, client: AsyncClient):
        """POST /api/v1/hr/analyze requires authentication."""
        response = await client.post(
            "/api/v1/hr/analyze",
            json={
                "name": "Test Co",
                "description": "A SaaS startup",
                "team_size": 2,
            },
        )
        assert response.status_code == 401

    async def test_analyze_business_success(
        self, client: AsyncClient, user_token: str
    ):
        """POST /api/v1/hr/analyze returns profile and recommendations."""
        response = await client.post(
            "/api/v1/hr/analyze",
            json={
                "name": "Acme SaaS",
                "description": "We build project management tools for remote teams",
                "team_size": 3,
                "has_technical": True,
                "has_marketing": False,
                "has_sales": False,
                "budget_tier": "pro",
            },
            headers=auth_header(user_token),
        )
        assert response.status_code == 200
        data = response.json()

        # Validate profile
        assert "profile" in data
        profile = data["profile"]
        assert profile["name"] == "Acme SaaS"
        assert profile["team_size"] == 3
        assert profile["has_technical_founder"] is True
        assert profile["budget_tier"] == "pro"

        # Validate recommendation
        assert "recommendation" in data
        rec = data["recommendation"]
        assert "agents" in rec
        assert "summary" in rec
        assert len(rec["agents"]) > 0

        # Each agent has required fields
        agent = rec["agents"][0]
        assert "role" in agent
        assert "priority" in agent
        assert "rationale" in agent

    async def test_analyze_business_invalid_tier(
        self, client: AsyncClient, user_token: str
    ):
        """Invalid tier returns 422."""
        response = await client.post(
            "/api/v1/hr/analyze",
            json={
                "name": "Test",
                "description": "Test",
                "budget_tier": "invalid_tier",
            },
            headers=auth_header(user_token),
        )
        assert response.status_code == 422

    async def test_analyze_questionnaire_success(
        self, client: AsyncClient, user_token: str
    ):
        """POST /api/v1/hr/analyze/questionnaire works."""
        response = await client.post(
            "/api/v1/hr/analyze/questionnaire",
            json={
                "name": "Acme Corp",
                "responses": {
                    "description": "We build e-commerce tools",
                    "industry": "ecommerce",
                    "stage": "growth",
                    "goals": "grow_revenue, improve_product",
                    "team_size": "5",
                    "has_technical": "yes",
                },
                "budget_tier": "starter",
            },
            headers=auth_header(user_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert "profile" in data
        assert "recommendation" in data


# =============================================================================
# Board of Mentors API Tests
# =============================================================================

class TestBoardOfMentorsAPI:
    """Test /api/v1/mentors endpoints."""

    # -------------------------------------------------------------------------
    # Public Endpoints
    # -------------------------------------------------------------------------

    async def test_list_mentors(self, client: AsyncClient):
        """GET /api/v1/mentors returns all mentors."""
        response = await client.get("/api/v1/mentors/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check structure
        mentor = data[0]
        assert "archetype" in mentor
        assert "name" in mentor
        assert "emoji" in mentor
        assert "domain" in mentor
        assert "title" in mentor
        assert "tagline" in mentor

    async def test_list_mentors_by_domain(self, client: AsyncClient):
        """GET /api/v1/mentors?domain=growth filters by domain."""
        response = await client.get("/api/v1/mentors/?domain=growth")
        assert response.status_code == 200
        data = response.json()
        # All returned mentors should be in growth domain
        for mentor in data:
            assert mentor["domain"] == "growth"

    async def test_list_mentors_invalid_domain(self, client: AsyncClient):
        """Invalid domain returns 400."""
        response = await client.get("/api/v1/mentors/?domain=invalid")
        assert response.status_code == 400

    async def test_list_domains(self, client: AsyncClient):
        """GET /api/v1/mentors/domains returns all domains."""
        response = await client.get("/api/v1/mentors/domains")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Each domain has domain and description
        domain_obj = data[0]
        assert "domain" in domain_obj
        assert "description" in domain_obj

    async def test_list_archetypes(self, client: AsyncClient):
        """GET /api/v1/mentors/archetypes returns all archetypes."""
        response = await client.get("/api/v1/mentors/archetypes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_get_mentor_detail(self, client: AsyncClient):
        """GET /api/v1/mentors/{archetype} returns full details."""
        response = await client.get("/api/v1/mentors/growth_hacker")
        assert response.status_code == 200
        data = response.json()
        assert "archetype" in data
        assert "name" in data
        assert "expertise" in data
        assert "personality" in data
        assert "communication_style" in data
        assert "signature_questions" in data
        assert "frameworks" in data

    async def test_get_mentor_not_found(self, client: AsyncClient):
        """Invalid archetype returns 404."""
        response = await client.get("/api/v1/mentors/nonexistent")
        assert response.status_code == 404

    async def test_quick_mentor_lookup(self, client: AsyncClient):
        """GET /api/v1/mentors/quick/{type} returns mentor."""
        response = await client.get("/api/v1/mentors/quick/growth")
        assert response.status_code == 200
        data = response.json()
        assert "archetype" in data
        assert "name" in data

    async def test_quick_mentor_lookup_invalid(self, client: AsyncClient):
        """Invalid challenge type returns 404."""
        response = await client.get("/api/v1/mentors/quick/invalidtype")
        assert response.status_code == 404

    async def test_mentors_for_industry(self, client: AsyncClient):
        """GET /api/v1/mentors/industry/{industry} returns mentors."""
        response = await client.get("/api/v1/mentors/industry/saas")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    # -------------------------------------------------------------------------
    # Authenticated Endpoints
    # -------------------------------------------------------------------------

    async def test_recommend_mentors_requires_auth(self, client: AsyncClient):
        """POST /api/v1/mentors/recommend requires auth."""
        response = await client.post(
            "/api/v1/mentors/recommend",
            json={"challenge": "How do I grow my startup?"},
        )
        assert response.status_code == 401

    async def test_recommend_mentors_success(
        self, client: AsyncClient, user_token: str
    ):
        """POST /api/v1/mentors/recommend returns recommendations."""
        response = await client.post(
            "/api/v1/mentors/recommend",
            json={
                "challenge": "I need to raise a Series A round",
                "industry": "saas",
            },
            headers=auth_header(user_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        rec = data[0]
        assert "mentor" in rec
        assert "relevance_score" in rec
        assert "reasons" in rec
        assert "suggested_questions" in rec

    async def test_default_board_requires_auth(self, client: AsyncClient):
        """POST /api/v1/mentors/default-board requires auth."""
        response = await client.post(
            "/api/v1/mentors/default-board",
            json={},
        )
        assert response.status_code == 401

    async def test_default_board_success(
        self, client: AsyncClient, user_token: str
    ):
        """POST /api/v1/mentors/default-board returns mentors."""
        response = await client.post(
            "/api/v1/mentors/default-board",
            json={"industry": "saas", "business_stage": "growth"},
            headers=auth_header(user_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_generate_soul_requires_auth(self, client: AsyncClient):
        """POST /api/v1/mentors/generate-soul requires auth."""
        response = await client.post(
            "/api/v1/mentors/generate-soul",
            json={
                "archetype": "growth_hacker",
                "tenant_name": "Acme",
            },
        )
        assert response.status_code == 401

    async def test_generate_soul_success(
        self, client: AsyncClient, user_token: str
    ):
        """POST /api/v1/mentors/generate-soul returns SOUL.md content."""
        response = await client.post(
            "/api/v1/mentors/generate-soul",
            json={
                "archetype": "growth_hacker",
                "tenant_name": "Acme Corp",
                "context": "We are a B2B SaaS startup",
            },
            headers=auth_header(user_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert "archetype" in data
        assert "mentor_name" in data
        assert "soul_md" in data
        assert "# SOUL.md" in data["soul_md"] or "SOUL" in data["soul_md"]


# =============================================================================
# Board of Advisors API Tests
# =============================================================================

class TestBoardOfAdvisorsAPI:
    """Test /api/v1/advisors endpoints."""

    # -------------------------------------------------------------------------
    # Public Endpoints
    # -------------------------------------------------------------------------

    async def test_list_advisors(self, client: AsyncClient):
        """GET /api/v1/advisors returns all advisors."""
        response = await client.get("/api/v1/advisors")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        # Check structure
        advisor = data[0]
        assert "archetype" in advisor
        assert "name" in advisor
        assert "emoji" in advisor
        assert "title" in advisor
        assert "domain" in advisor
        assert "tagline" in advisor

    async def test_list_advisor_domains(self, client: AsyncClient):
        """GET /api/v1/advisors/domains returns all domains."""
        response = await client.get("/api/v1/advisors/domains")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_list_advisor_archetypes(self, client: AsyncClient):
        """GET /api/v1/advisors/archetypes returns all archetypes."""
        response = await client.get("/api/v1/advisors/archetypes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    async def test_advisors_by_domain(self, client: AsyncClient):
        """GET /api/v1/advisors/domain/{domain} filters by domain."""
        # First get valid domains
        domains_response = await client.get("/api/v1/advisors/domains")
        domains = domains_response.json()
        if domains:
            domain = domains[0]
            response = await client.get(f"/api/v1/advisors/domain/{domain}")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    async def test_advisors_by_invalid_domain(self, client: AsyncClient):
        """Invalid domain returns 400."""
        response = await client.get("/api/v1/advisors/domain/invalid_domain")
        assert response.status_code == 400

    async def test_get_advisor_detail(self, client: AsyncClient):
        """GET /api/v1/advisors/{archetype} returns full details."""
        # First get a valid archetype
        list_response = await client.get("/api/v1/advisors")
        advisors = list_response.json()
        if advisors:
            archetype = advisors[0]["archetype"]
            response = await client.get(f"/api/v1/advisors/{archetype}")
            assert response.status_code == 200
            data = response.json()
            assert "archetype" in data
            assert "name" in data
            assert "expertise" in data
            assert "traits" in data
            assert "strategic_questions" in data
            assert "frameworks" in data

    async def test_get_advisor_not_found(self, client: AsyncClient):
        """Invalid archetype returns 404."""
        response = await client.get("/api/v1/advisors/nonexistent_advisor")
        assert response.status_code == 404

    async def test_quick_advisor_lookup(self, client: AsyncClient):
        """GET /api/v1/advisors/quick/{type} returns advisor."""
        response = await client.get("/api/v1/advisors/quick/fundraising")
        assert response.status_code == 200
        data = response.json()
        assert "archetype" in data
        assert "name" in data

    # -------------------------------------------------------------------------
    # Authenticated/Unauthenticated (advisor routes are mostly public)
    # -------------------------------------------------------------------------

    async def test_recommend_advisors(self, client: AsyncClient):
        """POST /api/v1/advisors/recommend returns recommendations."""
        response = await client.post(
            "/api/v1/advisors/recommend",
            json={
                "challenge": "We're considering an exit and need M&A advice",
                "industry": "tech",
                "max_results": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 3
        if data:
            rec = data[0]
            assert "advisor" in rec
            assert "relevance_score" in rec
            assert "reasons" in rec
            assert "suggested_questions" in rec

    async def test_default_advisory_board(self, client: AsyncClient):
        """POST /api/v1/advisors/default-board returns board."""
        response = await client.post(
            "/api/v1/advisors/default-board",
            json={
                "industry": "fintech",
                "stage": "scale",
                "size": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "advisors" in data
        assert "rationale" in data
        assert "industry_context" in data
        assert len(data["advisors"]) <= 5

    async def test_generate_advisor_soul(self, client: AsyncClient):
        """POST /api/v1/advisors/generate-soul returns SOUL.md content."""
        # First get a valid archetype
        list_response = await client.get("/api/v1/advisors")
        advisors = list_response.json()
        if advisors:
            archetype = advisors[0]["archetype"]
            response = await client.post(
                "/api/v1/advisors/generate-soul",
                json={
                    "archetype": archetype,
                    "tenant_name": "Test Corp",
                    "business_context": "Series B fintech startup",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert "content" in data
            assert len(data["content"]) > 100  # Should have substantial content


# =============================================================================
# Core Tenant API Tests (Admin-focused)
# =============================================================================

class TestTenantAPI:
    """Test /api/v1/tenants endpoints."""

    async def test_list_tenants_requires_admin(
        self, client: AsyncClient, user_token: str
    ):
        """Non-admin cannot list tenants."""
        response = await client.get(
            "/api/v1/tenants",
            headers=auth_header(user_token),
        )
        assert response.status_code == 403

    async def test_list_tenants_admin_success(
        self, client: AsyncClient, admin_token: str
    ):
        """Admin can list tenants."""
        response = await client.get(
            "/api/v1/tenants",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_create_tenant_requires_admin(
        self, client: AsyncClient, user_token: str
    ):
        """Non-admin cannot create tenant."""
        response = await client.post(
            "/api/v1/tenants",
            json={
                "name": "Test Tenant",
                "email": "test@tenant.com",
                "subdomain": "test-tenant",
            },
            headers=auth_header(user_token),
        )
        assert response.status_code == 403

    @patch("provisioning.services.provisioner.Provisioner.provision_tenant")
    async def test_create_tenant_admin_success(
        self, mock_provision, client: AsyncClient, admin_token: str
    ):
        """Admin can create tenant."""
        # Mock provisioning to avoid external API calls
        mock_provision.return_value = AsyncMock()
        
        response = await client.post(
            "/api/v1/tenants",
            json={
                "name": "New Tenant",
                "email": "new@tenant.com",
                "subdomain": "new-tenant",
            },
            headers=auth_header(admin_token),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Tenant"
        assert data["email"] == "new@tenant.com"
        assert data["subdomain"] == "new-tenant"
        assert "id" in data

    async def test_get_tenant_not_found(
        self, client: AsyncClient, admin_token: str
    ):
        """Nonexistent tenant returns 404."""
        response = await client.get(
            "/api/v1/tenants/nonexistent-id",
            headers=auth_header(admin_token),
        )
        assert response.status_code == 404

    async def test_update_tenant_not_found(
        self, client: AsyncClient, admin_token: str
    ):
        """Update nonexistent tenant returns 404."""
        response = await client.patch(
            "/api/v1/tenants/nonexistent-id",
            json={"name": "New Name"},
            headers=auth_header(admin_token),
        )
        assert response.status_code == 404


# =============================================================================
# Health & Utility Endpoints
# =============================================================================

class TestHealthEndpoints:
    """Test health check endpoints."""

    async def test_health_check(self, client: AsyncClient):
        """GET /health returns status."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    async def test_readiness_check(self, client: AsyncClient):
        """GET /ready returns database status (may be 503 with test SQLite)."""
        response = await client.get("/ready")
        # In test environment with SQLite, might be 200 or 503
        assert response.status_code in (200, 503)
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "ready"


# =============================================================================
# Self-Service Endpoints
# =============================================================================

class TestSelfServiceEndpoints:
    """Test /api/v1/me endpoints."""

    async def test_get_my_tenant_no_tenant(
        self, client: AsyncClient, user_token: str
    ):
        """User without tenant gets 404."""
        response = await client.get(
            "/api/v1/me/tenant",
            headers=auth_header(user_token),
        )
        assert response.status_code == 404

    async def test_get_my_billing_no_tenant(
        self, client: AsyncClient, user_token: str
    ):
        """User without tenant gets 404 for billing."""
        response = await client.get(
            "/api/v1/me/billing",
            headers=auth_header(user_token),
        )
        assert response.status_code == 404


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
