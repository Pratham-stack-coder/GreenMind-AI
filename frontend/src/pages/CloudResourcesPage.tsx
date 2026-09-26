import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Server, Database, HardDrive, Search, Filter, RefreshCw,
  CheckCircle2, AlertTriangle, ArrowUpRight, ShieldCheck, Zap
} from 'lucide-react'
import { useAppStore } from '../store'
import { fetchCloudResources, fetchCloudProviders } from '../api/client'
import type { CloudResource } from '../types'

export default function CloudResourcesPage() {
  const { provider, region, setProvider, setRegion } = useAppStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [filterCandidate, setFilterCandidate] = useState(false)

  const { data: resourceData, isLoading, refetch } = useQuery({
    queryKey: ['cloudResources', provider, region],
    queryFn: () => fetchCloudResources(provider, region),
    refetchInterval: 30_000,
  })

  const { data: providersData } = useQuery({
    queryKey: ['cloudProviders'],
    queryFn: fetchCloudProviders,
  })

  const resources: CloudResource[] = resourceData?.resources || []

  const filtered = resources.filter(r => {
    const matchesSearch =
      r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.type.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.id.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesFilter = filterCandidate ? r.right_size_candidate : true
    return matchesSearch && matchesFilter
  })

  const rightSizeCount = resources.filter(r => r.right_size_candidate).length

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Cloud Resources Inventory</h1>
          <p className="text-secondary text-sm mt-1">
            Real-time infrastructure discovery & resource telemetry across {provider.toUpperCase()} ({region})
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="badge badge-emerald">
            {providersData?.providers?.find(p => p.id === provider)?.mode === 'LIVE' ? 'LIVE AWS' : 'DEMO MODE'}
          </span>
          <button
            onClick={() => refetch()}
            className="btn btn-secondary text-xs flex items-center gap-1"
          >
            <RefreshCw size={12} />
            Refresh
          </button>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid-4 mb-4">
        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Total Tracked Resources</div>
          <div className="text-2xl font-black">{resources.length}</div>
          <div className="text-xs text-secondary mt-1">EC2, Containers, EBS, RDS</div>
        </div>

        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Right-Size Candidates</div>
          <div className="text-2xl font-black text-amber-400">{rightSizeCount}</div>
          <div className="text-xs text-secondary mt-1">Sustained CPU &lt; 25%</div>
        </div>

        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Average Resource Load</div>
          <div className="text-2xl font-black text-emerald-400">
            {resources.length
              ? (resources.reduce((acc, r) => acc + r.cpu_utilization, 0) / resources.length).toFixed(1)
              : '0'}%
          </div>
          <div className="text-xs text-secondary mt-1">Across active workloads</div>
        </div>

        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Total Hourly Burn</div>
          <div className="text-2xl font-black text-indigo-400">
            ${resources.reduce((acc, r) => acc + r.cost_per_hour, 0).toFixed(3)}/hr
          </div>
          <div className="text-xs text-secondary mt-1">Compute & storage compute run-rate</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card mb-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="resource-filter-row">
            <div className="relative flex-1" style={{ minWidth: 200 }}>
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
              />
              <input
                type="text"
                placeholder="Search by resource ID, name, or instance type..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="input pl-9 text-xs w-full"
                style={{ paddingLeft: 32 }}
              />
            </div>

            <button
              onClick={() => setFilterCandidate(!filterCandidate)}
              className={`btn text-xs ${filterCandidate ? 'btn-primary' : 'btn-secondary'}`}
              style={{ whiteSpace: 'nowrap' }}
            >
              <Filter size={12} className="mr-1 inline" />
              Right-Size Candidates Only ({rightSizeCount})
            </button>
          </div>

          <div className="flex items-center gap-3">
            <label className="text-xs text-secondary font-medium">Provider:</label>
            <select
              value={provider}
              onChange={e => setProvider(e.target.value)}
              className="select text-xs"
              style={{ minWidth: 100 }}
            >
              <option value="aws">AWS</option>
              <option value="azure">Azure</option>
              <option value="gcp">GCP</option>
            </select>
          </div>
        </div>
      </div>

      {/* Resources Table */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table className="table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)', background: 'rgba(255,255,255,0.02)' }}>
                <th style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>RESOURCE</th>
                <th style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>TYPE</th>
                <th style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>STATUS</th>
                <th style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>CPU LOAD</th>
                <th style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>MEMORY</th>
                <th style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>COST/HR</th>
                <th style={{ padding: '12px 16px', fontSize: 12, color: 'var(--text-muted)' }}>OPTIMIZATION</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                    Loading cloud resource inventory...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
                    No matching resources found in {provider.toUpperCase()} ({region}).
                  </td>
                </tr>
              ) : (
                filtered.map(r => (
                  <tr
                    key={r.id}
                    style={{ borderBottom: '1px solid var(--border)' }}
                    className="hover:bg-white/5 transition-colors"
                  >
                    <td style={{ padding: '12px 16px' }}>
                      <div className="flex items-center gap-2">
                        <Server size={14} color="var(--emerald-400)" />
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600 }}>{r.name}</div>
                          <div style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                            {r.id}
                          </div>
                        </div>
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 12, fontFamily: 'monospace' }}>
                      {r.type}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span className="badge badge-emerald" style={{ fontSize: 10 }}>
                        <span className="status-dot online" style={{ width: 4, height: 4 }} />
                        {r.status.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <div className="flex items-center gap-2">
                        <div style={{ width: 50, height: 6, background: 'rgba(255,255,255,0.1)', borderRadius: 3, overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${Math.min(100, r.cpu_utilization)}%`,
                              height: '100%',
                              background: r.cpu_utilization > 75 ? 'var(--red-400)' : r.cpu_utilization < 25 ? 'var(--amber-400)' : 'var(--emerald-400)',
                            }}
                          />
                        </div>
                        <span style={{ fontSize: 12, fontWeight: 600 }}>{r.cpu_utilization.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 12 }}>
                      {r.memory_utilization ? `${r.memory_utilization.toFixed(1)}%` : 'CWAgent Req.'}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: 12, fontWeight: 600 }}>
                      ${r.cost_per_hour.toFixed(3)}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      {r.right_size_candidate ? (
                        <span className="badge badge-amber text-xs font-semibold">
                          <AlertTriangle size={10} className="mr-1 inline" />
                          RIGHT-SIZE (-40%)
                        </span>
                      ) : (
                        <span className="badge badge-muted text-xs">OPTIMAL</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
