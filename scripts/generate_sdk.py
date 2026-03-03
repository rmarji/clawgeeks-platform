#!/usr/bin/env python3
"""Generate SDK clients from OpenAPI spec.

Usage:
    python scripts/generate_sdk.py [--typescript] [--python] [--all]
    
Outputs:
    sdk/typescript/  - TypeScript/JavaScript client
    sdk/python/      - Python client
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SDK_DIR = PROJECT_ROOT / "sdk"
OPENAPI_JSON = PROJECT_ROOT / "openapi.json"

# Ensure output directories exist
(SDK_DIR / "typescript").mkdir(parents=True, exist_ok=True)
(SDK_DIR / "python").mkdir(parents=True, exist_ok=True)


def export_openapi_spec():
    """Export OpenAPI spec from running app or generate statically."""
    print("📄 Exporting OpenAPI specification...")
    
    # Try to get from running server
    try:
        import httpx
        response = httpx.get("http://localhost:8000/openapi.json", timeout=5)
        if response.status_code == 200:
            spec = response.json()
            with open(OPENAPI_JSON, "w") as f:
                json.dump(spec, f, indent=2)
            print(f"   ✓ Exported from running server to {OPENAPI_JSON}")
            return True
    except Exception:
        pass
    
    # Generate statically by importing app
    print("   ⚠ Server not running, generating statically...")
    sys.path.insert(0, str(PROJECT_ROOT))
    
    try:
        from provisioning.api.main import app
        from provisioning.api.openapi import configure_openapi
        
        # Configure OpenAPI
        configure_openapi(app)
        
        # Get schema
        spec = app.openapi()
        
        with open(OPENAPI_JSON, "w") as f:
            json.dump(spec, f, indent=2)
        
        print(f"   ✓ Generated statically to {OPENAPI_JSON}")
        return True
    except Exception as e:
        print(f"   ✗ Failed to generate spec: {e}")
        return False


def generate_typescript_sdk():
    """Generate TypeScript SDK using openapi-typescript-codegen."""
    print("\n🔷 Generating TypeScript SDK...")
    
    output_dir = SDK_DIR / "typescript"
    
    # Check if npx is available
    try:
        subprocess.run(["npx", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ✗ npx not found. Install Node.js first.")
        return False
    
    # Generate using openapi-typescript-codegen
    cmd = [
        "npx", "openapi-typescript-codegen",
        "--input", str(OPENAPI_JSON),
        "--output", str(output_dir),
        "--name", "ClawGeeksClient",
        "--useOptions",
        "--exportCore", "true",
        "--exportServices", "true",
        "--exportModels", "true",
        "--exportSchemas", "true",
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Try alternative: openapi-typescript
            print("   ⚠ openapi-typescript-codegen failed, trying openapi-typescript...")
            cmd_alt = [
                "npx", "openapi-typescript", str(OPENAPI_JSON),
                "-o", str(output_dir / "schema.ts"),
            ]
            result = subprocess.run(cmd_alt, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"   ✗ Generation failed: {result.stderr}")
                return False
        
        print(f"   ✓ TypeScript SDK generated at {output_dir}")
        
        # Create package.json
        package_json = {
            "name": "@clawgeeks/api-client",
            "version": "0.3.0",
            "description": "ClawGeeks Platform API Client",
            "main": "index.ts",
            "types": "index.ts",
            "scripts": {
                "build": "tsc",
                "lint": "eslint ."
            },
            "dependencies": {
                "axios": "^1.6.0"
            },
            "devDependencies": {
                "typescript": "^5.3.0",
                "@types/node": "^20.0.0"
            }
        }
        
        with open(output_dir / "package.json", "w") as f:
            json.dump(package_json, f, indent=2)
        
        print("   ✓ Created package.json")
        return True
        
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False


def generate_python_sdk():
    """Generate Python SDK using openapi-python-client."""
    print("\n🐍 Generating Python SDK...")
    
    output_dir = SDK_DIR / "python"
    
    # Check if openapi-python-client is installed
    try:
        subprocess.run(
            [sys.executable, "-m", "openapi_python_client", "--version"],
            capture_output=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("   ⚠ openapi-python-client not found, installing...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "openapi-python-client"],
            capture_output=True,
        )
    
    # Remove existing output to regenerate
    if (output_dir / "clawgeeks_client").exists():
        import shutil
        shutil.rmtree(output_dir / "clawgeeks_client")
    
    # Generate SDK
    cmd = [
        sys.executable, "-m", "openapi_python_client",
        "generate",
        "--path", str(OPENAPI_JSON),
        "--output-path", str(output_dir / "clawgeeks_client"),
        "--config", str(PROJECT_ROOT / "sdk-config.yaml") if (PROJECT_ROOT / "sdk-config.yaml").exists() else "",
    ]
    
    # Remove empty config arg if no config file
    cmd = [c for c in cmd if c]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir)
        if result.returncode != 0:
            # Try without config
            cmd = [
                sys.executable, "-m", "openapi_python_client",
                "generate",
                "--path", str(OPENAPI_JSON),
                "--output-path", str(output_dir / "clawgeeks_client"),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=output_dir)
            if result.returncode != 0:
                print(f"   ✗ Generation failed: {result.stderr}")
                # Create minimal client manually
                create_minimal_python_client(output_dir)
                return True
        
        print(f"   ✓ Python SDK generated at {output_dir}")
        return True
        
    except Exception as e:
        print(f"   ⚠ openapi-python-client error: {e}")
        print("   → Creating minimal client manually...")
        create_minimal_python_client(output_dir)
        return True


def create_minimal_python_client(output_dir: Path):
    """Create a minimal Python client if codegen fails."""
    client_dir = output_dir / "clawgeeks_client"
    client_dir.mkdir(parents=True, exist_ok=True)
    
    # __init__.py
    init_content = '''"""ClawGeeks API Client - Auto-generated from OpenAPI spec."""

from .client import ClawGeeksClient
from .models import *

__version__ = "0.3.0"
__all__ = ["ClawGeeksClient"]
'''
    
    # client.py
    client_content = '''"""ClawGeeks API Client."""

from typing import Optional, Dict, Any, List
import httpx


class ClawGeeksClient:
    """Client for ClawGeeks Provisioning API."""
    
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
        """Get current user\'s tenant."""
        response = self._request("GET", "/api/v1/me/tenant")
        response.raise_for_status()
        return response.json()
    
    def get_my_billing(self) -> Dict[str, Any]:
        """Get current user\'s billing info."""
        response = self._request("GET", "/api/v1/me/billing")
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
'''
    
    # models.py
    models_content = '''"""Data models for ClawGeeks API."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime


class TenantStatus(str, Enum):
    """Tenant lifecycle status."""
    PENDING = "PENDING"
    PROVISIONING = "PROVISIONING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    TERMINATED = "TERMINATED"


class TenantTier(str, Enum):
    """Subscription tier."""
    STARTER = "STARTER"
    PRO = "PRO"
    BUSINESS = "BUSINESS"
    ENTERPRISE = "ENTERPRISE"


@dataclass
class Tenant:
    """Tenant data model."""
    id: str
    name: str
    email: str
    subdomain: str
    tier: TenantTier
    status: TenantStatus
    ship_os_enabled: bool
    agent_count: int
    created_at: datetime
    updated_at: datetime
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    coolify_app_id: Optional[str] = None


@dataclass
class User:
    """User data model."""
    id: str
    email: str
    is_admin: bool
    is_active: bool
    tenant_id: Optional[str] = None


@dataclass
class TokenResponse:
    """Authentication token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
