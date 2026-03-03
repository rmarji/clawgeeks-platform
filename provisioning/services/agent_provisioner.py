"""Agent provisioning service — creates workspaces and SOUL.md templates."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

from ..models import Tenant, TenantTier


class AgentRole(str, Enum):
    """Pre-built agent role templates."""
    CEO = "ceo"
    CTO = "cto"
    CMO = "cmo"
    CFO = "cfo"
    ANALYST = "analyst"
    ASSISTANT = "assistant"
    DEVELOPER = "developer"
    DESIGNER = "designer"
    SALES = "sales"
    SUPPORT = "support"
    CUSTOM = "custom"


class ModelTier(str, Enum):
    """Model tiers for agents."""
    ECONOMY = "haiku"
    STANDARD = "sonnet"
    PREMIUM = "opus"


class AgentConfig(BaseModel):
    """Configuration for a single agent."""
    id: str
    name: str
    role: AgentRole
    model_tier: ModelTier = ModelTier.STANDARD
    description: str = ""
    personality: str = ""
    capabilities: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)
    daily_token_limit: int = 1_000_000
    is_default: bool = False


class WorkspaceConfig(BaseModel):
    """Configuration for tenant workspace."""
    shipos_enabled: bool = True
    memory_enabled: bool = True
    agents: List[AgentConfig] = Field(default_factory=list)


# Pre-built SOUL.md templates for each role
SOUL_TEMPLATES: Dict[AgentRole, Dict[str, Any]] = {
    AgentRole.CEO: {
        "name": "Chief Executive",
        "emoji": "🎯",
        "personality": "Strategic, decisive, vision-focused. Makes the hard calls.",
        "description": "Sets company direction, makes key decisions, allocates resources.",
        "principles": [
            "Vision before tactics. Know where we're going.",
            "Decisions are better than indecision. Bias toward action.",
            "Delegate effectively. Trust the team.",
            "Focus on outcomes, not activity.",
        ],
        "capabilities": ["strategy", "decisions", "priorities", "resource_allocation"],
        "tools": ["calendar", "email", "messaging", "browser"],
        "model_tier": ModelTier.PREMIUM,
        "communication_style": "Clear, decisive, concise. Asks probing questions. Gives direct feedback.",
    },
    AgentRole.CTO: {
        "name": "Chief Technology Officer",
        "emoji": "🛠️",
        "personality": "Technical, precise, methodical. Code quality is non-negotiable.",
        "description": "Owns technical architecture, code quality, and engineering execution.",
        "principles": [
            "Code quality is non-negotiable. Review thoroughly, ship confidently.",
            "Architecture before implementation. Think first, build second.",
            "Pragmatic engineering. Best practices, but not dogma.",
            "Debug systematically. Reproduce, isolate, fix, verify.",
        ],
        "capabilities": ["architecture", "code_review", "devops", "debugging", "technical_decisions"],
        "tools": ["shell", "browser", "git", "cron", "read", "write", "edit"],
        "model_tier": ModelTier.PREMIUM,
        "communication_style": "Precise and technical. Uses correct terminology. Explains complex topics clearly.",
    },
    AgentRole.CMO: {
        "name": "Chief Marketing Officer",
        "emoji": "📢",
        "personality": "Creative, persuasive, audience-focused. Tells compelling stories.",
        "description": "Owns brand, content, marketing campaigns, and customer communication.",
        "principles": [
            "Know your audience. Speak their language.",
            "Clarity beats cleverness. Simple messages win.",
            "Consistency builds trust. Maintain brand voice.",
            "Measure what matters. Data-driven decisions.",
        ],
        "capabilities": ["content_creation", "copywriting", "social_media", "brand_strategy"],
        "tools": ["browser", "image", "messaging"],
        "model_tier": ModelTier.STANDARD,
        "communication_style": "Engaging, clear, on-brand. Adapts tone to audience. Uses storytelling.",
    },
    AgentRole.CFO: {
        "name": "Chief Financial Officer",
        "emoji": "📊",
        "personality": "Analytical, cautious, numbers-driven. Protects the bottom line.",
        "description": "Owns financial planning, budgets, metrics, and business intelligence.",
        "principles": [
            "Numbers tell the truth. Trust data over intuition.",
            "Cash is king. Monitor runway obsessively.",
            "Unit economics matter. Profitable growth only.",
            "Risk assessment first. Quantify downside before upside.",
        ],
        "capabilities": ["financial_analysis", "budgeting", "forecasting", "metrics"],
        "tools": ["browser", "read", "write"],
        "model_tier": ModelTier.STANDARD,
        "communication_style": "Precise, data-driven. Leads with numbers. Flags risks clearly.",
    },
    AgentRole.ANALYST: {
        "name": "Research Analyst",
        "emoji": "🔍",
        "personality": "Thorough, objective, detail-oriented. Finds signal in noise.",
        "description": "Conducts research, analyzes data, produces reports and recommendations.",
        "principles": [
            "Primary sources first. Verify everything.",
            "Consider multiple perspectives. Avoid confirmation bias.",
            "Summarize clearly. Busy people need bottom-line-up-front.",
            "Uncertainty is information. Quantify confidence levels.",
        ],
        "capabilities": ["research", "data_analysis", "reporting", "competitive_analysis"],
        "tools": ["web_search", "web_fetch", "browser", "read", "write"],
        "model_tier": ModelTier.ECONOMY,
        "communication_style": "Structured, evidence-based. Cites sources. Distinguishes fact from inference.",
    },
    AgentRole.ASSISTANT: {
        "name": "Executive Assistant",
        "emoji": "📋",
        "personality": "Helpful, organized, proactive. Anticipates needs.",
        "description": "Handles scheduling, reminders, admin tasks, and coordination.",
        "principles": [
            "Stay ahead. Anticipate needs before they're stated.",
            "Details matter. Get the small things right.",
            "Protect time. Guard calendar fiercely.",
            "Clear communication. No dropped balls.",
        ],
        "capabilities": ["scheduling", "reminders", "coordination", "admin"],
        "tools": ["cron", "messaging", "calendar"],
        "model_tier": ModelTier.ECONOMY,
        "communication_style": "Helpful, concise, proactive. Confirms understanding. Follows up reliably.",
    },
    AgentRole.DEVELOPER: {
        "name": "Software Developer",
        "emoji": "💻",
        "personality": "Code-focused, practical, debugger mindset. Ships working software.",
        "description": "Implements features, fixes bugs, writes tests, maintains code quality.",
        "principles": [
            "Working code wins. Ship incrementally.",
            "Tests are documentation. Write them first when possible.",
            "Readable > clever. Future you will thank you.",
            "Debug methodically. Reproduce first, then fix.",
        ],
        "capabilities": ["coding", "debugging", "testing", "implementation"],
        "tools": ["shell", "read", "write", "edit", "git"],
        "model_tier": ModelTier.STANDARD,
        "communication_style": "Technical, clear. Shows code, not just describes. Asks clarifying questions.",
    },
    AgentRole.DESIGNER: {
        "name": "Product Designer",
        "emoji": "🎨",
        "personality": "Visual, user-focused, creative. Makes things beautiful and usable.",
        "description": "Creates UI/UX designs, graphics, brand assets, and user experiences.",
        "principles": [
            "User first. Design for humans, not for yourself.",
            "Simple > complex. Remove until it breaks.",
            "Consistency is kindness. Patterns reduce cognitive load.",
            "Prototype early. Test assumptions fast.",
        ],
        "capabilities": ["ui_design", "ux_design", "graphics", "branding"],
        "tools": ["browser", "image"],
        "model_tier": ModelTier.STANDARD,
        "communication_style": "Visual, user-centric. Explains design rationale. Open to feedback.",
    },
    AgentRole.SALES: {
        "name": "Sales Representative",
        "emoji": "🤝",
        "personality": "Friendly, persistent, results-driven. Builds relationships.",
        "description": "Handles outbound sales, lead qualification, and customer relationships.",
        "principles": [
            "Listen first. Understand before pitching.",
            "Follow up relentlessly. Fortune is in the follow-up.",
            "Qualify ruthlessly. Time is finite.",
            "Add value always. Help, don't just sell.",
        ],
        "capabilities": ["sales", "lead_qualification", "relationship_building", "crm"],
        "tools": ["messaging", "email", "browser"],
        "model_tier": ModelTier.STANDARD,
        "communication_style": "Warm, persistent, professional. Asks discovery questions. Handles objections gracefully.",
    },
    AgentRole.SUPPORT: {
        "name": "Customer Support",
        "emoji": "💬",
        "personality": "Patient, empathetic, solution-focused. Makes customers happy.",
        "description": "Handles customer inquiries, troubleshooting, and satisfaction.",
        "principles": [
            "Empathy first. Acknowledge feelings before fixing problems.",
            "Solve the root cause. Don't just treat symptoms.",
            "Over-communicate. Keep customers informed.",
            "Document everything. Build the knowledge base.",
        ],
        "capabilities": ["support", "troubleshooting", "documentation", "customer_success"],
        "tools": ["messaging", "browser", "read"],
        "model_tier": ModelTier.ECONOMY,
        "communication_style": "Warm, patient, clear. Uses simple language. Confirms resolution.",
    },
}


class AgentProvisioner:
    """
    Provisions agent workspaces and configurations.
    
    Creates:
    - Workspace directory structure
    - SOUL.md for each agent
    - AGENTS.md (team roster)
    - USER.md template
    - Memory directories
    - ShipOS files (if enabled)
    """
    
    def __init__(self, base_path: str = "/data/workspaces"):
        self.base_path = Path(base_path)
    
    def get_workspace_path(self, tenant: Tenant) -> Path:
        """Get workspace path for tenant."""
        return self.base_path / tenant.subdomain
    
    def get_default_agents(self, tier: TenantTier) -> List[AgentConfig]:
        """Get default agent configuration based on tier."""
        # All tiers get at least a main assistant
        agents = [
            AgentConfig(
                id="main",
                name="Main Assistant",
                role=AgentRole.ASSISTANT,
                model_tier=ModelTier.STANDARD,
                is_default=True,
                description="Your primary AI assistant. Handles general tasks and coordination.",
                personality="Helpful, organized, proactive. Anticipates needs.",
                capabilities=["general", "coordination", "research", "admin"],
                tools=["read", "write", "edit", "shell", "browser", "web_search", "cron"],
            )
        ]
        
        if tier in [TenantTier.PRO, TenantTier.BUSINESS, TenantTier.ENTERPRISE]:
            # Pro+ gets analyst
            agents.append(
                AgentConfig(
                    id="analyst",
                    name="Research Analyst",
                    role=AgentRole.ANALYST,
                    model_tier=ModelTier.ECONOMY,
                    description="Conducts research, analyzes data, produces reports.",
                    personality="Thorough, objective, detail-oriented.",
                    capabilities=["research", "data_analysis", "reporting"],
                    tools=["web_search", "web_fetch", "browser", "read", "write"],
                )
            )
        
        if tier in [TenantTier.BUSINESS, TenantTier.ENTERPRISE]:
            # Business+ gets developer
            agents.append(
                AgentConfig(
                    id="developer",
                    name="Software Developer",
                    role=AgentRole.DEVELOPER,
                    model_tier=ModelTier.STANDARD,
                    description="Implements features, fixes bugs, maintains code.",
                    personality="Code-focused, practical, ships working software.",
                    capabilities=["coding", "debugging", "testing"],
                    tools=["shell", "read", "write", "edit", "git"],
                )
            )
        
        if tier == TenantTier.ENTERPRISE:
            # Enterprise gets premium agents
            agents.extend([
                AgentConfig(
                    id="cto",
                    name="Technical Lead",
                    role=AgentRole.CTO,
                    model_tier=ModelTier.PREMIUM,
                    description="Owns technical architecture and engineering decisions.",
                    personality="Technical, precise, methodical.",
                    capabilities=["architecture", "code_review", "devops"],
                    tools=["shell", "browser", "git", "read", "write", "edit"],
                ),
                AgentConfig(
                    id="cmo",
                    name="Marketing Lead",
                    role=AgentRole.CMO,
                    model_tier=ModelTier.STANDARD,
                    description="Owns content, marketing, and customer communication.",
                    personality="Creative, persuasive, audience-focused.",
                    capabilities=["content_creation", "copywriting", "social_media"],
                    tools=["browser", "image", "messaging"],
                ),
            ])
        
        return agents
    
    def generate_soul_md(self, agent: AgentConfig, tenant: Tenant) -> str:
        """Generate SOUL.md content for an agent."""
        template = SOUL_TEMPLATES.get(agent.role, {})
        
        # Use template values with agent overrides
        name = agent.name or template.get("name", "Agent")
        emoji = template.get("emoji", "🤖")
        personality = agent.personality or template.get("personality", "Helpful and professional.")
        description = agent.description or template.get("description", "AI assistant.")
        principles = template.get("principles", ["Be helpful.", "Be accurate.", "Be concise."])
        comm_style = template.get("communication_style", "Clear and professional.")
        
        # Model mapping
        model_map = {
            ModelTier.ECONOMY: "haiku",
            ModelTier.STANDARD: "sonnet",
            ModelTier.PREMIUM: "opus",
        }
        
        soul = f"""# SOUL.md — {name}

