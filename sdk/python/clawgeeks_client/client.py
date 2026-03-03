"""ClawGeeks API Client."""

from typing import Optional, Dict, Any, List
import httpx


class ClawGeeksClient:
    """Client for ClawGeeks Provisioning API.
    
    Example:
        >>> client = ClawGeeksClient(api_key="cg_your_key")
        >>> tenants = client.list_tenants()
        
        >>> # Or with JWT auth
        >>> client = ClawGeeksClient()
        >>> client.login("admin@example.com", "password")
        >>> my_tenant = client.get_my_tenant()
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        token: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize the client.
        
        Args:
            base_url: API base URL
            token: JWT bearer token
            api_key: API key (cg_...)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._token = token
        self._api_key = api_key
    
    @property
    def _headers(self) -> Dict[str, str]:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        elif self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers
    
    def _request(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an HTTP request."""
        url = f"{self.base_url}{path}"
        with httpx.Client(timeout=self.timeout) as client:
            return client.request(method, url, headers=self._headers, **kwargs)
    
    async def _arequest(
        self,
        method: str,
        path: str,
        **kwargs,
    ) -> httpx.Response:
        """Make an async HTTP request."""
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            return await client.request(method, url, headers=self._headers, **kwargs)
    
    # =========================================================================
    # Auth
    # =========================================================================
    
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate and get JWT token."""
        response = self._request(
            "POST",
            "/api/v1/auth/login",
            json={"email": email, "password": password},
        )
        response.raise_for_status()
        data = response.json()
        self._token = data.get("access_token")
        return data
    
    def get_me(self) -> Dict[str, Any]:
        """Get current user info."""
        response = self._request("GET", "/api/v1/auth/me")
        response.raise_for_status()
        return response.json()
    
    def change_password(self, current_password: str, new_password: str) -> Dict[str, Any]:
        """Change current user's password."""
        response = self._request(
            "POST",
            "/api/v1/auth/change-password",
            json={"current_password": current_password, "new_password": new_password},
        )
        response.raise_for_status()
        return response.json()
    
    def create_api_key(
        self,
        name: str,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new API key. Returns the key only once."""
        payload = {"name": name}
        if expires_in_days:
            payload["expires_in_days"] = expires_in_days
        response = self._request("POST", "/api/v1/auth/api-keys", json=payload)
        response.raise_for_status()
        return response.json()
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """List user's API keys."""
        response = self._request("GET", "/api/v1/auth/api-keys")
        response.raise_for_status()
        return response.json()
    
    def revoke_api_key(self, key_id: str) -> Dict[str, Any]:
        """Revoke an API key."""
        response = self._request("DELETE", f"/api/v1/auth/api-keys/{key_id}")
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Users (Admin only)
    # =========================================================================
    
    def create_user(
        self,
        email: str,
        password: str,
        is_admin: bool = False,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new user (admin only)."""
        response = self._request(
            "POST",
            "/api/v1/auth/users",
            json={
                "email": email,
                "password": password,
                "is_admin": is_admin,
                "tenant_id": tenant_id,
            },
        )
        response.raise_for_status()
        return response.json()
    
    def list_users(self) -> List[Dict[str, Any]]:
        """List all users (admin only)."""
        response = self._request("GET", "/api/v1/auth/users")
        response.raise_for_status()
        return response.json()
    
    def get_user(self, user_id: str) -> Dict[str, Any]:
        """Get user by ID (admin only)."""
        response = self._request("GET", f"/api/v1/auth/users/{user_id}")
        response.raise_for_status()
        return response.json()
    
    def update_user(self, user_id: str, **updates) -> Dict[str, Any]:
        """Update user (admin only)."""
        response = self._request("PATCH", f"/api/v1/auth/users/{user_id}", json=updates)
        response.raise_for_status()
        return response.json()
    
    def delete_user(self, user_id: str) -> Dict[str, Any]:
        """Delete user (admin only)."""
        response = self._request("DELETE", f"/api/v1/auth/users/{user_id}")
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Tenants
    # =========================================================================
    
    def list_tenants(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List all tenants (admin only)."""
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        response = self._request("GET", "/api/v1/tenants", params=params)
        response.raise_for_status()
        return response.json()
    
    def create_tenant(
        self,
        name: str,
        email: str,
        tier: str = "STARTER",
        ship_os_enabled: bool = True,
    ) -> Dict[str, Any]:
        """Create a new tenant (admin only)."""
        response = self._request(
            "POST",
            "/api/v1/tenants",
            json={
                "name": name,
                "email": email,
                "tier": tier,
                "ship_os_enabled": ship_os_enabled,
            },
        )
        response.raise_for_status()
        return response.json()
    
    def get_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant by ID."""
        response = self._request("GET", f"/api/v1/tenants/{tenant_id}")
        response.raise_for_status()
        return response.json()
    
    def get_tenant_by_subdomain(self, subdomain: str) -> Dict[str, Any]:
        """Get tenant by subdomain (admin only)."""
        response = self._request("GET", f"/api/v1/tenants/by-subdomain/{subdomain}")
        response.raise_for_status()
        return response.json()
    
    def get_tenant_by_email(self, email: str) -> Dict[str, Any]:
        """Get tenant by email (admin only)."""
        response = self._request("GET", f"/api/v1/tenants/by-email/{email}")
        response.raise_for_status()
        return response.json()
    
    def update_tenant(
        self,
        tenant_id: str,
        **updates,
    ) -> Dict[str, Any]:
        """Update tenant settings."""
        response = self._request(
            "PATCH",
            f"/api/v1/tenants/{tenant_id}",
            json=updates,
        )
        response.raise_for_status()
        return response.json()
    
    def provision_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Trigger tenant provisioning (admin only)."""
        response = self._request(
            "POST",
            f"/api/v1/tenants/{tenant_id}/provision",
        )
        response.raise_for_status()
        return response.json()
    
    def suspend_tenant(
        self,
        tenant_id: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Suspend a tenant (admin only)."""
        params = {}
        if reason:
            params["reason"] = reason
        response = self._request(
            "POST",
            f"/api/v1/tenants/{tenant_id}/suspend",
            params=params,
        )
        response.raise_for_status()
        return response.json()
    
    def reactivate_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Reactivate a suspended tenant (admin only)."""
        response = self._request(
            "POST",
            f"/api/v1/tenants/{tenant_id}/reactivate",
        )
        response.raise_for_status()
        return response.json()
    
    def terminate_tenant(self, tenant_id: str) -> Dict[str, Any]:
        """Terminate a tenant (admin only)."""
        response = self._request(
            "DELETE",
            f"/api/v1/tenants/{tenant_id}",
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Self-Service
    # =========================================================================
    
    def get_my_tenant(self) -> Dict[str, Any]:
        """Get current user's tenant."""
        response = self._request("GET", "/api/v1/me/tenant")
        response.raise_for_status()
        return response.json()
    
    def get_my_billing(self) -> Dict[str, Any]:
        """Get current user's billing info."""
        response = self._request("GET", "/api/v1/me/billing")
        response.raise_for_status()
        return response.json()
    
    def access_my_billing_portal(self, return_url: str) -> Dict[str, Any]:
        """Get billing portal URL for current user."""
        response = self._request(
            "POST",
            "/api/v1/me/billing/portal",
            json={"return_url": return_url},
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Billing
    # =========================================================================
    
    def create_checkout(
        self,
        tenant_id: str,
        tier: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """Create a Stripe checkout session."""
        response = self._request(
            "POST",
            f"/api/v1/billing/{tenant_id}/checkout",
            json={
                "tier": tier,
                "success_url": success_url,
                "cancel_url": cancel_url,
            },
        )
        response.raise_for_status()
        return response.json()
    
    def create_billing_portal(
        self,
        tenant_id: str,
        return_url: str,
    ) -> Dict[str, Any]:
        """Create a Stripe billing portal session."""
        response = self._request(
            "POST",
            f"/api/v1/billing/{tenant_id}/portal",
            json={"return_url": return_url},
        )
        response.raise_for_status()
        return response.json()
    
    def get_subscription(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant subscription details."""
        response = self._request(
            "GET",
            f"/api/v1/billing/{tenant_id}/subscription",
        )
        response.raise_for_status()
        return response.json()
    
    def change_tier(
        self,
        tenant_id: str,
        tier: str,
    ) -> Dict[str, Any]:
        """Change subscription tier."""
        response = self._request(
            "POST",
            f"/api/v1/billing/{tenant_id}/change-tier",
            params={"tier": tier},
        )
        response.raise_for_status()
        return response.json()
    
    def cancel_subscription(
        self,
        tenant_id: str,
        immediately: bool = False,
    ) -> Dict[str, Any]:
        """Cancel subscription."""
        response = self._request(
            "POST",
            f"/api/v1/billing/{tenant_id}/cancel",
            params={"immediately": immediately},
        )
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # Health
    # =========================================================================
    
    def health(self) -> Dict[str, Any]:
        """Check API health."""
        response = self._request("GET", "/health")
        response.raise_for_status()
        return response.json()
    
    def ready(self) -> Dict[str, Any]:
        """Check API readiness (DB connectivity)."""
        response = self._request("GET", "/ready")
        response.raise_for_status()
        return response.json()
