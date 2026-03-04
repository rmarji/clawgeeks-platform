"""Stripe webhook handlers for ClawGeeks Platform.

Processes billing events and updates tenant status accordingly.
"""

import asyncio
import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse

from ..services.billing import get_billing_service, BillingService, SubscriptionEvent
from ..services.provisioner import Provisioner
from ..services.coolify import CoolifyClient
from ..db.repository import TenantRepository, get_repository
from ..db import get_db
from ..models.tenant import TenantStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def handle_subscription_created(
    data: dict,
    repository: TenantRepository
) -> bool:
    """Handle new subscription creation.
    
    Links Stripe subscription to tenant and triggers provisioning.
    """
    subscription_id = data.get("id")
    customer_id = data.get("customer")
    metadata = data.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    
    if not tenant_id:
        logger.warning(f"Subscription {subscription_id} missing tenant_id in metadata")
        return False
    
    tenant = await repository.get(tenant_id)
    if not tenant:
        logger.error(f"Tenant {tenant_id} not found for subscription {subscription_id}")
        return False
    
    # Update tenant with Stripe IDs
    await repository.update(tenant_id, {
        "stripe_customer_id": customer_id,
        "stripe_subscription_id": subscription_id,
    })
    
    # If subscription is active/trialing, start provisioning
    status = data.get("status")
    if status in ("active", "trialing"):
        if tenant.status == TenantStatus.PENDING:
            await repository.update_status(tenant_id, TenantStatus.PROVISIONING)
            logger.info(f"Tenant {tenant_id} moved to PROVISIONING after subscription {subscription_id}")
            # Trigger provisioning via Coolify in background
            asyncio.create_task(_provision_tenant_background(tenant_id))
    
    logger.info(f"Linked subscription {subscription_id} to tenant {tenant_id}")
    return True


async def _provision_tenant_background(tenant_id: str) -> None:
    """Background task to provision tenant via Coolify."""
    try:
        async for session in get_db():
            repository = TenantRepository(session)
            coolify = CoolifyClient()
            provisioner = Provisioner(coolify, repository)
            await provisioner.provision_tenant(tenant_id)
            logger.info(f"Successfully provisioned tenant {tenant_id}")
            break
    except Exception as e:
        logger.error(f"Failed to provision tenant {tenant_id}: {e}")


async def handle_subscription_updated(
    data: dict,
    repository: TenantRepository
) -> bool:
    """Handle subscription updates (tier changes, cancellations, etc.)."""
    subscription_id = data.get("id")
    status = data.get("status")
    cancel_at_period_end = data.get("cancel_at_period_end", False)
    metadata = data.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    
    if not tenant_id:
        # Try to find by subscription ID
        tenant = await repository.get_by_subscription(subscription_id)
        if tenant:
            tenant_id = tenant.id
        else:
            logger.warning(f"Could not find tenant for subscription {subscription_id}")
            return False
    
    tenant = await repository.get(tenant_id)
    if not tenant:
        return False
    
    # Map Stripe status to tenant status
    if status == "past_due":
        # Payment failed but still trying
        logger.warning(f"Tenant {tenant_id} subscription past_due")
    elif status == "unpaid":
        # Payment failed, access should be revoked
        await repository.update_status(tenant_id, TenantStatus.SUSPENDED)
        logger.warning(f"Tenant {tenant_id} suspended due to unpaid subscription")
    elif status == "canceled":
        await repository.update_status(tenant_id, TenantStatus.TERMINATED)
        logger.info(f"Tenant {tenant_id} terminated due to cancelled subscription")
    elif status == "active" and tenant.status == TenantStatus.SUSPENDED:
        # Reactivated (e.g., payment succeeded after failure)
        await repository.update_status(tenant_id, TenantStatus.ACTIVE)
        logger.info(f"Tenant {tenant_id} reactivated after subscription update")
    
    if cancel_at_period_end:
        logger.info(f"Tenant {tenant_id} subscription scheduled for cancellation")
        # Could add a "cancelling" flag or send notification
    
    return True


