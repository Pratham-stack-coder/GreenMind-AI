import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, BarChart, Bar
} from 'recharts'
import {
  Cpu, MemoryStick, HardDrive, Network, DollarSign, Leaf,
  Activity, TrendingUp, AlertTriangle, ShieldCheck,
  Sparkles, RotateCcw
} from 'lucide-react'
import { useAppStore } from '../store'
import {
  fetchLiveMetrics, fetchScores, fetchTelemetryHistory,
  fetchRecommendations, applyRecommendation, simulateRecommendation,
  resetSimulation, fetchForecast, fetchSettingsStatus
} from '../api/client'
import type { CloudMetrics, OptimizationScores } from '../types'
import MetricCard from '../components/MetricCard/MetricCard'

// ── Radar Chart for 5 Domains ────────────────────────────────────────────────
function ScoreRadar({ scores }: { scores: OptimizationScores }) {
  const data = [
    { subject: 'Cost', value: scores.cost, fullMark: 100 },
    { subject: 'Performance', value: scores.performance, fullMark: 100 },
    { subject: 'Sustainability', value: scores.sustainability, fullMark: 100 },
    { subject: 'Security', value: scores.security, fullMark: 100 },
    { subject: 'Reliability', value: scores.reliability, fullMark: 100 },
  ]

  return (
    <ResponsiveContainer width="100%" height={230}>
      <RadarChart data={data} margin={{ top: 12, right: 38, bottom: 12, left: 38 }}>
        <PolarGrid stroke="var(--chart-grid)" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 10, fill: 'var(--text-secondary)' }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
        <Radar
          name="Optimization Score"
          dataKey="value"
          stroke="var(--emerald-600)"
          fill="var(--emerald-600)"
          fillOpacity={0.15}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}

