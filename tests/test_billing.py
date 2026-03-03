"""Tests for Stripe billing integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from provisioning.services.billing import (
    BillingService,
    BillingResult,
    get_billing_service,
    TIER_PRICING,
)
from provisioning.models.tenant import TenantTier


class TestBillingService:
    """Tests for BillingService."""
    
    @pytest.fixture
    def billing(self):
        """Create a billing service instance."""
        with patch("provisioning.services.billing.stripe"):
            return BillingService(webhook_secret="whsec_test")
    
    @pytest.mark.asyncio
    async def test_create_customer_success(self, billing):
        """Test successful customer creation."""
        with patch("stripe.Customer.create") as mock_create:
            mock_create.return_value = MagicMock(id="cus_test123")
            
            result = await billing.create_customer(
                email="test@example.com",
                name="Test Corp",
                tenant_id="tenant_abc"
            )
            
            assert result.success
            assert result.customer_id == "cus_test123"
            assert result.error is None
            
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["email"] == "test@example.com"
            assert call_kwargs["name"] == "Test Corp"
            assert call_kwargs["metadata"]["tenant_id"] == "tenant_abc"
    
    @pytest.mark.asyncio
    async def test_create_customer_failure(self, billing):
        """Test customer creation failure."""
        import stripe
        with patch("stripe.Customer.create") as mock_create:
            mock_create.side_effect = stripe.StripeError("API error")
            
            result = await billing.create_customer(
                email="test@example.com",
                name="Test Corp",
                tenant_id="tenant_abc"
            )
            
            assert not result.success
            assert result.customer_id is None
            assert "API error" in result.error
    
    @pytest.mark.asyncio
    async def test_create_subscription_success(self, billing):
        """Test successful subscription creation."""
        with patch("stripe.Subscription.create") as mock_create:
            mock_sub = MagicMock()
            mock_sub.id = "sub_test123"
            mock_sub.status = "trialing"
            mock_create.return_value = mock_sub
            
            result = await billing.create_subscription(
                customer_id="cus_test",
                tier=TenantTier.STARTER,
                trial_days=14
            )
            
            assert result.success
            assert result.subscription_id == "sub_test123"
            assert result.status == "trialing"
    
    @pytest.mark.asyncio
    async def test_create_subscription_enterprise_fails(self, billing):
        """Test that enterprise tier requires manual setup."""
        result = await billing.create_subscription(
            customer_id="cus_test",
            tier=TenantTier.ENTERPRISE
        )
        
        assert not result.success
        assert "manual setup" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_at_period_end(self, billing):
        """Test cancellation at period end."""
        with patch("stripe.Subscription.modify") as mock_modify:
            mock_sub = MagicMock()
            mock_sub.status = "active"
            mock_modify.return_value = mock_sub
            
            result = await billing.cancel_subscription(
                subscription_id="sub_test",
                immediately=False
            )
            
            assert result.success
            mock_modify.assert_called_once_with(
                "sub_test",
                cancel_at_period_end=True
            )
    
    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately(self, billing):
        """Test immediate cancellation."""
        with patch("stripe.Subscription.delete") as mock_delete:
            mock_sub = MagicMock()
            mock_sub.status = "canceled"
            mock_delete.return_value = mock_sub
            
            result = await billing.cancel_subscription(
                subscription_id="sub_test",
                immediately=True
            )
            
            assert result.success
            mock_delete.assert_called_once_with("sub_test")
    
    @pytest.mark.asyncio
    async def test_change_tier_success(self, billing):
        """Test tier upgrade/downgrade."""
        with patch("stripe.Subscription.retrieve") as mock_retrieve, \
             patch("stripe.Subscription.modify") as mock_modify:
            
            # Mock current subscription with items
            mock_item = MagicMock()
            mock_item.id = "si_test"
            mock_sub = MagicMock()
            mock_sub.items.data = [mock_item]
            mock_retrieve.return_value = mock_sub
            
            # Mock updated subscription
            mock_updated = MagicMock()
            mock_updated.status = "active"
            mock_modify.return_value = mock_updated
            
            result = await billing.change_tier(
                subscription_id="sub_test",
                new_tier=TenantTier.PRO
            )
            
            assert result.success
            assert result.status == "active"
    
    @pytest.mark.asyncio
    async def test_get_subscription(self, billing):
        """Test getting subscription details."""
        with patch("stripe.Subscription.retrieve") as mock_retrieve:
            mock_sub = MagicMock()
            mock_sub.id = "sub_test"
            mock_sub.status = "active"
            mock_sub.current_period_start = 1704067200
            mock_sub.current_period_end = 1706745600
            mock_sub.cancel_at_period_end = False
            mock_sub.trial_end = None
            mock_retrieve.return_value = mock_sub
            
            result = await billing.get_subscription("sub_test")
            
            assert result is not None
            assert result["id"] == "sub_test"
            assert result["status"] == "active"
            assert result["cancel_at_period_end"] is False
    
    def test_verify_webhook_valid(self, billing):
        """Test webhook signature verification."""
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_event = MagicMock()
            mock_event.id = "evt_test"
            mock_event.type = "customer.subscription.created"
            mock_event.data.object = {"subscription": "sub_test"}
            mock_event.created = 1704067200
            mock_construct.return_value = mock_event
            
            result = billing.verify_webhook(b"payload", "sig_test")
            
            assert result is not None
            assert result["id"] == "evt_test"
            assert result["type"] == "customer.subscription.created"
    
    def test_verify_webhook_invalid_signature(self, billing):
        """Test webhook with invalid signature."""
        import stripe
        with patch("stripe.Webhook.construct_event") as mock_construct:
            mock_construct.side_effect = stripe.SignatureVerificationError(
                "Invalid", "sig"
            )
            
            result = billing.verify_webhook(b"payload", "bad_sig")
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_create_checkout_session(self, billing):
        """Test checkout session creation."""
        with patch("stripe.checkout.Session.create") as mock_create:
            mock_session = MagicMock()
            mock_session.url = "https://checkout.stripe.com/test"
            mock_create.return_value = mock_session
            
            url = await billing.create_checkout_session(
                tier=TenantTier.STARTER,
                tenant_id="tenant_abc",
                success_url="https://app.test/success",
                cancel_url="https://app.test/cancel",
                customer_email="test@example.com"
            )
            
            assert url == "https://checkout.stripe.com/test"
    
    @pytest.mark.asyncio
    async def test_create_billing_portal_session(self, billing):
        """Test billing portal session creation."""
        with patch("stripe.billing_portal.Session.create") as mock_create:
            mock_session = MagicMock()
            mock_session.url = "https://billing.stripe.com/portal/test"
            mock_create.return_value = mock_session
            
            url = await billing.create_billing_portal_session(
                customer_id="cus_test",
                return_url="https://app.test/dashboard"
            )
            
            assert url == "https://billing.stripe.com/portal/test"


class TestTierPricing:
    """Tests for tier pricing constants."""
    
    def test_starter_tier_price(self):
        """Starter is $49/mo."""
        assert TIER_PRICING[TenantTier.STARTER] == 4900
    
    def test_pro_tier_price(self):
        """Pro is $149/mo."""
        assert TIER_PRICING[TenantTier.PRO] == 14900
    
    def test_business_tier_price(self):
        """Business is $299/mo."""
        assert TIER_PRICING[TenantTier.BUSINESS] == 29900


class TestBillingServiceSingleton:
    """Tests for billing service singleton."""
    
    def test_get_billing_service_returns_same_instance(self):
        """Test that singleton returns same instance."""
        # Reset singleton
        import provisioning.services.billing as billing_module
        billing_module._billing_service = None
        
        with patch("provisioning.services.billing.stripe"):
            service1 = get_billing_service()
            service2 = get_billing_service()
            assert service1 is service2
