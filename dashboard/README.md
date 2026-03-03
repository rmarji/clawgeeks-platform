# ClawGeeks Dashboard

Admin dashboard for the ClawGeeks AI Workforce Platform.

## Features

- **Tenant Management** — View, create, provision, suspend, reactivate tenants
- **Stats Overview** — Real-time MRR, tenant counts by status
- **Tier Management** — Starter, Pro, Business, Enterprise
- **ShipOS Toggle** — Enable/disable productivity system per tenant

## Tech Stack

- **Next.js 14** — App Router, Server Components
- **TypeScript** — Type safety
- **Tailwind CSS** — Styling
- **FastAPI Backend** — API proxy via Next.js rewrites

## Development

```bash
# Install dependencies
npm install

# Run dev server
npm run dev

# Build for production
npm run build

# Start production server
npm start
```

## Environment Variables

```env
# API URL (defaults to /api for proxy, or set full URL)
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

# For Next.js rewrites (backend proxy)
API_URL=http://localhost:8000
```

## Docker

```bash
# Build image
docker build -t clawgeeks-dashboard .

# Run container
docker run -p 3000:3000 -e API_URL=http://api:8000 clawgeeks-dashboard
```

## Pages

| Route | Description |
|-------|-------------|
| `/` | Dashboard overview with stats |
| `/tenants` | Tenant list with CRUD |
| `/agents` | Agent management (TODO) |
| `/billing` | Billing overview (TODO) |
| `/settings` | Platform settings (TODO) |

## Components

- `Sidebar` — Navigation sidebar
- `StatsCard` — Metric display card
- `TenantCard` — Individual tenant card with actions

## API Integration

The dashboard connects to the FastAPI provisioning backend. API calls are proxied through Next.js rewrites in development, or configured via `NEXT_PUBLIC_API_URL` in production.

### Endpoints Used

- `GET /api/v1/tenants` — List all tenants
- `POST /api/v1/tenants` — Create tenant
- `POST /api/v1/tenants/{id}/provision` — Provision tenant
- `POST /api/v1/tenants/{id}/suspend` — Suspend tenant
- `POST /api/v1/tenants/{id}/reactivate` — Reactivate tenant
- `POST /api/v1/tenants/{id}/terminate` — Terminate tenant