export default function DashboardPage() {
  const { provider, region, addNotification } = useAppStore()
  const queryClient = useQueryClient()
  const [applyingId, setApplyingId] = useState<string | null>(null)
  const [simulatingId, setSimulatingId] = useState<string | null>(null)
  const [isResetting, setIsResetting] = useState(false)

  const { data: metrics } = useQuery({
    queryKey: ['liveMetrics', provider, region],
    queryFn: () => fetchLiveMetrics(provider, region),
    refetchInterval: 15_000,
  })

  const { data: scores } = useQuery({
    queryKey: ['scores', provider, region],
    queryFn: () => fetchScores(provider, region),
    refetchInterval: 60_000,
  })

  const { data: history } = useQuery({
    queryKey: ['history', provider, region],
    queryFn: () => fetchTelemetryHistory(48, provider, region),
    refetchInterval: 60_000,
  })

  const { data: recs } = useQuery({
    queryKey: ['recommendations', provider, region],
    queryFn: () => fetchRecommendations({ provider, region }),
    refetchInterval: 120_000,
  })

  const { data: forecast } = useQuery({
    queryKey: ['forecast', metrics?.cpu, region],
    queryFn: () =>
      fetchForecast({
        cpu: metrics!.cpu,
        memory: metrics!.memory as number,
        network: metrics!.network as number,
        hour: new Date().getUTCHours(),
        day_of_week: new Date().getUTCDay(),
        region,
      }),
    enabled: Boolean(metrics && metrics.source !== 'ERROR' && metrics.cpu != null && metrics.memory != null && metrics.network != null),
  })

  const { data: settingsStatus } = useQuery({
    queryKey: ['settings-status'],
    queryFn: fetchSettingsStatus,
    refetchInterval: 30_000,
  })

  const handlePreviewRec = async (id: string, title: string) => {
    try {
      setApplyingId(id)
      const res = await applyRecommendation(id, { dry_run: true })
      const delta = res.score_delta != null ? res.score_delta : 0
      const deltaStr = delta > 0 ? `+${delta}` : `${delta}`
      addNotification({
        title: 'Dry-run preview ready',
        body: `${title}: baseline ${res.baseline_score ?? scores?.overall ?? 'N/A'}/100 → projected ${res.projected_score ?? res.new_score ?? 'N/A'}/100 (${deltaStr} pts). No cloud resources changed.`,
        priority: 'high',
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['scores', provider, region] }),
        queryClient.invalidateQueries({ queryKey: ['recommendations', provider, region] }),
      ])
    } catch (err) {
      addNotification({
        title: 'Preview failed',
        body: err instanceof Error ? err.message : 'The recommendation preview could not be completed.',
        priority: 'high',
      })
    } finally {
      setApplyingId(null)
    }
  }

  const handleSimulateRec = async (id: string, title: string) => {
    try {
      setSimulatingId(id)
      const res = await simulateRecommendation(id)
      const delta = res.score_delta != null ? res.score_delta : 0
      const deltaStr = delta > 0 ? `+${delta}` : `${delta}`
      addNotification({
        title: 'Simulated optimization active',
        body: `${title} applied to Digital Twin model. Projected score: ${res.projected_score ?? res.new_score}/100 (${deltaStr} pts). No live cloud resources were modified.`,
        priority: 'high',
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['scores', provider, region] }),
        queryClient.invalidateQueries({ queryKey: ['recommendations', provider, region] }),
      ])
    } catch (err) {
      addNotification({
        title: 'Simulation failed',
        body: err instanceof Error ? err.message : 'The simulation could not be applied.',
        priority: 'high',
      })
    } finally {
      setSimulatingId(null)
    }
  }

  const handleResetSimulation = async () => {
    try {
      setIsResetting(true)
      await resetSimulation()
      addNotification({
        title: 'Simulation reset',
        body: 'All simulated optimizations have been cleared and returned to baseline telemetry.',
        priority: 'low',
      })
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['scores', provider, region] }),
        queryClient.invalidateQueries({ queryKey: ['recommendations', provider, region] }),
      ])
    } catch (err) {
      addNotification({
        title: 'Reset failed',
        body: err instanceof Error ? err.message : 'Failed to reset simulation.',
        priority: 'high',
      })
    } finally {
      setIsResetting(false)
    }
  }

  // Determine Data Source Badge truthfully based on actual source
  const metricsAvailable = Boolean(metrics && metrics.source !== 'ERROR')
  const isLive = Boolean(metricsAvailable && metrics?.source?.startsWith('LIVE'))
  const sourceLabel = metrics?.source === 'ERROR'
    ? 'PROVIDER ERROR'
    : isLive
      ? `LIVE ${provider.toUpperCase()}`
      : metrics?.source === 'DEMO'
        ? 'DEMO MODE (SYNTHETIC)'
        : 'DATA UNAVAILABLE'

  // Prepare chart histories
  const rawEntries = Array.isArray(history?.entries) ? history.entries.slice(0, 24).reverse() : []
  const chartData = rawEntries.map((e: CloudMetrics) => ({
    time: e.timestamp ? new Date(e.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Unknown time',
    CPU: typeof e?.cpu === 'number' ? e.cpu : null,
    Memory: typeof e?.memory === 'number' ? e.memory : null,
    Network: typeof e?.network === 'number' ? e.network : null,
    Cost: typeof e?.cost_usd_per_hour === 'number' ? e.cost_usd_per_hour : null,
    Carbon: typeof e?.carbon_gco2_per_hour === 'number' ? e.carbon_gco2_per_hour : null,
  }))

  // Chart data for Predicted CPU (Historical + Future Projection)
  const currentCpu = typeof metrics?.cpu === 'number' ? metrics.cpu : null
  const predictedChartData = forecast?.cpu && currentCpu != null
    ? [
        ...chartData.slice(-6).map(c => ({ time: c.time, Actual: c.CPU, Projected: null as number | null })),
        { time: 'Now', Actual: currentCpu, Projected: currentCpu },
        { time: '+60m', Actual: null, Projected: forecast.cpu.predicted },
      ]
    : []

  const recsList = Array.isArray(recs?.recommendations) ? recs.recommendations : []
  const criticalCount = recsList.filter(r => r.priority === 'critical').length
  const topRec = recsList[0]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="dashboard-header mb-4">
        <div className="dashboard-header-title">
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Cloud Overview Dashboard</h1>
          <p className="text-secondary text-sm mt-1">
            Cloud telemetry and efficiency recommendations · {provider.toUpperCase()} · {region}
          </p>
        </div>

        <div className="dashboard-header-badges">
          {/* Multi-cloud provider mini pills */}
          <div className="provider-pills-row">
            {(['aws', 'azure', 'gcp'] as const).map(p => {
              const pStatus = settingsStatus?.providers?.[p]
              const isConnected = pStatus?.mode === 'LIVE' && pStatus.status === 'connected'
              const providerLabel = !pStatus
                ? 'UNKNOWN'
                : isConnected
                  ? 'LIVE'
                  : pStatus.mode === 'DEMO'
                    ? 'DEMO'
                    : 'ERROR'
              return (
                <span
                  key={p}
                  className={`badge ${providerLabel === 'LIVE' ? 'badge-emerald' : providerLabel === 'ERROR' ? 'badge-red' : 'badge-muted'}`}
                  style={{ fontSize: 10, padding: '2px 7px', flexShrink: 0 }}
                  title={pStatus?.message || p.toUpperCase()}
                >
                  <span className={`status-dot ${isConnected ? 'online' : 'muted'}`} style={{ width: 5, height: 5 }} />
                  {p.toUpperCase()}: {providerLabel}
                </span>
              )
            })}
          </div>

          {/* Current Provider Telemetry Source badge */}
          <span
            className={`badge ${isLive ? 'badge-emerald' : 'badge-muted'}`}
            style={{ fontWeight: 700, letterSpacing: '0.05em', flexShrink: 0 }}
          >
            <span
              className={`status-dot ${isLive ? 'online' : 'muted'}`}
              style={{ width: 6, height: 6 }}
            />
            {sourceLabel}
          </span>

          {criticalCount > 0 && (
            <span className="badge badge-red" style={{ flexShrink: 0 }}>
              <AlertTriangle size={10} />
              {criticalCount} CRITICAL
            </span>
          )}
        </div>
      </div>

      {/* Domain Score & Radar Banner */}
      {scores && typeof scores.overall === 'number' && (
        <div className={`card ${scores.is_simulated ? 'card-accent-amber' : 'card-accent-emerald'} mb-4`}>
          <div className="score-banner-content">
            <div className="score-banner-text">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs text-muted font-bold uppercase tracking-wider">
                  Overall Optimization Score
                </span>
                {scores.is_simulated && (
                  <span className="badge badge-amber text-xs font-mono" style={{ fontSize: 10, padding: '2px 6px' }}>
                    SIMULATED TWIN
                  </span>
                )}
              </div>
              <div
                style={{
                  fontSize: 48,
                  fontWeight: 900,
                  color:
                    scores.overall >= 70
                      ? 'var(--emerald-600)'
                      : scores.overall >= 50
                      ? 'var(--amber-600)'
                      : 'var(--red-600)',
                  lineHeight: 1,
                  letterSpacing: '-0.04em',
                }}
              >
                {scores.overall}
                <span style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-muted)' }}>/100</span>
              </div>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <div
                  className={`badge ${
                    scores.trend === 'improving'
                      ? 'badge-emerald'
                      : scores.trend === 'declining'
                      ? 'badge-red'
                      : 'badge-muted'
                  }`}
                >
                  {scores.trend === 'improving'
                    ? '↑ Improving'
                    : scores.trend === 'declining'
                    ? '↓ Declining'
                    : '→ Stable'}
                </div>
                {scores.is_simulated && scores.baseline_overall != null && (
                  <span className="badge badge-muted text-xs">
                    Baseline: {scores.baseline_overall}/100 ({scores.score_delta != null && scores.score_delta > 0 ? `+${scores.score_delta}` : scores.score_delta ?? 0} pts)
                  </span>
                )}
                {scores.is_simulated && (
                  <button
                    onClick={handleResetSimulation}
                    disabled={isResetting}
                    className="btn btn-secondary text-xs"
                    style={{ padding: '3px 8px' }}
                    title="Reset all simulated optimizations to baseline telemetry"
                  >
                    <RotateCcw size={11} className={isResetting ? 'animate-spin' : ''} />
                    {isResetting ? 'Resetting...' : 'Reset Simulation'}
                  </button>
                )}
              </div>
              <div className="text-xs text-secondary mt-2">
                {scores.is_simulated
                  ? 'Projected score calculated from simulated after-state metrics under identical scoring methodology.'
                  : 'Evaluated continuously across Cost, Performance, Carbon, Security, and Reliability.'}
              </div>
            </div>

            <div className="score-banner-radar">
              <ScoreRadar scores={scores} />
            </div>
          </div>
        </div>
      )}

      {/* 8 Required Metric Cards: CPU, Memory, Storage, Network, Cost, Carbon, Cloud Health, Optimization Score */}
      <div className="grid-4 mb-4">
        <MetricCard
          label="CPU Load"
          value={metricsAvailable ? metrics!.cpu : 'N/A'}
          unit={metricsAvailable ? '%' : ''}
          icon={Cpu}
          color="emerald"
          source={metrics?.source || 'UNAVAILABLE'}
        />
        <MetricCard
          label="Memory Used"
          value={metricsAvailable && metrics?.memory != null ? metrics.memory : 'N/A'}
          unit={metricsAvailable && metrics?.memory != null ? '%' : ''}
          icon={MemoryStick}
          color={metricsAvailable && metrics?.memory != null ? 'blue' : 'amber'}
          subtext={metricsAvailable && metrics?.memory == null ? 'Requires CloudWatch/OS Agent' : undefined}
          source={!metricsAvailable ? (metrics?.source === 'ERROR' ? 'ERROR' : 'UNAVAILABLE') : metrics?.memory != null ? (metrics.memory_source || metrics.source) : 'UNAVAILABLE'}
          sourceNote={metrics?.memory_note || undefined}
        />
        <MetricCard
          label="Storage In-Use"
          value={metricsAvailable && metrics?.storage != null ? metrics.storage : 'N/A'}
          unit={metricsAvailable && metrics?.storage != null ? '%' : ''}
          icon={HardDrive}
          color="indigo"
          source={metricsAvailable && metrics?.storage != null ? metrics.source : metrics?.source === 'ERROR' ? 'ERROR' : 'UNAVAILABLE'}
        />
        <MetricCard
          label="Network I/O"
          value={metricsAvailable && metrics?.network != null ? metrics.network : 'N/A'}
          unit={metricsAvailable && metrics?.network != null ? 'Mbps' : ''}
          icon={Network}
          color="purple"
          source={metricsAvailable && metrics?.network != null ? (metrics.network_source || metrics.source) : metrics?.source === 'ERROR' ? 'ERROR' : 'UNAVAILABLE'}
        />
      </div>

      <div className="grid-4 mb-4">
        <MetricCard
          label="Hourly Cost"
          value={metricsAvailable && metrics?.cost_usd_per_hour != null ? metrics.cost_usd_per_hour : 'N/A'}
          unit={metricsAvailable && metrics?.cost_usd_per_hour != null ? '$/hr' : ''}
          icon={DollarSign}
          color="amber"
          subtext={metricsAvailable && metrics?.cost_usd_per_hour != null ? `Estimated $${(metrics.cost_usd_per_hour * 24 * 30).toFixed(0)}/month` : undefined}
          source={!metricsAvailable ? (metrics?.source === 'ERROR' ? 'ERROR' : 'UNAVAILABLE') : metrics?.cost_usd_per_hour != null ? (metrics.cost_source || (isLive ? 'ESTIMATED' : 'DEMO')) : 'UNAVAILABLE'}
        />
        <MetricCard
          label="Emissions Rate"
          value={metricsAvailable && metrics?.carbon_gco2_per_hour != null ? metrics.carbon_gco2_per_hour : 'N/A'}
          unit={metricsAvailable && metrics?.carbon_gco2_per_hour != null ? 'gCO₂/hr' : ''}
          icon={Leaf}
          color="emerald"
          subtext={metricsAvailable && metrics?.carbon_gco2_per_hour != null ? 'GHG Scope 2/3 power model' : undefined}
          source={!metricsAvailable ? (metrics?.source === 'ERROR' ? 'ERROR' : 'UNAVAILABLE') : 'ESTIMATED'}
        />
        <MetricCard
          label="Optimization Status"
          value={scores ? (scores.overall >= 70 ? 'HEALTHY' : 'REVIEW') : 'UNAVAILABLE'}
          unit=""
          icon={Activity}
          color="emerald"
          subtext={scores ? 'Based on composite optimization score' : undefined}
          source={scores?.source || 'UNAVAILABLE'}
        />
        <MetricCard
          label="Opt. Score"
          value={scores?.overall ?? 'N/A'}
          unit="/100"
          icon={ShieldCheck}
          color="blue"
          subtext="Composite efficiency"
          source={scores?.source || 'UNAVAILABLE'}
        />
      </div>

      {/* 6 Required Charts Grid */}
      {/* Row 1: CPU History & Memory History */}
      <div className="grid-2 mb-4">
        {/* 1. CPU History */}
        <div className="card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Cpu size={16} color="var(--emerald-600)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>CPU History (Last 24 Readings)</h3>
            </div>
            <span className="text-xs text-muted">Current: {metricsAvailable && metrics?.cpu != null ? `${metrics.cpu}%` : 'Unavailable'}</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="cpuArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Area type="monotone" dataKey="CPU" stroke="#16a34a" fill="url(#cpuArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Memory History */}
        <div className="card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <MemoryStick size={16} color="var(--emerald-600)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Memory History</h3>
            </div>
            <span className="text-xs text-muted">Current: {metricsAvailable && metrics?.memory != null ? `${metrics.memory}%` : 'Unavailable'}</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="memArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#15803d" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#15803d" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Area type="monotone" dataKey="Memory" stroke="#15803d" fill="url(#memArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 2: Cost Trend & Carbon Trend */}
      <div className="grid-2 mb-4">
        {/* 3. Cost Trend */}
        <div className="card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <DollarSign size={16} color="var(--amber-600)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Cost Trend ($/hr)</h3>
            </div>
            <span className="text-xs text-muted">{metricsAvailable && metrics?.cost_usd_per_hour != null ? `$${metrics.cost_usd_per_hour}/hr` : 'Unavailable'}</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="costArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#d97706" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#d97706" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Area type="monotone" dataKey="Cost" stroke="#d97706" fill="url(#costArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Carbon Trend */}
        <div className="card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Leaf size={16} color="var(--emerald-600)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Carbon Emissions Trend (gCO₂/hr)</h3>
            </div>
            <span className="text-xs text-muted">{metricsAvailable && metrics?.carbon_gco2_per_hour != null ? `${metrics.carbon_gco2_per_hour} gCO₂/hr` : 'Unavailable'}</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="carbArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#16a34a" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#16a34a" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Area type="monotone" dataKey="Carbon" stroke="#16a34a" fill="url(#carbArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 3: Network Usage & Predicted CPU */}
      <div className="grid-2 mb-4">
        {/* 5. Network Usage */}
        <div className="card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Network size={16} color="var(--emerald-600)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Network Usage (Mbps)</h3>
            </div>
            <span className="text-xs text-muted">{metricsAvailable && metrics?.network != null ? `${metrics.network} Mbps` : 'Unavailable'}</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Bar dataKey="Network" fill="#16a34a" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 6. Predicted CPU */}
        <div className="card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} color="var(--emerald-600)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Predicted CPU Load (60-Min ML Forecast)</h3>
            </div>
            <div className="flex items-center gap-1">
              <span className={`badge ${!forecast ? 'badge-muted' : forecast.risk === 'HIGH' ? 'badge-red' : forecast.risk === 'MEDIUM' ? 'badge-amber' : 'badge-emerald'}`}>
                {forecast?.risk ? `Risk: ${forecast.risk}` : 'Forecast unavailable'}
              </span>
            </div>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={predictedChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: '#FFFFFF', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
                <Line type="monotone" dataKey="Actual" stroke="#6b7280" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="Projected" stroke="#16a34a" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-between text-xs text-muted mt-2 flex-wrap gap-2">
            <span>Current: <strong>{metricsAvailable && metrics?.cpu != null ? `${metrics.cpu}%` : 'Unavailable'}</strong></span>
            <span>Forecast +60m: <strong className="text-emerald font-bold">{forecast?.cpu?.predicted != null ? `${forecast.cpu.predicted}%` : 'Unavailable'}</strong></span>
            <span>Confidence: <strong>{forecast?.cpu?.confidence != null ? `${(forecast.cpu.confidence * 100).toFixed(0)}%` : 'Unavailable'}</strong></span>
          </div>
        </div>
      </div>

      {/* Top AI Recommendation Spotlight */}
      {topRec && (
        <div className="card mb-4" style={{ background: '#F0FDF4', border: '1px solid rgba(22, 163, 74, 0.2)' }}>
          <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Sparkles size={16} color="var(--emerald-600)" />
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>Priority AI Recommendation</h3>
              <span className={`badge ${topRec.priority === 'critical' ? 'badge-red' : 'badge-amber'}`}>
                {topRec.priority.toUpperCase()}
              </span>
              {topRec.status === 'simulated' && (
                <span className="badge badge-amber text-xs font-mono">SIMULATED</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => handlePreviewRec(topRec.id, topRec.title)}
                disabled={applyingId === topRec.id || topRec.status === 'applied'}
                className="btn btn-secondary text-xs"
              >
                {applyingId === topRec.id ? 'Calculating preview...' : 'Preview Impact (Dry-Run)'}
              </button>
              <button
                onClick={() => handleSimulateRec(topRec.id, topRec.title)}
                disabled={simulatingId === topRec.id || topRec.status === 'simulated' || topRec.status === 'applied'}
                className="btn btn-primary text-xs"
              >
                {topRec.status === 'simulated' ? 'Simulated in Twin' : simulatingId === topRec.id ? 'Simulating...' : 'Simulate in Twin'}
              </button>
            </div>
          </div>
          <p className="text-sm text-secondary mb-2">{topRec.description}</p>
          <div className="flex items-center gap-4 text-xs font-semibold flex-wrap">
            {topRec.estimated_monthly_savings_usd > 0 && (
              <span className="text-emerald-400">Save ${topRec.estimated_monthly_savings_usd.toFixed(0)}/month</span>
            )}
            {topRec.estimated_carbon_reduction_pct > 0 && (
              <span className="text-emerald-400">Reduce {topRec.estimated_carbon_reduction_pct.toFixed(0)}% CO₂</span>
            )}
            <span className="text-muted font-normal">Action: <code>{topRec.action}</code></span>
          </div>
        </div>
      )}
    </div>
  )
}
