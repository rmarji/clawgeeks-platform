import { Tenant, CreateTenantRequest, ApiError } from './types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1'

async function fetchJSON<T>(
  endpoint: string, 
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!res.ok) {
    const error: ApiError = await res.json().catch(() => ({ 
      detail: `HTTP ${res.status}: ${res.statusText}` 
    }))
    throw new Error(error.detail)
  }

  return res.json()
}

export async function fetchTenants(): Promise<Tenant[]> {
  return fetchJSON<Tenant[]>('/tenants')
}

export async function fetchTenant(id: string): Promise<Tenant> {
  return fetchJSON<Tenant>(`/tenants/${id}`)
}

export async function createTenant(data: CreateTenantRequest): Promise<Tenant> {
  return fetchJSON<Tenant>('/tenants', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function provisionTenant(id: string): Promise<Tenant> {
  return fetchJSON<Tenant>(`/tenants/${id}/provision`, {
    method: 'POST',
  })
}

export async function suspendTenant(id: string): Promise<Tenant> {
  return fetchJSON<Tenant>(`/tenants/${id}/suspend`, {
    method: 'POST',
  })
}

export async function reactivateTenant(id: string): Promise<Tenant> {
  return fetchJSON<Tenant>(`/tenants/${id}/reactivate`, {
    method: 'POST',
  })
}

export async function terminateTenant(id: string): Promise<Tenant> {
  return fetchJSON<Tenant>(`/tenants/${id}/terminate`, {
    method: 'POST',
  })
}