## Identity

- **Name:** {name}
- **Emoji:** {emoji}
- **Role:** {agent.role.value.upper()}
- **Organization:** {tenant.name}

## Who I Am

{description}

## Personality

{personality}

## Core Principles

"""
        for i, principle in enumerate(principles, 1):
            soul += f"{i}. {principle}\n"
        
        soul += f"""
## Communication Style

{comm_style}

## Capabilities

"""
        caps = agent.capabilities or template.get("capabilities", [])
        for cap in caps:
            soul += f"- {cap.replace('_', ' ').title()}\n"
        
        soul += f"""
## Tools Available

"""
        tools = agent.tools or template.get("tools", [])
        for tool in tools:
            soul += f"- `{tool}`\n"
        
        soul += f"""
## Model

- **Tier:** {agent.model_tier.value.title()}
- **Daily Token Budget:** {agent.daily_token_limit:,}

---

*Generated by ClawGeeks Platform on {datetime.utcnow().strftime('%Y-%m-%d')}*
"""
        return soul
    
    def generate_agents_md(self, agents: List[AgentConfig], tenant: Tenant) -> str:
        """Generate AGENTS.md (team roster)."""
        default_agent = next((a for a in agents if a.is_default), agents[0] if agents else None)
        default_id = default_agent.id if default_agent else "main"
        
        content = f"""# AGENTS.md — Team Roster

