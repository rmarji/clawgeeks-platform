"""ClawGeeks Provisioning API - Protected with RBAC."""

import os
from contextlib import asynccontextmanager
from typing import Optional, Annotated

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantStatus,
    TenantTier,
)
from ..services import Provisioner, ProvisioningError, TenantNotFoundError
from ..services.billing import get_billing_service, BillingService
from ..db import get_db, init_db, TenantRepository
from .webhooks import router as webhook_router
from .openapi import configure_openapi, API_VERSION
from .hr_routes import router as hr_router
from .mentor_routes import router as mentor_router
from .advisor_routes import router as advisor_router
from .coding import router as coding_router
from ..auth.routes import router as auth_router
from ..auth.dependencies import (
    require_auth,
    require_admin,
    TenantScopedDependency,
)
from ..auth.models import UserModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: init DB on startup."""
    await init_db()
    yield


app = FastAPI(
    title="ClawGeeks Provisioning API",
    description="Manage OpenClaw tenant lifecycle",
    version=API_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure enhanced OpenAPI
configure_openapi(app)

# CORS configuration: Use ALLOWED_ORIGINS env var (comma-separated) or default to localhost
_cors_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000")
ALLOWED_ORIGINS = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (auth routes handle their own protection)
app.include_router(webhook_router)  # Webhooks verify signatures internally
app.include_router(auth_router)
app.include_router(hr_router)  # HR Department (business analysis, team recommendations)
app.include_router(mentor_router)  # Board of Mentors (domain expert AI advisors)
app.include_router(advisor_router)  # Board of Advisors (strategic counsel AI)
app.include_router(coding_router)  # AI Coding Agent (powered by OpenHands)


# =============================================================================
# Dependencies
# =============================================================================

async def get_repository(
    session: AsyncSession = Depends(get_db),
) -> TenantRepository:
    """Get tenant repository with database session."""
    return TenantRepository(session)


async def get_provisioner(
    repo: TenantRepository = Depends(get_repository),
) -> Provisioner:
    """Get provisioner with repository."""
    return Provisioner(repository=repo)


# Tenant-scoped access dependency
tenant_access = TenantScopedDependency()


# =============================================================================
# Health (Public)
# =============================================================================

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint (public)."""
    return {"status": "healthy", "service": "provisioning", "version": "0.3.0"}


@app.get("/ready", tags=["Health"])
async def readiness_check(
    session: AsyncSession = Depends(get_db),
):
    """Readiness check: verifies database connectivity (public)."""
    try:
        await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database not ready: {e}")


# =============================================================================
# Tenant CRUD (Admin-only for create/list, Tenant-scoped for read/update)
# =============================================================================

@app.post(
    "/api/v1/tenants",
    response_model=Tenant,
    status_code=201,
    tags=["Tenants"],
    summary="Create tenant (admin only)",
)
async def create_tenant(
    request: TenantCreate,
    background_tasks: BackgroundTasks,
    user: Annotated[UserModel, Depends(require_admin)],
    prov: Provisioner = Depends(get_provisioner),
):
    """
    Create a new tenant. **Admin only.**
    
    Creates tenant record and triggers async provisioning.
    Returns immediately with PENDING status.
    """
    tenant = await prov.create_tenant(request)
    
    # Trigger provisioning in background
    background_tasks.add_task(prov.provision_tenant, tenant.id)
    
    return tenant


@app.get(
    "/api/v1/tenants",
    response_model=list[Tenant],
    tags=["Tenants"],
    summary="List all tenants (admin only)",
)
async def list_tenants(
    user: Annotated[UserModel, Depends(require_admin)],
    status: Optional[TenantStatus] = None,
    limit: int = 100,
    offset: int = 0,
    repo: TenantRepository = Depends(get_repository),
):
    """List all tenants with optional filters. **Admin only.**"""
    return await repo.list_all(status=status, limit=limit, offset=offset)


