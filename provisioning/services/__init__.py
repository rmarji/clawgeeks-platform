"""Provisioning services."""

from .coolify import CoolifyClient
from .provisioner import Provisioner, ProvisioningError, TenantNotFoundError
from .agent_provisioner import (
    AgentProvisioner,
    AgentConfig,
    AgentRole,
    ModelTier,
    WorkspaceConfig,
)
from .hr_department import (
    HRDepartment,
    BusinessProfile,
    Industry,
    BusinessStage,
    BusinessGoal,
    TeamRecommendation,
    AgentRecommendation,
    auto_recruit,
)
from .board_of_mentors import (
    BoardOfMentors,
    BoardConfig,
    Mentor,
    MentorArchetype,
    MentorDomain,
    MentorRecommendation,
    get_mentor_for_challenge,
)
from .board_of_advisors import (
    BoardOfAdvisors,
    Advisor,
    AdvisorArchetype,
    AdvisorDomain,
    AdvisorRecommendation,
    DefaultBoardRecommendation,
    get_advisor_for_challenge,
)

__all__ = [
    # Core provisioning
    "CoolifyClient",
    "Provisioner",
    "ProvisioningError",
    "TenantNotFoundError",
    # Agent provisioning
    "AgentProvisioner",
    "AgentConfig",
    "AgentRole",
    "ModelTier",
    "WorkspaceConfig",
    # HR Department
    "HRDepartment",
    "BusinessProfile",
    "Industry",
    "BusinessStage",
    "BusinessGoal",
    "TeamRecommendation",
    "AgentRecommendation",
    "auto_recruit",
    # Board of Mentors
    "BoardOfMentors",
    "BoardConfig",
    "Mentor",
    "MentorArchetype",
    "MentorDomain",
    "MentorRecommendation",
    "get_mentor_for_challenge",
    # Board of Advisors
    "BoardOfAdvisors",
    "Advisor",
    "AdvisorArchetype",
    "AdvisorDomain",
    "AdvisorRecommendation",
    "DefaultBoardRecommendation",
    "get_advisor_for_challenge",
]
