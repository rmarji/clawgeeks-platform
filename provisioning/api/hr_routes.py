"""
HR Department API routes.

Endpoints for business analysis and agent team recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.hr_department import (
    HRDepartment,
    BusinessProfile,
    Industry,
    BusinessStage,
    BusinessGoal,
    TeamRecommendation,
)
from ..auth.dependencies import require_auth, require_admin
from ..auth.schemas import UserRead


router = APIRouter(prefix="/api/v1/hr", tags=["HR Department"])


# Request/Response schemas

class AnalyzeBusinessRequest(BaseModel):
    """Request to analyze a business."""
    name: str = Field(..., description="Business name")
    description: str = Field(..., description="Business description (free text)")
    team_size: int = Field(1, ge=1, description="Number of human team members")
    has_technical: bool = Field(False, description="Team has technical skills")
    has_marketing: bool = Field(False, description="Team has marketing experience")
    has_sales: bool = Field(False, description="Team has sales experience")
    budget_tier: str = Field("starter", description="Subscription tier")

    model_config = {"json_schema_extra": {
        "example": {
            "name": "Acme Corp",
            "description": "We're a SaaS startup building project management tools for remote teams",
            "team_size": 2,
            "has_technical": True,
            "has_marketing": False,
            "has_sales": False,
            "budget_tier": "pro"
        }
    }}


class QuestionnaireRequest(BaseModel):
    """Request with questionnaire responses."""
    name: str = Field(..., description="Business name")
    responses: dict[str, str] = Field(..., description="Questionnaire responses")
    budget_tier: str = Field("starter", description="Subscription tier")

    model_config = {"json_schema_extra": {
        "example": {
            "name": "Acme Corp",
            "responses": {
                "description": "We build software tools for developers",
                "industry": "saas",
                "stage": "early",
                "goals": "grow_revenue, improve_product",
                "team_size": "2",
                "has_technical": "yes"
            },
            "budget_tier": "pro"
        }
    }}


class BusinessProfileResponse(BaseModel):
    """Analyzed business profile."""
    name: str
    description: str
    industry: str
    industry_description: str
    stage: str
    goals: list[str]
    team_size: int
    has_technical_founder: bool
    has_marketing_experience: bool
    has_sales_experience: bool
    budget_tier: str
    needs_technical: bool
    needs_marketing: bool
    needs_sales: bool
    needs_finance: bool
    needs_operations: bool
    needs_research: bool
    needs_design: bool
    needs_support: bool


class AgentRecommendationResponse(BaseModel):
    """Single agent recommendation."""
    role: str
    priority: int
    rationale: str
    is_essential: bool


class TeamRecommendationResponse(BaseModel):
    """Complete team recommendation."""
    agents: list[AgentRecommendationResponse]
    summary: str
    warnings: list[str]
    suggestions: list[str]


class FullAnalysisResponse(BaseModel):
    """Full analysis with profile and recommendations."""
    profile: BusinessProfileResponse
    recommendation: TeamRecommendationResponse


class QuestionnairePrompt(BaseModel):
    """Single questionnaire prompt."""
    key: str
    prompt: str
    required: bool = False
    options: list[str] | None = None
    multi: bool = False
    type: str = "text"


class QuestionnairePromptsResponse(BaseModel):
    """All questionnaire prompts."""
    prompts: list[QuestionnairePrompt]


class IndustryInfo(BaseModel):
    """Industry information."""
    id: str
    name: str
    description: str


class IndustriesResponse(BaseModel):
    """List of supported industries."""
    industries: list[IndustryInfo]


# Dependency
def get_hr_department() -> HRDepartment:
    """Get HR Department instance."""
    return HRDepartment()


# Helper functions
def profile_to_response(profile: BusinessProfile, hr: HRDepartment) -> BusinessProfileResponse:
    """Convert BusinessProfile to response model."""
    return BusinessProfileResponse(
        name=profile.name,
        description=profile.description,
        industry=profile.industry.value,
        industry_description=hr.get_industry_description(profile.industry),
        stage=profile.stage.value,
        goals=[g.value for g in profile.goals],
        team_size=profile.team_size,
        has_technical_founder=profile.has_technical_founder,
        has_marketing_experience=profile.has_marketing_experience,
        has_sales_experience=profile.has_sales_experience,
        budget_tier=profile.budget_tier,
        needs_technical=profile.needs_technical,
        needs_marketing=profile.needs_marketing,
        needs_sales=profile.needs_sales,
        needs_finance=profile.needs_finance,
        needs_operations=profile.needs_operations,
        needs_research=profile.needs_research,
        needs_design=profile.needs_design,
        needs_support=profile.needs_support,
    )


def recommendation_to_response(recommendation: TeamRecommendation) -> TeamRecommendationResponse:
    """Convert TeamRecommendation to response model."""
    return TeamRecommendationResponse(
        agents=[
            AgentRecommendationResponse(
                role=r.role.value,
                priority=r.priority,
                rationale=r.rationale,
                is_essential=r.is_essential,
            )
            for r in recommendation.agents
        ],
        summary=recommendation.summary,
        warnings=recommendation.warnings,
        suggestions=recommendation.suggestions,
    )


# Routes

@router.get(
    "/questionnaire",
    response_model=QuestionnairePromptsResponse,
    summary="Get questionnaire prompts",
    description="Returns the questionnaire prompts for onboarding flow.",
)
async def get_questionnaire(
    hr: HRDepartment = Depends(get_hr_department),
) -> QuestionnairePromptsResponse:
    """Get questionnaire prompts for onboarding."""
    prompts = hr.get_questionnaire_prompts()
    return QuestionnairePromptsResponse(
        prompts=[
            QuestionnairePrompt(
                key=p["key"],
                prompt=p["prompt"],
                required=p.get("required", False),
                options=p.get("options"),
                multi=p.get("multi", False),
                type=p.get("type", "text"),
            )
            for p in prompts
        ]
    )


@router.get(
    "/industries",
    response_model=IndustriesResponse,
    summary="List supported industries",
    description="Returns list of all supported industry classifications.",
)
async def list_industries(
    hr: HRDepartment = Depends(get_hr_department),
) -> IndustriesResponse:
    """List all supported industries."""
    industries = [
        IndustryInfo(
            id=industry.value,
            name=industry.value.replace("_", " ").title(),
            description=hr.get_industry_description(industry),
        )
        for industry in Industry
    ]
    return IndustriesResponse(industries=industries)


@router.post(
    "/analyze",
    response_model=FullAnalysisResponse,
    summary="Analyze business and recommend team",
    description="Analyzes a business description and recommends an optimal agent team.",
)
async def analyze_business(
    request: AnalyzeBusinessRequest,
    hr: HRDepartment = Depends(get_hr_department),
    user: UserRead = Depends(require_auth),
) -> FullAnalysisResponse:
    """Analyze business and get team recommendation."""
    # Validate tier
    if request.budget_tier not in hr.TIER_LIMITS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tier. Must be one of: {list(hr.TIER_LIMITS.keys())}",
        )
    
    # Analyze business
    profile = hr.analyze_business(
        name=request.name,
        description=request.description,
        team_size=request.team_size,
        has_technical=request.has_technical,
        has_marketing=request.has_marketing,
        has_sales=request.has_sales,
        budget_tier=request.budget_tier,
    )
    
    # Get recommendation
    recommendation = hr.recommend_team(profile)
    
    return FullAnalysisResponse(
        profile=profile_to_response(profile, hr),
        recommendation=recommendation_to_response(recommendation),
    )


@router.post(
    "/analyze/questionnaire",
    response_model=FullAnalysisResponse,
    summary="Analyze from questionnaire responses",
    description="Analyzes questionnaire responses and recommends an optimal agent team.",
)
async def analyze_from_questionnaire(
    request: QuestionnaireRequest,
    hr: HRDepartment = Depends(get_hr_department),
    user: UserRead = Depends(require_auth),
) -> FullAnalysisResponse:
    """Analyze from questionnaire and get team recommendation."""
    # Validate tier
    if request.budget_tier not in hr.TIER_LIMITS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid tier. Must be one of: {list(hr.TIER_LIMITS.keys())}",
        )
    
    # Process questionnaire
    profile = hr.questionnaire_to_profile(
        name=request.name,
        responses=request.responses,
        budget_tier=request.budget_tier,
    )
    
    # Get recommendation
    recommendation = hr.recommend_team(profile)
    
    return FullAnalysisResponse(
        profile=profile_to_response(profile, hr),
        recommendation=recommendation_to_response(recommendation),
    )


@router.get(
    "/stages",
    summary="List business stages",
    description="Returns list of all business stage classifications.",
)
async def list_stages() -> dict:
    """List all business stages."""
    return {
        "stages": [
            {"id": stage.value, "name": stage.value.replace("_", " ").title()}
            for stage in BusinessStage
        ]
    }


@router.get(
    "/goals",
    summary="List business goals",
    description="Returns list of all business goal classifications.",
)
async def list_goals() -> dict:
    """List all business goals."""
    return {
        "goals": [
            {"id": goal.value, "name": goal.value.replace("_", " ").title()}
            for goal in BusinessGoal
        ]
    }
