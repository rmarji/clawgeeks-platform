# ClawGeeks Platform Deployment Guide

## Quick Start (Development)

```bash
# 1. Clone and configure
cd clawgeeks-platform
cp .env.example .env
# Edit .env with your values

# 2. Run migrations first
docker compose --profile migrate up migrate

# 3. Start the stack
docker compose up -d

# 4. Check status
docker compose ps
docker compose logs -f
```

**Endpoints:**
- Dashboard: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432

## Production Deployment (Coolify)

### Prerequisites
- Coolify instance with Docker Compose support
- Stripe account with products/prices created
- Domain name for the platform

### 1. Create Stripe Products

In Stripe Dashboard, create 3 products:
- **Starter** ($49/mo) → copy price_id
- **Pro** ($149/mo) → copy price_id  
- **Business** ($299/mo) → copy price_id

### 2. Deploy to Coolify

1. Create new **Docker Compose** resource
2. Connect this repository
3. Set environment variables:
   ```
   POSTGRES_PASSWORD=<strong-password>
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_PRICE_STARTER=price_...
   STRIPE_PRICE_PRO=price_...
   STRIPE_PRICE_BUSINESS=price_...
   COOLIFY_API_URL=https://your-coolify.com
   COOLIFY_API_TOKEN=...
   APP_ENV=production
   ```
4. Configure domain: `platform.yourdomain.com`
5. Enable SSL (Let's Encrypt)
6. Deploy

### 3. Configure Stripe Webhook

1. Go to Stripe Dashboard → Webhooks
2. Add endpoint: `https://platform.yourdomain.com/webhooks/stripe`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_failed`
   - `invoice.payment_succeeded`
4. Copy signing secret to `STRIPE_WEBHOOK_SECRET`
5. Redeploy

### 4. Run Migrations

```bash
# In Coolify container terminal:
docker compose --profile migrate run migrate
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Internet                              │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    ┌───────▼───────┐
                    │   Coolify     │
                    │  (Reverse     │
                    │   Proxy)      │
                    └───────┬───────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
   ┌─────▼─────┐      ┌─────▼─────┐     ┌─────▼─────┐
   │ Dashboard │      │    API    │     │  Stripe   │
   │  (Next.js)│─────▶│ (FastAPI) │◀────│ Webhooks  │
   │   :3000   │      │   :8000   │     │           │
   └───────────┘      └─────┬─────┘     └───────────┘
                            │
                      ┌─────▼─────┐
                      │ PostgreSQL│
                      │   :5432   │
                      └───────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| postgres | 5432 | PostgreSQL 16 database |
| api | 8000 | FastAPI provisioning engine |
| dashboard | 3000 | Next.js admin dashboard |
| migrate | - | One-shot migration runner |

## Commands

```bash
# View logs
docker compose logs -f api
docker compose logs -f dashboard

# Restart services
docker compose restart api

# Run migrations
docker compose --profile migrate run migrate

# Shell into container
docker compose exec api bash

# Database shell
docker compose exec postgres psql -U clawgeeks

# Rebuild after code changes
docker compose build api
docker compose up -d api
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_PASSWORD` | Yes | Database password |
| `STRIPE_SECRET_KEY` | Yes | Stripe API key |
| `STRIPE_WEBHOOK_SECRET` | Yes | Stripe webhook signing secret |
| `STRIPE_PRICE_*` | Yes | Price IDs for each tier |
| `COOLIFY_API_URL` | Yes | Your Coolify instance URL |
| `COOLIFY_API_TOKEN` | Yes | Coolify API token |
| `APP_ENV` | No | `development` or `production` |
| `LOG_LEVEL` | No | `debug`, `info`, `warning`, `error` |

## Troubleshooting

### API won't start
```bash
# Check logs
docker compose logs api

# Verify database connection
docker compose exec api python -c "
from provisioning.db import init_db
import asyncio
asyncio.run(init_db())
print('DB OK')
"
```

### Dashboard can't reach API
```bash
# Verify network
docker compose exec dashboard wget -qO- http://api:8000/health

# Check API health
curl http://localhost:8000/health
```

### Stripe webhooks failing
1. Verify `STRIPE_WEBHOOK_SECRET` matches Stripe Dashboard
2. Check API logs for signature verification errors
3. Ensure endpoint URL is accessible from internet
