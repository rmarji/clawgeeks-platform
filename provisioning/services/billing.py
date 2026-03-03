"""Stripe billing integration for ClawGeeks Platform.

Handles:
- Customer creation
- Subscription lifecycle
- Webhook processing
- Usage-based billing (future)
"""

import os
import logging
from datetime import datetime
from enum import Enum
from typing import Optional
from dataclasses import dataclass

import stripe
from stripe import Customer, Subscription, Price, Product

from ..models.tenant import TenantTier, TenantStatus

logger = logging.getLogger(__name__)

# Stripe API key from environment
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

# Price IDs mapped to tiers (set via environment)
TIER_PRICE_IDS = {
    TenantTier.STARTER: os.environ.get("STRIPE_PRICE_STARTER", "price_starter"),
    TenantTier.PRO: os.environ.get("STRIPE_PRICE_PRO", "price_pro"),
    TenantTier.BUSINESS: os.environ.get("STRIPE_PRICE_BUSINESS", "price_business"),
}

# Tier pricing (for reference/validation)
TIER_PRICING = {
    TenantTier.STARTER: 4900,    # $49/mo in cents
    TenantTier.PRO: 14900,       # $149/mo
    TenantTier.BUSINESS: 29900,  # $299/mo
}


class SubscriptionEvent(str, Enum):
    """Stripe subscription events we handle."""
    CREATED = "customer.subscription.created"
    UPDATED = "customer.subscription.updated"
    DELETED = "customer.subscription.deleted"
    PAUSED = "customer.subscription.paused"
    RESUMED = "customer.subscription.resumed"
    TRIAL_ENDING = "customer.subscription.trial_will_end"
    PAYMENT_FAILED = "invoice.payment_failed"
    PAYMENT_SUCCEEDED = "invoice.payment_succeeded"


@dataclass
class BillingResult:
    """Result of a billing operation."""
    success: bool
    customer_id: Optional[str] = None
    subscription_id: Optional[str] = None
    error: Optional[str] = None
    status: Optional[str] = None