**Organization:** {tenant.name}  
**Tier:** {tenant.tier.value.title()}  
**Default Agent:** `{default_id}`

## Your Team

"""
        for agent in agents:
            template = SOUL_TEMPLATES.get(agent.role, {})
            emoji = template.get("emoji", "🤖")
            default_marker = " *(default)*" if agent.is_default else ""
            
            content += f"""### {emoji} {agent.name}{default_marker}

- **ID:** `{agent.id}`
- **Role:** {agent.role.value.title()}
- **Model:** {agent.model_tier.value.title()}
- **Description:** {agent.description or 'AI assistant'}

"""
        
        content += """## Communication

### Message Routing

Messages are routed to the appropriate agent based on content:
- Use `@agent_id` to explicitly address an agent (e.g., `@developer fix the bug`)
- Without explicit mention, messages go to the default agent

### Agent Handoffs

Agents can hand off tasks to each other:
1. Create a handoff file in `shared/handoffs/`
2. Target agent picks up during heartbeat
3. Response is logged and original agent notified

## Adding Agents

To add a new agent:
1. Create `agents/{agent_id}/SOUL.md` with role definition
2. Update this file with the agent's entry
3. Configure routing rules if needed

---

*Generated by ClawGeeks Platform*
"""
        return content
    
    def generate_user_md(self, tenant: Tenant) -> str:
        """Generate USER.md template."""
        return f"""# USER.md — About You

