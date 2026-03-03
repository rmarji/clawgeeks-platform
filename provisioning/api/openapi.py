"""OpenAPI configuration and metadata for ClawGeeks Provisioning API."""

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

# API Metadata
API_TITLE = "ClawGeeks Provisioning API"
API_VERSION = "0.3.0"
API_DESCRIPTION = """
# ClawGeeks Platform API

Multi-tenant OpenClaw hosting platform with automated provisioning, billing, and agent management.

## Overview

This API provides complete management of OpenClaw tenants including:

- **Tenant Lifecycle**: Create, provision, suspend, reactivate, terminate
- **Billing**: Stripe integration with checkout, subscriptions, and self-service portal
- **Authentication**: JWT tokens and API keys with RBAC
- **Self-Service**: User endpoints for managing own tenant and billing

## Authentication

The API supports two authentication methods:

### JWT Bearer Token
```
Authorization: Bearer <token>
```
Obtain tokens via `POST /api/v1/auth/login`.

### API Key
```
X-API-Key: cg_<key>
```
Create API keys via `POST /api/v1/auth/api-keys`.

## Access Control

| Role | Access |
|------|--------|
| **Admin** | Full access to all tenants and operations |
| **User** | Access to own tenant via scoped endpoints |
| **Public** | Health checks only |

## Rate Limits

- Standard endpoints: 100 requests/minute
- Auth endpoints: 10 requests/minute
- Webhook endpoints: 1000 requests/minute

## Errors

All errors return JSON with `detail` field:
```json
{
  "detail": "Tenant not found"
}
```

Common status codes:
- `400` - Bad request / validation error
- `401` - Authentication required
- `403` - Forbidden (insufficient permissions)
- `404` - Resource not found
- `503` - Service unavailable
"""

# Tag metadata for grouping endpoints
TAGS_METADATA = [
    {
        "name": "Health",
        "description": "Health and readiness checks. **Public access.**",
    },
    {
        "name": "Auth",
        "description": "Authentication: login, tokens, API keys, user management.",
    },
    {
        "name": "Tenants",
        "description": "Tenant CRUD operations. Admin-only for create/list, tenant-scoped for read/update.",
    },
    {
        "name": "Tenant Lifecycle",
        "description": "Tenant provisioning and lifecycle management. **Admin only.**",
    },
    {
        "name": "Billing",
        "description": "Stripe billing integration. Tenant-scoped access.",
    },
    {
        "name": "Self-Service",
        "description": "Convenience endpoints for users to manage their own tenant and billing.",
    },
    {
        "name": "Webhooks",
        "description": "External webhook receivers (Stripe). **Signature-verified.**",
    },
]

# Security scheme definitions
SECURITY_SCHEMES = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT token obtained from /api/v1/auth/login",
    },
    "ApiKeyAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key in format: cg_<key>",
    },
}

# Contact and license info
CONTACT_INFO = {
    "name": "ClawGeeks Support",
    "url": "https://clawgeeks.com/support",
    "email": "support@clawgeeks.com",
}

LICENSE_INFO = {
    "name": "Proprietary",
    "url": "https://clawgeeks.com/terms",
}

# Servers for different environments
SERVERS = [
    {
        "url": "http://localhost:8000",
        "description": "Development server",
    },
    {
        "url": "https://api.clawgeeks.com",
        "description": "Production server",
    },
    {
        "url": "https://api-staging.clawgeeks.com",
        "description": "Staging server",
    },
]


def custom_openapi(app: FastAPI):
    """Generate custom OpenAPI schema with full metadata."""
    
    def openapi_schema():
        if app.openapi_schema:
            return app.openapi_schema
        
        schema = get_openapi(
            title=API_TITLE,
            version=API_VERSION,
            description=API_DESCRIPTION,
            routes=app.routes,
            tags=TAGS_METADATA,
        )
        
        # Add security schemes
        schema["components"]["securitySchemes"] = SECURITY_SCHEMES
        
        # Add global security (can be overridden per-operation)
        schema["security"] = [
            {"BearerAuth": []},
            {"ApiKeyAuth": []},
        ]
        
        # Add contact and license
        schema["info"]["contact"] = CONTACT_INFO
        schema["info"]["license"] = LICENSE_INFO
        
        # Add servers
        schema["servers"] = SERVERS
        
        # Add x-tagGroups for ReDoc
        schema["x-tagGroups"] = [
            {
                "name": "General",
                "tags": ["Health"],
            },
            {
                "name": "Authentication",
                "tags": ["Auth"],
            },
            {
                "name": "Tenant Management",
                "tags": ["Tenants", "Tenant Lifecycle"],
            },
            {
                "name": "Billing",
                "tags": ["Billing", "Self-Service"],
            },
            {
                "name": "Integrations",
                "tags": ["Webhooks"],
            },
        ]
        
        app.openapi_schema = schema
        return app.openapi_schema
    
    return openapi_schema


def configure_openapi(app: FastAPI) -> FastAPI:
    """Configure OpenAPI for the FastAPI app."""
    app.title = API_TITLE
    app.description = API_DESCRIPTION
    app.version = API_VERSION
    app.openapi_tags = TAGS_METADATA
    app.contact = CONTACT_INFO
    app.license_info = LICENSE_INFO
    app.servers = SERVERS
    app.openapi = custom_openapi(app)
    return app
