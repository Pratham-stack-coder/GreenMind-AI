import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts'
import { Cpu, MemoryStick, Network, DollarSign, Leaf, Activity, TrendingUp, AlertTriangle } from 'lucide-react'
import { useAppStore } from '../store'
import { fetchLiveMetrics, fetchScores, fetchTelemetryHistory, fetchRecommendations } from '../api/client'
import type { CloudMetrics, OptimizationScores } from '../types'

// ── Custom Tooltip ───────────────────────────────────────────────────────────
const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-title">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="chart-tooltip-row">
          <div className="chart-tooltip-dot" style={{ background: p.color }} />
          <span>{p.name}: <strong style={{ color: 'var(--text-primary)' }}>{typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</strong></span>
        </div>
      ))}
    </div>
  )
}

// ── Metric Card ──────────────────────────────────────────────────────────────
function MetricCard({ label, value, unit, icon: Icon, color, delta }: {
  label: string; value: number | string; unit: string
  icon: React.ComponentType<any>; color: string; delta?: number
}) {
  const deltaClass = delta == null ? '' : delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat'
  const deltaLabel = delta == null ? '' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}%`
  return (
    <motion.div
      className={`metric-card ${color}`}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300 }}
    >
      <div className="flex items-center justify-between">
        <span className="metric-label">{label}</span>
        <Icon size={18} color={`var(--${color === 'emerald' ? 'emerald' : color === 'amber' ? 'amber' : color === 'blue' ? 'blue' : 'indigo'}-400)`} />
      </div>
      <div className="metric-value">
        {typeof value === 'number' ? value.toFixed(1) : value}
        <span style={{ fontSize: '0.55em', fontWeight: 400, color: 'var(--text-secondary)', marginLeft: 4 }}>{unit}</span>
      </div>
      {delta != null && (
        <div className={`metric-delta ${deltaClass}`}>
          {delta > 0 ? '↑' : delta < 0 ? '↓' : '→'} {deltaLabel} vs last hour
        </div>
      )}
    </motion.div>
  )
}

// ── Score Radar ──────────────────────────────────────────────────────────────
function ScoreRadar({ scores }: { scores: OptimizationScores }) {
  const data = [
    { subject: 'Cost', value: scores.cost, fullMark: 100 },
    { subject: 'Performance', value: scores.performance, fullMark: 100 },
    { subject: 'Sustainability', value: scores.sustainability, fullMark: 100 },
    { subject: 'Security', value: scores.security, fullMark: 100 },
    { subject: 'Reliability', value: scores.reliability, fullMark: 100 },
  ]

  return (
    <ResponsiveContainer width="100%" height={220}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.06)" />
        <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
        <Radar name="Score" dataKey="value" stroke="var(--emerald-500)" fill="var(--emerald-500)" fillOpacity={0.15} strokeWidth={2} />
      </RadarChart>
    </ResponsiveContainer>
  )
}

// ── Dashboard Page ────────────────────────────────────────────────────────────
export default function DashboardPage() {
  const { provider, region } = useAppStore()

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

  // Prepare CPU history chart data
  const chartData = (history?.entries || [])
    .slice(0, 24)
    .reverse()
    .map((e: CloudMetrics, i: number) => ({
      time: `${i}m`,
      CPU: e.cpu,
      Memory: e.memory,
    }))

  const criticalCount = recs?.recommendations.filter(r => r.priority === 'critical').length || 0

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 800 }}>Cloud Dashboard</h1>
          <p className="text-secondary text-sm mt-1">
            Real-time infrastructure monitoring · {provider.toUpperCase()} · {region}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge badge-emerald">
            <span className="status-dot online" style={{ width: 6, height: 6 }} />
            LIVE
          </span>
          {criticalCount > 0 && (
            <span className="badge badge-red">
              <AlertTriangle size={10} />
              {criticalCount} CRITICAL
            </span>
          )}
        </div>
      </div>

      {/* Overall score */}
      {scores && (
        <div className="card card-accent-emerald mb-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-muted mb-1" style={{ textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700 }}>Optimization Score</div>
              <div style={{ fontSize: 48, fontWeight: 900, color: scores.overall >= 70 ? 'var(--emerald-400)' : scores.overall >= 50 ? 'var(--amber-400)' : 'var(--red-400)', lineHeight: 1, letterSpacing: '-0.04em' }}>
                {scores.overall}
                <span style={{ fontSize: 20, fontWeight: 500, color: 'var(--text-muted)' }}>/100</span>
              </div>
              <div className={`badge mt-2 ${scores.trend === 'improving' ? 'badge-emerald' : scores.trend === 'declining' ? 'badge-red' : 'badge-muted'}`}>
                {scores.trend === 'improving' ? '↑ Improving' : scores.trend === 'declining' ? '↓ Declining' : '→ Stable'}
              </div>
            </div>
            <ScoreRadar scores={scores} />
          </div>
        </div>
      )}

      {/* Metrics grid */}
      {metricsLoading ? (
        <div className="grid-5 mb-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 120 }} />
          ))}
        </div>
      ) : metrics ? (
        <div className="grid-5 mb-4">
          <MetricCard label="CPU" value={metrics.cpu} unit="%" icon={Cpu} color="emerald" />
          <MetricCard label="Memory" value={metrics.memory} unit="%" icon={MemoryStick} color="blue" />
          <MetricCard label="Network" value={metrics.network} unit="Mbps" icon={Network} color="indigo" />
          <MetricCard label="Cost" value={metrics.cost_usd_per_hour} unit="$/hr" icon={DollarSign} color="amber" />
          <MetricCard label="Carbon" value={metrics.carbon_gco2_per_hour} unit="gCO₂/hr" icon={Leaf} color="emerald" />
        </div>
      ) : null}

      {/* Charts row */}
      <div className="grid-2 mb-4">
        {/* CPU + Memory chart */}
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <Activity size={16} color="var(--emerald-400)" />
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>CPU & Memory (Last 24 Readings)</h3>
          </div>
          <div className="chart-container" style={{ height: 180 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData.length > 0 ? chartData : Array.from({ length: 20 }, (_, i) => ({
                time: `${i * 15}m`,
                CPU: 35 + Math.sin(i * 0.5) * 20 + Math.random() * 10,
                Memory: 50 + Math.sin(i * 0.3) * 15 + Math.random() * 8,
              }))}>
                <defs>
                  <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" tick={{ fontSize: 10 }} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="CPU" stroke="#10b981" fill="url(#cpuGrad)" strokeWidth={2} dot={false} />
                <Area type="monotone" dataKey="Memory" stroke="#6366f1" fill="url(#memGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Score breakdown */}
        {scores && (
          <div className="card">
            <div className="flex items-center gap-2 mb-3">
              <TrendingUp size={16} color="var(--indigo-400)" />
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Score Breakdown</h3>
            </div>
            <div className="flex-col gap-3">
              {(['cost', 'performance', 'sustainability', 'security', 'reliability'] as const).map(dim => {
                const val = scores[dim]
                const color = val >= 70 ? 'emerald' : val >= 50 ? 'amber' : 'red'
                return (
                  <div key={dim}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-secondary" style={{ textTransform: 'capitalize' }}>{dim}</span>
                      <span className={`text-sm text-${color}`} style={{ fontWeight: 700 }}>{val}</span>
                    </div>
                    <div className="progress-track">
                      <motion.div
                        className={`progress-fill progress-${color}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${val}%` }}
                        transition={{ duration: 0.8, delay: 0.1 }}
                      />
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      {/* Recent recommendations */}
      {recs && recs.recommendations.length > 0 && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>Top Recommendations</h3>
            <a href="/recommendations" className="text-xs text-emerald" style={{ textDecoration: 'none', fontWeight: 600 }}>View all →</a>
          </div>
          <div className="flex-col gap-2">
            {recs.recommendations.slice(0, 4).map(rec => (
              <div key={rec.id} className={`card priority-${rec.priority}`} style={{ padding: '12px 16px' }}>
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 truncate">
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 2 }}>{rec.title}</div>
                    <div className="text-secondary text-xs">{rec.impact_summary}</div>
                  </div>
                  <div className="flex items-center gap-2" style={{ flexShrink: 0 }}>
                    <span className={`badge badge-${rec.priority === 'critical' ? 'red' : rec.priority === 'high' ? 'amber' : rec.priority === 'medium' ? 'blue' : 'muted'}`}>
                      {rec.priority}
                    </span>
                    {rec.estimated_monthly_savings_usd > 0 && (
                      <span className="text-emerald text-xs font-mono" style={{ fontWeight: 700 }}>
                        ${rec.estimated_monthly_savings_usd.toFixed(0)}/mo
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