async def handle_subscription_deleted(
    data: dict,
    repository: TenantRepository
) -> bool:
    """Handle subscription deletion (final cancellation)."""
    subscription_id = data.get("id")
    metadata = data.get("metadata", {})
    tenant_id = metadata.get("tenant_id")
    
    if not tenant_id:
        tenant = await repository.get_by_subscription(subscription_id)
        if tenant:
            tenant_id = tenant.id
        else:
            return False
    
    await repository.update_status(tenant_id, TenantStatus.TERMINATED)
    logger.info(f"Tenant {tenant_id} terminated after subscription deletion")
    
    # Trigger deprovisioning in background
    asyncio.create_task(_deprovision_tenant_background(tenant_id))
    return True


async def _deprovision_tenant_background(tenant_id: str) -> None:
    """Background task to deprovision tenant (stop container, cleanup)."""
    try:
        async for session in get_db():
            repository = TenantRepository(session)
            coolify = CoolifyClient()
            provisioner = Provisioner(coolify, repository)
            await provisioner.terminate_tenant(tenant_id)
            logger.info(f"Successfully deprovisioned tenant {tenant_id}")
            break
    except Exception as e:
        logger.error(f"Failed to deprovision tenant {tenant_id}: {e}")


async def handle_payment_failed(
    data: dict,
    repository: TenantRepository
) -> bool:
    """Handle failed payment (invoice.payment_failed)."""
    subscription_id = data.get("subscription")
    if not subscription_id:
        return False
    
    tenant = await repository.get_by_subscription(subscription_id)
    if not tenant:
        return False
    
    # Log the failure - Stripe will retry
    logger.warning(f"Payment failed for tenant {tenant.id}")
    
    # Could send notification, add grace period tracking, etc.
    return True


async def handle_payment_succeeded(
    data: dict,
    repository: TenantRepository
) -> bool:
    """Handle successful payment (invoice.payment_succeeded)."""
    subscription_id = data.get("subscription")
    if not subscription_id:
        return False
    
    tenant = await repository.get_by_subscription(subscription_id)
    if not tenant:
        return False
    
    # If tenant was suspended due to payment failure, reactivate
    if tenant.status == TenantStatus.SUSPENDED:
        await repository.update_status(tenant.id, TenantStatus.ACTIVE)
        logger.info(f"Tenant {tenant.id} reactivated after successful payment")
    
    return True


# Event handler registry
EVENT_HANDLERS = {
    SubscriptionEvent.CREATED: handle_subscription_created,
    SubscriptionEvent.UPDATED: handle_subscription_updated,
    SubscriptionEvent.DELETED: handle_subscription_deleted,
    SubscriptionEvent.PAYMENT_FAILED: handle_payment_failed,
    SubscriptionEvent.PAYMENT_SUCCEEDED: handle_payment_succeeded,
}


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    repository: TenantRepository = Depends(get_repository)
):
    """
    Stripe webhook endpoint.
    
    Verifies signature and processes billing events.
    """
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    
    if not signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    billing = get_billing_service()
    event = billing.verify_webhook(payload, signature)
    
    if not event:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    
    event_type = event["type"]
    event_data = event["data"]
    
    logger.info(f"Received Stripe webhook: {event_type} ({event['id']})")
    
    # Find and execute handler
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        try:
            success = await handler(event_data, repository)
            if not success:
                logger.warning(f"Handler returned False for {event_type}")
        except Exception as e:
            logger.error(f"Error handling {event_type}: {e}")
            # Don't raise - Stripe will retry
    else:
        logger.debug(f"No handler for event type: {event_type}")
    
    # Always return 200 to acknowledge receipt
    return JSONResponse(content={"received": True})


@router.get("/stripe/test")
async def test_webhook():
    """Test endpoint to verify webhook route is accessible."""
    return {"status": "ok", "message": "Stripe webhook endpoint active"}
