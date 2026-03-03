"""
Board of Mentors API Routes

Endpoints for discovering and consulting AI mentors.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ..auth.dependencies import require_auth
from ..services.board_of_mentors import (
    BoardOfMentors,
    BoardConfig,
    Mentor,
    MentorArchetype,
    MentorDomain,
    MentorRecommendation,
)


router = APIRouter(prefix="/api/v1/mentors", tags=["Mentors"])


# ============================================================================
# Response Models
# ============================================================================


class MentorSummary(BaseModel):
    """Brief mentor info for listings."""
    archetype: str
    name: str
    emoji: str
    domain: str
    title: str
    tagline: str
    
    @classmethod
    def from_mentor(cls, mentor: Mentor) -> "MentorSummary":
        return cls(
            archetype=mentor.archetype.value,
            name=mentor.name,
            emoji=mentor.emoji,
            domain=mentor.domain.value,
            title=mentor.title,
            tagline=mentor.tagline,
        )


class MentorDetail(BaseModel):
    """Full mentor details."""
    archetype: str
    name: str
    emoji: str
    domain: str
    title: str
    tagline: str
    expertise: list[str]
    personality: list[str]
    communication_style: str
    signature_questions: list[str]
    frameworks: list[str]
    anti_patterns: list[str]
    ideal_for: list[str]
    background: str
    
    @classmethod
    def from_mentor(cls, mentor: Mentor) -> "MentorDetail":
        return cls(
            archetype=mentor.archetype.value,
            name=mentor.name,
            emoji=mentor.emoji,
            domain=mentor.domain.value,
            title=mentor.title,
            tagline=mentor.tagline,
            expertise=mentor.expertise,
            personality=mentor.personality,
            communication_style=mentor.communication_style,
            signature_questions=mentor.signature_questions,
            frameworks=mentor.frameworks,
            anti_patterns=mentor.anti_patterns,
            ideal_for=mentor.ideal_for,
            background=mentor.background,
        )


class MentorRecommendationResponse(BaseModel):
    """Mentor recommendation with relevance context."""
    mentor: MentorSummary
    relevance_score: float
    reasons: list[str]
    suggested_questions: list[str]


class RecommendRequest(BaseModel):
    """Request for mentor recommendations."""
    challenge: str = Field(..., description="Description of the challenge or question")
    industry: Optional[str] = Field(None, description="Business industry for context")
    exclude: list[str] = Field(default_factory=list, description="Archetypes to exclude")


class GenerateSoulRequest(BaseModel):
    """Request to generate mentor SOUL.md."""
    archetype: str = Field(..., description="Mentor archetype to generate for")
    tenant_name: str = Field(..., description="Organization name")
    context: Optional[str] = Field(None, description="Optional business context")


class DefaultBoardRequest(BaseModel):
    """Request for default board recommendation."""
    industry: Optional[str] = None
    business_stage: Optional[str] = None


# ============================================================================
# Dependencies
# ============================================================================


def get_board() -> BoardOfMentors:
    """Get Board of Mentors service."""
    return BoardOfMentors()


# ============================================================================
# Public Endpoints (discovery)
# ============================================================================


@router.get("/", response_model=list[MentorSummary])
async def list_mentors(
    domain: Optional[str] = Query(None, description="Filter by domain"),
    board: BoardOfMentors = Depends(get_board),
) -> list[MentorSummary]:
    """
    List all available mentors.
    
    Optionally filter by domain (growth, fundraising, sales, etc.)
    """
    if domain:
        try:
            domain_enum = MentorDomain(domain.lower())
            mentors = board.get_mentors_by_domain(domain_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid domain: {domain}. Valid domains: {[d.value for d in MentorDomain]}"
            )
    else:
        mentors = board.get_all_mentors()
    
    return [MentorSummary.from_mentor(m) for m in mentors]


@router.get("/domains")
async def list_domains() -> list[dict]:
    """List all mentor domains with descriptions."""
    domain_descriptions = {
        MentorDomain.GROWTH: "Scaling, growth hacking, virality",
        MentorDomain.FUNDRAISING: "VC, angels, pitch decks",
        MentorDomain.SALES: "Enterprise sales, negotiations",
        MentorDomain.MARKETING: "Brand, positioning, campaigns",
        MentorDomain.PRODUCT: "Product strategy, roadmaps",
        MentorDomain.ENGINEERING: "Architecture, scaling systems",
        MentorDomain.OPERATIONS: "Process, efficiency, logistics",
        MentorDomain.FINANCE: "Accounting, cash flow, M&A",
        MentorDomain.LEGAL: "Contracts, IP, compliance",
        MentorDomain.HIRING: "Recruiting, culture, retention",
        MentorDomain.LEADERSHIP: "Management, executive presence",
        MentorDomain.WELLNESS: "Founder mental health, balance",
        MentorDomain.INDUSTRY: "Domain-specific expertise",
    }
    
    return [
        {"domain": d.value, "description": domain_descriptions.get(d, "")}
        for d in MentorDomain
    ]


@router.get("/archetypes")
async def list_archetypes() -> list[dict]:
    """List all mentor archetypes with brief descriptions."""
    board = BoardOfMentors()
    return [
        {
            "archetype": m.archetype.value,
            "name": m.name,
            "emoji": m.emoji,
            "title": m.title,
            "tagline": m.tagline,
        }
        for m in board.get_all_mentors()
    ]


@router.get("/{archetype}", response_model=MentorDetail)
async def get_mentor(
    archetype: str,
    board: BoardOfMentors = Depends(get_board),
) -> MentorDetail:
    """Get detailed info about a specific mentor."""
    try:
        archetype_enum = MentorArchetype(archetype.lower())
    except ValueError:
        raise HTTPException(
            status_code=404,
            detail=f"Mentor not found: {archetype}"
        )
    
    mentor = board.get_mentor(archetype_enum)
    if not mentor:
        raise HTTPException(status_code=404, detail=f"Mentor not found: {archetype}")
    
    return MentorDetail.from_mentor(mentor)


@router.get("/industry/{industry}", response_model=list[MentorSummary])
async def get_mentors_for_industry(
    industry: str,
    board: BoardOfMentors = Depends(get_board),
) -> list[MentorSummary]:
    """Get recommended mentors for a specific industry."""
    mentors = board.get_mentors_for_industry(industry)
    if not mentors:
        # Return generic mentors if no industry-specific ones
        mentors = board.get_default_board()
    
    return [MentorSummary.from_mentor(m) for m in mentors]


# ============================================================================
# Authenticated Endpoints (recommendations, generation)
# ============================================================================


@router.post("/recommend", response_model=list[MentorRecommendationResponse])
async def recommend_mentors(
    request: RecommendRequest,
    board: BoardOfMentors = Depends(get_board),
    _user = Depends(require_auth),
) -> list[MentorRecommendationResponse]:
    """
    Get mentor recommendations for a specific challenge.
    
    Analyzes the challenge description and matches to mentor expertise.
    """
    # Convert exclude list to archetypes
    exclude_archetypes = []
    for arch in request.exclude:
        try:
            exclude_archetypes.append(MentorArchetype(arch.lower()))
        except ValueError:
            pass  # Ignore invalid archetypes
    
    recommendations = board.recommend_mentor(
        challenge=request.challenge,
        industry=request.industry,
        current_mentors=exclude_archetypes,
    )
    
    return [
        MentorRecommendationResponse(
            mentor=MentorSummary.from_mentor(rec.mentor),
            relevance_score=rec.relevance_score,
            reasons=rec.reasons,
            suggested_questions=rec.suggested_questions,
        )
        for rec in recommendations
    ]


@router.post("/default-board", response_model=list[MentorSummary])
async def get_default_board(
    request: DefaultBoardRequest,
    board: BoardOfMentors = Depends(get_board),
    _user = Depends(require_auth),
) -> list[MentorSummary]:
    """
    Get a recommended default board of mentors.
    
    Based on industry and business stage, returns a curated set of mentors.
    """
    mentors = board.get_default_board(
        industry=request.industry,
        business_stage=request.business_stage,
    )
    return [MentorSummary.from_mentor(m) for m in mentors]


@router.post("/generate-soul")
async def generate_mentor_soul(
    request: GenerateSoulRequest,
    board: BoardOfMentors = Depends(get_board),
    _user = Depends(require_auth),
) -> dict:
    """
    Generate a SOUL.md file for a mentor.
    
    Returns the SOUL.md content ready to be saved to a tenant's workspace.
    """
    try:
        archetype_enum = MentorArchetype(request.archetype.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid archetype: {request.archetype}"
        )
    
    mentor = board.get_mentor(archetype_enum)
    if not mentor:
        raise HTTPException(status_code=404, detail=f"Mentor not found: {request.archetype}")
    
    soul_content = board.generate_mentor_soul(
        mentor=mentor,
        tenant_name=request.tenant_name,
        organization_context=request.context,
    )
    
    return {
        "archetype": request.archetype,
        "mentor_name": mentor.name,
        "soul_md": soul_content,
    }


# ============================================================================
# Industry-specific shortcuts
# ============================================================================


@router.get("/quick/{challenge_type}", response_model=MentorDetail)
async def quick_mentor_lookup(
    challenge_type: str,
    board: BoardOfMentors = Depends(get_board),
) -> MentorDetail:
    """
    Quick lookup for common challenge types.
    
    Challenge types: growth, fundraising, sales, product, engineering,
    operations, finance, legal, hiring, leadership, wellness, pricing,
    churn, hiring, pitch
    """
    # Map quick lookups to archetypes
    quick_map = {
        "growth": MentorArchetype.THE_GROWTH_HACKER,
        "fundraising": MentorArchetype.THE_DEALMAKER,
        "sales": MentorArchetype.THE_CLOSER,
        "product": MentorArchetype.THE_VISIONARY,
        "engineering": MentorArchetype.THE_ARCHITECT,
        "tech": MentorArchetype.THE_ARCHITECT,
        "operations": MentorArchetype.THE_SYSTEMATIZER,
        "ops": MentorArchetype.THE_SYSTEMATIZER,
        "finance": MentorArchetype.THE_CFO_WHISPERER,
        "money": MentorArchetype.THE_CFO_WHISPERER,
        "legal": MentorArchetype.THE_CONTRACT_SAGE,
        "contracts": MentorArchetype.THE_CONTRACT_SAGE,
        "hiring": MentorArchetype.THE_TALENT_MAGNET,
        "recruiting": MentorArchetype.THE_TALENT_MAGNET,
        "team": MentorArchetype.THE_TALENT_MAGNET,
        "leadership": MentorArchetype.THE_EXECUTIVE_COACH,
        "management": MentorArchetype.THE_EXECUTIVE_COACH,
        "wellness": MentorArchetype.THE_BURNOUT_PREVENTER,
        "burnout": MentorArchetype.THE_BURNOUT_PREVENTER,
        "stress": MentorArchetype.THE_BURNOUT_PREVENTER,
        "pitch": MentorArchetype.THE_PITCH_COACH,
        "deck": MentorArchetype.THE_PITCH_COACH,
        "pricing": MentorArchetype.THE_SAAS_SAGE,
        "churn": MentorArchetype.THE_SAAS_SAGE,
        "saas": MentorArchetype.THE_SAAS_SAGE,
        "ai": MentorArchetype.THE_AI_ORACLE,
        "ml": MentorArchetype.THE_AI_ORACLE,
        "ecommerce": MentorArchetype.THE_ECOMMERCE_EXPERT,
        "marketplace": MentorArchetype.THE_MARKETPLACE_MAVEN,
        "first-time": MentorArchetype.THE_FIRST_TIME_FOUNDER_GUIDE,
        "beginner": MentorArchetype.THE_FIRST_TIME_FOUNDER_GUIDE,
    }
    
    archetype = quick_map.get(challenge_type.lower())
    if not archetype:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown challenge type: {challenge_type}. Try: {list(quick_map.keys())}"
        )
    
    mentor = board.get_mentor(archetype)
    if not mentor:
        raise HTTPException(status_code=500, detail="Mentor lookup failed")
    
    return MentorDetail.from_mentor(mentor)
