"""Tests for agent provisioning service."""

import pytest
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

from provisioning.services.agent_provisioner import (
    AgentProvisioner,
    AgentConfig,
    AgentRole,
    ModelTier,
    WorkspaceConfig,
    SOUL_TEMPLATES,
)
from provisioning.models import Tenant, TenantTier, TenantStatus, TenantConfig


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_tenant():
    """Create sample tenant for testing."""
    return Tenant(
        id="test-tenant-123",
        name="Test Company",
        email="test@example.com",
        subdomain="test-company-abc123",
        tier=TenantTier.PRO,
        status=TenantStatus.ACTIVE,
        config=TenantConfig(max_agents=3, shipos_enabled=True),
    )


@pytest.fixture
def provisioner(temp_workspace):
    """Create AgentProvisioner with temp workspace."""
    return AgentProvisioner(base_path=temp_workspace)


class TestSoulTemplates:
    """Test SOUL.md templates."""
    
    def test_all_roles_have_templates(self):
        """All pre-built roles should have templates."""
        for role in AgentRole:
            if role != AgentRole.CUSTOM:
                assert role in SOUL_TEMPLATES, f"Missing template for {role}"
    
    def test_templates_have_required_fields(self):
        """Templates should have required fields."""
        required_fields = ["name", "emoji", "personality", "description", "principles"]
        for role, template in SOUL_TEMPLATES.items():
            for field in required_fields:
                assert field in template, f"Template {role} missing field: {field}"
    
    def test_ceo_template_is_premium(self):
        """CEO should use premium model tier."""
        assert SOUL_TEMPLATES[AgentRole.CEO]["model_tier"] == ModelTier.PREMIUM
    
    def test_analyst_template_is_economy(self):
        """Analyst should use economy model tier."""
        assert SOUL_TEMPLATES[AgentRole.ANALYST]["model_tier"] == ModelTier.ECONOMY


class TestAgentConfig:
    """Test AgentConfig model."""
    
    def test_create_minimal_config(self):
        """Create config with minimal fields."""
        config = AgentConfig(id="test", name="Test Agent", role=AgentRole.ASSISTANT)
        assert config.id == "test"
        assert config.model_tier == ModelTier.STANDARD
        assert config.is_default == False
    
    def test_create_full_config(self):
        """Create config with all fields."""
        config = AgentConfig(
            id="cto",
            name="Chief Tech",
            role=AgentRole.CTO,
            model_tier=ModelTier.PREMIUM,
            description="Tech lead",
            personality="Technical",
            capabilities=["coding", "review"],
            tools=["shell", "git"],
            daily_token_limit=500_000,
            is_default=True,
        )
        assert config.model_tier == ModelTier.PREMIUM
        assert len(config.capabilities) == 2
        assert config.is_default == True


class TestDefaultAgents:
    """Test tier-based default agent configurations."""
    
    def test_starter_gets_one_agent(self, provisioner):
        """Starter tier gets 1 agent."""
        agents = provisioner.get_default_agents(TenantTier.STARTER)
        assert len(agents) == 1
        assert agents[0].is_default == True
    
    def test_pro_gets_two_agents(self, provisioner):
        """Pro tier gets 2 agents (main + analyst)."""
        agents = provisioner.get_default_agents(TenantTier.PRO)
        assert len(agents) == 2
        roles = [a.role for a in agents]
        assert AgentRole.ASSISTANT in roles
        assert AgentRole.ANALYST in roles
    
    def test_business_gets_three_agents(self, provisioner):
        """Business tier gets 3 agents."""
        agents = provisioner.get_default_agents(TenantTier.BUSINESS)
        assert len(agents) == 3
        roles = [a.role for a in agents]
        assert AgentRole.DEVELOPER in roles
    
    def test_enterprise_gets_five_agents(self, provisioner):
        """Enterprise tier gets 5 agents including premium."""
        agents = provisioner.get_default_agents(TenantTier.ENTERPRISE)
        assert len(agents) == 5
        roles = [a.role for a in agents]
        assert AgentRole.CTO in roles
        assert AgentRole.CMO in roles


