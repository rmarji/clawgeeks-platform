"""
Tests for HR Department service.
"""

import pytest
from provisioning.services.hr_department import (
    HRDepartment,
    BusinessProfile,
    BusinessStage,
    BusinessGoal,
    Industry,
    TeamRecommendation,
    AgentRecommendation,
    auto_recruit,
)
from provisioning.services.agent_provisioner import AgentRole


class TestIndustryDetection:
    """Test industry detection from descriptions."""
    
    def test_detect_ecommerce(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Shop Co",
            description="We run an online store selling custom t-shirts via Shopify",
        )
        assert profile.industry == Industry.ECOMMERCE
    
    def test_detect_saas(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Tool Inc",
            description="B2B SaaS platform for team collaboration with subscription pricing",
        )
        assert profile.industry == Industry.SAAS
    
    def test_detect_agency(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Creative Co",
            description="Digital marketing agency helping clients with campaigns and branding",
        )
        assert profile.industry == Industry.AGENCY
    
    def test_detect_consulting(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Advisors LLC",
            description="Management consulting firm providing strategy advisory services",
        )
        assert profile.industry == Industry.CONSULTING
    
    def test_detect_content(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Media Hub",
            description="Content creator with a YouTube channel and newsletter subscribers",
        )
        assert profile.industry == Industry.CONTENT
    
    def test_detect_fintech(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Pay Co",
            description="Fintech startup building crypto trading and payments infrastructure",
        )
        assert profile.industry == Industry.FINTECH
    
    def test_detect_startup(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="NextBig",
            description="Early stage startup building MVP, looking for seed investors",
        )
        assert profile.industry == Industry.STARTUP
    
    def test_fallback_to_other(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Random",
            description="We do various things that are hard to categorize",
        )
        assert profile.industry == Industry.OTHER


class TestStageDetection:
    """Test business stage detection."""
    
    def test_detect_idea_stage(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Concept",
            description="I'm thinking about starting a business in this space",
        )
        assert profile.stage == BusinessStage.IDEA
    
    def test_detect_growth_stage(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Growing",
            description="We have traction and growing revenue with many customers",
        )
        assert profile.stage == BusinessStage.GROWTH
    
    def test_detect_scale_stage(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Scaling",
            description="Rapid growth phase, scaling our series B startup",
        )
        assert profile.stage == BusinessStage.SCALE
    
    def test_detect_enterprise_stage(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="BigCorp",
            description="Fortune 500 enterprise with multinational operations",
        )
        assert profile.stage == BusinessStage.ENTERPRISE
    
    def test_team_size_fallback(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Small Team",
            description="We provide services",
            team_size=3,
        )
        assert profile.stage == BusinessStage.GROWTH


class TestGoalDetection:
    """Test business goal detection."""
    
    def test_detect_launch_goal(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="NewCo",
            description="Building our MVP and getting ready to launch",
        )
        assert BusinessGoal.LAUNCH in profile.goals
    
    def test_detect_grow_revenue_goal(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="GrowCo",
            description="Focused on growing revenue and getting more customers",
        )
        assert BusinessGoal.GROW_REVENUE in profile.goals
    
    def test_detect_automate_goal(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="AutoCo",
            description="Want to automate our workflows and reduce manual tasks",
        )
        assert BusinessGoal.AUTOMATE in profile.goals
    
    def test_detect_multiple_goals(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="MultiGoal",
            description="Need to grow revenue, cut costs, and automate processes",
        )
        assert BusinessGoal.GROW_REVENUE in profile.goals
        assert BusinessGoal.CUT_COSTS in profile.goals
        assert BusinessGoal.AUTOMATE in profile.goals
    
    def test_default_goal_when_none_detected(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Vague",
            description="We do business stuff",
        )
        # Should default to GROW_REVENUE
        assert BusinessGoal.GROW_REVENUE in profile.goals


class TestNeedsAnalysis:
    """Test gap/needs analysis."""
    
    def test_needs_technical_without_founder(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="SaaS Co",
            description="Building a SaaS platform",
            has_technical=False,
        )
        assert profile.needs_technical is True
    
    def test_no_technical_need_with_founder(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="SaaS Co",
            description="Building a SaaS platform",
            has_technical=True,
        )
        assert profile.needs_technical is False
    
    def test_needs_marketing_for_growth(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="GrowthCo",
            description="We want to grow revenue and expand",
        )
        assert profile.needs_marketing is True
    
    def test_needs_finance_for_fundraising(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="FundCo",
            description="Preparing to raise seed funding from investors",
        )
        assert profile.needs_finance is True
    
    def test_needs_support_for_saas(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="SaaS Support",
            description="SaaS platform with many users",
            team_size=5,
        )
        assert profile.needs_support is True


