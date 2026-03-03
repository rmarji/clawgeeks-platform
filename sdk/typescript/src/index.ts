/**
 * ClawGeeks API Client
 * 
 * Official TypeScript client for the ClawGeeks Provisioning API.
 * 
 * @example
 * ```typescript
 * import { ClawGeeksClient, TenantTier } from '@clawgeeks/api-client';
 * 
 * const client = new ClawGeeksClient({
 *   baseUrl: 'https://api.clawgeeks.com',
 *   apiKey: 'cg_your_api_key',
 * });
 * 
 * // List tenants
 * const tenants = await client.listTenants();
 * 
 * // Create tenant
 * const tenant = await client.createTenant({
 *   name: 'Acme Corp',
 *   email: 'admin@acme.com',
 *   tier: TenantTier.PRO,
 * });
 * ```
 */

export { ClawGeeksClient } from './client';
export * from './types';