class TestGenerateSoulMd:
    """Test SOUL.md generation."""
    
    def test_generate_basic_soul(self, provisioner, sample_tenant):
        """Generate basic SOUL.md."""
        agent = AgentConfig(
            id="test",
            name="Test Agent",
            role=AgentRole.ASSISTANT,
        )
        soul = provisioner.generate_soul_md(agent, sample_tenant)
        
        assert "# SOUL.md — Test Agent" in soul
        assert "Test Company" in soul
        assert "ASSISTANT" in soul
    
    def test_soul_includes_principles(self, provisioner, sample_tenant):
        """SOUL.md includes role principles."""
        agent = AgentConfig(id="ceo", name="CEO", role=AgentRole.CEO)
        soul = provisioner.generate_soul_md(agent, sample_tenant)
        
        assert "Core Principles" in soul
        assert "Vision before tactics" in soul
    
    def test_soul_includes_tools(self, provisioner, sample_tenant):
        """SOUL.md includes tool list."""
        agent = AgentConfig(
            id="dev",
            name="Developer",
            role=AgentRole.DEVELOPER,
            tools=["shell", "git", "read"],
        )
        soul = provisioner.generate_soul_md(agent, sample_tenant)
        
        assert "Tools Available" in soul
        assert "`shell`" in soul


class TestGenerateAgentsMd:
    """Test AGENTS.md generation."""
    
    def test_generate_agents_roster(self, provisioner, sample_tenant):
        """Generate team roster."""
        agents = [
            AgentConfig(id="main", name="Main", role=AgentRole.ASSISTANT, is_default=True),
            AgentConfig(id="analyst", name="Analyst", role=AgentRole.ANALYST),
        ]
        content = provisioner.generate_agents_md(agents, sample_tenant)
        
        assert "# AGENTS.md — Team Roster" in content
        assert "Test Company" in content
        assert "Default Agent:** `main`" in content
        assert "Main" in content
        assert "Analyst" in content
    
    def test_default_agent_marked(self, provisioner, sample_tenant):
        """Default agent is marked in roster."""
        agents = [
            AgentConfig(id="main", name="Main", role=AgentRole.ASSISTANT, is_default=True),
        ]
        content = provisioner.generate_agents_md(agents, sample_tenant)
        
        assert "*(default)*" in content


class TestProvisionWorkspace:
    """Test full workspace provisioning."""
    
    @pytest.mark.asyncio
    async def test_creates_directory_structure(self, provisioner, sample_tenant, temp_workspace):
        """Provisioning creates expected directories."""
        result = await provisioner.provision_workspace(sample_tenant)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        assert workspace.exists()
        assert (workspace / "agents").is_dir()
        assert (workspace / "shared").is_dir()
        assert (workspace / "memory").is_dir()
        assert (workspace / "shipos").is_dir()
    
    @pytest.mark.asyncio
    async def test_creates_core_files(self, provisioner, sample_tenant, temp_workspace):
        """Provisioning creates core files."""
        await provisioner.provision_workspace(sample_tenant)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        assert (workspace / "AGENTS.md").exists()
        assert (workspace / "USER.md").exists()
        assert (workspace / "MEMORY.md").exists()
        assert (workspace / "TOOLS.md").exists()
    
    @pytest.mark.asyncio
    async def test_creates_agent_directories(self, provisioner, sample_tenant, temp_workspace):
        """Provisioning creates agent directories with SOUL.md."""
        await provisioner.provision_workspace(sample_tenant)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        # Pro tier gets main + analyst
        assert (workspace / "agents" / "main" / "SOUL.md").exists()
        assert (workspace / "agents" / "analyst" / "SOUL.md").exists()
    
    @pytest.mark.asyncio
    async def test_creates_shipos_files(self, provisioner, sample_tenant, temp_workspace):
        """Provisioning creates ShipOS files when enabled."""
        await provisioner.provision_workspace(sample_tenant)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        assert (workspace / "shipos" / "plan.md").exists()
        assert (workspace / "shipos" / "PROJECT-STATUS-SOP.md").exists()
    
    @pytest.mark.asyncio
    async def test_skips_shipos_when_disabled(self, provisioner, sample_tenant, temp_workspace):
        """Provisioning skips ShipOS when disabled."""
        config = WorkspaceConfig(shipos_enabled=False, agents=[
            AgentConfig(id="main", name="Main", role=AgentRole.ASSISTANT, is_default=True)
        ])
        await provisioner.provision_workspace(sample_tenant, config)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        assert not (workspace / "shipos").exists()
    
    @pytest.mark.asyncio
    async def test_creates_daily_log(self, provisioner, sample_tenant, temp_workspace):
        """Provisioning creates initial daily log."""
        await provisioner.provision_workspace(sample_tenant)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        today = datetime.utcnow().strftime("%Y-%m-%d")
        assert (workspace / "memory" / f"{today}.md").exists()
    
    @pytest.mark.asyncio
    async def test_returns_summary(self, provisioner, sample_tenant):
        """Provisioning returns summary dict."""
        result = await provisioner.provision_workspace(sample_tenant)
        
        assert "workspace_path" in result
        assert "created_files" in result
        assert "agents_count" in result
        assert result["agents_count"] == 2  # Pro tier
    
    @pytest.mark.asyncio
    async def test_custom_config(self, provisioner, sample_tenant, temp_workspace):
        """Provisioning with custom config."""
        config = WorkspaceConfig(
            shipos_enabled=True,
            agents=[
                AgentConfig(id="ceo", name="CEO", role=AgentRole.CEO, is_default=True),
                AgentConfig(id="cto", name="CTO", role=AgentRole.CTO),
            ]
        )
        result = await provisioner.provision_workspace(sample_tenant, config)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        assert (workspace / "agents" / "ceo" / "SOUL.md").exists()
        assert (workspace / "agents" / "cto" / "SOUL.md").exists()
        assert result["agents_count"] == 2


