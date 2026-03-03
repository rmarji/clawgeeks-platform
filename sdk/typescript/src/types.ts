/**
 * ClawGeeks API Types
 */

export enum TenantStatus {
  PENDING = 'PENDING',
  PROVISIONING = 'PROVISIONING',
  ACTIVE = 'ACTIVE',
  SUSPENDED = 'SUSPENDED',
  TERMINATED = 'TERMINATED',
}

export enum TenantTier {
  STARTER = 'STARTER',
  PRO = 'PRO',
  BUSINESS = 'BUSINESS',
  ENTERPRISE = 'ENTERPRISE',
}

export interface Tenant {
  id: string;
  name: string;
  email: string;
  subdomain: string;
  tier: TenantTier;
  status: TenantStatus;
  ship_os_enabled: boolean;
  agent_count: number;
  created_at: string;
  updated_at: string;
  stripe_customer_id?: string;
  stripe_subscription_id?: string;
  coolify_app_id?: string;
}

export interface TenantCreate {
  name: string;
  email: string;
  tier?: TenantTier;
  ship_os_enabled?: boolean;
}

export interface TenantUpdate {
  name?: string;
  email?: string;
  tier?: TenantTier;
  ship_os_enabled?: boolean;
}

export interface User {
  id: string;
  email: string;
  is_admin: boolean;
  is_active: boolean;
  tenant_id?: string;
}

export interface UserCreate {
  email: string;
  password: string;
  is_admin?: boolean;
  tenant_id?: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface APIKey {
  id: string;
  name: string;
  prefix: string;
  is_active: boolean;
  expires_at?: string;
  last_used_at?: string;
  use_count: number;
}

export interface APIKeyCreate {
  name: string;
  expires_in_days?: number;
}

export interface CheckoutRequest {
  tier: TenantTier;
  success_url: string;
  cancel_url: string;
}

export interface CheckoutResponse {
  checkout_url: string;
}

export interface PortalRequest {
  return_url: string;
}

export interface PortalResponse {
  portal_url: string;
}

export interface SubscriptionResponse {
  subscription: Record<string, unknown> | null;
  message?: string;
}

export interface HealthResponse {
  status: string;
  service?: string;
  version?: string;
  database?: string;
}

export interface ClientConfig {
  baseUrl?: string;
  token?: string;
  apiKey?: string;
  timeout?: number;
}
