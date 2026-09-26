import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  DollarSign, TrendingDown, Layers, AlertCircle, ArrowUpRight,
  Sparkles, CheckCircle2, ChevronRight, BarChart3, PieChart
} from 'lucide-react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { useAppStore } from '../store'
import { fetchCostAnalytics, fetchRecommendations, simulateScenario } from '../api/client'
import type { CostDataPoint, RecommendationItem } from '../types'

export default function CostOptimizationPage() {
  const { provider, region } = useAppStore()
  const [days, setDays] = useState(7)
  const [selectedScenario, setSelectedScenario] = useState('RIGHT_SIZE')
  const [simResult, setSimResult] = useState<any>(null)
  const [simulating, setSimulating] = useState(false)

  const { data: costData, isLoading: costLoading } = useQuery({
    queryKey: ['costAnalytics', days],
    queryFn: () => fetchCostAnalytics(days),
  })

  const { data: recData } = useQuery({
    queryKey: ['recommendations', provider, region],
    queryFn: () => fetchRecommendations({ provider, region, category: 'cost' }),
  })

  const handleSimulate = async (scenario: string) => {
    setSelectedScenario(scenario)
    setSimulating(true)
    try {
      const res = await simulateScenario({ scenario })
      setSimResult(res)
    } catch (err) {
      console.error('Simulation failed', err)
    } finally {
      setSimulating(false)
    }
  }

  const costRecs = recData?.recommendations || []
  const totalSavings = costRecs.reduce((acc, r) => acc + r.estimated_monthly_savings_usd, 0)

  // Chart data
  const chartPoints = (costData?.data_points || []).map((p: CostDataPoint) => ({
    time: p.timestamp.slice(11, 16),
    cost: p.cost_usd,
  }))

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Cost Optimization Intelligence</h1>
          <p className="text-secondary text-sm mt-1">
            Autonomous underutilization detection, right-sizing analysis, and cloud spend reduction
          </p>
        </div>

        <div className="flex items-center gap-2">
          {[7, 14, 30].map(d => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`btn text-xs ${days === d ? 'btn-primary' : 'btn-secondary'}`}
            >
              {d} Days
            </button>
          ))}
        </div>
      </div>

      {/* Top summary cards */}
      <div className="grid-4 mb-4">
        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Total Period Spend</div>
          <div className="text-2xl font-black text-amber-400">
            ${costData?.total_usd?.toFixed(2) || '0.00'}
          </div>
          <div className="text-xs text-secondary mt-1">Across all compute & data transfer</div>
        </div>

        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Monthly Savings Opportunity</div>
          <div className="text-2xl font-black text-emerald-400">
            ${totalSavings.toFixed(0)}/mo
          </div>
          <div className="text-xs text-emerald-500 mt-1">~32% estimated cost cut</div>
        </div>

        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Idle Resource Burn</div>
          <div className="text-2xl font-black text-red-400">$185/mo</div>
          <div className="text-xs text-secondary mt-1">Unattached EBS &amp; idle nodes</div>
        </div>

        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">RI / Savings Plan Coverage</div>
          <div className="text-2xl font-black text-blue-400">42%</div>
          <div className="text-xs text-secondary mt-1">Target benchmark: &gt;75%</div>
        </div>
      </div>

      {/* Cost Trend Chart */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <DollarSign size={16} color="var(--amber-400)" />
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>Cloud Cost Spend Curve (${days}d Period)</h3>
          </div>
          <div className="text-xs text-muted">
            Hourly compute burn rate vs workload demand
          </div>
        </div>

        <div style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartPoints.length ? chartPoints : [{ time: '00:00', cost: 0.19 }]}>
              <defs>
                <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
              <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} domain={['auto', 'auto']} />
              <Tooltip
                contentStyle={{ background: 'var(--card-bg)', border: '1px solid var(--border)', borderRadius: 8 }}
                formatter={(val: any) => [`$${Number(val).toFixed(4)}/hr`, 'Spend Rate']}
              />
              <Area type="monotone" dataKey="cost" stroke="#f59e0b" fill="url(#costGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Interactive Right-Sizing Simulator Quick Panel */}
      <div className="card mb-4 card-accent-emerald">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Sparkles size={16} color="var(--emerald-400)" />
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>Instant Scenario Simulation (Digital Twin)</h3>
          </div>
          <span className="badge badge-emerald">SIMULATED / NON-DESTRUCTIVE</span>
        </div>

        <p className="text-secondary text-sm mb-3">
          Simulate how instance reconfiguration affects compute spend without applying any live changes:
        </p>

        <div className="flex items-center gap-2 mb-4 flex-wrap">
          {['RIGHT_SIZE', 'SCALE_DOWN', 'CONSOLIDATE'].map(sc => (
            <button
              key={sc}
              onClick={() => handleSimulate(sc)}
              disabled={simulating}
              className={`btn text-xs ${selectedScenario === sc ? 'btn-primary' : 'btn-secondary'}`}
            >
              Simulate {sc.replace('_', ' ')}
            </button>
          ))}
        </div>

        {simResult && (
          <div className="grid-3 p-3 rounded" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}>
            <div>
              <div className="text-xs text-muted">Baseline Spend</div>
              <div className="text-lg font-bold">${simResult.before?.cost?.toFixed(0)}/mo</div>
              <div className="text-xs text-secondary">CPU: {simResult.before?.cpu}%</div>
            </div>
            <div>
              <div className="text-xs text-muted">Projected Spend After</div>
              <div className="text-lg font-bold text-emerald-400">${simResult.after?.cost?.toFixed(0)}/mo</div>
              <div className="text-xs text-secondary">CPU: {simResult.after?.cpu}% (Headroom OK)</div>
            </div>
            <div>
              <div className="text-xs text-muted">Projected Net Monthly Savings</div>
              <div className="text-lg font-black text-emerald-400">+${simResult.estimated_saving?.toFixed(0)}/mo</div>
              <div className="text-xs text-emerald-500">Risk Assessment: {simResult.risk}</div>
            </div>
          </div>
        )}
      </div>

      {/* Active Cost Recommendations */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700 }} className="mb-3">
          Active Cost Optimization Actions ({costRecs.length})
        </h3>
        <div className="space-y-3">
          {costRecs.map(rec => (
            <div
              key={rec.id}
              className="p-3 rounded flex items-center justify-between flex-wrap gap-3"
              style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}
            >
              <div style={{ flex: '1 1 240px' }}>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{rec.title}</div>
                <div className="text-xs text-secondary mt-1">{rec.impact_summary}</div>
                <div className="flex items-center gap-2 mt-2 flex-wrap">
                  <span className="badge badge-amber text-xs font-mono">{rec.action}</span>
                  <span className="text-xs text-muted">Confidence: {(rec.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>
              <div className="text-right" style={{ flexShrink: 0 }}>
                <div className="text-lg font-bold text-emerald-400">
                  +${rec.estimated_monthly_savings_usd.toFixed(0)}/mo
                </div>
                <span className="badge badge-muted text-xs mt-1">Priority: {rec.priority}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
