export type TenantStatus = 
  | 'pending' 
  | 'provisioning' 
  | 'active' 
  | 'suspended' 
  | 'terminated'

export type TenantTier = 
  | 'starter' 
  | 'pro' 
  | 'business' 
  | 'enterprise'

export interface Tenant {
  id: string
  name: string
  email: string
  subdomain: string
  tier: TenantTier
  status: TenantStatus
  max_agents: number
  shipos_enabled: boolean
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  container_id: string | null
  created_at: string
  updated_at: string
  provisioned_at: string | null
  suspended_at: string | null
  terminated_at: string | null
}

export interface TenantStats {
  total: number
  active: number
  pending: number
  suspended: number
  mrr: number
}

export interface CreateTenantRequest {
  name: string
  email: string
  tier: TenantTier
  shipos_enabled?: boolean
}

export interface ApiError {
  detail: string
}