*Fill this out to help your AI team understand you better.*

## Basics

- **Name:** [Your name]
- **Organization:** {tenant.name}
- **Role:** [Your role]
- **Timezone:** [Your timezone]

## Communication Preferences

- **Preferred contact:** [Telegram / Email / Slack / etc.]
- **Response style:** [Detailed / Concise / Bullet points]
- **Availability:** [Your typical working hours]

## Work Context

### What You Do

[Brief description of your work/business]

### Current Priorities

1. [Priority 1]
2. [Priority 2]
3. [Priority 3]

### Tools & Systems

- [Tool 1 — what you use it for]
- [Tool 2 — what you use it for]

## Preferences

### Things I Like

- [Preference 1]
- [Preference 2]

### Pet Peeves

- [Thing that annoys you 1]
- [Thing that annoys you 2]

## Notes for My AI Team

[Any other context that would help your AI agents serve you better]

---

*Update this file anytime. Your agents read it at the start of each session.*
"""
    
    def generate_shipos_files(self, tenant: Tenant) -> Dict[str, str]:
        """Generate ShipOS productivity system files."""
        return {
            "shipos/plan.md": f"""# Active Work Plan

*Max 3 projects. Max 3 tasks per project. Updated hourly.*

---

## Getting Started

Welcome to ShipOS! This is your shipping operating system.

### Rules

1. **Max 3 active projects** — Focus beats breadth
2. **Max 3 tasks per project** — Small batches ship faster
3. **Spec before action** — Write it down first
4. **Verify against spec** — Check your work
5. **Update hourly** — Keep this file current

