/**
 * ClawGeeks API Client
 */

import axios, { AxiosInstance, AxiosRequestConfig } from 'axios';
import {
  Tenant,
  TenantCreate,
  TenantUpdate,
  TenantStatus,
  TenantTier,
  User,
  UserCreate,
  TokenResponse,
  LoginRequest,
  APIKey,
  APIKeyCreate,
  CheckoutRequest,
  CheckoutResponse,
  PortalRequest,
  PortalResponse,
  SubscriptionResponse,
  HealthResponse,
  ClientConfig,
} from './types';

export class ClawGeeksClient {
  private client: AxiosInstance;
  private token?: string;

  constructor(config: ClientConfig = {}) {
    const baseURL = config.baseUrl || 'http://localhost:8000';
    const timeout = config.timeout || 30000;

    this.client = axios.create({
      baseURL,
      timeout,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (config.token) {
      this.setToken(config.token);
    }

    if (config.apiKey) {
      this.setApiKey(config.apiKey);
    }
  }

  // ===========================================================================
  // Auth Configuration
  // ===========================================================================

  setToken(token: string): void {
    this.token = token;
    this.client.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    delete this.client.defaults.headers.common['X-API-Key'];
  }

  setApiKey(apiKey: string): void {
    this.client.defaults.headers.common['X-API-Key'] = apiKey;
    delete this.client.defaults.headers.common['Authorization'];
  }

  // ===========================================================================
  // Auth
  // ===========================================================================

  async login(email: string, password: string): Promise<TokenResponse> {
    const { data } = await this.client.post<TokenResponse>('/api/v1/auth/login', {
      email,
      password,
    });
    this.setToken(data.access_token);
    return data;
  }

  async getMe(): Promise<User> {
    const { data } = await this.client.get<User>('/api/v1/auth/me');
    return data;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await this.client.post('/api/v1/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  async createApiKey(request: APIKeyCreate): Promise<APIKey & { key: string }> {
    const { data } = await this.client.post('/api/v1/auth/api-keys', request);
    return data;
  }

  async listApiKeys(): Promise<APIKey[]> {
    const { data } = await this.client.get<APIKey[]>('/api/v1/auth/api-keys');
    return data;
  }

  async revokeApiKey(keyId: string): Promise<void> {
    await this.client.delete(`/api/v1/auth/api-keys/${keyId}`);
  }

  // ===========================================================================
  // Users (Admin)
  // ===========================================================================

  async createUser(request: UserCreate): Promise<User> {
    const { data } = await this.client.post<User>('/api/v1/auth/users', request);
    return data;
  }

  async listUsers(): Promise<User[]> {
    const { data } = await this.client.get<User[]>('/api/v1/auth/users');
    return data;
  }

  async getUser(userId: string): Promise<User> {
    const { data } = await this.client.get<User>(`/api/v1/auth/users/${userId}`);
    return data;
  }

  async updateUser(userId: string, updates: Partial<User>): Promise<User> {
    const { data } = await this.client.patch<User>(`/api/v1/auth/users/${userId}`, updates);
    return data;
  }

  async deleteUser(userId: string): Promise<void> {
    await this.client.delete(`/api/v1/auth/users/${userId}`);
  }

  // ===========================================================================
  // Tenants
  // ===========================================================================

  async listTenants(params?: {
    status?: TenantStatus;
    limit?: number;
    offset?: number;
  }): Promise<Tenant[]> {
    const { data } = await this.client.get<Tenant[]>('/api/v1/tenants', { params });
    return data;
  }

  async createTenant(request: TenantCreate): Promise<Tenant> {
    const { data } = await this.client.post<Tenant>('/api/v1/tenants', request);
    return data;
  }

  async getTenant(tenantId: string): Promise<Tenant> {
    const { data } = await this.client.get<Tenant>(`/api/v1/tenants/${tenantId}`);
    return data;
  }

  async getTenantBySubdomain(subdomain: string): Promise<Tenant> {
    const { data } = await this.client.get<Tenant>(`/api/v1/tenants/by-subdomain/${subdomain}`);
    return data;
  }

  async getTenantByEmail(email: string): Promise<Tenant> {
    const { data } = await this.client.get<Tenant>(`/api/v1/tenants/by-email/${email}`);
    return data;
  }

  async updateTenant(tenantId: string, updates: TenantUpdate): Promise<Tenant> {
    const { data } = await this.client.patch<Tenant>(`/api/v1/tenants/${tenantId}`, updates);
    return data;
  }

  async provisionTenant(tenantId: string): Promise<Tenant> {
    const { data } = await this.client.post<Tenant>(`/api/v1/tenants/${tenantId}/provision`);
    return data;
  }

  async suspendTenant(tenantId: string, reason?: string): Promise<Tenant> {
    const { data } = await this.client.post<Tenant>(
      `/api/v1/tenants/${tenantId}/suspend`,
      null,
      { params: { reason } }
    );
    return data;
  }

  async reactivateTenant(tenantId: string): Promise<Tenant> {
    const { data } = await this.client.post<Tenant>(`/api/v1/tenants/${tenantId}/reactivate`);
    return data;
  }

  async terminateTenant(tenantId: string): Promise<Tenant> {
    const { data } = await this.client.delete<Tenant>(`/api/v1/tenants/${tenantId}`);
    return data;
  }

  // ===========================================================================
  // Self-Service
  // ===========================================================================

  async getMyTenant(): Promise<Tenant> {
    const { data } = await this.client.get<Tenant>('/api/v1/me/tenant');
    return data;
  }

  async getMyBilling(): Promise<SubscriptionResponse> {
    const { data } = await this.client.get<SubscriptionResponse>('/api/v1/me/billing');
    return data;
  }

  async accessMyBillingPortal(returnUrl: string): Promise<PortalResponse> {
    const { data } = await this.client.post<PortalResponse>('/api/v1/me/billing/portal', {
      return_url: returnUrl,
    });
    return data;
  }

  // ===========================================================================
  // Billing
  // ===========================================================================

  async createCheckout(tenantId: string, request: CheckoutRequest): Promise<CheckoutResponse> {
    const { data } = await this.client.post<CheckoutResponse>(
      `/api/v1/billing/${tenantId}/checkout`,
      request
    );
    return data;
  }

  async createBillingPortal(tenantId: string, returnUrl: string): Promise<PortalResponse> {
    const { data } = await this.client.post<PortalResponse>(
      `/api/v1/billing/${tenantId}/portal`,
      { return_url: returnUrl }
    );
    return data;
  }

  async getSubscription(tenantId: string): Promise<SubscriptionResponse> {
    const { data } = await this.client.get<SubscriptionResponse>(
      `/api/v1/billing/${tenantId}/subscription`
    );
    return data;
  }

  async changeTier(tenantId: string, tier: TenantTier): Promise<{ success: boolean }> {
    const { data } = await this.client.post(
      `/api/v1/billing/${tenantId}/change-tier`,
      null,
      { params: { tier } }
    );
    return data;
  }

  async cancelSubscription(
    tenantId: string,
    immediately = false
  ): Promise<{ success: boolean; status: string; message: string }> {
    const { data } = await this.client.post(
      `/api/v1/billing/${tenantId}/cancel`,
      null,
      { params: { immediately } }
    );
    return data;
  }

  // ===========================================================================
  // Health
  // ===========================================================================

  async health(): Promise<HealthResponse> {
    const { data } = await this.client.get<HealthResponse>('/health');
    return data;
  }

  async ready(): Promise<HealthResponse> {
    const { data } = await this.client.get<HealthResponse>('/ready');
    return data;
  }
}
