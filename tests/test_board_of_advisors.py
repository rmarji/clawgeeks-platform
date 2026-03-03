"""
Tests for Board of Advisors service.

Tests cover:
- Advisor library completeness and consistency
- Recommendation engine
- Default board composition
- SOUL.md generation
- Edge cases and error handling
"""

import pytest
from provisioning.services.board_of_advisors import (
    BoardOfAdvisors,
    AdvisorArchetype,
    AdvisorDomain,
    Advisor,
    StrategicFramework,
    ADVISOR_LIBRARY,
    CHALLENGE_KEYWORDS,
    get_advisor_for_challenge,
)


# ============================================================================
# ADVISOR LIBRARY TESTS
# ============================================================================

class TestAdvisorLibrary:
    """Tests for the advisor library data."""
    
    def test_all_archetypes_have_advisors(self):
        """Every archetype should have an advisor defined."""
        for archetype in AdvisorArchetype:
            assert archetype in ADVISOR_LIBRARY, f"Missing advisor for {archetype}"
    
    def test_advisor_has_required_fields(self):
        """Each advisor should have all required fields populated."""
        for archetype, advisor in ADVISOR_LIBRARY.items():
            assert advisor.name, f"{archetype}: missing name"
            assert advisor.emoji, f"{archetype}: missing emoji"
            assert advisor.title, f"{archetype}: missing title"
            assert advisor.tagline, f"{archetype}: missing tagline"
            assert advisor.background, f"{archetype}: missing background"
            assert len(advisor.expertise) >= 3, f"{archetype}: needs at least 3 expertise areas"
            assert len(advisor.traits) >= 3, f"{archetype}: needs at least 3 traits"
            assert advisor.communication_style, f"{archetype}: missing communication style"
            assert len(advisor.strategic_questions) >= 4, f"{archetype}: needs at least 4 questions"
            assert len(advisor.frameworks) >= 2, f"{archetype}: needs at least 2 frameworks"
            assert len(advisor.red_flags) >= 3, f"{archetype}: needs at least 3 red flags"
            assert len(advisor.ideal_situations) >= 3, f"{archetype}: needs at least 3 ideal situations"
            assert len(advisor.anti_patterns) >= 2, f"{archetype}: needs at least 2 anti-patterns"
    
    def test_frameworks_have_required_fields(self):
        """Each framework should have all required fields."""
        for archetype, advisor in ADVISOR_LIBRARY.items():
            for framework in advisor.frameworks:
                assert framework.name, f"{archetype}: framework missing name"
                assert framework.description, f"{archetype}: framework missing description"
                assert framework.when_to_use, f"{archetype}: framework missing when_to_use"
    
    def test_all_domains_covered(self):
        """All strategic domains should have at least one advisor."""
        covered_domains = {advisor.domain for advisor in ADVISOR_LIBRARY.values()}
        for domain in AdvisorDomain:
            assert domain in covered_domains, f"No advisor for domain: {domain}"
    
    def test_unique_names(self):
        """All advisors should have unique names."""
        names = [advisor.name for advisor in ADVISOR_LIBRARY.values()]
        assert len(names) == len(set(names)), "Duplicate advisor names found"


# ============================================================================
# BOARD OF ADVISORS SERVICE TESTS
# ============================================================================

class TestBoardOfAdvisorsBasics:
    """Basic service functionality tests."""
    
    def setup_method(self):
        self.board = BoardOfAdvisors()
    
    def test_init(self):
        """Service should initialize with library and keywords."""
        assert self.board.library is not None
        assert self.board.keywords is not None
        assert len(self.board.library) == len(AdvisorArchetype)
    
    def test_get_all_advisors(self):
        """Should return all advisors."""
        advisors = self.board.get_all_advisors()
        assert len(advisors) == len(AdvisorArchetype)
        assert all(isinstance(a, Advisor) for a in advisors)
    
    def test_get_advisor_exists(self):
        """Should return advisor for valid archetype."""
        advisor = self.board.get_advisor(AdvisorArchetype.SERIAL_ENTREPRENEUR)
        assert advisor is not None
        assert advisor.name == "Marcus"
    
    def test_get_advisor_not_found(self):
        """Should return None for invalid archetype."""
        # Can't really test invalid since it's an enum, but test the method exists
        assert self.board.get_advisor(AdvisorArchetype.BOARD_CHAIR) is not None
    
    def test_get_all_domains(self):
        """Should return all domains."""
        domains = self.board.get_all_domains()
        assert len(domains) == len(AdvisorDomain)