@app.get(
    "/api/v1/tenants/{tenant_id}",
    response_model=Tenant,
    tags=["Tenants"],
    summary="Get tenant by ID",
)
async def get_tenant(
    tenant_id: str,
    user: Annotated[UserModel, Depends(tenant_access)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Get tenant by ID.
    
    - Admins can access any tenant.
    - Users can only access their own tenant.
    """
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@app.patch(
    "/api/v1/tenants/{tenant_id}",
    response_model=Tenant,
    tags=["Tenants"],
    summary="Update tenant settings",
)
async def update_tenant(
    tenant_id: str,
    update: TenantUpdate,
    user: Annotated[UserModel, Depends(tenant_access)],
    prov: Provisioner = Depends(get_provisioner),
):
    """
    Update tenant settings.
    
    - Admins can update any tenant.
    - Users can only update their own tenant (non-admin fields).
    """
    try:
        return await prov.update_tenant(tenant_id, update)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")


# =============================================================================
# Tenant Lifecycle (Admin-only)
# =============================================================================

@app.post(
    "/api/v1/tenants/{tenant_id}/provision",
    response_model=Tenant,
    tags=["Tenant Lifecycle"],
    summary="Trigger provisioning (admin only)",
)
async def provision_tenant(
    tenant_id: str,
    user: Annotated[UserModel, Depends(require_admin)],
    prov: Provisioner = Depends(get_provisioner),
):
    """
    Manually trigger provisioning. **Admin only.**
    
    Use this to retry failed provisioning or provision after creation.
    """
    try:
        return await prov.provision_tenant(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    except ProvisioningError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post(
    "/api/v1/tenants/{tenant_id}/suspend",
    response_model=Tenant,
    tags=["Tenant Lifecycle"],
    summary="Suspend tenant (admin only)",
)
async def suspend_tenant(
    tenant_id: str,
    user: Annotated[UserModel, Depends(require_admin)],
    reason: Optional[str] = None,
    prov: Provisioner = Depends(get_provisioner),
):
    """
    Suspend a tenant (stops container, preserves data). **Admin only.**
    """
    try:
        return await prov.suspend_tenant(tenant_id, reason)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")


@app.post(
    "/api/v1/tenants/{tenant_id}/reactivate",
    response_model=Tenant,
    tags=["Tenant Lifecycle"],
    summary="Reactivate suspended tenant (admin only)",
)
async def reactivate_tenant(
    tenant_id: str,
    user: Annotated[UserModel, Depends(require_admin)],
    prov: Provisioner = Depends(get_provisioner),
):
    """
    Reactivate a suspended tenant. **Admin only.**
    """
    try:
        return await prov.reactivate_tenant(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")
    except ProvisioningError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete(
    "/api/v1/tenants/{tenant_id}",
    response_model=Tenant,
    tags=["Tenant Lifecycle"],
    summary="Terminate tenant (admin only)",
)
async def terminate_tenant(
    tenant_id: str,
    user: Annotated[UserModel, Depends(require_admin)],
    prov: Provisioner = Depends(get_provisioner),
):
    """
    Terminate a tenant (deletes container and data). **Admin only.**
    
    This is destructive and cannot be undone.
    """
    try:
        return await prov.terminate_tenant(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(status_code=404, detail="Tenant not found")


# =============================================================================
# Utility (Admin-only for admin lookups, tenant-scoped for self-lookup)
# =============================================================================

@app.get(
    "/api/v1/tenants/by-subdomain/{subdomain}",
    response_model=Tenant,
    tags=["Tenants"],
    summary="Get tenant by subdomain (admin only)",
)
async def get_tenant_by_subdomain(
    subdomain: str,
    user: Annotated[UserModel, Depends(require_admin)],
    repo: TenantRepository = Depends(get_repository),
):
    """Get tenant by subdomain. **Admin only.**"""
    tenant = await repo.get_by_subdomain(subdomain)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@app.get(
    "/api/v1/tenants/by-email/{email}",
    response_model=Tenant,
    tags=["Tenants"],
    summary="Get tenant by email (admin only)",
)
async def get_tenant_by_email(
    email: str,
    user: Annotated[UserModel, Depends(require_admin)],
    repo: TenantRepository = Depends(get_repository),
):
    """Get tenant by email. **Admin only.**"""
    tenant = await repo.get_by_email(email)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


# =============================================================================
# My Tenant (Self-service for authenticated users)
# =============================================================================

@app.get(
    "/api/v1/me/tenant",
    response_model=Tenant,
    tags=["Self-Service"],
    summary="Get my tenant",
)
async def get_my_tenant(
    user: Annotated[UserModel, Depends(require_auth)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Get the current user's tenant.
    
    Convenience endpoint for non-admin users to access their own tenant
    without knowing the tenant ID.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=404, detail="No tenant associated with this user")
    
    tenant = await repo.get(user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


# =============================================================================
# Billing (Tenant-scoped)
# =============================================================================

class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    tier: TenantTier = TenantTier.STARTER
    success_url: str
    cancel_url: str


class PortalRequest(BaseModel):
    """Request to create a billing portal session."""
    return_url: str


@app.post(
    "/api/v1/billing/{tenant_id}/checkout",
    tags=["Billing"],
    summary="Create checkout session",
)
async def create_checkout(
    tenant_id: str,
    request: CheckoutRequest,
    user: Annotated[UserModel, Depends(tenant_access)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Create a Stripe Checkout session for new subscriptions.
    
    Returns a redirect URL to Stripe's hosted checkout page.
    Tenant-scoped: users can only create checkout for their own tenant.
    """
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    billing = get_billing_service()
    checkout_url = await billing.create_checkout_session(
        tier=request.tier,
        tenant_id=tenant_id,
        success_url=request.success_url,
        cancel_url=request.cancel_url,
        customer_email=tenant.email,
    )
    
    if not checkout_url:
        raise HTTPException(status_code=400, detail="Failed to create checkout session")
    
    return {"checkout_url": checkout_url}


@app.post(
    "/api/v1/billing/{tenant_id}/portal",
    tags=["Billing"],
    summary="Create billing portal session",
)
async def create_billing_portal(
    tenant_id: str,
    request: PortalRequest,
    user: Annotated[UserModel, Depends(tenant_access)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Create a Stripe Billing Portal session for self-service.
    
    Allows customers to update payment methods, view invoices,
    and manage their subscription. Tenant-scoped.
    """
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="Tenant has no billing account")
    
    billing = get_billing_service()
    portal_url = await billing.create_billing_portal_session(
        customer_id=tenant.stripe_customer_id,
        return_url=request.return_url,
    )
    
    if not portal_url:
        raise HTTPException(status_code=400, detail="Failed to create portal session")
    
    return {"portal_url": portal_url}


@app.get(
    "/api/v1/billing/{tenant_id}/subscription",
    tags=["Billing"],
    summary="Get subscription details",
)
async def get_subscription(
    tenant_id: str,
    user: Annotated[UserModel, Depends(tenant_access)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Get subscription details for a tenant. Tenant-scoped.
    """
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.stripe_subscription_id:
        return {"subscription": None, "message": "No active subscription"}
    
    billing = get_billing_service()
    subscription = await billing.get_subscription(tenant.stripe_subscription_id)
    
    if not subscription:
        return {"subscription": None, "message": "Subscription not found"}
    
    return {"subscription": subscription}


@app.post(
    "/api/v1/billing/{tenant_id}/change-tier",
    tags=["Billing"],
    summary="Change subscription tier",
)
async def change_subscription_tier(
    tenant_id: str,
    tier: TenantTier,
    user: Annotated[UserModel, Depends(tenant_access)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Change a tenant's subscription tier (upgrade/downgrade).
    
    Prorates the charge automatically. Tenant-scoped.
    """
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription to change")
    
    billing = get_billing_service()
    result = await billing.change_tier(
        subscription_id=tenant.stripe_subscription_id,
        new_tier=tier,
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Failed to change tier")
    
    # Update tenant tier in database
    await repo.update(tenant_id, {"tier": tier.value})
    
    return {"success": True, "new_tier": tier, "status": result.status}


@app.post(
    "/api/v1/billing/{tenant_id}/cancel",
    tags=["Billing"],
    summary="Cancel subscription",
)
async def cancel_subscription(
    tenant_id: str,
    user: Annotated[UserModel, Depends(tenant_access)],
    immediately: bool = False,
    repo: TenantRepository = Depends(get_repository),
):
    """
    Cancel a tenant's subscription. Tenant-scoped.
    
    By default, cancels at period end. Set immediately=True for immediate cancellation.
    """
    tenant = await repo.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription to cancel")
    
    billing = get_billing_service()
    result = await billing.cancel_subscription(
        subscription_id=tenant.stripe_subscription_id,
        immediately=immediately,
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or "Failed to cancel")
    
    return {
        "success": True,
        "status": result.status,
        "message": "Cancelled immediately" if immediately else "Scheduled for cancellation at period end"
    }


# =============================================================================
# My Billing (Self-service shortcuts)
# =============================================================================

@app.get(
    "/api/v1/me/billing",
    tags=["Self-Service"],
    summary="Get my subscription",
)
async def get_my_subscription(
    user: Annotated[UserModel, Depends(require_auth)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Get the current user's subscription details.
    
    Convenience endpoint for non-admin users.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=404, detail="No tenant associated with this user")
    
    tenant = await repo.get(user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.stripe_subscription_id:
        return {"subscription": None, "message": "No active subscription"}
    
    billing = get_billing_service()
    subscription = await billing.get_subscription(tenant.stripe_subscription_id)
    
    return {
        "tenant_id": user.tenant_id,
        "tenant_name": tenant.name,
        "tier": tenant.tier,
        "subscription": subscription,
    }


@app.post(
    "/api/v1/me/billing/portal",
    tags=["Self-Service"],
    summary="Access my billing portal",
)
async def access_my_billing_portal(
    request: PortalRequest,
    user: Annotated[UserModel, Depends(require_auth)],
    repo: TenantRepository = Depends(get_repository),
):
    """
    Access billing portal for current user's tenant.
    
    Convenience endpoint for non-admin users.
    """
    if not user.tenant_id:
        raise HTTPException(status_code=404, detail="No tenant associated with this user")
    
    tenant = await repo.get(user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")
    
    billing = get_billing_service()
    portal_url = await billing.create_billing_portal_session(
        customer_id=tenant.stripe_customer_id,
        return_url=request.return_url,
    )
    
    if not portal_url:
        raise HTTPException(status_code=400, detail="Failed to create portal session")
    
    return {"portal_url": portal_url}
