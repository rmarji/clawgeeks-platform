# ClawGeeks API Client (TypeScript)

Official TypeScript client for the ClawGeeks Provisioning API.

## Installation

```bash
npm install @clawgeeks/api-client
```

## Quick Start

### API Key Authentication

```typescript
import { ClawGeeksClient, TenantTier } from '@clawgeeks/api-client';

const client = new ClawGeeksClient({
  baseUrl: 'https://api.clawgeeks.com',
  apiKey: 'cg_your_api_key',
});

// List tenants (admin only)
const tenants = await client.listTenants();

// Create tenant
const tenant = await client.createTenant({
  name: 'Acme Corp',
  email: 'admin@acme.com',
  tier: TenantTier.PRO,
  ship_os_enabled: true,
});
```

### JWT Authentication

```typescript
import { ClawGeeksClient } from '@clawgeeks/api-client';

const client = new ClawGeeksClient({
  baseUrl: 'https://api.clawgeeks.com',
});

// Login to get JWT token
await client.login('admin@example.com', 'password');
// Token is automatically stored

// Access self-service endpoints
const myTenant = await client.getMyTenant();
const myBilling = await client.getMyBilling();
```

## Features

### Tenant Management

```typescript
// Create tenant
const tenant = await client.createTenant({
  name: 'Acme Corp',
  email: 'admin@acme.com',
  tier: TenantTier.PRO,
});

// Get tenant
const tenant = await client.getTenant(tenantId);

// Update tenant
await client.updateTenant(tenantId, { name: 'New Name' });

// Lifecycle operations
await client.provisionTenant(tenantId);
await client.suspendTenant(tenantId, 'Non-payment');
await client.reactivateTenant(tenantId);
await client.terminateTenant(tenantId);
```

### Billing

```typescript
// Create checkout session
const checkout = await client.createCheckout(tenantId, {
  tier: TenantTier.PRO,
  success_url: 'https://app.acme.com/success',
  cancel_url: 'https://app.acme.com/cancel',
});
console.log(checkout.checkout_url);

// Get subscription details
const subscription = await client.getSubscription(tenantId);

// Change tier
await client.changeTier(tenantId, TenantTier.BUSINESS);

// Cancel subscription
await client.cancelSubscription(tenantId, false);

// Access billing portal
const portal = await client.createBillingPortal(
  tenantId,
  'https://app.acme.com/settings'
);
console.log(portal.portal_url);
```

### User Management (Admin)

```typescript
// Create user
const user = await client.createUser({
  email: 'user@acme.com',
  password: 'secure_password',
  is_admin: false,
  tenant_id: tenantId,
});

// List users
const users = await client.listUsers();

// Update user
await client.updateUser(userId, { is_admin: true });

// Delete user
await client.deleteUser(userId);
```

### API Keys

```typescript
// Create API key
const key = await client.createApiKey({
  name: 'Production Key',
  expires_in_days: 365,
});
console.log(key.key); // Only shown once!

// List keys
const keys = await client.listApiKeys();

// Revoke key
await client.revokeApiKey(keyId);
```

## Error Handling

```typescript
import { ClawGeeksClient } from '@clawgeeks/api-client';
import axios from 'axios';

const client = new ClawGeeksClient({ apiKey: 'cg_invalid' });

try {
  const tenants = await client.listTenants();
} catch (error) {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    
    if (status === 401) {
      console.log('Invalid API key');
    } else if (status === 403) {
      console.log('Access denied');
    } else if (status === 404) {
      console.log('Not found');
    } else {
      console.log(`Error: ${detail}`);
    }
  }
}
```

## Types

All types are exported for use in your application:

```typescript
import {
  Tenant,
  TenantCreate,
  TenantUpdate,
  TenantStatus,
  TenantTier,
  User,
  UserCreate,
  TokenResponse,
  APIKey,
  CheckoutRequest,
  CheckoutResponse,
  PortalRequest,
  PortalResponse,
  SubscriptionResponse,
  HealthResponse,
  ClientConfig,
} from '@clawgeeks/api-client';
```

## Development

```bash
# Install dependencies
npm install

# Build
npm run build

# Lint
npm run lint

# Test
npm test
```

## License

MIT
