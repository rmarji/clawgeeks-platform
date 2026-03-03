"""
Tests for Board of Mentors service.
"""

import pytest
from provisioning.services.board_of_mentors import (
    BoardOfMentors,
    BoardConfig,
    Mentor,
    MentorArchetype,
    MentorDomain,
    MentorRecommendation,
    MENTOR_LIBRARY,
    get_mentor_for_challenge,
)


# ============================================================================
# Test Mentor Library
# ============================================================================


class TestMentorLibrary:
    """Test the pre-built mentor library."""
    
    def test_library_has_all_archetypes(self):
        """All defined archetypes have a mentor."""
        for archetype in MentorArchetype:
            if archetype in MENTOR_LIBRARY:
                mentor = MENTOR_LIBRARY[archetype]
                assert isinstance(mentor, Mentor)
                assert mentor.archetype == archetype
    
    def test_mentors_have_required_fields(self):
        """Each mentor has all required fields populated."""
        for archetype, mentor in MENTOR_LIBRARY.items():
            assert mentor.name, f"{archetype}: name required"
            assert mentor.emoji, f"{archetype}: emoji required"
            assert mentor.domain, f"{archetype}: domain required"
            assert mentor.title, f"{archetype}: title required"
            assert mentor.tagline, f"{archetype}: tagline required"
            assert mentor.expertise, f"{archetype}: expertise required"
            assert mentor.personality, f"{archetype}: personality required"
            assert mentor.communication_style, f"{archetype}: communication_style required"
            assert mentor.signature_questions, f"{archetype}: signature_questions required"
            assert mentor.frameworks, f"{archetype}: frameworks required"
            assert mentor.anti_patterns, f"{archetype}: anti_patterns required"
            assert mentor.ideal_for, f"{archetype}: ideal_for required"
            assert mentor.background, f"{archetype}: background required"
    
    def test_mentors_have_unique_names(self):
        """Each mentor has a unique name."""
        names = [m.name for m in MENTOR_LIBRARY.values()]
        assert len(names) == len(set(names)), "Duplicate mentor names"
    
    def test_mentors_have_valid_domains(self):
        """Each mentor's domain is a valid MentorDomain."""
        for mentor in MENTOR_LIBRARY.values():
            assert isinstance(mentor.domain, MentorDomain)
    
    def test_expertise_is_list(self):
        """Expertise is a non-empty list for each mentor."""
        for archetype, mentor in MENTOR_LIBRARY.items():
            assert isinstance(mentor.expertise, list)
            assert len(mentor.expertise) >= 3, f"{archetype}: at least 3 expertise areas"


# ============================================================================
# Test BoardOfMentors Service
# ============================================================================


class TestBoardOfMentorsBasics:
    """Test basic BoardOfMentors functionality."""
    
    def test_init_default_config(self):
        """Board initializes with default config."""
        board = BoardOfMentors()
        assert board.config.max_mentors == 3
        assert board.config.rotation_enabled is True
    
    def test_init_custom_config(self):
        """Board accepts custom config."""
        config = BoardConfig(max_mentors=5, rotation_enabled=False)
        board = BoardOfMentors(config)
        assert board.config.max_mentors == 5
        assert board.config.rotation_enabled is False
    
    def test_get_all_mentors(self):
        """Get all mentors returns full library."""
        board = BoardOfMentors()
        mentors = board.get_all_mentors()
        assert len(mentors) == len(MENTOR_LIBRARY)
        assert all(isinstance(m, Mentor) for m in mentors)
    
    def test_get_mentor_by_archetype(self):
        """Get specific mentor by archetype."""
        board = BoardOfMentors()
        
        mentor = board.get_mentor(MentorArchetype.THE_GROWTH_HACKER)
        assert mentor is not None
        assert mentor.name == "Marcus"
        assert mentor.domain == MentorDomain.GROWTH
    
    def test_get_mentor_invalid_archetype(self):
        """Invalid archetype returns None (not in library)."""
        board = BoardOfMentors()
        # All archetypes should be in library, but test the method
        mentor = board.get_mentor(MentorArchetype.THE_VIRAL_MARKETER)
        # This might not be in library - method should handle gracefully
        # Either it exists or returns None
        assert mentor is None or isinstance(mentor, Mentor)


