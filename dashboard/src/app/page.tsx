'use client'

import { useEffect, useState } from 'react'
import TenantCard from '@/components/TenantCard'
import StatsCard from '@/components/StatsCard'
import { Tenant, TenantStats } from '@/lib/types'
import { fetchTenants } from '@/lib/api'

export default function Dashboard() {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadTenants()
  }, [])

  async function loadTenants() {
    try {
      setLoading(true)
      const data = await fetchTenants()
      setTenants(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tenants')
    } finally {
      setLoading(false)
    }
  }

  const stats: TenantStats = {
    total: tenants.length,
    active: tenants.filter(t => t.status === 'active').length,
    pending: tenants.filter(t => t.status === 'pending').length,
    suspended: tenants.filter(t => t.status === 'suspended').length,
    mrr: tenants
      .filter(t => t.status === 'active')
      .reduce((sum, t) => sum + getPriceForTier(t.tier), 0),
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900">Dashboard</h1>
        <button
          onClick={loadTenants}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatsCard title="Total Tenants" value={stats.total} icon="🏢" />
        <StatsCard title="Active" value={stats.active} icon="✅" color="green" />
        <StatsCard title="Pending" value={stats.pending} icon="⏳" color="yellow" />
        <StatsCard title="Suspended" value={stats.suspended} icon="⚠️" color="red" />
        <StatsCard title="MRR" value={`$${stats.mrr}`} icon="💰" color="blue" />
      </div>

      {/* Tenants Grid */}
      <div>
        <h2 className="text-xl font-semibold text-slate-800 mb-4">Tenants</h2>
        
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : error ? (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
            {error}
          </div>
        ) : tenants.length === 0 ? (
          <div className="bg-slate-100 text-slate-600 px-4 py-12 rounded-lg text-center">
            No tenants yet. Create your first tenant to get started.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tenants.map(tenant => (
              <TenantCard key={tenant.id} tenant={tenant} onRefresh={loadTenants} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function getPriceForTier(tier: string): number {
  const prices: Record<string, number> = {
    starter: 49,
    pro: 149,
    business: 299,
    enterprise: 999,
  }
  return prices[tier] || 0
}
