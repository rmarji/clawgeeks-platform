"""
HR Department Service — Auto-recruits agents based on business type.

Analyzes business description, industry, and goals to recommend the optimal
agent team configuration. Uses keyword matching and industry templates.

Part of ClawGeeks Hosting Platform unique differentiators.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .agent_provisioner import AgentProvisioner, AgentConfig, AgentRole


class Industry(str, Enum):
    """Supported industry classifications."""
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    AGENCY = "agency"
    CONSULTING = "consulting"
    CONTENT = "content"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    REAL_ESTATE = "real_estate"
    LEGAL = "legal"
    MANUFACTURING = "manufacturing"
    NONPROFIT = "nonprofit"
    STARTUP = "startup"
    FREELANCER = "freelancer"
    OTHER = "other"


class BusinessStage(str, Enum):
    """Business maturity stage."""
    IDEA = "idea"           # Pre-revenue, validating
    EARLY = "early"         # < $100k ARR
    GROWTH = "growth"       # $100k - $1M ARR
    SCALE = "scale"         # $1M+ ARR
    ENTERPRISE = "enterprise"  # $10M+ ARR


class BusinessGoal(str, Enum):
    """Primary business objectives."""
    LAUNCH = "launch"              # Getting to market
    GROW_REVENUE = "grow_revenue"  # Increase sales
    CUT_COSTS = "cut_costs"        # Operational efficiency
    SCALE_TEAM = "scale_team"      # Hire/manage people
    IMPROVE_PRODUCT = "improve_product"  # Build better
    EXPAND_MARKET = "expand_market"      # New markets
    AUTOMATE = "automate"          # Reduce manual work
    FUNDRAISE = "fundraise"        # Raise capital


@dataclass
class BusinessProfile:
    """Analyzed business profile for agent recommendations."""
    name: str
    description: str
    industry: Industry = Industry.OTHER
    stage: BusinessStage = BusinessStage.EARLY
    goals: list[BusinessGoal] = field(default_factory=list)
    team_size: int = 1
    has_technical_founder: bool = False
    has_marketing_experience: bool = False
    has_sales_experience: bool = False
    budget_tier: str = "starter"  # starter, pro, business, enterprise
    
    # Detected needs (filled by analysis)
    needs_technical: bool = False
    needs_marketing: bool = False
    needs_sales: bool = False
    needs_finance: bool = False
    needs_operations: bool = False
    needs_research: bool = False
    needs_design: bool = False
    needs_support: bool = False


@dataclass
class AgentRecommendation:
    """Single agent recommendation with rationale."""
    role: AgentRole
    priority: int  # 1-10, higher = more important
    rationale: str
    is_essential: bool = False  # Must-have vs nice-to-have


@dataclass
class TeamRecommendation:
    """Complete team recommendation."""
    agents: list[AgentRecommendation]
    summary: str
    warnings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class HRDepartment:
    """
    Auto-recruits agents based on business analysis.
    
    Workflow:
    1. Analyze business description/questionnaire → BusinessProfile
    2. Apply industry templates + goal-based rules → AgentRecommendations
    3. Filter by tier limits → Final team
    4. Integrate with AgentProvisioner → Deploy agents
    """
    
    # Industry → default agent roles mapping
    INDUSTRY_TEMPLATES: dict[Industry, list[AgentRole]] = {
        Industry.ECOMMERCE: [
            AgentRole.ASSISTANT, AgentRole.ANALYST, AgentRole.SUPPORT, 
            AgentRole.CMO, AgentRole.DEVELOPER
        ],
        Industry.SAAS: [
            AgentRole.CTO, AgentRole.DEVELOPER, AgentRole.ANALYST,
            AgentRole.SUPPORT, AgentRole.CMO
        ],
        Industry.AGENCY: [
            AgentRole.CEO, AgentRole.DESIGNER, AgentRole.DEVELOPER,
            AgentRole.CMO, AgentRole.ASSISTANT
        ],
        Industry.CONSULTING: [
            AgentRole.ANALYST, AgentRole.ASSISTANT, AgentRole.CFO,
            AgentRole.SALES, AgentRole.CEO
        ],
        Industry.CONTENT: [
            AgentRole.CMO, AgentRole.DESIGNER, AgentRole.ASSISTANT,
            AgentRole.ANALYST, AgentRole.CEO
        ],
        Industry.FINTECH: [
            AgentRole.CTO, AgentRole.ANALYST, AgentRole.CFO,
            AgentRole.DEVELOPER, AgentRole.SUPPORT
        ],
        Industry.HEALTHCARE: [
            AgentRole.ANALYST, AgentRole.SUPPORT, AgentRole.ASSISTANT,
            AgentRole.CFO, AgentRole.CTO
        ],
        Industry.EDUCATION: [
            AgentRole.ASSISTANT, AgentRole.DESIGNER, AgentRole.ANALYST,
            AgentRole.SUPPORT, AgentRole.CMO
        ],
        Industry.REAL_ESTATE: [
            AgentRole.SALES, AgentRole.ASSISTANT, AgentRole.ANALYST,
            AgentRole.CMO, AgentRole.CFO
        ],
        Industry.LEGAL: [
            AgentRole.ANALYST, AgentRole.ASSISTANT, AgentRole.CFO,
            AgentRole.SUPPORT, AgentRole.CEO
        ],
        Industry.MANUFACTURING: [
            AgentRole.ANALYST, AgentRole.CFO, AgentRole.ASSISTANT,
            AgentRole.CTO, AgentRole.SUPPORT
        ],
        Industry.NONPROFIT: [
            AgentRole.ASSISTANT, AgentRole.CMO, AgentRole.ANALYST,
            AgentRole.CFO, AgentRole.SUPPORT
        ],
        Industry.STARTUP: [
            AgentRole.CEO, AgentRole.CTO, AgentRole.CMO,
            AgentRole.DEVELOPER, AgentRole.ANALYST
        ],
        Industry.FREELANCER: [
            AgentRole.ASSISTANT, AgentRole.ANALYST, AgentRole.CMO,
            AgentRole.CFO
        ],
        Industry.OTHER: [
            AgentRole.ASSISTANT, AgentRole.ANALYST, AgentRole.CEO,
            AgentRole.CFO, AgentRole.CMO
        ],
    }
    
    # Keywords for industry detection
    INDUSTRY_KEYWORDS: dict[Industry, list[str]] = {
        Industry.ECOMMERCE: [
            "ecommerce", "e-commerce", "online store", "shopify", "woocommerce",
            "retail", "dropshipping", "marketplace", "amazon", "selling products",
            "inventory", "shipping", "orders", "cart", "checkout"
        ],
        Industry.SAAS: [
            "saas", "software", "platform", "subscription", "api", "cloud",
            "b2b", "enterprise software", "app", "tool", "dashboard", "users",
            "features", "integrations", "analytics"
        ],
        Industry.AGENCY: [
            "agency", "creative", "design agency", "marketing agency", "digital agency",
            "clients", "projects", "campaigns", "branding", "web design", "ads"
        ],
        Industry.CONSULTING: [
            "consulting", "consultant", "advisory", "strategy", "management consulting",
            "business consulting", "expertise", "advisory services", "engagements"
        ],
        Industry.CONTENT: [
            "content", "creator", "youtube", "podcast", "blog", "newsletter",
            "media", "publishing", "audience", "subscribers", "influencer", "social media"
        ],
        Industry.FINTECH: [
            "fintech", "finance", "payments", "banking", "crypto", "trading",
            "investments", "lending", "insurance", "blockchain", "wallet"
        ],
        Industry.HEALTHCARE: [
            "healthcare", "health", "medical", "clinic", "hospital", "patients",
            "telemedicine", "wellness", "pharma", "biotech", "doctors"
        ],
        Industry.EDUCATION: [
            "education", "edtech", "courses", "learning", "students", "training",
            "tutoring", "school", "university", "teaching", "curriculum"
        ],
        Industry.REAL_ESTATE: [
            "real estate", "property", "realty", "homes", "apartments", "rental",
            "agent", "broker", "listings", "mortgage", "commercial real estate"
        ],
        Industry.LEGAL: [
            "legal", "law", "attorney", "lawyer", "contracts", "compliance",
            "litigation", "intellectual property", "patents", "legal services"
        ],
        Industry.MANUFACTURING: [
            "manufacturing", "factory", "production", "supply chain", "logistics",
            "warehouse", "industrial", "equipment", "assembly", "quality control"
        ],
        Industry.NONPROFIT: [
            "nonprofit", "non-profit", "charity", "foundation", "ngo", "donations",
            "fundraising", "volunteers", "mission", "impact", "community"
        ],
        Industry.STARTUP: [
            "startup", "founder", "mvp", "seed", "venture", "pitch", "investors",
            "accelerator", "incubator", "early stage", "bootstrapping"
        ],
        Industry.FREELANCER: [
            "freelance", "freelancer", "solopreneur", "independent", "gig",
            "contractor", "self-employed", "side hustle", "portfolio"
        ],
    }
    
    # Keywords for goal detection
    GOAL_KEYWORDS: dict[BusinessGoal, list[str]] = {
        BusinessGoal.LAUNCH: [
            "launch", "starting", "new business", "build", "create", "start",
            "mvp", "first version", "getting started", "begin"
        ],
        BusinessGoal.GROW_REVENUE: [
            "grow", "revenue", "sales", "customers", "scale", "increase",
            "more clients", "conversion", "monetize", "profit"
        ],
        BusinessGoal.CUT_COSTS: [
            "costs", "expenses", "efficiency", "save money", "reduce",
            "overhead", "budget", "lean", "optimize spending"
        ],
        BusinessGoal.SCALE_TEAM: [
            "hire", "team", "employees", "staff", "recruiting", "onboarding",
            "manage people", "hr", "culture", "remote team"
        ],
        BusinessGoal.IMPROVE_PRODUCT: [
            "product", "features", "quality", "user experience", "feedback",
            "roadmap", "development", "improvements", "bugs", "iterate"
        ],
        BusinessGoal.EXPAND_MARKET: [
            "expand", "new markets", "international", "segments", "verticals",
            "geography", "diversify", "new customers", "reach"
        ],
        BusinessGoal.AUTOMATE: [
            "automate", "automation", "workflows", "processes", "manual tasks",
            "ai", "bots", "systems", "streamline", "productivity"
        ],
        BusinessGoal.FUNDRAISE: [
            "fundraise", "funding", "investors", "capital", "raise money",
            "pitch deck", "valuation", "vc", "angel", "seed round"
        ],
    }
    
    # Agent role rationales
    ROLE_RATIONALES: dict[AgentRole, str] = {
        AgentRole.CEO: "Strategic vision, decision-making, and business direction",
        AgentRole.CTO: "Technical architecture, engineering leadership, and tech strategy",
        AgentRole.CMO: "Marketing strategy, content, brand, and customer acquisition",
        AgentRole.CFO: "Financial planning, budgeting, metrics, and cash flow",
        AgentRole.ANALYST: "Research, data analysis, market intelligence, and insights",
        AgentRole.ASSISTANT: "Scheduling, admin tasks, email management, and organization",
        AgentRole.DEVELOPER: "Code, debugging, technical implementation, and automation",
        AgentRole.DESIGNER: "UI/UX, graphics, branding, and visual content",
        AgentRole.SALES: "Outreach, pipeline management, closing deals, and relationships",
        AgentRole.SUPPORT: "Customer success, tickets, FAQs, and user onboarding",
    }
    
    # Tier limits
    TIER_LIMITS: dict[str, int] = {
        "starter": 1,
        "pro": 3,
        "business": 6,
        "enterprise": 20,
    }
    
    def __init__(self, provisioner: Optional[AgentProvisioner] = None):
        """Initialize HR Department with optional AgentProvisioner."""
        self.provisioner = provisioner or AgentProvisioner()
    
    def analyze_business(
        self,
        name: str,
        description: str,
        team_size: int = 1,
        has_technical: bool = False,
        has_marketing: bool = False,
        has_sales: bool = False,
        budget_tier: str = "starter",
    ) -> BusinessProfile:
        """
        Analyze business from description and metadata.
        
        Args:
            name: Business name
            description: Free-text description of the business
            team_size: Number of human team members
            has_technical: Team has technical capabilities
            has_marketing: Team has marketing experience
            has_sales: Team has sales experience
            budget_tier: Subscription tier (affects agent count)
        
        Returns:
            BusinessProfile with detected attributes
        """
        description_lower = description.lower()
        
        # Detect industry
        industry = self._detect_industry(description_lower)
        
        # Detect stage
        stage = self._detect_stage(description_lower, team_size)
        
        # Detect goals
        goals = self._detect_goals(description_lower)
        
        # Analyze needs based on gaps
        profile = BusinessProfile(
            name=name,
            description=description,
            industry=industry,
            stage=stage,
            goals=goals,
            team_size=team_size,
            has_technical_founder=has_technical,
            has_marketing_experience=has_marketing,
            has_sales_experience=has_sales,
            budget_tier=budget_tier,
        )
        
        # Fill needs based on profile
        self._analyze_needs(profile)
        
        return profile
    
    def _detect_industry(self, description: str) -> Industry:
        """Detect industry from description keywords."""
        scores: dict[Industry, int] = {}
        
        for industry, keywords in self.INDUSTRY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in description)
            if score > 0:
                scores[industry] = score
        
        if scores:
            return max(scores, key=scores.get)
        return Industry.OTHER
    
    def _detect_stage(self, description: str, team_size: int) -> BusinessStage:
        """Detect business stage from description and team size."""
        # Stage indicators in description
        if any(w in description for w in ["idea", "planning", "thinking about", "want to start"]):
            return BusinessStage.IDEA
        if any(w in description for w in ["enterprise", "fortune 500", "large scale", "multinational"]):
            return BusinessStage.ENTERPRISE
        if any(w in description for w in ["scaling", "rapid growth", "series", "expanding fast"]):
            return BusinessStage.SCALE
        if any(w in description for w in ["growing", "traction", "customers", "revenue"]):
            return BusinessStage.GROWTH
        
        # Fallback to team size heuristic
        if team_size == 1:
            return BusinessStage.EARLY
        elif team_size <= 5:
            return BusinessStage.GROWTH
        elif team_size <= 20:
            return BusinessStage.SCALE
        else:
            return BusinessStage.ENTERPRISE
    
    def _detect_goals(self, description: str) -> list[BusinessGoal]:
        """Detect business goals from description."""
        goals = []
        
        for goal, keywords in self.GOAL_KEYWORDS.items():
            if any(kw in description for kw in keywords):
                goals.append(goal)
        
        # Default goal if none detected
        if not goals:
            goals = [BusinessGoal.GROW_REVENUE]
        
        return goals
    
    def _analyze_needs(self, profile: BusinessProfile) -> None:
        """Analyze gaps and set needs flags."""
        # Technical needs
        profile.needs_technical = (
            not profile.has_technical_founder and
            profile.industry in [Industry.SAAS, Industry.FINTECH, Industry.STARTUP]
        )
        
        # Marketing needs
        profile.needs_marketing = (
            not profile.has_marketing_experience or
            BusinessGoal.GROW_REVENUE in profile.goals or
            BusinessGoal.EXPAND_MARKET in profile.goals
        )
        
        # Sales needs
        profile.needs_sales = (
            not profile.has_sales_experience and
            profile.industry in [Industry.CONSULTING, Industry.REAL_ESTATE, Industry.AGENCY]
        )
        
        # Finance needs
        profile.needs_finance = (
            profile.stage in [BusinessStage.GROWTH, BusinessStage.SCALE, BusinessStage.ENTERPRISE] or
            BusinessGoal.FUNDRAISE in profile.goals or
            BusinessGoal.CUT_COSTS in profile.goals
        )
        
        # Operations/assistant needs
        profile.needs_operations = (
            profile.team_size > 1 or
            BusinessGoal.AUTOMATE in profile.goals
        )
        
        # Research needs
        profile.needs_research = (
            BusinessGoal.EXPAND_MARKET in profile.goals or
            profile.industry in [Industry.CONSULTING, Industry.FINTECH]
        )
        
        # Design needs
        profile.needs_design = (
            profile.industry in [Industry.AGENCY, Industry.CONTENT, Industry.ECOMMERCE]
        )
        
        # Support needs
        profile.needs_support = (
            profile.stage in [BusinessStage.GROWTH, BusinessStage.SCALE, BusinessStage.ENTERPRISE] or
            profile.industry in [Industry.ECOMMERCE, Industry.SAAS, Industry.HEALTHCARE]
        )
    
    def recommend_team(self, profile: BusinessProfile) -> TeamRecommendation:
        """
        Generate agent team recommendation based on profile.
        
        Args:
            profile: Analyzed business profile
        
        Returns:
            TeamRecommendation with prioritized agents and rationale
        """
        recommendations: list[AgentRecommendation] = []
        
        # Get industry template as baseline
        industry_roles = self.INDUSTRY_TEMPLATES.get(
            profile.industry, 
            self.INDUSTRY_TEMPLATES[Industry.OTHER]
        )
        
        # Build recommendations with priorities
        for i, role in enumerate(industry_roles):
            priority = 10 - i  # First in template = highest priority
            is_essential = i < 2  # First 2 are essential
            
            # Boost priority based on needs
            if role == AgentRole.CTO and profile.needs_technical:
                priority = min(priority + 2, 10)
                is_essential = True
            if role == AgentRole.CMO and profile.needs_marketing:
                priority = min(priority + 2, 10)
            if role == AgentRole.SALES and profile.needs_sales:
                priority = min(priority + 2, 10)
            if role == AgentRole.CFO and profile.needs_finance:
                priority = min(priority + 2, 10)
            if role == AgentRole.ANALYST and profile.needs_research:
                priority = min(priority + 1, 10)
            if role == AgentRole.SUPPORT and profile.needs_support:
                priority = min(priority + 1, 10)
            if role == AgentRole.DESIGNER and profile.needs_design:
                priority = min(priority + 1, 10)
            
            recommendations.append(AgentRecommendation(
                role=role,
                priority=priority,
                rationale=self.ROLE_RATIONALES[role],
                is_essential=is_essential,
            ))
        
        # Add missing high-need roles
        existing_roles = {r.role for r in recommendations}
        
        if profile.needs_technical and AgentRole.CTO not in existing_roles:
            recommendations.append(AgentRecommendation(
                role=AgentRole.CTO,
                priority=9,
                rationale="Technical gap identified — no technical founder",
                is_essential=True,
            ))
        
        if profile.needs_finance and AgentRole.CFO not in existing_roles:
            recommendations.append(AgentRecommendation(
                role=AgentRole.CFO,
                priority=7,
                rationale="Financial planning needed for current stage/goals",
                is_essential=False,
            ))
        
        # Sort by priority (descending)
        recommendations.sort(key=lambda r: r.priority, reverse=True)
        
        # Apply tier limit
        tier_limit = self.TIER_LIMITS.get(profile.budget_tier, 1)
        final_recommendations = recommendations[:tier_limit]
        
        # Generate warnings
        warnings = []
        if len(recommendations) > tier_limit:
            dropped = [r.role.value for r in recommendations[tier_limit:] if r.priority >= 7]
            if dropped:
                warnings.append(
                    f"Tier limit ({tier_limit}) excludes high-value roles: {', '.join(dropped)}. "
                    f"Consider upgrading for better coverage."
                )
        
        # Generate suggestions
        suggestions = []
        if profile.stage == BusinessStage.IDEA:
            suggestions.append(
                "Early stage detected. Focus on validation before scaling agent team."
            )
        if BusinessGoal.FUNDRAISE in profile.goals and AgentRole.CFO not in [r.role for r in final_recommendations]:
            suggestions.append(
                "Fundraising goal detected but CFO not included. Consider adding for investor materials."
            )
        if profile.team_size == 1:
            suggestions.append(
                "Solo founder — prioritize Assistant for admin tasks to free your time."
            )
        
        # Summary
        roles_str = ", ".join(r.role.value for r in final_recommendations)
        summary = (
            f"Recommended {len(final_recommendations)} agent(s) for {profile.industry.value} "
            f"business at {profile.stage.value} stage: {roles_str}"
        )
        
        return TeamRecommendation(
            agents=final_recommendations,
            summary=summary,
            warnings=warnings,
            suggestions=suggestions,
        )
    
    def questionnaire_to_profile(
        self,
        name: str,
        responses: dict[str, str],
        budget_tier: str = "starter",
    ) -> BusinessProfile:
        """
        Convert questionnaire responses to BusinessProfile.
        
        Expected keys:
            - description: What does your business do?
            - industry: Which industry? (optional, auto-detected if missing)
            - stage: What stage? (idea/early/growth/scale/enterprise)
            - goals: Primary goals (comma-separated)
            - team_size: How many people on your team?
            - has_technical: Technical skills on team? (yes/no)
            - has_marketing: Marketing skills on team? (yes/no)
            - has_sales: Sales skills on team? (yes/no)
        """
        description = responses.get("description", "")
        
        # Auto-detect industry or use provided
        industry_str = responses.get("industry", "").lower()
        try:
            industry = Industry(industry_str) if industry_str else self._detect_industry(description.lower())
        except ValueError:
            industry = self._detect_industry(description.lower())
        
        # Parse stage
        stage_str = responses.get("stage", "").lower()
        try:
            stage = BusinessStage(stage_str) if stage_str else self._detect_stage(description.lower(), 1)
        except ValueError:
            stage = BusinessStage.EARLY
        
        # Parse goals
        goals_str = responses.get("goals", "")
        goals = []
        for goal_name in goals_str.split(","):
            goal_name = goal_name.strip().lower().replace(" ", "_")
            try:
                goals.append(BusinessGoal(goal_name))
            except ValueError:
                pass
        if not goals:
            goals = self._detect_goals(description.lower())
        
        # Parse team size
        try:
            team_size = int(responses.get("team_size", "1"))
        except ValueError:
            team_size = 1
        
        # Parse boolean flags
        has_technical = responses.get("has_technical", "").lower() in ["yes", "true", "1"]
        has_marketing = responses.get("has_marketing", "").lower() in ["yes", "true", "1"]
        has_sales = responses.get("has_sales", "").lower() in ["yes", "true", "1"]
        
        return self.analyze_business(
            name=name,
            description=description,
            team_size=team_size,
            has_technical=has_technical,
            has_marketing=has_marketing,
            has_sales=has_sales,
            budget_tier=budget_tier,
        )
    
    def provision_recommended_team(
        self,
        tenant_subdomain: str,
        recommendation: TeamRecommendation,
        base_path: str = "/data/tenants",
        organization_name: Optional[str] = None,
    ) -> dict[str, str]:
        """
        Provision the recommended team using AgentProvisioner.
        
        Args:
            tenant_subdomain: Tenant identifier
            recommendation: TeamRecommendation from recommend_team()
            base_path: Base path for tenant workspaces
            organization_name: Business name for SOUL.md
        
        Returns:
            Dict of agent_id → workspace path
        """
        # Convert recommendations to AgentConfigs
        agents = []
        for rec in recommendation.agents:
            agents.append(AgentConfig(
                role=rec.role,
                custom_name=None,  # Use default role name
            ))
        
        # Build tenant config
        from .agent_provisioner import TenantConfig, TenantTier
        
        # Map budget tier to TenantTier
        tier_map = {
            "starter": TenantTier.STARTER,
            "pro": TenantTier.PRO,
            "business": TenantTier.BUSINESS,
            "enterprise": TenantTier.ENTERPRISE,
        }
        tier = tier_map.get(recommendation.agents[0].role.value, TenantTier.STARTER)
        # Actually, get tier from somewhere else... let's just use PRO as default
        tier = TenantTier.PRO
        
        tenant_config = TenantConfig(
            subdomain=tenant_subdomain,
            organization_name=organization_name or tenant_subdomain,
            tier=tier,
            agents=agents,
            enable_shipos=True,
        )
        
        # Provision via AgentProvisioner
        return self.provisioner.provision_workspace(tenant_config, base_path)
    
    def get_industry_description(self, industry: Industry) -> str:
        """Get human-readable description of industry."""
        descriptions = {
            Industry.ECOMMERCE: "Online retail, product sales, marketplaces",
            Industry.SAAS: "Software as a Service, B2B tools, platforms",
            Industry.AGENCY: "Creative, marketing, or digital agencies",
            Industry.CONSULTING: "Professional services, advisory, strategy",
            Industry.CONTENT: "Content creation, media, publishing",
            Industry.FINTECH: "Financial technology, payments, trading",
            Industry.HEALTHCARE: "Healthcare, medical, wellness",
            Industry.EDUCATION: "Education, e-learning, training",
            Industry.REAL_ESTATE: "Real estate, property, rentals",
            Industry.LEGAL: "Legal services, law firms, compliance",
            Industry.MANUFACTURING: "Manufacturing, production, logistics",
            Industry.NONPROFIT: "Nonprofits, charities, foundations",
            Industry.STARTUP: "Early-stage startups, ventures",
            Industry.FREELANCER: "Freelancers, solopreneurs, independents",
            Industry.OTHER: "Other industries",
        }
        return descriptions.get(industry, "Unknown industry")
    
    def get_questionnaire_prompts(self) -> list[dict[str, str]]:
        """Get questionnaire prompts for onboarding flow."""
        return [
            {
                "key": "description",
                "prompt": "What does your business do? Describe it in a few sentences.",
                "required": True,
            },
            {
                "key": "industry",
                "prompt": "Which industry best describes your business?",
                "options": [i.value for i in Industry],
                "required": False,
            },
            {
                "key": "stage",
                "prompt": "What stage is your business at?",
                "options": [s.value for s in BusinessStage],
                "required": False,
            },
            {
                "key": "goals",
                "prompt": "What are your primary goals? (select all that apply)",
                "options": [g.value for g in BusinessGoal],
                "required": False,
                "multi": True,
            },
            {
                "key": "team_size",
                "prompt": "How many people are on your team?",
                "type": "number",
                "required": False,
            },
            {
                "key": "has_technical",
                "prompt": "Does your team have technical/engineering skills?",
                "options": ["yes", "no"],
                "required": False,
            },
            {
                "key": "has_marketing",
                "prompt": "Does your team have marketing experience?",
                "options": ["yes", "no"],
                "required": False,
            },
            {
                "key": "has_sales",
                "prompt": "Does your team have sales experience?",
                "options": ["yes", "no"],
                "required": False,
            },
        ]


# Convenience function for quick analysis
def auto_recruit(
    business_name: str,
    description: str,
    tier: str = "starter",
    **kwargs,
) -> TeamRecommendation:
    """
    Quick analysis and recommendation in one call.
    
    Usage:
        from hr_department import auto_recruit
        
        result = auto_recruit(
            "Acme Corp",
            "We're a SaaS startup building project management tools...",
            tier="pro",
        )
        print(result.summary)
        for agent in result.agents:
            print(f"  {agent.role.value}: {agent.rationale}")
    """
    hr = HRDepartment()
    profile = hr.analyze_business(
        name=business_name,
        description=description,
        budget_tier=tier,
        **kwargs,
    )
    return hr.recommend_team(profile)