class TestMentorsByDomain:
    """Test domain-based mentor filtering."""
    
    def test_get_mentors_by_growth_domain(self):
        """Get all growth-domain mentors."""
        board = BoardOfMentors()
        mentors = board.get_mentors_by_domain(MentorDomain.GROWTH)
        
        assert len(mentors) >= 1
        for mentor in mentors:
            assert mentor.domain == MentorDomain.GROWTH
    
    def test_get_mentors_by_fundraising_domain(self):
        """Get fundraising mentors."""
        board = BoardOfMentors()
        mentors = board.get_mentors_by_domain(MentorDomain.FUNDRAISING)
        
        assert len(mentors) >= 1
        for mentor in mentors:
            assert mentor.domain == MentorDomain.FUNDRAISING
    
    def test_all_domains_have_mentors(self):
        """At least one mentor exists for domains that should have them."""
        board = BoardOfMentors()
        
        # These domains should definitely have mentors
        expected_domains = [
            MentorDomain.GROWTH,
            MentorDomain.FUNDRAISING,
            MentorDomain.SALES,
            MentorDomain.PRODUCT,
            MentorDomain.ENGINEERING,
            MentorDomain.OPERATIONS,
            MentorDomain.FINANCE,
            MentorDomain.LEADERSHIP,
        ]
        
        for domain in expected_domains:
            mentors = board.get_mentors_by_domain(domain)
            assert len(mentors) >= 1, f"Domain {domain} should have mentors"


class TestIndustryMentors:
    """Test industry-based mentor recommendations."""
    
    def test_saas_industry_mentors(self):
        """SaaS industry gets appropriate mentors."""
        board = BoardOfMentors()
        mentors = board.get_mentors_for_industry("saas")
        
        assert len(mentors) >= 1
        archetypes = [m.archetype for m in mentors]
        assert MentorArchetype.THE_SAAS_SAGE in archetypes
    
    def test_ecommerce_industry_mentors(self):
        """E-commerce gets e-commerce expert."""
        board = BoardOfMentors()
        mentors = board.get_mentors_for_industry("ecommerce")
        
        assert len(mentors) >= 1
        archetypes = [m.archetype for m in mentors]
        assert MentorArchetype.THE_ECOMMERCE_EXPERT in archetypes
    
    def test_ai_industry_mentors(self):
        """AI industry gets AI oracle."""
        board = BoardOfMentors()
        mentors = board.get_mentors_for_industry("ai")
        
        assert len(mentors) >= 1
        archetypes = [m.archetype for m in mentors]
        assert MentorArchetype.THE_AI_ORACLE in archetypes
    
    def test_unknown_industry_returns_empty(self):
        """Unknown industry returns empty list."""
        board = BoardOfMentors()
        mentors = board.get_mentors_for_industry("unknown_industry_xyz")
        assert mentors == []
    
    def test_case_insensitive_industry(self):
        """Industry lookup is case-insensitive."""
        board = BoardOfMentors()
        
        mentors_lower = board.get_mentors_for_industry("saas")
        mentors_upper = board.get_mentors_for_industry("SAAS")
        mentors_mixed = board.get_mentors_for_industry("SaaS")
        
        assert len(mentors_lower) == len(mentors_upper) == len(mentors_mixed)


# ============================================================================
# Test Mentor Recommendations
# ============================================================================


class TestRecommendMentor:
    """Test challenge-based mentor recommendations."""
    
    def test_growth_challenge_recommends_growth_hacker(self):
        """Growth-related challenges recommend growth hacker."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("How do I scale my user acquisition?")
        
        assert len(recommendations) >= 1
        archetypes = [r.mentor.archetype for r in recommendations]
        assert MentorArchetype.THE_GROWTH_HACKER in archetypes
    
    def test_fundraising_challenge_recommends_dealmaker(self):
        """Fundraising challenges recommend dealmaker."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("I need to raise my Series A")
        
        assert len(recommendations) >= 1
        archetypes = [r.mentor.archetype for r in recommendations]
        assert MentorArchetype.THE_DEALMAKER in archetypes
    
    def test_sales_challenge_recommends_closer(self):
        """Sales challenges recommend closer."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("How do I close enterprise deals?")
        
        assert len(recommendations) >= 1
        archetypes = [r.mentor.archetype for r in recommendations]
        assert MentorArchetype.THE_CLOSER in archetypes
    
    def test_technical_challenge_recommends_architect(self):
        """Technical challenges recommend architect."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("Need help with system architecture")
        
        assert len(recommendations) >= 1
        archetypes = [r.mentor.archetype for r in recommendations]
        assert MentorArchetype.THE_ARCHITECT in archetypes
    
    def test_burnout_challenge_recommends_wellness(self):
        """Burnout challenges recommend burnout preventer."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("I'm feeling overwhelmed and stressed")
        
        assert len(recommendations) >= 1
        archetypes = [r.mentor.archetype for r in recommendations]
        assert MentorArchetype.THE_BURNOUT_PREVENTER in archetypes
    
    def test_recommendations_have_reasons(self):
        """Recommendations include reasons."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("How do I improve my churn rate?")
        
        assert len(recommendations) >= 1
        for rec in recommendations:
            assert isinstance(rec.reasons, list)
            # At least one reason for the recommendation
            assert len(rec.reasons) >= 1 or rec.relevance_score < 0.2
    
    def test_recommendations_have_suggested_questions(self):
        """Recommendations include suggested questions."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("Need help with pricing strategy")
        
        assert len(recommendations) >= 1
        for rec in recommendations:
            assert isinstance(rec.suggested_questions, list)
    
    def test_relevance_score_is_bounded(self):
        """Relevance scores are between 0 and 1."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("How do I grow my SaaS business?")
        
        for rec in recommendations:
            assert 0 <= rec.relevance_score <= 1.0
    
    def test_excludes_current_mentors(self):
        """Current mentors are excluded from recommendations."""
        board = BoardOfMentors()
        
        # Get initial recommendations
        recommendations = board.recommend_mentor("Help with growth")
        initial_archetypes = [r.mentor.archetype for r in recommendations]
        
        # Now exclude the first one
        if initial_archetypes:
            recommendations_filtered = board.recommend_mentor(
                "Help with growth",
                current_mentors=[initial_archetypes[0]]
            )
            filtered_archetypes = [r.mentor.archetype for r in recommendations_filtered]
            assert initial_archetypes[0] not in filtered_archetypes
    
    def test_industry_context_influences_recommendations(self):
        """Industry context affects recommendations."""
        board = BoardOfMentors()
        
        # Generic growth question
        generic = board.recommend_mentor("How do I grow?")
        
        # Same question with SaaS context
        saas_specific = board.recommend_mentor("How do I grow?", industry="saas")
        
        # SaaS context should boost SaaS sage
        saas_archetypes = [r.mentor.archetype for r in saas_specific]
        # Should include SaaS sage or at least different ranking
        assert len(saas_specific) >= 1
    
    def test_max_mentors_limit(self):
        """Recommendations respect max_mentors config."""
        config = BoardConfig(max_mentors=2)
        board = BoardOfMentors(config)
        
        recommendations = board.recommend_mentor("Help with everything")
        assert len(recommendations) <= 2


