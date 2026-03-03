# ClawGeeks API Client

Official Python client for the ClawGeeks Provisioning API.

## Installation

```bash
# From source
pip install -e sdk/python

# From PyPI (when published)
pip install clawgeeks-client
```

## Quick Start

### API Key Authentication

```python
from clawgeeks_client import ClawGeeksClient

client = ClawGeeksClient(
    base_url="https://api.clawgeeks.com",
    api_key="cg_your_api_key",
)

# List tenants (admin only)
tenants = client.list_tenants()

# Create tenant
tenant = client.create_tenant(
    name="Acme Corp",
    email="admin@acme.com",
    tier="PRO",
    ship_os_enabled=True,
)
```

### JWT Authentication

```python
from clawgeeks_client import ClawGeeksClient

client = ClawGeeksClient(base_url="https://api.clawgeeks.com")

# Login to get JWT token
tokens = client.login("admin@example.com", "password")
# Token is automatically stored in client

# Access self-service endpoints
my_tenant = client.get_my_tenant()
my_billing = client.get_my_billing()
```

## Features

### Tenant Management

```python
# Create tenant
tenant = client.create_tenant(
    name="Acme Corp",
    email="admin@acme.com",
    tier="PRO",
)

# Get tenant
tenant = client.get_tenant(tenant_id)

# Update tenant
client.update_tenant(tenant_id, name="New Name")

# Lifecycle operations
client.provision_tenant(tenant_id)
client.suspend_tenant(tenant_id, reason="Non-payment")
client.reactivate_tenant(tenant_id)
client.terminate_tenant(tenant_id)
```

### Billing

```python
# Create checkout session
checkout = client.create_checkout(
    tenant_id=tenant_id,
    tier="PRO",
    success_url="https://app.acme.com/success",
    cancel_url="https://app.acme.com/cancel",
)
print(checkout["checkout_url"])

# Get subscription details
subscription = client.get_subscription(tenant_id)

# Change tier
client.change_tier(tenant_id, tier="BUSINESS")

# Cancel subscription
client.cancel_subscription(tenant_id, immediately=False)

# Access billing portal
portal = client.create_billing_portal(
    tenant_id=tenant_id,
    return_url="https://app.acme.com/settings",
)
print(portal["portal_url"])
```

### User Management (Admin)

```python
# Create user
user = client.create_user(
    email="user@acme.com",
    password="secure_password",
    is_admin=False,
    tenant_id=tenant_id,
)

# List users
users = client.list_users()

# Update user
client.update_user(user_id, is_admin=True)

# Delete user
client.delete_user(user_id)
```

### API Keys

```python
# Create API key
key = client.create_api_key(
    name="Production Key",
    expires_in_days=365,
)
print(key["key"])  # Only shown once!

# List keys
keys = client.list_api_keys()

# Revoke key
client.revoke_api_key(key_id)
```

## Models

```python
from clawgeeks_client import Tenant, TenantStatus, TenantTier, User

# Parse API responses into typed models
tenant = Tenant.from_dict(client.get_tenant(tenant_id))
print(f"Tenant: {tenant.name} ({tenant.tier.value})")
print(f"Max agents: {tenant.tier.max_agents}")

user = User.from_dict(client.get_me())
print(f"User: {user.email} (admin: {user.is_admin})")
```

## Error Handling

```python
import httpx
from clawgeeks_client import ClawGeeksClient

client = ClawGeeksClient(api_key="cg_invalid")

try:
    tenants = client.list_tenants()
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        print("Invalid API key")
    elif e.response.status_code == 403:
        print("Access denied")
    elif e.response.status_code == 404:
        print("Not found")
    else:
        print(f"Error: {e.response.json()['detail']}")
```

## Development

```bash
# Install dev dependencies
pip install -e "sdk/python[dev]"

# Run tests
pytest

# Type checking
mypy clawgeeks_client
```

## License

MIT
