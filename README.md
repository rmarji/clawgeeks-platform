# ClawGeeks Hosting Platform

**Status:** 🟠 BUILD  
**Spec:** `../carapace/specs/clawgeeks-hosting-platform.md`

## Overview

Managed OpenClaw hosting with unique differentiators:
- **ShipOS** — Built-in productivity system
- **Multi-Agent** — Teams of agents, not single agents
- **HR Department** — Auto-recruits/configures agents
- **Board of Mentors/Advisors** — Domain expert AI counsel

## Architecture

```
clawgeeks-platform/
├── provisioning/          # Core provisioning engine
│   ├── api/               # FastAPI routes
│   ├── services/          # Business logic
│   ├── models/            # Database models
│   └── templates/         # OpenClaw config templates
├── dashboard/             # Next.js frontend (future)
├── tests/                 # Test suite
└── docker-compose.yml     # Local development
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run provisioning API
uvicorn provisioning.api.main:app --reload

# Run tests
pytest tests/
```

## Technical Stack

- **API:** FastAPI + Pydantic
- **Database:** PostgreSQL
- **Container Runtime:** Docker via Coolify API
- **Auth:** Clerk (dashboard), API keys (programmatic)
- **Billing:** Stripe

## Related Specs

- [ShipOS Integration](../carapace/specs/shipos-integration.md)
- [Multi-Agent Architecture](../carapace/specs/multi-agent-architecture.md)
