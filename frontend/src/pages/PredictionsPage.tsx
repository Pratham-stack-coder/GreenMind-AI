import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Cell, ReferenceLine, ComposedChart,
} from 'recharts'
import { TrendingUp, AlertTriangle, RefreshCw } from 'lucide-react'
import { useAppStore } from '../store'
import { fetchLiveMetrics, fetchForecast, fetchCarbonCurve } from '../api/client'

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-title">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="chart-tooltip-row">
          <div className="chart-tooltip-dot" style={{ background: p.color }} />
          <span>{p.name}: <strong style={{ color: 'var(--text-primary)' }}>{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</strong></span>
        </div>
      ))}
    </div>
  )
}

export default function PredictionsPage() {
  const { provider, region } = useAppStore()
  const now = new Date()

  const { data: metrics } = useQuery({
    queryKey: ['liveMetrics', provider, region],
    queryFn: () => fetchLiveMetrics(provider, region),
    refetchInterval: 15_000,
  })

  const { data: carbonCurve } = useQuery({
    queryKey: ['carbonCurve', region],
    queryFn: () => fetchCarbonCurve(region),
  })

  const { data: forecast, isLoading: forecasting, refetch } = useQuery({
    queryKey: ['forecast', metrics?.cpu, metrics?.memory, region],
    queryFn: () => fetchForecast({
      cpu: metrics?.cpu || 45,
      memory: metrics?.memory || 55,
      network: metrics?.network || 500,
      hour: now.getHours() + now.getMinutes() / 60,
      day_of_week: now.getDay(),
      region,
    }),
    enabled: !!metrics,
  })

  const forecastMetrics = [
    { key: 'cpu', label: 'CPU', unit: '%', color: '#10b981' },
    { key: 'memory', label: 'Memory', unit: '%', color: '#6366f1' },
    { key: 'network', label: 'Network', unit: 'Mbps', color: '#3b82f6' },
    { key: 'cost_usd_per_hour', label: 'Cost', unit: '$/hr', color: '#f59e0b' },
    { key: 'carbon_gco2_per_hour', label: 'Carbon', unit: 'gCO₂/hr', color: '#34d399' },
  ]

  const riskColors: Record<string, string> = {
    LOW: 'var(--emerald-400)',
    MEDIUM: 'var(--amber-400)',
    HIGH: 'var(--red-400)',
    CRITICAL: '#ff0040',
  }

  // Build carbon curve chart data
  const curveData = (carbonCurve?.curve || []).map((p: any, i: number) => ({
    hour: `${i}:00`,
    intensity: p.carbon_intensity_gco2_per_kwh,
    isCurrent: i === now.getHours(),
  }))

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1>ML Predictions</h1>
          <p className="text-secondary text-sm mt-1">5-model forecast engine · 60-minute horizon</p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={() => refetch()} disabled={forecasting}>
          <RefreshCw size={14} className={forecasting ? 'animate-spin' : ''} />
          Refresh Forecast
        </button>
      </div>

      {/* Risk badge */}
      {forecast && (
        <div className="card mb-4" style={{ padding: '16px 20px' }}>
          <div className="prediction-risk-banner">
            <div>
              <div className="text-xs text-muted mb-1" style={{ textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 }}>Predicted Risk Level</div>
              <div style={{ fontSize: 36, fontWeight: 900, color: riskColors[forecast.risk] || 'var(--text-primary)' }}>
                {forecast.risk}
              </div>
            </div>
            {forecast.risk !== 'LOW' && (
              <div className="flex items-center gap-2 badge badge-amber" style={{ padding: '8px 14px' }}>
                <AlertTriangle size={14} />
                Action recommended
              </div>
            )}
            <div className="flex-1 hidden-sm" />
            <div className="prediction-risk-metrics">
              <div className="text-right">
                <div className="text-xs text-muted mb-1">Model MAE</div>
                <div className="font-mono text-emerald" style={{ fontSize: 18, fontWeight: 700 }}>
                  {forecast.model_mae?.toFixed(3) || '–'}%
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted mb-1">Horizon</div>
                <div className="font-mono text-indigo" style={{ fontSize: 18, fontWeight: 700 }}>
                  {forecast.horizon_minutes}min
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Forecast metrics */}
      <div className="grid-5 mb-4">
        {forecastMetrics.map(({ key, label, unit, color }) => {
          const fc = forecast?.[key as keyof typeof forecast] as any
          return (
            <motion.div
              key={key}
              className="card"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 * forecastMetrics.indexOf({ key, label, unit, color }) }}
            >
              <div className="text-xs text-muted mb-2" style={{ textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.08em' }}>{label}</div>
              {fc ? (
                <>
                  <div className="flex items-end gap-2 mb-3">
                    <div>
                      <div className="text-xs text-muted">Now</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color }}>
                        {fc.current.toFixed(key.includes('cost') ? 4 : 1)}
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 3 }}>{unit}</span>
                      </div>
                    </div>
                    <div style={{ color: 'var(--text-muted)', marginBottom: 4 }}>→</div>
                    <div>
                      <div className="text-xs text-muted">Predicted</div>
                      <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' }}>
                        {fc.predicted.toFixed(key.includes('cost') ? 4 : 1)}
                        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 3 }}>{unit}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className={`text-xs ${fc.delta_pct > 5 ? 'text-amber' : fc.delta_pct < -5 ? 'text-emerald' : 'text-muted'}`}>
                      {fc.delta_pct > 0 ? '+' : ''}{fc.delta_pct.toFixed(1)}%
                    </span>
                    {fc.anomaly && <span className="badge badge-red" style={{ fontSize: 9 }}>ANOMALY</span>}
                    <span className="text-xs text-muted">{(fc.confidence * 100).toFixed(0)}% conf.</span>
                  </div>
                  <div className="progress-track mt-2">
                    <div
                      className="progress-fill"
                      style={{
                        width: `${Math.min(100, Math.max(0, fc.predicted))}%`,
                        background: color,
                      }}
                    />
                  </div>
                </>
              ) : (
                <div className="skeleton" style={{ height: 80 }} />
              )}
            </motion.div>
          )
        })}
      </div>

      {/* Confidence band forecast chart */}
      {forecast && (
        <div className="card mb-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>CPU Forecast with Confidence Band</h3>
              <p className="text-xs text-muted mt-1">
                Shaded area shows ±{(((forecast.cpu as any)?.confidence_interval || 0.1) * 100).toFixed(0)}% confidence interval
              </p>
            </div>
            <span className="badge badge-indigo">
              {((forecast.cpu as any)?.confidence * 100 || 95).toFixed(0)}% confidence
            </span>
          </div>
          {(() => {
            const cpu = forecast.cpu as any
            if (!cpu) return null
            const now = cpu.current
            const predicted = cpu.predicted
            const ci = cpu.confidence_interval || 0.1
            // Build a simulated 60-min trajectory
            const points = Array.from({ length: 13 }, (_, i) => {
              const t = i * 5
              const progress = i / 12
              const val = now + (predicted - now) * progress + Math.sin(progress * Math.PI) * 3
              const band = ci * 100 * (0.5 + progress * 0.7)
              return {
                min: Math.max(0, val - band),
                max: Math.min(100, val + band),
                cpu: val,
                label: t === 0 ? 'Now' : `+${t}m`,
              }
            })
            return (
              <div className="chart-container" style={{ height: 200 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={points}>
                    <defs>
                      <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={v => `${v}%`} />
                    <Tooltip content={<ChartTooltip />} />
                    {/* Confidence band */}
                    <Area type="monotone" dataKey="max" stroke="transparent" fill="url(#bandGrad)" legendType="none" name="Upper bound" />
                    <Area type="monotone" dataKey="min" stroke="transparent" fill="var(--bg-deep)" legendType="none" name="Lower bound" />
                    {/* Actual prediction line */}
                    <Area type="monotone" dataKey="cpu" stroke="#10b981" fill="rgba(16,185,129,0.1)" strokeWidth={2.5} dot={false} name="CPU Forecast" />
                    <ReferenceLine y={now} stroke="rgba(251,191,36,0.5)" strokeDasharray="4 3" label={{ value: 'current', fill: 'var(--amber-400)', fontSize: 9, position: 'insideTopRight' }} />
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
            )
          })()}
        </div>
      )}

      {/* Carbon intensity curve */}
      <div className="card">
        <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
          <div>
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>24h Carbon Intensity — {region}</h3>
            <p className="text-xs text-muted mt-1">Lower is greener · gCO₂ per kWh · DEMO data</p>
          </div>
          {carbonCurve && (
            <div className="badge badge-emerald">
              Green Score: {carbonCurve.green_score}/100
            </div>
          )}
        </div>
        <div className="chart-container" style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={curveData} barSize={24}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" tick={{ fontSize: 9 }} interval={2} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip content={<ChartTooltip />} />
              <Bar dataKey="intensity" name="gCO₂/kWh" radius={[3,3,0,0]}>
                {curveData.map((entry: any, i: number) => (
                  <Cell
                    key={i}
                    fill={entry.isCurrent ? '#f59e0b' : entry.intensity < 250 ? '#10b981' : entry.intensity < 400 ? '#3b82f6' : '#ef4444'}
                    fillOpacity={entry.isCurrent ? 1 : 0.7}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="flex gap-3 mt-2 flex-wrap" style={{ justifyContent: 'flex-end' }}>
          <div className="flex items-center gap-1"><div style={{ width: 10, height: 10, borderRadius: 2, background: '#10b981' }} /><span className="text-xs text-muted">Clean (&lt;250)</span></div>
          <div className="flex items-center gap-1"><div style={{ width: 10, height: 10, borderRadius: 2, background: '#3b82f6' }} /><span className="text-xs text-muted">Moderate</span></div>
          <div className="flex items-center gap-1"><div style={{ width: 10, height: 10, borderRadius: 2, background: '#ef4444' }} /><span className="text-xs text-muted">High</span></div>
          <div className="flex items-center gap-1"><div style={{ width: 10, height: 10, borderRadius: 2, background: '#f59e0b' }} /><span className="text-xs text-muted">Now</span></div>
        </div>
      </div>
    </div>
  )
}
