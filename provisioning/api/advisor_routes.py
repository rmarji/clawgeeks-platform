"""
Board of Advisors API Routes

Endpoints for discovering and provisioning strategic advisors.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from provisioning.services.board_of_advisors import (
    BoardOfAdvisors,
    AdvisorArchetype,
    AdvisorDomain,
    Advisor,
)


router = APIRouter(prefix="/api/v1/advisors", tags=["Board of Advisors"])

# Initialize service
_board = BoardOfAdvisors()


# ============================================================================
# SCHEMAS
# ============================================================================

class FrameworkResponse(BaseModel):
    """Strategic framework used by an advisor."""
    name: str
    description: str
    when_to_use: str


class AdvisorResponse(BaseModel):
    """Advisor archetype details."""
    archetype: str
    name: str
    emoji: str
    title: str
    domain: str
    tagline: str
    background: str
    expertise: list[str]
    traits: list[str]
    communication_style: str
    strategic_questions: list[str]
    frameworks: list[FrameworkResponse]
    red_flags: list[str]
    ideal_situations: list[str]
    anti_patterns: list[str]
    
    @classmethod
    def from_advisor(cls, advisor: Advisor) -> "AdvisorResponse":
        return cls(
            archetype=advisor.archetype.value,
            name=advisor.name,
            emoji=advisor.emoji,
            title=advisor.title,
            domain=advisor.domain.value,
            tagline=advisor.tagline,
            background=advisor.background,
            expertise=advisor.expertise,
            traits=advisor.traits,
            communication_style=advisor.communication_style,
            strategic_questions=advisor.strategic_questions,
            frameworks=[
                FrameworkResponse(
                    name=f.name,
                    description=f.description,
                    when_to_use=f.when_to_use
                )
                for f in advisor.frameworks
            ],
            red_flags=advisor.red_flags,
            ideal_situations=advisor.ideal_situations,
            anti_patterns=advisor.anti_patterns
        )


class AdvisorSummary(BaseModel):
    """Brief advisor summary for listings."""
    archetype: str
    name: str
    emoji: str
    title: str
    domain: str
    tagline: str


class RecommendationRequest(BaseModel):
    """Request for advisor recommendations."""
    challenge: str = Field(..., description="Description of the strategic challenge")
    industry: str | None = Field(None, description="Optional industry context")
    max_results: int = Field(3, ge=1, le=10, description="Maximum advisors to return")


class RecommendationResponse(BaseModel):
    """Advisor recommendation with relevance."""
    advisor: AdvisorSummary
    relevance_score: float
    reasons: list[str]
    suggested_questions: list[str]


class DefaultBoardRequest(BaseModel):
    """Request for default board composition."""
    industry: str | None = Field(None, description="Business industry")
    stage: str | None = Field("growth", description="Company stage: seed, growth, scale, mature")
    size: int = Field(5, ge=3, le=7, description="Board size")


class DefaultBoardResponse(BaseModel):
    """Default board recommendation."""
    advisors: list[AdvisorSummary]
    rationale: str
    industry_context: str


class GenerateSoulRequest(BaseModel):
    """Request to generate advisor SOUL.md."""
    archetype: str = Field(..., description="Advisor archetype")
    tenant_name: str = Field(..., description="Tenant/organization name")
    business_context: str | None = Field(None, description="Optional business context")


class GenerateSoulResponse(BaseModel):
    """Generated SOUL.md content."""
    content: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=list[AdvisorSummary])
async def list_advisors():
    """List all advisor archetypes."""
    advisors = _board.get_all_advisors()
    return [
        AdvisorSummary(
            archetype=a.archetype.value,
            name=a.name,
            emoji=a.emoji,
            title=a.title,
            domain=a.domain.value,
            tagline=a.tagline
        )
        for a in advisors
    ]


@router.get("/domains", response_model=list[str])
async def list_domains():
    """List all advisor domains."""
    return [d.value for d in _board.get_all_domains()]


@router.get("/archetypes", response_model=list[str])
async def list_archetypes():
    """List all advisor archetype values."""
    return [a.value for a in AdvisorArchetype]


@router.get("/domain/{domain}", response_model=list[AdvisorSummary])
async def advisors_by_domain(domain: str):
    """Get advisors in a specific domain."""
    try:
        domain_enum = AdvisorDomain(domain)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid domain: {domain}")
    
    advisors = _board.get_advisors_by_domain(domain_enum)
    return [
        AdvisorSummary(
            archetype=a.archetype.value,
            name=a.name,
            emoji=a.emoji,
            title=a.title,
            domain=a.domain.value,
            tagline=a.tagline
        )
        for a in advisors
    ]


@router.get("/{archetype}", response_model=AdvisorResponse)
async def get_advisor(archetype: str):
    """Get detailed advisor information by archetype."""
    try:
        archetype_enum = AdvisorArchetype(archetype)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Advisor not found: {archetype}")
    
    advisor = _board.get_advisor(archetype_enum)
    if not advisor:
        raise HTTPException(status_code=404, detail=f"Advisor not found: {archetype}")
    
    return AdvisorResponse.from_advisor(advisor)


@router.post("/recommend", response_model=list[RecommendationResponse])
async def recommend_advisors(request: RecommendationRequest):
    """
    Get advisor recommendations based on a strategic challenge.
    
    Analyzes the challenge description and returns relevant advisors
    with relevance scoring and suggested questions.
    """
    recommendations = _board.recommend_advisor(
        challenge=request.challenge,
        industry=request.industry,
        max_results=request.max_results
    )
    
    return [
        RecommendationResponse(
            advisor=AdvisorSummary(
                archetype=r.advisor.archetype.value,
                name=r.advisor.name,
                emoji=r.advisor.emoji,
                title=r.advisor.title,
                domain=r.advisor.domain.value,
                tagline=r.advisor.tagline
            ),
            relevance_score=r.relevance_score,
            reasons=r.reasons,
            suggested_questions=r.suggested_questions
        )
        for r in recommendations
    ]


@router.post("/default-board", response_model=DefaultBoardResponse)
async def get_default_board(request: DefaultBoardRequest):
    """
    Get a recommended advisory board composition.
    
    Returns a balanced board based on company stage and industry.
    """
    recommendation = _board.get_default_board(
        industry=request.industry,
        stage=request.stage,
        size=request.size
    )
    
    return DefaultBoardResponse(
        advisors=[
            AdvisorSummary(
                archetype=a.archetype.value,
                name=a.name,
                emoji=a.emoji,
                title=a.title,
                domain=a.domain.value,
                tagline=a.tagline
            )
            for a in recommendation.advisors
        ],
        rationale=recommendation.rationale,
        industry_context=recommendation.industry_context
    )


@router.post("/generate-soul", response_model=GenerateSoulResponse)
async def generate_advisor_soul(request: GenerateSoulRequest):
    """
    Generate SOUL.md content for an advisor.
    
    Creates a complete SOUL.md file that can be used to provision
    an advisor agent in a tenant workspace.
    """
    try:
        archetype_enum = AdvisorArchetype(request.archetype)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid archetype: {request.archetype}")
    
    advisor = _board.get_advisor(archetype_enum)
    if not advisor:
        raise HTTPException(status_code=404, detail=f"Advisor not found: {request.archetype}")
    
    content = _board.generate_advisor_soul(
        advisor=advisor,
        tenant_name=request.tenant_name,
        business_context=request.business_context
    )
    
    return GenerateSoulResponse(content=content)


@router.get("/quick/{challenge_type}", response_model=AdvisorSummary)
async def quick_advisor_lookup(challenge_type: str):
    """
    Quick lookup for common challenge types.
    
    Examples: fundraising, exit, scaling, governance, crisis
    """
    result = _board.recommend_advisor(challenge_type, max_results=1)
    if not result:
        raise HTTPException(status_code=404, detail="No advisor found for that challenge type")
    
    advisor = result[0].advisor
    return AdvisorSummary(
        archetype=advisor.archetype.value,
        name=advisor.name,
        emoji=advisor.emoji,
        title=advisor.title,
        domain=advisor.domain.value,
        tagline=advisor.tagline
    )
