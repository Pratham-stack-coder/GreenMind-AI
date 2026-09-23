import React, { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  LineChart, Line, BarChart, Bar
} from 'recharts'
import {
  Cpu, MemoryStick, HardDrive, Network, DollarSign, Leaf,
  Activity, TrendingUp, AlertTriangle, CheckCircle2, ShieldCheck,
  Zap, Sparkles, RefreshCw, Server
} from 'lucide-react'
import { useAppStore } from '../store'
import {
  fetchLiveMetrics, fetchScores, fetchTelemetryHistory,
  fetchRecommendations, applyRecommendation, fetchForecast,
  fetchSettingsStatus
} from '../api/client'
import type { CloudMetrics, OptimizationScores, PredictResponse } from '../types'
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
    <ResponsiveContainer width="100%" height={210}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
        <Radar
          name="Optimization Score"
          dataKey="value"
          stroke="var(--emerald-500)"
          fill="var(--emerald-500)"
          fillOpacity={0.2}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}

export default function DashboardPage() {
  const queryClient = useQueryClient()
  const { provider, region, addNotification } = useAppStore()
  const [applyingId, setApplyingId] = useState<string | null>(null)

  const { data: metrics, isLoading: metricsLoading } = useQuery({
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
    queryKey: ['history'],
    queryFn: () => fetchTelemetryHistory(48),
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
        cpu: metrics?.cpu ?? 50,
        memory: metrics?.memory ?? 55,
        network: metrics?.network ?? 450,
        hour: new Date().getUTCHours(),
        day_of_week: new Date().getUTCDay(),
        region,
      }),
    enabled: !!metrics,
  })

  const { data: settingsStatus } = useQuery({
    queryKey: ['settings-status'],
    queryFn: fetchSettingsStatus,
    refetchInterval: 30_000,
  })

  const handleApplyRec = async (id: string, title: string) => {
    try {
      setApplyingId(id)
      const res = await applyRecommendation(id, { dry_run: false })
      addNotification({
        title: 'Optimization Applied',
        body: `${title} applied successfully. Score updated to ${res.new_score || 85}/100.`,
        priority: 'high',
      })
      queryClient.invalidateQueries({ queryKey: ['recommendations'] })
      queryClient.invalidateQueries({ queryKey: ['scores'] })
      queryClient.invalidateQueries({ queryKey: ['liveMetrics'] })
    } catch (err) {
      console.error('Failed to apply recommendation', err)
    } finally {
      setApplyingId(null)
    }
  }

  // Determine Data Source Badge truthfully based on actual source
  const isLive = Boolean(metrics?.source && typeof metrics.source === 'string' && metrics.source.startsWith('LIVE'))
  const sourceLabel = isLive ? `LIVE ${provider.toUpperCase()}` : 'DEMO MODE (SYNTHETIC)'

  // Prepare chart histories
  const rawEntries = Array.isArray(history?.entries) ? history.entries.slice(0, 24).reverse() : []
  const chartData = rawEntries.map((e: CloudMetrics, i: number) => ({
    time: `${i * 15}m`,
    CPU: typeof e?.cpu === 'number' ? e.cpu : 45,
    Memory: typeof e?.memory === 'number' ? e.memory : 55,
    Network: typeof e?.network === 'number' ? e.network : 400,
    Cost: typeof e?.cost_usd_per_hour === 'number' ? e.cost_usd_per_hour : 0.19,
    Carbon: typeof e?.carbon_gco2_per_hour === 'number' ? e.carbon_gco2_per_hour : 75,
  }))

  // Chart data for Predicted CPU (Historical + Future Projection)
  const currentCpu = typeof metrics?.cpu === 'number' ? metrics.cpu : 50
  const predictedChartData = [
    ...chartData.slice(-6).map((c, i) => ({ time: `T-${(6 - i) * 15}m`, Actual: c.CPU, Projected: null as number | null })),
    { time: 'Now', Actual: currentCpu, Projected: currentCpu },
    { time: '+15m', Actual: null, Projected: Math.round(((currentCpu * 0.6) + ((forecast?.cpu?.predicted ?? 50) * 0.4)) * 10) / 10 },
    { time: '+30m', Actual: null, Projected: Math.round(((currentCpu * 0.3) + ((forecast?.cpu?.predicted ?? 50) * 0.7)) * 10) / 10 },
    { time: '+60m', Actual: null, Projected: forecast?.cpu?.predicted ?? 50 },
  ]

  const recsList = Array.isArray(recs?.recommendations) ? recs.recommendations : []
  const criticalCount = recsList.filter(r => r.priority === 'critical').length
  const topRec = recsList[0]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Cloud Overview Dashboard</h1>
          <p className="text-secondary text-sm mt-1">
            Telemetry ingestion &amp; autonomous green cloud management · {provider.toUpperCase()} · {region}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Multi-cloud provider mini pills */}
          <div className="flex items-center gap-1.5 mr-1">
            {(['aws', 'azure', 'gcp'] as const).map(p => {
              const pStatus = settingsStatus?.providers?.[p]
              const isConnected = pStatus?.status === 'connected'
              return (
                <span
                  key={p}
                  className={`badge ${isConnected ? 'badge-emerald' : 'badge-muted'}`}
                  style={{ fontSize: 10, padding: '2px 7px' }}
                  title={pStatus?.message || p.toUpperCase()}
                >
                  <span className={`status-dot ${isConnected ? 'online' : 'muted'}`} style={{ width: 5, height: 5 }} />
                  {p.toUpperCase()}: {isConnected ? 'LIVE' : 'DEMO'}
                </span>
              )
            })}
          </div>

          {/* Current Provider Telemetry Source badge */}
          <span
            className={`badge ${isLive ? 'badge-emerald' : 'badge-blue'}`}
            style={{ fontWeight: 700, letterSpacing: '0.05em' }}
          >
            <span
              className={`status-dot ${isLive ? 'online' : 'muted'}`}
              style={{ width: 6, height: 6 }}
            />
            {sourceLabel}
          </span>

          {criticalCount > 0 && (
            <span className="badge badge-red">
              <AlertTriangle size={10} />
              {criticalCount} CRITICAL
            </span>
          )}
        </div>
      </div>

      {/* Domain Score & Radar Banner */}
      {scores && typeof scores.overall === 'number' && (
        <div className="card card-accent-emerald mb-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <div className="text-xs text-muted mb-1 font-bold uppercase tracking-wider">
                Overall Optimization Score
              </div>
              <div
                style={{
                  fontSize: 48,
                  fontWeight: 900,
                  color:
                    scores.overall >= 70
                      ? 'var(--emerald-400)'
                      : scores.overall >= 50
                      ? 'var(--amber-400)'
                      : 'var(--red-400)',
                  lineHeight: 1,
                  letterSpacing: '-0.04em',
                }}
              >
                {scores.overall}
                <span style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-muted)' }}>/100</span>
              </div>
              <div
                className={`badge mt-2 ${
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
              <div className="text-xs text-secondary mt-2">
                Evaluated continuously across Cost, Performance, Carbon, Security, and Reliability
              </div>
            </div>

            <div style={{ width: 340, maxWidth: '100%' }}>
              <ScoreRadar scores={scores} />
            </div>
          </div>
        </div>
      )}

      {/* 8 Required Metric Cards: CPU, Memory, Storage, Network, Cost, Carbon, Cloud Health, Optimization Score */}
      <div className="grid-4 mb-4">
        <MetricCard
          label="CPU Load"
          value={metrics?.cpu ?? 45.0}
          unit="%"
          icon={Cpu}
          color="emerald"
          delta={2.4}
        />
        <MetricCard
          label="Memory Used"
          value={metrics?.memory ?? 55.0}
          unit="%"
          icon={MemoryStick}
          color="blue"
          delta={-1.2}
        />
        <MetricCard
          label="Storage In-Use"
          value={metrics?.storage ?? 48.0}
          unit="%"
          icon={HardDrive}
          color="indigo"
          delta={0.5}
        />
        <MetricCard
          label="Network I/O"
          value={metrics?.network ?? 420.0}
          unit="Mbps"
          icon={Network}
          color="purple"
          delta={4.8}
        />
      </div>

      <div className="grid-4 mb-4">
        <MetricCard
          label="Hourly Cost"
          value={metrics?.cost_usd_per_hour ?? 0.192}
          unit="$/hr"
          icon={DollarSign}
          color="amber"
          delta={-3.1}
          subtext={`Est. $${((metrics?.cost_usd_per_hour ?? 0.192) * 24 * 30).toFixed(0)}/month`}
        />
        <MetricCard
          label="Emissions Rate"
          value={metrics?.carbon_gco2_per_hour ?? 78.4}
          unit="gCO₂/hr"
          icon={Leaf}
          color="emerald"
          delta={-6.4}
          subtext="Scope 2 grid emissions"
        />
        <MetricCard
          label="Cloud Health"
          value={scores ? (scores.overall >= 70 ? 'HEALTHY' : 'WARN') : 'HEALTHY'}
          unit=""
          icon={Activity}
          color="emerald"
          subtext="0 active alarm disruptions"
        />
        <MetricCard
          label="Opt. Score"
          value={scores?.overall ?? 82}
          unit="/100"
          icon={ShieldCheck}
          color="blue"
          subtext="Composite efficiency"
        />
      </div>

      {/* 6 Required Charts Grid */}
      {/* Row 1: CPU History & Memory History */}
      <div className="grid-2 mb-4">
        {/* 1. CPU History */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Cpu size={16} color="var(--emerald-400)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>CPU History (Last 24 Readings)</h3>
            </div>
            <span className="text-xs text-muted">Current: {metrics?.cpu ?? 45}%</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.length ? chartData : [{ time: '0m', CPU: 45 }]}>
                <defs>
                  <linearGradient id="cpuArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--card-bg)', border: '1px solid var(--border)' }} />
                <Area type="monotone" dataKey="CPU" stroke="#10b981" fill="url(#cpuArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 2. Memory History */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <MemoryStick size={16} color="var(--blue-400)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Memory History</h3>
            </div>
            <span className="text-xs text-muted">Current: {metrics?.memory ?? 55}%</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.length ? chartData : [{ time: '0m', Memory: 55 }]}>
                <defs>
                  <linearGradient id="memArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--card-bg)', border: '1px solid var(--border)' }} />
                <Area type="monotone" dataKey="Memory" stroke="#3b82f6" fill="url(#memArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 2: Cost Trend & Carbon Trend */}
      <div className="grid-2 mb-4">
        {/* 3. Cost Trend */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <DollarSign size={16} color="var(--amber-400)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Cost Trend ($/hr)</h3>
            </div>
            <span className="text-xs text-muted">${metrics?.cost_usd_per_hour ?? 0.192}/hr</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.length ? chartData : [{ time: '0m', Cost: 0.19 }]}>
                <defs>
                  <linearGradient id="costArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--card-bg)', border: '1px solid var(--border)' }} />
                <Area type="monotone" dataKey="Cost" stroke="#f59e0b" fill="url(#costArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 4. Carbon Trend */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Leaf size={16} color="var(--emerald-400)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Carbon Emissions Trend (gCO₂/hr)</h3>
            </div>
            <span className="text-xs text-muted">{metrics?.carbon_gco2_per_hour ?? 78.4} gCO₂/hr</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.length ? chartData : [{ time: '0m', Carbon: 75 }]}>
                <defs>
                  <linearGradient id="carbArea" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.35} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--card-bg)', border: '1px solid var(--border)' }} />
                <Area type="monotone" dataKey="Carbon" stroke="#10b981" fill="url(#carbArea)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Row 3: Network Usage & Predicted CPU */}
      <div className="grid-2 mb-4">
        {/* 5. Network Usage */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Network size={16} color="var(--purple-400)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Network Usage (Mbps)</h3>
            </div>
            <span className="text-xs text-muted">{metrics?.network ?? 420} Mbps</span>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData.length ? chartData : [{ time: '0m', Network: 400 }]}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--card-bg)', border: '1px solid var(--border)' }} />
                <Bar dataKey="Network" fill="#a855f7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 6. Predicted CPU */}
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} color="var(--emerald-400)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Predicted CPU Load (60-Min ML Forecast)</h3>
            </div>
            <div className="flex items-center gap-1">
              <span className={`badge ${forecast?.risk === 'HIGH' ? 'badge-red' : forecast?.risk === 'MEDIUM' ? 'badge-amber' : 'badge-emerald'}`}>
                Risk: {forecast?.risk || 'LOW'}
              </span>
            </div>
          </div>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={predictedChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: 'var(--text-muted)' }} />
                <Tooltip contentStyle={{ background: 'var(--card-bg)', border: '1px solid var(--border)' }} />
                <Line type="monotone" dataKey="Actual" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="Projected" stroke="#10b981" strokeWidth={2} strokeDasharray="4 4" dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center justify-between text-xs text-muted mt-2">
            <span>Current: <strong>{metrics?.cpu ?? 45}%</strong></span>
            <span>Forecast +60m: <strong className="text-emerald-400">{forecast?.cpu?.predicted ?? 48}%</strong></span>
            <span>Confidence: <strong>{((forecast?.cpu?.confidence ?? 0.88) * 100).toFixed(0)}%</strong></span>
          </div>
        </div>
      </div>

      {/* Top AI Recommendation Spotlight */}
      {topRec && (
        <div className="card mb-4" style={{ background: 'rgba(16, 185, 129, 0.03)', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Sparkles size={16} color="var(--emerald-400)" />
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>Priority AI Recommendation</h3>
              <span className={`badge ${topRec.priority === 'critical' ? 'badge-red' : 'badge-amber'}`}>
                {topRec.priority.toUpperCase()}
              </span>
            </div>
            <button
              onClick={() => handleApplyRec(topRec.id, topRec.title)}
              disabled={applyingId === topRec.id || topRec.status === 'applied'}
              className="btn btn-primary text-xs"
            >
              {topRec.status === 'applied' ? 'Applied' : applyingId === topRec.id ? 'Applying...' : 'Apply Recommendation'}
            </button>
          </div>
          <p className="text-sm text-secondary mb-2">{topRec.description}</p>
          <div className="flex items-center gap-4 text-xs font-semibold">
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