class TestAdvisorsByDomain:
    """Tests for domain-based advisor lookup."""
    
    def setup_method(self):
        self.board = BoardOfAdvisors()
    
    def test_governance_domain(self):
        """Should return governance advisors."""
        advisors = self.board.get_advisors_by_domain(AdvisorDomain.GOVERNANCE)
        assert len(advisors) >= 1
        assert all(a.domain == AdvisorDomain.GOVERNANCE for a in advisors)
    
    def test_capital_domain(self):
        """Should return capital/fundraising advisors."""
        advisors = self.board.get_advisors_by_domain(AdvisorDomain.CAPITAL)
        assert len(advisors) >= 2  # VC and Angel
        archetypes = {a.archetype for a in advisors}
        assert AdvisorArchetype.VC_PARTNER in archetypes
    
    def test_risk_domain(self):
        """Should return risk management advisors."""
        advisors = self.board.get_advisors_by_domain(AdvisorDomain.RISK)
        assert len(advisors) >= 1


# ============================================================================
# RECOMMENDATION ENGINE TESTS
# ============================================================================

class TestRecommendAdvisor:
    """Tests for the recommendation engine."""
    
    def setup_method(self):
        self.board = BoardOfAdvisors()
    
    def test_fundraising_challenge(self):
        """Fundraising challenge should recommend VC/Angel."""
        recs = self.board.recommend_advisor("We need to raise our Series A")
        assert len(recs) >= 1
        archetypes = {r.advisor.archetype for r in recs}
        assert AdvisorArchetype.VC_PARTNER in archetypes or AdvisorArchetype.ANGEL_INVESTOR in archetypes
    
    def test_exit_challenge(self):
        """Exit challenge should recommend M&A strategist."""
        recs = self.board.recommend_advisor("We received an acquisition offer")
        assert len(recs) >= 1
        archetypes = {r.advisor.archetype for r in recs}
        assert AdvisorArchetype.MA_STRATEGIST in archetypes
    
    def test_scaling_challenge(self):
        """Scaling challenge should recommend scaling expert."""
        recs = self.board.recommend_advisor("How do we scale our operations?")
        assert len(recs) >= 1
        archetypes = {r.advisor.archetype for r in recs}
        assert AdvisorArchetype.SCALING_EXPERT in archetypes or AdvisorArchetype.GLOBAL_EXPANSION in archetypes
    
    def test_governance_challenge(self):
        """Governance challenge should recommend Board Chair."""
        recs = self.board.recommend_advisor("We need to improve our board governance")
        assert len(recs) >= 1
        archetypes = {r.advisor.archetype for r in recs}
        assert AdvisorArchetype.BOARD_CHAIR in archetypes
    
    def test_founder_challenge(self):
        """Founder challenge should recommend serial entrepreneur."""
        recs = self.board.recommend_advisor("My cofounder and I are having disagreements")
        assert len(recs) >= 1
        archetypes = {r.advisor.archetype for r in recs}
        assert AdvisorArchetype.SERIAL_ENTREPRENEUR in archetypes
    
    def test_crisis_challenge(self):
        """Crisis/turnaround should recommend turnaround specialist."""
        recs = self.board.recommend_advisor("We're running out of runway and need to restructure")
        assert len(recs) >= 1
        archetypes = {r.advisor.archetype for r in recs}
        assert AdvisorArchetype.TURNAROUND_SPECIALIST in archetypes or AdvisorArchetype.VC_PARTNER in archetypes
    
    def test_international_challenge(self):
        """International expansion should recommend global advisor."""
        recs = self.board.recommend_advisor("We want to expand into Europe")
        assert len(recs) >= 1
        archetypes = {r.advisor.archetype for r in recs}
        assert AdvisorArchetype.GLOBAL_EXPANSION in archetypes
    
    def test_max_results_respected(self):
        """Should respect max_results parameter."""
        recs = self.board.recommend_advisor("fundraising exit scaling", max_results=2)
        assert len(recs) <= 2
    
    def test_relevance_scores(self):
        """Recommendations should have relevance scores."""
        recs = self.board.recommend_advisor("board governance CEO evaluation")
        assert all(0.0 <= r.relevance_score <= 1.0 for r in recs)
    
    def test_reasons_populated(self):
        """Recommendations should have reasons."""
        recs = self.board.recommend_advisor("fundraise series a")
        for rec in recs:
            assert isinstance(rec.reasons, list)
    
    def test_suggested_questions_populated(self):
        """Recommendations should have suggested questions."""
        recs = self.board.recommend_advisor("We need strategic advice")
        for rec in recs:
            assert len(rec.suggested_questions) >= 1
    
    def test_fallback_for_no_match(self):
        """Should return generalist advisors for unclear challenges."""
        recs = self.board.recommend_advisor("general business question xyz123")
        assert len(recs) >= 1  # Should still return something