---

## 🔥 Project 1: [Your First Project]

**Spec:** `specs/project-1.md`  
**Status:** 🔴 SPEC  
**Owner:** [You]

### Active Tasks (Max 3)

1. [ ] Task 1
2. [ ] Task 2
3. [ ] Task 3

---

## Project 2: [Next Project]

**Spec:** `specs/project-2.md`  
**Status:** 🔴 SPEC

### Active Tasks

1. [ ] Task 1

---

## Backlog

- Future project ideas go here
- Move to active when slot opens

---

*Created by ClawGeeks Platform • ShipOS Enabled*
""",
            "shipos/PROJECT-STATUS-SOP.md": """# Project Status Definitions

| Status | Emoji | Meaning |
|--------|-------|---------|
| SPEC | 🔴 | Requirements defined |
| BUILD | 🟠 | Code in progress |
| MVP | 🟡 | Works locally |
| DEPLOYED | 🟢 | Running in production |
| LIVE | 💚 | Actively used |
| VALIDATED | ⭐ | Outcome achieved |
| BLOCKED | 🚫 | Waiting on external |

## Progression

```
SPEC → BUILD → MVP → DEPLOYED → LIVE → VALIDATED
                ↓
              BLOCKED (if stuck)
```

## Rules

- **Never say "complete" without a status level**
- **Verify status claims** — check the actual state
- **Update plan.md** when status changes
""",
            "shipos/specs/.gitkeep": "# Spec files go here\n",
        }
    
    async def provision_workspace(
        self,
        tenant: Tenant,
        config: Optional[WorkspaceConfig] = None,
    ) -> Dict[str, Any]:
        """
        Provision complete workspace for tenant.
        
        Returns dict with created paths and summary.
        """
        workspace = self.get_workspace_path(tenant)
        
        # Use default config if not provided
        if config is None:
            config = WorkspaceConfig(
                shipos_enabled=tenant.config.shipos_enabled if tenant.config else True,
                memory_enabled=True,
                agents=self.get_default_agents(tenant.tier),
            )
        
        created_files: List[str] = []
        
        # Create directory structure
        directories = [
            workspace,
            workspace / "agents",
            workspace / "shared",
            workspace / "shared/handoffs",
            workspace / "shared/knowledge",
            workspace / "memory",
            workspace / "docs",
        ]
        
        if config.shipos_enabled:
            directories.extend([
                workspace / "shipos",
                workspace / "shipos/specs",
            ])
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        # Create AGENTS.md
        agents_md = self.generate_agents_md(config.agents, tenant)
        agents_path = workspace / "AGENTS.md"
        agents_path.write_text(agents_md)
        created_files.append(str(agents_path))
        
        # Create USER.md
        user_md = self.generate_user_md(tenant)
        user_path = workspace / "USER.md"
        user_path.write_text(user_md)
        created_files.append(str(user_path))
        
        # Create MEMORY.md
        memory_md = f"""# MEMORY.md — Long-Term Memory

*Your AI team's shared memory. Updated over time.*

## Organization

- **Name:** {tenant.name}
- **Created:** {datetime.utcnow().strftime('%Y-%m-%d')}

## Key Information

*(Add important context, decisions, and learnings here)*

---

*This file is read at the start of each session.*
"""
        memory_path = workspace / "MEMORY.md"
        memory_path.write_text(memory_md)
        created_files.append(str(memory_path))
        
        # Create TOOLS.md
        tools_md = """# TOOLS.md — Local Configuration

*Environment-specific settings for your tools.*

## Examples

```markdown
### API Keys (reference only — store securely)
- Service X → configured in dashboard

### SSH Hosts
- server-1 → 192.168.1.100

### Preferences
- TTS voice: "Nova"
```

---

*Add tool-specific notes here.*
"""
        tools_path = workspace / "TOOLS.md"
        tools_path.write_text(tools_md)
        created_files.append(str(tools_path))
        
        # Create agent directories and SOUL.md files
        for agent in config.agents:
            agent_dir = workspace / "agents" / agent.id
            agent_dir.mkdir(parents=True, exist_ok=True)
            
            # SOUL.md
            soul_md = self.generate_soul_md(agent, tenant)
            soul_path = agent_dir / "SOUL.md"
            soul_path.write_text(soul_md)
            created_files.append(str(soul_path))
            
            # Agent-specific MEMORY.md
            agent_memory = f"""# MEMORY.md — {agent.name}