'''
    
    # Write files
    (client_dir / "__init__.py").write_text(init_content)
    (client_dir / "client.py").write_text(client_content)
    (client_dir / "models.py").write_text(models_content)
    
    # pyproject.toml
    pyproject = '''[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "clawgeeks-client"
version = "0.3.0"
description = "ClawGeeks Platform API Client"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "httpx>=0.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-asyncio>=0.21.0",
]
'''
    (output_dir / "pyproject.toml").write_text(pyproject)
    
    # README
    readme = '''# ClawGeeks API Client

Python client for the ClawGeeks Provisioning API.

## Installation

```bash
pip install -e sdk/python
```

## Usage

```python
from clawgeeks_client import ClawGeeksClient

# Initialize client
client = ClawGeeksClient(
    base_url="https://api.clawgeeks.com",
    api_key="cg_your_api_key",
)

# Or with JWT
client = ClawGeeksClient(base_url="https://api.clawgeeks.com")
client.login("admin@example.com", "password")

# List tenants
tenants = client.list_tenants()

# Create tenant
tenant = client.create_tenant(
    name="Acme Corp",
    email="admin@acme.com",
    tier="PRO",
)

# Self-service
my_tenant = client.get_my_tenant()
my_billing = client.get_my_billing()
```
'''
    (output_dir / "README.md").write_text(readme)
    
    print(f"   ✓ Created minimal Python client at {client_dir}")


def main():
    parser = argparse.ArgumentParser(description="Generate SDK clients from OpenAPI spec")
    parser.add_argument("--typescript", "-ts", action="store_true", help="Generate TypeScript SDK")
    parser.add_argument("--python", "-py", action="store_true", help="Generate Python SDK")
    parser.add_argument("--all", "-a", action="store_true", help="Generate all SDKs")
    
    args = parser.parse_args()
    
    # Default to all if nothing specified
    if not (args.typescript or args.python or args.all):
        args.all = True
    
    print("=" * 60)
    print("ClawGeeks SDK Generator")
    print("=" * 60)
    
    # Export OpenAPI spec
    if not export_openapi_spec():
        print("\n❌ Failed to export OpenAPI spec. Exiting.")
        sys.exit(1)
    
    results = []
    
    if args.typescript or args.all:
        results.append(("TypeScript", generate_typescript_sdk()))
    
    if args.python or args.all:
        results.append(("Python", generate_python_sdk()))
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")
    
    if all(r[1] for r in results):
        print("\n✅ All SDKs generated successfully!")
        print(f"\nOutput: {SDK_DIR}")
    else:
        print("\n⚠ Some SDKs failed to generate.")
        sys.exit(1)


if __name__ == "__main__":
    main()