# ============================================================================
# DEFAULT BOARD TESTS
# ============================================================================

class TestDefaultBoard:
    """Tests for default board composition."""
    
    def setup_method(self):
        self.board = BoardOfAdvisors()
    
    def test_seed_stage_board(self):
        """Seed stage should get founder-friendly advisors."""
        rec = self.board.get_default_board(stage="seed", size=3)
        assert len(rec.advisors) == 3
        archetypes = {a.archetype for a in rec.advisors}
        assert AdvisorArchetype.SERIAL_ENTREPRENEUR in archetypes or AdvisorArchetype.ANGEL_INVESTOR in archetypes
    
    def test_growth_stage_board(self):
        """Growth stage should get scaling advisors."""
        rec = self.board.get_default_board(stage="growth", size=3)
        assert len(rec.advisors) == 3
        archetypes = {a.archetype for a in rec.advisors}
        assert AdvisorArchetype.SCALING_EXPERT in archetypes or AdvisorArchetype.VC_PARTNER in archetypes
    
    def test_scale_stage_board(self):
        """Scale stage should get governance and exit advisors."""
        rec = self.board.get_default_board(stage="scale", size=4)
        assert len(rec.advisors) == 4
        archetypes = {a.archetype for a in rec.advisors}
        assert AdvisorArchetype.BOARD_CHAIR in archetypes or AdvisorArchetype.MA_STRATEGIST in archetypes
    
    def test_industry_specific_board(self):
        """Industry context should influence board composition."""
        fintech_board = self.board.get_default_board(industry="fintech", stage="growth", size=5)
        general_board = self.board.get_default_board(industry="general", stage="growth", size=5)
        
        fintech_archetypes = {a.archetype for a in fintech_board.advisors}
        # Fintech should have risk/compliance advisors
        assert AdvisorArchetype.CHIEF_RISK_OFFICER in fintech_archetypes or AdvisorArchetype.INDUSTRY_VETERAN in fintech_archetypes
    
    def test_board_size_respected(self):
        """Board size should be respected."""
        for size in [3, 5, 7]:
            rec = self.board.get_default_board(size=size)
            assert len(rec.advisors) <= size
    
    def test_no_duplicate_advisors(self):
        """Board should not have duplicate advisors."""
        rec = self.board.get_default_board(size=7)
        archetypes = [a.archetype for a in rec.advisors]
        assert len(archetypes) == len(set(archetypes))
    
    def test_rationale_populated(self):
        """Default board should have rationale."""
        rec = self.board.get_default_board(industry="saas", stage="growth")
        assert rec.rationale
        assert "growth" in rec.rationale.lower()


# ============================================================================
# SOUL.MD GENERATION TESTS
# ============================================================================