class BillingService:
    """Handles all Stripe billing operations."""
    
    def __init__(self, webhook_secret: Optional[str] = None):
        """Initialize billing service.
        
        Args:
            webhook_secret: Stripe webhook signing secret for verification
        """
        self.webhook_secret = webhook_secret or os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        
        if not stripe.api_key:
            logger.warning("STRIPE_SECRET_KEY not set - billing operations will fail")
    
    async def create_customer(
        self,
        email: str,
        name: str,
        tenant_id: str,
        metadata: Optional[dict] = None
    ) -> BillingResult:
        """Create a Stripe customer for a tenant.
        
        Args:
            email: Customer email
            name: Customer/company name
            tenant_id: Our internal tenant ID (stored in metadata)
            metadata: Additional metadata to attach
        
        Returns:
            BillingResult with customer_id on success
        """
        try:
            customer_metadata = {
                "tenant_id": tenant_id,
                "platform": "clawgeeks",
                **(metadata or {})
            }
            
            customer = stripe.Customer.create(
                email=email,
                name=name,
                metadata=customer_metadata
            )
            
            logger.info(f"Created Stripe customer {customer.id} for tenant {tenant_id}")
            return BillingResult(success=True, customer_id=customer.id)
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create customer: {e}")
            return BillingResult(success=False, error=str(e))
    
    async def create_subscription(
        self,
        customer_id: str,
        tier: TenantTier,
        trial_days: int = 14,
        metadata: Optional[dict] = None
    ) -> BillingResult:
        """Create a subscription for a customer.
        
        Args:
            customer_id: Stripe customer ID
            tier: Subscription tier
            trial_days: Free trial period (0 to disable)
            metadata: Additional metadata
        
        Returns:
            BillingResult with subscription_id on success
        """
        if tier == TenantTier.ENTERPRISE:
            # Enterprise is custom pricing
            return BillingResult(
                success=False,
                error="Enterprise tier requires manual setup"
            )
        
        price_id = TIER_PRICE_IDS.get(tier)
        if not price_id:
            return BillingResult(success=False, error=f"No price configured for tier {tier}")
        
        try:
            subscription_params = {
                "customer": customer_id,
                "items": [{"price": price_id}],
                "metadata": metadata or {},
                "payment_behavior": "default_incomplete",
                "expand": ["latest_invoice.payment_intent"],
            }
            
            if trial_days > 0:
                subscription_params["trial_period_days"] = trial_days
            
            subscription = stripe.Subscription.create(**subscription_params)
            
            logger.info(f"Created subscription {subscription.id} for customer {customer_id}")
            return BillingResult(
                success=True,
                subscription_id=subscription.id,
                status=subscription.status
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create subscription: {e}")
            return BillingResult(success=False, error=str(e))
    
    async def cancel_subscription(
        self,
        subscription_id: str,
        immediately: bool = False
    ) -> BillingResult:
        """Cancel a subscription.
        
        Args:
            subscription_id: Stripe subscription ID
            immediately: If True, cancel now. If False, cancel at period end.
        
        Returns:
            BillingResult indicating success/failure
        """
        try:
            if immediately:
                subscription = stripe.Subscription.delete(subscription_id)
            else:
                subscription = stripe.Subscription.modify(
                    subscription_id,
                    cancel_at_period_end=True
                )
            
            logger.info(f"Cancelled subscription {subscription_id} (immediate={immediately})")
            return BillingResult(
                success=True,
                subscription_id=subscription_id,
                status=subscription.status
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to cancel subscription: {e}")
            return BillingResult(success=False, error=str(e))
    
    async def pause_subscription(self, subscription_id: str) -> BillingResult:
        """Pause a subscription (stop billing but keep access).
        
        Args:
            subscription_id: Stripe subscription ID
        
        Returns:
            BillingResult indicating success/failure
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                pause_collection={"behavior": "mark_uncollectible"}
            )
            
            logger.info(f"Paused subscription {subscription_id}")
            return BillingResult(
                success=True,
                subscription_id=subscription_id,
                status="paused"
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to pause subscription: {e}")
            return BillingResult(success=False, error=str(e))
    
    async def resume_subscription(self, subscription_id: str) -> BillingResult:
        """Resume a paused subscription.
        
        Args:
            subscription_id: Stripe subscription ID
        
        Returns:
            BillingResult indicating success/failure
        """
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                pause_collection=""  # Clear pause
            )
            
            logger.info(f"Resumed subscription {subscription_id}")
            return BillingResult(
                success=True,
                subscription_id=subscription_id,
                status=subscription.status
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to resume subscription: {e}")
            return BillingResult(success=False, error=str(e))
    
    async def change_tier(
        self,
        subscription_id: str,
        new_tier: TenantTier,
        prorate: bool = True
    ) -> BillingResult:
        """Change subscription tier (upgrade/downgrade).
        
        Args:
            subscription_id: Stripe subscription ID
            new_tier: New tier to switch to
            prorate: If True, prorate the change
        
        Returns:
            BillingResult indicating success/failure
        """
        if new_tier == TenantTier.ENTERPRISE:
            return BillingResult(
                success=False,
                error="Enterprise tier requires manual setup"
            )
        
        price_id = TIER_PRICE_IDS.get(new_tier)
        if not price_id:
            return BillingResult(success=False, error=f"No price configured for tier {new_tier}")
        
        try:
            # Get current subscription to find the item ID
            subscription = stripe.Subscription.retrieve(subscription_id)
            if not subscription.items.data:
                return BillingResult(success=False, error="No items in subscription")
            
            item_id = subscription.items.data[0].id
            
            # Update the subscription item with new price
            updated = stripe.Subscription.modify(
                subscription_id,
                items=[{
                    "id": item_id,
                    "price": price_id,
                }],
                proration_behavior="create_prorations" if prorate else "none"
            )
            
            logger.info(f"Changed subscription {subscription_id} to tier {new_tier}")
            return BillingResult(
                success=True,
                subscription_id=subscription_id,
                status=updated.status
            )
            
        except stripe.StripeError as e:
            logger.error(f"Failed to change tier: {e}")
            return BillingResult(success=False, error=str(e))
    
    async def get_subscription(self, subscription_id: str) -> Optional[dict]:
        """Get subscription details.
        
        Args:
            subscription_id: Stripe subscription ID
        
        Returns:
            Subscription data or None if not found
        """
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            return {
                "id": subscription.id,
                "status": subscription.status,
                "current_period_start": datetime.fromtimestamp(subscription.current_period_start),
                "current_period_end": datetime.fromtimestamp(subscription.current_period_end),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "trial_end": datetime.fromtimestamp(subscription.trial_end) if subscription.trial_end else None,
            }
        except stripe.StripeError as e:
            logger.error(f"Failed to get subscription: {e}")
            return None
    
    def verify_webhook(self, payload: bytes, signature: str) -> Optional[dict]:
        """Verify and parse a Stripe webhook event.
        
        Args:
            payload: Raw request body
            signature: Stripe-Signature header value
        
        Returns:
            Parsed event data or None if verification fails
        """
        if not self.webhook_secret:
            logger.error("Webhook secret not configured")
            return None
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return {
                "id": event.id,
                "type": event.type,
                "data": event.data.object,
                "created": datetime.fromtimestamp(event.created)
            }
        except stripe.SignatureVerificationError as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Webhook parsing error: {e}")
            return None
    
    async def create_checkout_session(
        self,
        tier: TenantTier,
        tenant_id: str,
        success_url: str,
        cancel_url: str,
        customer_email: Optional[str] = None,
        trial_days: int = 14
    ) -> Optional[str]:
        """Create a Stripe Checkout session for new signups.
        
        Args:
            tier: Subscription tier
            tenant_id: Our internal tenant ID
            success_url: Redirect URL on success
            cancel_url: Redirect URL on cancel
            customer_email: Pre-fill email if known
            trial_days: Free trial period
        
        Returns:
            Checkout session URL or None on error
        """
        if tier == TenantTier.ENTERPRISE:
            return None
        
        price_id = TIER_PRICE_IDS.get(tier)
        if not price_id:
            return None
        
        try:
            session_params = {
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": {"tenant_id": tenant_id},
                "subscription_data": {
                    "metadata": {"tenant_id": tenant_id}
                }
            }
            
            if customer_email:
                session_params["customer_email"] = customer_email
            
            if trial_days > 0:
                session_params["subscription_data"]["trial_period_days"] = trial_days
            
            session = stripe.checkout.Session.create(**session_params)
            return session.url
            
        except stripe.StripeError as e:
            logger.error(f"Failed to create checkout session: {e}")
            return None
    
    async def create_billing_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> Optional[str]:
        """Create a Stripe Billing Portal session for self-service.
        
        Args:
            customer_id: Stripe customer ID
            return_url: URL to return to after portal
        
        Returns:
            Portal session URL or None on error
        """
        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=return_url
            )
            return session.url
        except stripe.StripeError as e:
            logger.error(f"Failed to create portal session: {e}")
            return None


# Singleton instance
_billing_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    """Get or create the billing service singleton."""
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service
