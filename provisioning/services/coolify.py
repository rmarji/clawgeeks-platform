"""Coolify API integration for container orchestration."""

import os
import httpx
from typing import Optional
from ..models import Tenant, TenantTier


# Tier → max agents mapping
TIER_AGENT_LIMITS = {
    TenantTier.STARTER: 1,
    TenantTier.PRO: 3,
    TenantTier.BUSINESS: 6,
    TenantTier.ENTERPRISE: 20,
}


class CoolifyClient:
    """Client for Coolify API to manage OpenClaw containers."""
    
    def __init__(
        self,
        base_url: str = None,
        api_key: str = None,
    ):
        self.base_url = base_url or os.getenv("COOLIFY_URL", "https://coolify.claw.jogeeks.com")
        self.api_key = api_key or os.getenv("COOLIFY_API_KEY")
        self.team_id = os.getenv("COOLIFY_TEAM_ID", "0")
        
    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    async def deploy_openclaw(
        self,
        tenant: Tenant,
        openclaw_image: str = "ghcr.io/openclaw/openclaw:latest",
    ) -> dict:
        """Deploy OpenClaw container for tenant.
        
        Creates a new application in Coolify with:
        - OpenClaw Docker image
        - Environment variables for config
        - Unique subdomain
        - Auto-SSL via Coolify
        """
        # Generate gateway token (256-bit)
        import secrets
        gateway_token = secrets.token_hex(32)
        
        payload = {
            "project_uuid": os.getenv("COOLIFY_PROJECT_UUID"),
            "server_uuid": os.getenv("COOLIFY_SERVER_UUID"),
            "environment_name": "production",
            "type": "dockerfile",
            "name": f"tenant-{tenant.subdomain}",
            "description": f"OpenClaw instance for {tenant.name}",
            "domains": f"{tenant.subdomain}.clawgeeks.cloud",
            "docker_compose_raw": self._generate_compose(tenant, gateway_token),
            "instant_deploy": True,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/applications",
                headers=self.headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            result = response.json()
            
        return {
            "application_uuid": result.get("uuid"),
            "gateway_url": f"https://{tenant.subdomain}.clawgeeks.cloud",
            "gateway_token": gateway_token,
        }
    
    def _generate_compose(self, tenant: Tenant, gateway_token: str) -> str:
        """Generate docker-compose for tenant."""
        max_agents = TIER_AGENT_LIMITS.get(tenant.tier, 1)
        
        return f"""
version: '3.8'
services:
  openclaw:
    image: ghcr.io/openclaw/openclaw:latest
    restart: unless-stopped
    environment:
      - OPENCLAW_TOKEN={gateway_token}
      - OPENCLAW_MODEL={tenant.config.model}
      - OPENCLAW_TENANT_ID={tenant.id}
      - OPENCLAW_TENANT_NAME={tenant.name}
      - OPENCLAW_MAX_AGENTS={max_agents}
      - SHIPOS_ENABLED={str(tenant.config.shipos_enabled).lower()}
    volumes:
      - ./data:/data
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
"""

    async def get_application_status(self, application_uuid: str) -> dict:
        """Get status of a Coolify application."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/applications/{application_uuid}",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.json()
    
    async def stop_application(self, application_uuid: str) -> bool:
        """Stop a running application (suspend tenant)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/applications/{application_uuid}/stop",
                headers=self.headers,
            )
            return response.status_code == 200
    
    async def start_application(self, application_uuid: str) -> bool:
        """Start a stopped application (reactivate tenant)."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/v1/applications/{application_uuid}/start",
                headers=self.headers,
            )
            return response.status_code == 200
    
    async def delete_application(self, application_uuid: str) -> bool:
        """Delete application (terminate tenant)."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/api/v1/applications/{application_uuid}",
                headers=self.headers,
            )
            return response.status_code == 200