class TestAddAgent:
    """Test adding agents to existing workspace."""
    
    @pytest.mark.asyncio
    async def test_add_agent_to_workspace(self, provisioner, sample_tenant, temp_workspace):
        """Add new agent to existing workspace."""
        # First provision
        await provisioner.provision_workspace(sample_tenant)
        
        # Add new agent
        new_agent = AgentConfig(
            id="developer",
            name="Developer",
            role=AgentRole.DEVELOPER,
        )
        result = await provisioner.add_agent(sample_tenant, new_agent)
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        assert (workspace / "agents" / "developer" / "SOUL.md").exists()
        assert result["agent_id"] == "developer"
    
    @pytest.mark.asyncio
    async def test_add_agent_fails_if_exists(self, provisioner, sample_tenant, temp_workspace):
        """Adding duplicate agent fails."""
        await provisioner.provision_workspace(sample_tenant)
        
        # Try to add main again
        duplicate = AgentConfig(id="main", name="Main", role=AgentRole.ASSISTANT)
        with pytest.raises(ValueError, match="already exists"):
            await provisioner.add_agent(sample_tenant, duplicate)
    
    @pytest.mark.asyncio
    async def test_add_agent_fails_if_no_workspace(self, provisioner, sample_tenant):
        """Adding agent to non-existent workspace fails."""
        agent = AgentConfig(id="test", name="Test", role=AgentRole.ASSISTANT)
        with pytest.raises(ValueError, match="does not exist"):
            await provisioner.add_agent(sample_tenant, agent)


class TestRemoveAgent:
    """Test removing agents from workspace."""
    
    @pytest.mark.asyncio
    async def test_remove_agent(self, provisioner, sample_tenant, temp_workspace):
        """Remove agent archives it."""
        await provisioner.provision_workspace(sample_tenant)
        
        result = await provisioner.remove_agent(sample_tenant, "analyst")
        
        workspace = Path(temp_workspace) / sample_tenant.subdomain
        assert result == True
        assert not (workspace / "agents" / "analyst").exists()
        assert (workspace / "agents" / ".archived").exists()
    
    @pytest.mark.asyncio
    async def test_remove_nonexistent_agent(self, provisioner, sample_tenant, temp_workspace):
        """Removing non-existent agent returns False."""
        await provisioner.provision_workspace(sample_tenant)
        
        result = await provisioner.remove_agent(sample_tenant, "nonexistent")
        assert result == False


class TestListAgents:
    """Test listing agents in workspace."""
    
    @pytest.mark.asyncio
    async def test_list_agents(self, provisioner, sample_tenant, temp_workspace):
        """List agents returns all agents."""
        await provisioner.provision_workspace(sample_tenant)
        
        agents = await provisioner.list_agents(sample_tenant)
        
        assert len(agents) == 2  # Pro tier: main + analyst
        agent_ids = [a["id"] for a in agents]
        assert "main" in agent_ids
        assert "analyst" in agent_ids
    
    @pytest.mark.asyncio
    async def test_list_agents_includes_metadata(self, provisioner, sample_tenant, temp_workspace):
        """List agents includes metadata."""
        await provisioner.provision_workspace(sample_tenant)
        
        agents = await provisioner.list_agents(sample_tenant)
        
        for agent in agents:
            assert "id" in agent
            assert "path" in agent
            assert "has_soul" in agent
            assert "has_memory" in agent
            assert agent["has_soul"] == True
    
    @pytest.mark.asyncio
    async def test_list_agents_empty_workspace(self, provisioner, sample_tenant):
        """List agents on non-existent workspace returns empty."""
        agents = await provisioner.list_agents(sample_tenant)
        assert agents == []