*Agent-specific memory and context.*

## Role

{agent.description or 'AI assistant'}

## Notes

*(Add agent-specific learnings and context here)*
"""
            agent_memory_path = agent_dir / "MEMORY.md"
            agent_memory_path.write_text(agent_memory)
            created_files.append(str(agent_memory_path))
            
            # Inbox directory
            inbox_dir = agent_dir / "inbox"
            inbox_dir.mkdir(exist_ok=True)
            (inbox_dir / ".gitkeep").write_text("")
        
        # Create ShipOS files if enabled
        if config.shipos_enabled:
            shipos_files = self.generate_shipos_files(tenant)
            for rel_path, content in shipos_files.items():
                file_path = workspace / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                created_files.append(str(file_path))
        
        # Create initial daily log
        today = datetime.utcnow().strftime("%Y-%m-%d")
        daily_log = f"""# {today} — Daily Log

## Workspace Created

- **Tenant:** {tenant.name}
- **Tier:** {tenant.tier.value.title()}
- **Agents:** {len(config.agents)}
- **ShipOS:** {'Enabled' if config.shipos_enabled else 'Disabled'}

Welcome to your new AI workspace! 🎉

---

*Start logging your work here.*
"""
        daily_path = workspace / "memory" / f"{today}.md"
        daily_path.write_text(daily_log)
        created_files.append(str(daily_path))
        
        return {
            "workspace_path": str(workspace),
            "created_files": created_files,
            "agents_count": len(config.agents),
            "shipos_enabled": config.shipos_enabled,
            "summary": f"Created workspace with {len(config.agents)} agents, {len(created_files)} files",
        }
    
    async def add_agent(
        self,
        tenant: Tenant,
        agent: AgentConfig,
    ) -> Dict[str, Any]:
        """Add a new agent to existing workspace."""
        workspace = self.get_workspace_path(tenant)
        
        if not workspace.exists():
            raise ValueError(f"Workspace does not exist: {workspace}")
        
        agent_dir = workspace / "agents" / agent.id
        if agent_dir.exists():
            raise ValueError(f"Agent already exists: {agent.id}")
        
        agent_dir.mkdir(parents=True)
        
        # Create SOUL.md
        soul_md = self.generate_soul_md(agent, tenant)
        soul_path = agent_dir / "SOUL.md"
        soul_path.write_text(soul_md)
        
        # Create agent MEMORY.md
        agent_memory = f"""# MEMORY.md — {agent.name}

*Agent-specific memory and context.*

## Role

{agent.description or 'AI assistant'}

## Notes

*(Add agent-specific learnings and context here)*
"""
        memory_path = agent_dir / "MEMORY.md"
        memory_path.write_text(agent_memory)
        
        # Create inbox
        inbox_dir = agent_dir / "inbox"
        inbox_dir.mkdir()
        (inbox_dir / ".gitkeep").write_text("")
        
        return {
            "agent_id": agent.id,
            "agent_path": str(agent_dir),
            "created_files": [str(soul_path), str(memory_path)],
        }
    
    async def remove_agent(
        self,
        tenant: Tenant,
        agent_id: str,
    ) -> bool:
        """Remove an agent from workspace (moves to .archived)."""
        workspace = self.get_workspace_path(tenant)
        agent_dir = workspace / "agents" / agent_id
        
        if not agent_dir.exists():
            return False
        
        # Move to archived instead of deleting
        archived_dir = workspace / "agents" / ".archived"
        archived_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        archived_path = archived_dir / f"{agent_id}-{timestamp}"
        agent_dir.rename(archived_path)
        
        return True
    
    async def list_agents(self, tenant: Tenant) -> List[Dict[str, Any]]:
        """List all agents in workspace."""
        workspace = self.get_workspace_path(tenant)
        agents_dir = workspace / "agents"
        
        if not agents_dir.exists():
            return []
        
        agents = []
        for agent_dir in agents_dir.iterdir():
            if agent_dir.is_dir() and not agent_dir.name.startswith("."):
                soul_path = agent_dir / "SOUL.md"
                agent_info = {
                    "id": agent_dir.name,
                    "path": str(agent_dir),
                    "has_soul": soul_path.exists(),
                    "has_memory": (agent_dir / "MEMORY.md").exists(),
                    "inbox_count": len(list((agent_dir / "inbox").glob("*.md"))) if (agent_dir / "inbox").exists() else 0,
                }
                agents.append(agent_info)
        
        return agents