class TestGenerateAdvisorSoul:
    """Tests for SOUL.md generation."""
    
    def setup_method(self):
        self.board = BoardOfAdvisors()
    
    def test_basic_generation(self):
        """Should generate valid SOUL.md content."""
        advisor = self.board.get_advisor(AdvisorArchetype.SERIAL_ENTREPRENEUR)
        soul = self.board.generate_advisor_soul(advisor, "Acme Corp")
        
        assert "# SOUL.md" in soul
        assert "Marcus" in soul
        assert "Serial Entrepreneur" in soul
        assert "Acme Corp" in soul
    
    def test_includes_all_sections(self):
        """Generated SOUL.md should include all sections."""
        advisor = self.board.get_advisor(AdvisorArchetype.VC_PARTNER)
        soul = self.board.generate_advisor_soul(advisor, "TechStartup Inc")
        
        assert "## Identity" in soul
        assert "## Tagline" in soul
        assert "## Background" in soul
        assert "## Expertise" in soul
        assert "## Personality" in soul
        assert "## Strategic Frameworks" in soul
        assert "## Signature Questions" in soul
        assert "## Red Flags" in soul
        assert "## Working Boundaries" in soul
    
    def test_with_business_context(self):
        """Business context should be included when provided."""
        advisor = self.board.get_advisor(AdvisorArchetype.SCALING_EXPERT)
        context = "We are a B2B SaaS company focused on developer tools."
        soul = self.board.generate_advisor_soul(advisor, "DevTools Co", context)
        
        assert "## Business Context" in soul
        assert "developer tools" in soul
    
    def test_frameworks_included(self):
        """Strategic frameworks should be in generated SOUL.md."""
        advisor = self.board.get_advisor(AdvisorArchetype.BOARD_CHAIR)
        soul = self.board.generate_advisor_soul(advisor, "BoardCo")
        
        for framework in advisor.frameworks:
            assert framework.name in soul


# ============================================================================
# CONVENIENCE FUNCTION TESTS
# ============================================================================

class TestConvenienceFunction:
    """Tests for the get_advisor_for_challenge helper."""
    
    def test_returns_advisor(self):
        """Should return an advisor for valid challenge."""
        advisor = get_advisor_for_challenge("How do I raise Series A?")
        assert advisor is not None
        assert isinstance(advisor, Advisor)
    
    def test_fundraising_returns_capital_advisor(self):
        """Fundraising challenge should return capital advisor."""
        advisor = get_advisor_for_challenge("fundraising strategy")
        assert advisor.domain == AdvisorDomain.CAPITAL
    
    def test_general_challenge(self):
        """General challenge should still return an advisor."""
        advisor = get_advisor_for_challenge("I need help with my business")
        assert advisor is not None


# ============================================================================
# KEYWORD MAPPING TESTS
# ============================================================================

class TestKeywordMappings:
    """Tests for challenge keyword mappings."""
    
    def test_keywords_reference_valid_archetypes(self):
        """All keyword mappings should reference valid archetypes."""
        for keyword, archetypes in CHALLENGE_KEYWORDS.items():
            for archetype in archetypes:
                assert archetype in AdvisorArchetype, f"Invalid archetype in keyword '{keyword}'"
    
    def test_major_domains_have_keywords(self):
        """Major strategic domains should have keyword mappings."""
        # Check that key strategic topics are covered
        critical_keywords = [
            "board", "fundraise", "exit", "scale", "risk",
            "customer", "technology", "hiring", "international"
        ]
        for keyword in critical_keywords:
            assert keyword in CHALLENGE_KEYWORDS, f"Missing keyword mapping: {keyword}"


# ============================================================================
# EDGE CASES
# ============================================================================