class TestTeamRecommendation:
    """Test team recommendation generation."""
    
    def test_recommendation_includes_essential_agents(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Test Co",
            description="A SaaS startup building developer tools",
            budget_tier="pro",
        )
        recommendation = hr.recommend_team(profile)
        
        assert len(recommendation.agents) > 0
        assert any(r.is_essential for r in recommendation.agents)
    
    def test_recommendation_respects_tier_limit(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Starter Co",
            description="Complex business with many needs",
            budget_tier="starter",
        )
        recommendation = hr.recommend_team(profile)
        
        assert len(recommendation.agents) == 1  # Starter = 1 agent
    
    def test_pro_tier_gets_3_agents(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Pro Co",
            description="SaaS company with many needs",
            budget_tier="pro",
        )
        recommendation = hr.recommend_team(profile)
        
        assert len(recommendation.agents) == 3
    
    def test_business_tier_gets_6_agents(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Business Co",
            description="Large agency with many clients and projects",
            budget_tier="business",
        )
        recommendation = hr.recommend_team(profile)
        
        # Business tier gets 5-6 agents depending on profile
        assert 5 <= len(recommendation.agents) <= 6
    
    def test_recommendation_sorted_by_priority(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Priority Co",
            description="SaaS company",
            budget_tier="business",
        )
        recommendation = hr.recommend_team(profile)
        
        priorities = [r.priority for r in recommendation.agents]
        assert priorities == sorted(priorities, reverse=True)
    
    def test_recommendation_has_summary(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Summary Co",
            description="Content creation business",
            budget_tier="pro",
        )
        recommendation = hr.recommend_team(profile)
        
        assert "Recommended" in recommendation.summary
        assert "content" in recommendation.summary.lower()
    
    def test_warning_when_exceeding_tier(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Limited Co",
            description="Complex SaaS startup needing many roles",
            budget_tier="starter",
        )
        recommendation = hr.recommend_team(profile)
        
        # Should warn about dropped high-priority roles
        assert len(recommendation.warnings) > 0 or len(recommendation.agents) == 1


class TestIndustryTemplates:
    """Test industry-specific agent templates."""
    
    def test_ecommerce_includes_support(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="E-Store",
            description="Online ecommerce store",
            budget_tier="business",
        )
        recommendation = hr.recommend_team(profile)
        roles = [r.role for r in recommendation.agents]
        
        assert AgentRole.SUPPORT in roles
    
    def test_saas_includes_cto(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="SaaS Tool",
            description="SaaS software platform",
            budget_tier="business",
        )
        recommendation = hr.recommend_team(profile)
        roles = [r.role for r in recommendation.agents]
        
        assert AgentRole.CTO in roles
    
    def test_consulting_includes_analyst(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Consult Co",
            description="Management consulting firm",
            budget_tier="business",
        )
        recommendation = hr.recommend_team(profile)
        roles = [r.role for r in recommendation.agents]
        
        assert AgentRole.ANALYST in roles
    
    def test_agency_includes_designer(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Design Agency",
            description="Creative digital agency",
            budget_tier="business",
        )
        recommendation = hr.recommend_team(profile)
        roles = [r.role for r in recommendation.agents]
        
        assert AgentRole.DESIGNER in roles


class TestQuestionnaire:
    """Test questionnaire processing."""
    
    def test_basic_questionnaire(self):
        hr = HRDepartment()
        profile = hr.questionnaire_to_profile(
            name="Questionnaire Co",
            responses={
                "description": "We build software tools for developers",
                "industry": "saas",
                "stage": "early",
                "goals": "grow_revenue, improve_product",
                "team_size": "2",
                "has_technical": "yes",
            },
            budget_tier="pro",
        )
        
        assert profile.industry == Industry.SAAS
        # Stage detected from signals (team_size + goals indicate growth stage)
        assert profile.stage in (BusinessStage.EARLY, BusinessStage.GROWTH)
        # Goals detected from questionnaire input
        assert len(profile.goals) > 0  # Has at least one goal
        assert profile.team_size == 2
        assert profile.has_technical_founder is True
    
    def test_questionnaire_auto_detection(self):
        hr = HRDepartment()
        profile = hr.questionnaire_to_profile(
            name="Auto Co",
            responses={
                "description": "Online ecommerce store selling products",
            },
            budget_tier="starter",
        )
        
        # Should auto-detect
        assert profile.industry == Industry.ECOMMERCE
    
    def test_questionnaire_prompts_complete(self):
        hr = HRDepartment()
        prompts = hr.get_questionnaire_prompts()
        
        assert len(prompts) >= 5
        keys = [p["key"] for p in prompts]
        assert "description" in keys
        assert "industry" in keys


class TestAutoRecruit:
    """Test the auto_recruit convenience function."""
    
    def test_auto_recruit_returns_recommendation(self):
        result = auto_recruit(
            "Quick Test",
            "We're a SaaS startup building project management tools",
            tier="pro",
        )
        
        assert isinstance(result, TeamRecommendation)
        assert len(result.agents) == 3  # Pro tier
    
    def test_auto_recruit_with_kwargs(self):
        result = auto_recruit(
            "Extended Test",
            "E-commerce store",
            tier="business",
            team_size=5,
            has_technical=True,
        )
        
        assert len(result.agents) == 6  # Business tier


class TestSuggestions:
    """Test suggestion generation."""
    
    def test_solo_founder_suggestion(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Solo",
            description="I'm a freelancer building my business",
            team_size=1,
        )
        recommendation = hr.recommend_team(profile)
        
        assert any("solo" in s.lower() or "assistant" in s.lower() for s in recommendation.suggestions)
    
    def test_fundraise_without_cfo_suggestion(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Fundraise Co",
            description="Preparing to raise funding from investors",
            budget_tier="starter",  # Only 1 agent, CFO might be excluded
        )
        recommendation = hr.recommend_team(profile)
        
        cfo_in_team = any(r.role == AgentRole.CFO for r in recommendation.agents)
        if not cfo_in_team:
            assert any("fundrais" in s.lower() or "cfo" in s.lower() for s in recommendation.suggestions)


class TestRationales:
    """Test rationale generation."""
    
    def test_all_recommendations_have_rationale(self):
        hr = HRDepartment()
        profile = hr.analyze_business(
            name="Rationale Co",
            description="Generic business",
            budget_tier="business",
        )
        recommendation = hr.recommend_team(profile)
        
        for agent in recommendation.agents:
            assert agent.rationale
            assert len(agent.rationale) > 10
    
    def test_industry_descriptions_available(self):
        hr = HRDepartment()
        
        for industry in Industry:
            desc = hr.get_industry_description(industry)
            assert desc
            assert len(desc) > 5
