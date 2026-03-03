'use client'

import { useState } from 'react'
import { Tenant, TenantStatus } from '@/lib/types'
import { provisionTenant, suspendTenant, reactivateTenant } from '@/lib/api'

interface TenantCardProps {
  tenant: Tenant
  onRefresh: () => void
}

const statusConfig: Record<TenantStatus, { label: string; color: string; bg: string }> = {
  pending: { label: 'Pending', color: 'text-slate-600', bg: 'bg-slate-100' },
  provisioning: { label: 'Provisioning', color: 'text-blue-600', bg: 'bg-blue-100' },
  active: { label: 'Active', color: 'text-green-600', bg: 'bg-green-100' },
  suspended: { label: 'Suspended', color: 'text-yellow-600', bg: 'bg-yellow-100' },
  terminated: { label: 'Terminated', color: 'text-red-600', bg: 'bg-red-100' },
}

const tierBadges: Record<string, { label: string; color: string }> = {
  starter: { label: 'Starter', color: 'bg-slate-200 text-slate-700' },
  pro: { label: 'Pro', color: 'bg-primary-100 text-primary-700' },
  business: { label: 'Business', color: 'bg-purple-100 text-purple-700' },
  enterprise: { label: 'Enterprise', color: 'bg-amber-100 text-amber-700' },
}

export default function TenantCard({ tenant, onRefresh }: TenantCardProps) {
  const [loading, setLoading] = useState(false)
  const status = statusConfig[tenant.status]
  const tier = tierBadges[tenant.tier] || tierBadges.starter

  async function handleAction(action: () => Promise<Tenant>) {
    try {
      setLoading(true)
      await action()
      onRefresh()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Action failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-100">
        <div className="flex items-start justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">{tenant.name}</h3>
            <p className="text-sm text-slate-500">{tenant.email}</p>
          </div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${status.bg} ${status.color}`}>
            {status.label}
          </span>
        </div>
      </div>

      {/* Details */}
      <div className="p-4 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">Subdomain</span>
          <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-700">
            {tenant.subdomain}.clawgeeks.com
          </code>
        </div>
        
        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">Tier</span>
          <span className={`px-2 py-0.5 rounded text-xs font-medium ${tier.color}`}>
            {tier.label}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">Agents</span>
          <span className="text-slate-700">{tenant.max_agents} max</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">ShipOS</span>
          <span className={tenant.shipos_enabled ? 'text-green-600' : 'text-slate-400'}>
            {tenant.shipos_enabled ? '✅ Enabled' : '❌ Disabled'}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-slate-500">Created</span>
          <span className="text-slate-700">
            {new Date(tenant.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      {/* Actions */}
      <div className="p-4 bg-slate-50 border-t border-slate-100 flex gap-2">
        {tenant.status === 'pending' && (
          <button
            onClick={() => handleAction(() => provisionTenant(tenant.id))}
            disabled={loading}
            className="flex-1 px-3 py-2 bg-primary-600 text-white text-sm rounded-lg hover:bg-primary-700 disabled:opacity-50"
          >
            {loading ? 'Working...' : 'Provision'}
          </button>
        )}
        
        {tenant.status === 'active' && (
          <button
            onClick={() => handleAction(() => suspendTenant(tenant.id))}
            disabled={loading}
            className="flex-1 px-3 py-2 bg-yellow-500 text-white text-sm rounded-lg hover:bg-yellow-600 disabled:opacity-50"
          >
            {loading ? 'Working...' : 'Suspend'}
          </button>
        )}
        
        {tenant.status === 'suspended' && (
          <button
            onClick={() => handleAction(() => reactivateTenant(tenant.id))}
            disabled={loading}
            className="flex-1 px-3 py-2 bg-green-600 text-white text-sm rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {loading ? 'Working...' : 'Reactivate'}
          </button>
        )}

        <button className="px-3 py-2 bg-slate-200 text-slate-700 text-sm rounded-lg hover:bg-slate-300">
          View
        </button>
      </div>
    </div>
  )
}