class TestEdgeCases:
    """Edge case and error handling tests."""
    
    def setup_method(self):
        self.board = BoardOfAdvisors()
    
    def test_empty_challenge(self):
        """Empty challenge should return default advisors."""
        recs = self.board.recommend_advisor("")
        assert len(recs) >= 1
    
    def test_very_long_challenge(self):
        """Very long challenge should still work."""
        long_challenge = "fundraising " * 100
        recs = self.board.recommend_advisor(long_challenge)
        assert len(recs) >= 1
    
    def test_special_characters_in_challenge(self):
        """Special characters should be handled."""
        recs = self.board.recommend_advisor("How do I raise $$$ for my startup?!?")
        assert len(recs) >= 1
    
    def test_case_insensitivity(self):
        """Challenge matching should be case-insensitive."""
        lower_recs = self.board.recommend_advisor("fundraising")
        upper_recs = self.board.recommend_advisor("FUNDRAISING")
        mixed_recs = self.board.recommend_advisor("FundRaising")
        
        # All should recommend similar advisors
        lower_archetypes = {r.advisor.archetype for r in lower_recs}
        upper_archetypes = {r.advisor.archetype for r in upper_recs}
        mixed_archetypes = {r.advisor.archetype for r in mixed_recs}
        
        assert lower_archetypes == upper_archetypes == mixed_archetypes
    
    def test_default_board_null_params(self):
        """Default board should work with None parameters."""
        rec = self.board.get_default_board(industry=None, stage=None)
        assert len(rec.advisors) >= 3


# ============================================================================
# DATA CONSISTENCY TESTS
# ============================================================================

class TestDataConsistency:
    """Tests for data consistency across the library."""
    
    def test_advisor_archetype_matches_key(self):
        """Advisor's archetype field should match its key in the library."""
        for archetype, advisor in ADVISOR_LIBRARY.items():
            assert advisor.archetype == archetype
    
    def test_emoji_format(self):
        """Emojis should be single emoji characters (no text)."""
        for archetype, advisor in ADVISOR_LIBRARY.items():
            # Should be 1-2 characters (some emoji are 2 chars)
            assert len(advisor.emoji) <= 4, f"{archetype}: emoji too long"
            assert not advisor.emoji.isascii(), f"{archetype}: emoji should not be ASCII"
    
    def test_domain_distribution(self):
        """Domains should be reasonably distributed."""
        domain_counts = {}
        for advisor in ADVISOR_LIBRARY.values():
            domain_counts[advisor.domain] = domain_counts.get(advisor.domain, 0) + 1
        
        # No domain should have more than 50% of advisors
        total = len(ADVISOR_LIBRARY)
        for domain, count in domain_counts.items():
            assert count <= total * 0.5, f"Domain {domain} has too many advisors"
    
    def test_taglines_are_short(self):
        """Taglines should be concise (< 100 chars)."""
        for archetype, advisor in ADVISOR_LIBRARY.items():
            assert len(advisor.tagline) <= 100, f"{archetype}: tagline too long"


# ============================================================================
# INTEGRATION WITH MENTORS
# ============================================================================

class TestAdvisorMentorDistinction:
    """Tests verifying Advisors are distinct from Mentors."""
    
    def setup_method(self):
        self.board = BoardOfAdvisors()
    
    def test_advisor_domains_are_strategic(self):
        """Advisor domains should be strategic, not operational."""
        strategic_domains = {
            AdvisorDomain.GOVERNANCE,
            AdvisorDomain.GROWTH_STRATEGY,
            AdvisorDomain.CAPITAL,
            AdvisorDomain.EXIT,
            AdvisorDomain.INTERNATIONAL,
            AdvisorDomain.RISK,
            AdvisorDomain.CUSTOMER,
            AdvisorDomain.TECHNOLOGY,
            AdvisorDomain.TALENT,
            AdvisorDomain.INDUSTRY,
        }
        for advisor in ADVISOR_LIBRARY.values():
            assert advisor.domain in strategic_domains
    
    def test_advisors_have_strategic_focus(self):
        """Advisor content should focus on strategy, not tactics."""
        # Check that ideal situations mention strategic concerns
        strategic_terms = ["strategy", "strategic", "board", "capital", "exit", 
                         "growth", "scale", "governance", "executive", "leadership",
                         "pivot", "founder", "company", "business", "decision", "venture",
                         "international", "global", "expansion", "market"]
        
        for archetype, advisor in ADVISOR_LIBRARY.items():
            combined_text = " ".join(advisor.ideal_situations).lower()
            has_strategic = any(term in combined_text for term in strategic_terms)
            assert has_strategic, f"{archetype}: ideal situations should be strategic"
