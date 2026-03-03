# Contributing to ClawGeeks Platform

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 16+ (or use Docker)

### Quick Start

```bash
# Clone the repo
git clone https://github.com/clawgeeks/clawgeeks-platform.git
cd clawgeeks-platform

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Copy environment file
cp .env.example .env

# Start PostgreSQL (if using Docker)
docker compose up -d postgres

# Run migrations
alembic upgrade head

# Start the API server
uvicorn provisioning.api.main:app --reload
```

### Frontend Setup

```bash
cd dashboard
npm install
npm run dev
```

### Running Tests

```bash
# Unit tests
pytest tests/test_*.py -v

# Integration tests (requires PostgreSQL)
pytest tests/test_integration_e2e.py -v

# With coverage
pytest --cov=provisioning --cov-report=html

# Specific test file
pytest tests/test_auth.py -v
```

### Code Quality

```bash
# Linting
ruff check provisioning/ tests/

# Format code
ruff format provisioning/ tests/

# Type checking
mypy provisioning/

# All checks (via pre-commit)
pre-commit run --all-files
```

## CI/CD Pipeline

The pipeline runs on every push and PR:

1. **Lint & Format** - Ruff, Black, MyPy
2. **Unit Tests** - SQLite in-memory
3. **Integration Tests** - PostgreSQL service
4. **Docker Build** - API + Dashboard images
5. **Deploy** - Coolify webhook (main branch only)

### Required Secrets

For deployment, set these in GitHub Secrets:

- `COOLIFY_WEBHOOK_URL` - Coolify deployment webhook
- `COOLIFY_API_TOKEN` - Coolify API token
- `TELEGRAM_BOT_TOKEN` - (Optional) CI notifications
- `TELEGRAM_CHAT_ID` - (Optional) CI notifications

## Project Structure

```
clawgeeks-platform/
├── provisioning/           # Backend API
│   ├── api/               # FastAPI routes
│   ├── auth/              # Authentication
│   ├── db/                # Database layer
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic
│   └── templates/         # OpenClaw templates
├── dashboard/             # Next.js frontend
├── sdk/                   # Generated SDKs
│   ├── python/
│   └── typescript/
├── tests/                 # Test suite
├── alembic/               # Database migrations
└── docker-compose.yml     # Local development
```

## Pull Request Guidelines

1. Create feature branch from `develop`
2. Write tests for new functionality
3. Run `pre-commit run --all-files` before committing
4. PR into `develop`, not `main`
5. Get review approval
6. Squash merge

## Versioning

We use [SemVer](https://semver.org/):

- MAJOR: Breaking API changes
- MINOR: New features, backward compatible
- PATCH: Bug fixes

Update version in `pyproject.toml` and `provisioning/__init__.py`.