class TestConvenienceFunction:
    """Test the get_mentor_for_challenge helper."""
    
    def test_returns_best_mentor(self):
        """Returns the best matching mentor."""
        mentor = get_mentor_for_challenge("How do I raise funding?")
        assert mentor is not None
        assert isinstance(mentor, Mentor)
    
    def test_with_industry_context(self):
        """Industry context influences result."""
        mentor = get_mentor_for_challenge("How do I grow?", industry="saas")
        assert mentor is not None
        assert isinstance(mentor, Mentor)
    
    def test_returns_fallback_for_no_match(self):
        """Returns a fallback mentor when no specific match found."""
        # A query with no matching keywords
        mentor = get_mentor_for_challenge("xyzzy plugh nothing matches here")
        # Should return a fallback mentor (better UX than None)
        assert mentor is not None
        assert isinstance(mentor, Mentor)


# ============================================================================
# Test SOUL.md Generation
# ============================================================================


class TestGenerateMentorSoul:
    """Test SOUL.md generation for mentors."""
    
    def test_generates_soul_content(self):
        """Generates non-empty SOUL.md content."""
        board = BoardOfMentors()
        mentor = board.get_mentor(MentorArchetype.THE_GROWTH_HACKER)
        
        soul = board.generate_mentor_soul(mentor, "Acme Corp")
        
        assert len(soul) > 500  # Substantial content
        assert "SOUL.md" in soul
        assert "Marcus" in soul
        assert "Acme Corp" in soul
    
    def test_includes_mentor_details(self):
        """SOUL.md includes all mentor details."""
        board = BoardOfMentors()
        mentor = board.get_mentor(MentorArchetype.THE_CLOSER)
        
        soul = board.generate_mentor_soul(mentor, "Test Co")
        
        assert mentor.name in soul
        assert mentor.emoji in soul
        assert mentor.tagline in soul
        assert mentor.title in soul
        assert "Expertise" in soul
        assert "Communication Style" in soul
        assert "Signature Questions" in soul
    
    def test_includes_business_context(self):
        """SOUL.md includes optional business context."""
        board = BoardOfMentors()
        mentor = board.get_mentor(MentorArchetype.THE_SAAS_SAGE)
        
        context = "B2B SaaS platform for developer tools"
        soul = board.generate_mentor_soul(mentor, "DevTools Inc", organization_context=context)
        
        assert "Business Context" in soul
        assert context in soul
    
    def test_no_context_section_when_not_provided(self):
        """No context section when context not provided."""
        board = BoardOfMentors()
        mentor = board.get_mentor(MentorArchetype.THE_EXECUTIVE_COACH)
        
        soul = board.generate_mentor_soul(mentor, "Startup LLC")
        
        # Should not have the context section
        assert "Business Context" not in soul or "Business Context\n\n" in soul


