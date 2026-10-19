import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  DollarSign, Sparkles, ChevronRight,
  AlertTriangle, RefreshCw, Loader2
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts'
import { useAppStore } from '../store'
import { fetchCostAnalytics, fetchRecommendations, simulateScenario } from '../api/client'
import type { CostDataPoint } from '../types'

export default function CostOptimizationPage() {
  const { provider, region } = useAppStore()
  const [days, setDays] = useState(7)
  const [selectedScenario, setSelectedScenario] = useState('RIGHT_SIZE')
  const [simResult, setSimResult] = useState<any>(null)
  const [simulating, setSimulating] = useState(false)
  const [simError, setSimError] = useState<string | null>(null)

  const {
    data: costData,
    isLoading: costLoading,
    isError: costError,
    refetch: refetchCost,
  } = useQuery({
    queryKey: ['costAnalytics', days],
    queryFn: () => fetchCostAnalytics(days),
  })

  const {
    data: recData,
    isLoading: recLoading,
    isError: recError,
    refetch: refetchRecs,
  } = useQuery({
    queryKey: ['recommendations', provider, region],
    queryFn: () => fetchRecommendations({ provider, region, category: 'cost' }),
  })

  const handleSimulate = async (scenario: string) => {
    setSelectedScenario(scenario)
    setSimulating(true)
    setSimError(null)
    try {
      const res = await simulateScenario({ scenario })
      setSimResult(res)
    } catch (err: unknown) {
      console.error('Simulation failed', err)
      setSimError(err instanceof Error ? err.message : 'Simulation failed')
    } finally {
      setSimulating(false)
    }
  }

  const costRecs = recData?.recommendations || []
  const totalSavings = costRecs.reduce((acc, r) => acc + r.estimated_monthly_savings_usd, 0)

  // Dynamic idle resource burn calculation from active recommendations
  const idleRecs = costRecs.filter(r =>
    r.title.toLowerCase().includes('idle') ||
    r.action.toLowerCase().includes('idle') ||
    r.description.toLowerCase().includes('idle') ||
    r.description.toLowerCase().includes('unattached')
  )
  const detectedIdleBurn = idleRecs.reduce((acc, r) => acc + r.estimated_monthly_savings_usd, 0)

  // Dynamic savings cut percentage based on period spend annualized to monthly
  const periodSpend = costData?.total_usd ?? 0
  const normalizedMonthlySpend = days > 0 ? (periodSpend / days) * 30 : 0
  const savingsPct = normalizedMonthlySpend > 0
    ? Math.min(100, Math.round((totalSavings / normalizedMonthlySpend) * 100))
    : null

  // Chart data
  const chartPoints = (costData?.data_points || []).map((p: CostDataPoint) => ({
    time: p.timestamp ? p.timestamp.slice(11, 16) : '00:00',
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
          <button
            className="btn btn-secondary text-xs"
            onClick={() => { refetchCost(); refetchRecs(); }}
            title="Refresh Cost Analytics"
          >
            <RefreshCw size={13} />
          </button>
        </div>
      </div>

      {/* Top summary cards */}
      <div className="grid-4 mb-4">
        {/* Total Period Spend */}
        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Total Period Spend</div>
          {costLoading ? (
            <div className="skeleton" style={{ height: 32, width: 120, margin: '4px 0' }} />
          ) : costError ? (
            <div className="text-sm text-red-400">Unavailable</div>
          ) : (
            <div className="text-2xl font-black text-amber-400">
              ${periodSpend.toFixed(2)}
            </div>
          )}
          <div className="text-xs text-secondary mt-1">
            Telemetry spend over {days}d window
          </div>
        </div>

        {/* Monthly Savings Opportunity */}
        <div className="card">
          <div className="text-xs text-muted mb-1 font-semibold uppercase">Monthly Savings Opportunity</div>
          {recLoading ? (
            <div className="skeleton" style={{ height: 32, width: 120, margin: '4px 0' }} />
          ) : (
            <div className="text-2xl font-black text-emerald-400">
              ${totalSavings.toFixed(0)}/mo
            </div>
          )}
          <div className="text-xs text-emerald-500 mt-1">
            {savingsPct !== null
              ? `~${savingsPct}% projected spend reduction (Simulated)`
              : 'Projected from open recommendations'}
          </div>
        </div>

        {/* Idle Resource Burn */}
        <div className="card">
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs text-muted font-semibold uppercase">Idle Resource Burn</div>
            {detectedIdleBurn > 0 ? (
              <span className="badge badge-red" style={{ fontSize: 9, padding: '1px 5px' }}>Detected</span>
            ) : (
              <span className="badge badge-muted" style={{ fontSize: 9, padding: '1px 5px' }}>Demo Ref</span>
            )}
          </div>
          {recLoading ? (
            <div className="skeleton" style={{ height: 32, width: 120, margin: '4px 0' }} />
          ) : detectedIdleBurn > 0 ? (
            <>
              <div className="text-2xl font-black text-red">${detectedIdleBurn.toFixed(0)}/mo</div>
              <div className="text-xs text-secondary mt-1">
                {idleRecs.length} idle/unattached resource(s) detected
              </div>
            </>
          ) : (
            <>
              <div className="text-2xl font-black text-secondary">$0/mo</div>
              <div className="text-xs text-muted mt-1">
                No idle waste detected in active telemetry (sample ref: $185/mo)
              </div>
            </>
          )}
        </div>

        {/* RI / Savings Plan Coverage */}
        <div className="card">
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs text-muted font-semibold uppercase">Commitment Coverage</div>
            <span className="badge badge-amber" style={{ fontSize: 9, padding: '1px 5px' }}>Demo Benchmark</span>
          </div>
          <div className="text-2xl font-black text-emerald">42%</div>
          <div className="text-xs text-secondary mt-1">
            Industry benchmark: &gt;75% (Live RI API not connected)
          </div>
        </div>
      </div>

      {/* Cost Trend Chart */}
      <div className="card mb-4">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <DollarSign size={16} color="var(--amber-600)" />
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>Cloud Cost Spend Curve ({days}d Period)</h3>
          </div>
          <div className="text-xs text-muted">
            Hourly compute burn rate vs workload demand
          </div>
        </div>

        {costLoading ? (
          <div className="skeleton" style={{ height: 220, borderRadius: 8 }} />
        ) : costError ? (
          <div style={{ height: 220, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <AlertTriangle size={24} color="var(--red-600)" className="mb-2" />
            <div className="text-sm text-secondary">Unable to load telemetry cost trend.</div>
            <button className="btn btn-secondary btn-sm mt-2" onClick={() => refetchCost()}>Retry</button>
          </div>
        ) : chartPoints.length === 0 ? (
          <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div className="text-sm text-muted">No cost data points available for this period.</div>
          </div>
        ) : (
          <div style={{ height: 220 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartPoints}>
                <defs>
                  <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#d97706" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#d97706" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} domain={['auto', 'auto']} />
                <Tooltip
                  contentStyle={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }}
                  formatter={(val: any) => [`$${Number(val).toFixed(4)}/hr`, 'Spend Rate']}
                />
                <Area type="monotone" dataKey="cost" stroke="#d97706" fill="url(#costGrad)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Interactive Right-Sizing Simulator Quick Panel */}
      <div className="card mb-4 card-accent-emerald">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Sparkles size={16} color="var(--emerald-600)" />
            <h3 style={{ fontSize: 15, fontWeight: 700 }}>Instant Scenario Simulation (Digital Twin)</h3>
          </div>
          <span className="badge badge-emerald">SIMULATED / NON-DESTRUCTIVE</span>
        </div>

        <p className="text-secondary text-sm mb-3">
          Simulate how instance reconfiguration affects compute spend without applying any live changes:
        </p>

        <div className="flex items-center gap-2 mb-4 flex-wrap">
          {['RIGHT_SIZE', 'SCALE_DOWN', 'CONSOLIDATE', 'REGION_MIGRATION'].map(sc => (
            <button
              key={sc}
              onClick={() => handleSimulate(sc)}
              disabled={simulating}
              className={`btn text-xs ${selectedScenario === sc ? 'btn-primary' : 'btn-secondary'}`}
            >
              {simulating && selectedScenario === sc ? (
                <Loader2 size={12} className="animate-spin inline mr-1" />
              ) : null}
              Simulate {sc.replace('_', ' ')}
            </button>
          ))}
        </div>

        {simError && (
          <div className="card mb-3 p-3" style={{ background: '#FEE2E2', borderColor: 'rgba(239, 68, 68, 0.25)' }}>
            <div className="text-xs text-red flex items-center gap-2" style={{ color: '#991B1B' }}>
              <AlertTriangle size={14} />
              Simulation warning: {simError}
            </div>
          </div>
        )}

        {simResult && (
          <div className="flex-col gap-3">
            <div className="grid-3 p-3 rounded" style={{ background: 'var(--bg-hover)', border: '1px solid var(--border)' }}>
              <div>
                <div className="text-xs text-muted">Baseline Spend</div>
                <div className="text-lg font-bold">${simResult.before?.cost?.toFixed(0) ?? '0'}/mo</div>
                <div className="text-xs text-secondary">
                  CPU: {simResult.before?.cpu ?? 0}% · Memory: {simResult.before?.memory ?? 0}%
                </div>
              </div>
              <div>
                <div className="text-xs text-muted">Projected Spend After</div>
                <div className="text-lg font-bold text-emerald">${simResult.after?.cost?.toFixed(0) ?? '0'}/mo</div>
                <div className="text-xs text-secondary">
                  CPU: {simResult.after?.cpu ?? 0}% · Headroom OK
                </div>
              </div>
              <div>
                <div className="text-xs text-muted">Projected Monthly Savings</div>
                <div className="text-lg font-black text-emerald">
                  +${simResult.estimated_saving?.toFixed(0) ?? '0'}/mo
                </div>
                <div className="text-xs text-emerald" style={{ fontWeight: 600 }}>Risk Assessment: {simResult.risk}</div>
              </div>
            </div>

            {/* Score Projection Details */}
            {simResult.baseline_score !== undefined && simResult.projected_score !== undefined && (
              <div
                className="p-3 rounded flex items-center justify-between flex-wrap gap-3"
                style={{ background: '#F0FDF4', border: '1px solid rgba(22, 163, 74, 0.2)' }}
              >
                <div>
                  <div className="text-xs font-semibold" style={{ color: 'var(--emerald-700)' }}>
                    Optimization Score Impact
                  </div>
                  <div className="text-xs text-secondary mt-0.5">
                    {simResult.scoring_explanation || 'Projected based on post-scenario metrics.'}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <div className="text-xs text-muted">Baseline</div>
                    <div className="text-sm font-bold">{simResult.baseline_score}/100</div>
                  </div>
                  <ChevronRight size={14} color="var(--text-muted)" />
                  <div className="text-right">
                    <div className="text-xs text-muted">Projected</div>
                    <div className="text-sm font-bold text-emerald-400">{simResult.projected_score}/100</div>
                  </div>
                  <span
                    className={`badge ${simResult.score_delta > 0 ? 'badge-emerald' : simResult.score_delta < 0 ? 'badge-red' : 'badge-muted'}`}
                    style={{ fontSize: 11 }}
                  >
                    {simResult.score_delta > 0 ? `+${simResult.score_delta}` : simResult.score_delta} pts
                  </span>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Active Cost Recommendations */}
      <div className="card">
        <h3 style={{ fontSize: 15, fontWeight: 700 }} className="mb-3">
          Active Cost Optimization Actions ({costRecs.length})
        </h3>
        {recLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map(i => (
              <div key={i} className="skeleton" style={{ height: 60, borderRadius: 6 }} />
            ))}
          </div>
        ) : recError ? (
          <div className="p-4 text-center text-sm text-red-400">
            Failed to load cost recommendations.
          </div>
        ) : costRecs.length === 0 ? (
          <div className="p-4 text-center text-sm text-secondary">
            No active cost recommendations found for this provider and region.
          </div>
        ) : (
          <div className="space-y-3">
            {costRecs.map(rec => (
              <div
                key={rec.id}
                className="p-3 rounded flex items-center justify-between flex-wrap gap-3"
                style={{ background: 'var(--bg-hover)', border: '1px solid var(--border)' }}
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
        )}
      </div>
    </div>
  )
}