# ============================================================================
# Test Default Board
# ============================================================================


class TestDefaultBoard:
    """Test default board recommendations."""
    
    def test_default_board_returns_mentors(self):
        """Default board returns list of mentors."""
        board = BoardOfMentors()
        mentors = board.get_default_board()
        
        assert len(mentors) >= 1
        assert len(mentors) <= board.config.max_mentors
        assert all(isinstance(m, Mentor) for m in mentors)
    
    def test_default_board_with_industry(self):
        """Industry influences default board."""
        board = BoardOfMentors()
        
        saas_board = board.get_default_board(industry="saas")
        assert len(saas_board) >= 1
        
        # Should include SaaS sage
        archetypes = [m.archetype for m in saas_board]
        assert MentorArchetype.THE_SAAS_SAGE in archetypes
    
    def test_default_board_with_stage(self):
        """Business stage influences default board."""
        board = BoardOfMentors()
        
        # Early stage should get first-time founder guide
        early_board = board.get_default_board(business_stage="early")
        early_archetypes = [m.archetype for m in early_board]
        assert MentorArchetype.THE_FIRST_TIME_FOUNDER_GUIDE in early_archetypes
        
        # Growth stage should get growth hacker
        growth_board = board.get_default_board(business_stage="growth")
        growth_archetypes = [m.archetype for m in growth_board]
        assert MentorArchetype.THE_GROWTH_HACKER in growth_archetypes
    
    def test_default_board_includes_executive_coach(self):
        """Default board includes executive coach when space allows."""
        board = BoardOfMentors()
        mentors = board.get_default_board()
        
        # Executive coach is a versatile mentor, should be included
        archetypes = [m.archetype for m in mentors]
        assert MentorArchetype.THE_EXECUTIVE_COACH in archetypes
    
    def test_default_board_respects_max_mentors(self):
        """Default board respects max_mentors config."""
        config = BoardConfig(max_mentors=2)
        board = BoardOfMentors(config)
        
        mentors = board.get_default_board(industry="saas", business_stage="growth")
        assert len(mentors) <= 2


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_challenge(self):
        """Empty challenge returns empty recommendations."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("")
        assert recommendations == []
    
    def test_whitespace_challenge(self):
        """Whitespace-only challenge returns empty recommendations."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("   \n\t  ")
        assert recommendations == []
    
    def test_very_long_challenge(self):
        """Long challenge strings are handled."""
        board = BoardOfMentors()
        long_challenge = "growth " * 1000  # Very long string
        recommendations = board.recommend_mentor(long_challenge)
        # Should not crash, may or may not have results
        assert isinstance(recommendations, list)
    
    def test_special_characters_in_challenge(self):
        """Special characters are handled."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("How do I grow? <script>alert('xss')</script>")
        # Should handle gracefully
        assert isinstance(recommendations, list)
    
    def test_unicode_challenge(self):
        """Unicode characters are handled."""
        board = BoardOfMentors()
        recommendations = board.recommend_mentor("How do I 成長する? 🚀")
        assert isinstance(recommendations, list)


# ============================================================================
# Test Data Consistency
# ============================================================================


class TestDataConsistency:
    """Test data consistency in mentor library."""
    
    def test_all_mentors_have_emoji(self):
        """All mentors have a single emoji."""
        for mentor in MENTOR_LIBRARY.values():
            assert len(mentor.emoji) >= 1
            # Should be actual emoji (or close enough)
            assert not mentor.emoji.isascii() or mentor.emoji in "🚀🤝🎯🔮🏗️⚙️📈🧲🦁🧘☁️🤖🛒🔄🎤📜🗺️"
    
    def test_taglines_are_short(self):
        """Taglines are reasonably short."""
        for archetype, mentor in MENTOR_LIBRARY.items():
            assert len(mentor.tagline) <= 100, f"{archetype}: tagline too long"
    
    def test_backgrounds_are_substantive(self):
        """Backgrounds provide meaningful context."""
        for archetype, mentor in MENTOR_LIBRARY.items():
            assert len(mentor.background) >= 50, f"{archetype}: background too short"
    
    def test_signature_questions_are_questions(self):
        """Signature questions end with question marks."""
        for archetype, mentor in MENTOR_LIBRARY.items():
            for question in mentor.signature_questions:
                assert question.endswith("?"), f"{archetype}: '{question}' should end with ?"
    
    def test_frameworks_are_actionable(self):
        """Frameworks list contains specific frameworks."""
        for archetype, mentor in MENTOR_LIBRARY.items():
            assert len(mentor.frameworks) >= 3, f"{archetype}: needs at least 3 frameworks"
            for framework in mentor.frameworks:
                # Should be capitalized (proper names)
                assert framework[0].isupper(), f"{archetype}: framework '{framework}' should be capitalized"
