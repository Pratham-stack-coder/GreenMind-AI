import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { BarChart3, DollarSign, Leaf } from 'lucide-react'
import { useAppStore } from '../store'
import { fetchCostAnalytics, fetchCarbonAnalytics, fetchScores } from '../api/client'

const ChartTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-title">{label}</div>
      {payload.map((p: any) => (
        <div key={p.name} className="chart-tooltip-row">
          <div className="chart-tooltip-dot" style={{ background: p.color }} />
          <span>{p.name}: <strong style={{ color: 'var(--text-primary)' }}>
            {typeof p.value === 'number' ? p.value.toFixed(4) : p.value}
          </strong></span>
        </div>
      ))}
    </div>
  )
}

export default function AnalyticsPage() {
  const { provider, region } = useAppStore()
  const [days, setDays] = useState(7)

  const { data: costData } = useQuery({
    queryKey: ['costAnalytics', days],
    queryFn: () => fetchCostAnalytics(days),
  })

  const { data: carbonData } = useQuery({
    queryKey: ['carbonAnalytics', days, region],
    queryFn: () => fetchCarbonAnalytics(days, region),
  })

  const { data: scores } = useQuery({
    queryKey: ['scores', provider, region],
    queryFn: () => fetchScores(provider, region),
    refetchInterval: 60_000,
  })

  // Downsample to max 168 points (hourly for 7 days)
  const sampleEvery = (arr: any[], n: number) => arr.filter((_, i) => i % n === 0)
  const step = Math.max(1, Math.floor((costData?.data_points.length || 1) / 120))

  const costPoints = sampleEvery(costData?.data_points || [], step).map(p => ({
    time: new Date(p.timestamp).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit' }),
    cost: p.cost_usd,
  }))

  const carbonPoints = sampleEvery(carbonData?.data_points || [], step).map(p => ({
    time: new Date(p.timestamp).toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit' }),
    carbon: p.carbon_gco2,
    intensity: p.intensity_gco2_per_kwh,
  }))

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1>Analytics</h1>
          <p className="text-secondary text-sm mt-1">Cost and carbon emissions over time</p>
        </div>
        <div className="flex gap-2">
          {[7, 14, 30].map(d => (
            <button
              key={d}
              className={`btn btn-sm ${days === d ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setDays(d)}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid-3 mb-4">
        <div className="metric-card amber">
          <div className="metric-label">Total Cost ({days}d)</div>
          <div className="metric-value">
            ${costData?.total_usd.toFixed(2) || '–'}
          </div>
          <div className="text-xs text-muted mt-1">
            Top driver: {costData?.top_cost_drivers[0] || '–'}
          </div>
        </div>
        <div className="metric-card emerald">
          <div className="metric-label">Total Carbon ({days}d)</div>
          <div className="metric-value">
            {carbonData ? (carbonData.total_gco2 / 1000).toFixed(2) : '–'}
            <span style={{ fontSize: '0.4em', fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>kg CO₂</span>
          </div>
          <div className="text-xs text-muted mt-1">
            {carbonData?.green_hours_pct.toFixed(0)}% green hours
          </div>
        </div>
        <div className="metric-card indigo">
          <div className="metric-label">Sustainability Score</div>
          <div className="metric-value" style={{ color: scores?.sustainability && scores.sustainability >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)' }}>
            {scores?.sustainability || '–'}
            <span style={{ fontSize: '0.4em', fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>/100</span>
          </div>
          <div className="text-xs text-muted mt-1">Region: {region}</div>
        </div>
      </div>

      {/* Cost chart */}
      <div className="card mb-4">
        <div className="flex items-center gap-2 mb-3">
          <DollarSign size={16} color="var(--amber-400)" />
          <h3 style={{ fontSize: 14, fontWeight: 700 }}>Hourly Cost ($/hr)</h3>
        </div>
        <div className="chart-container" style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={costPoints}>
              <defs>
                <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `$${v.toFixed(3)}`} />
              <Tooltip content={<ChartTooltip />} />
              <Area type="monotone" dataKey="cost" name="Cost ($/hr)" stroke="#f59e0b" fill="url(#costGrad)" strokeWidth={2} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Carbon chart */}
      <div className="card mb-4">
        <div className="flex items-center gap-2 mb-3">
          <Leaf size={16} color="var(--emerald-400)" />
          <h3 style={{ fontSize: 14, fontWeight: 700 }}>Carbon Emissions & Intensity</h3>
        </div>
        <div className="chart-container" style={{ height: 220 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={carbonPoints}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" tick={{ fontSize: 9 }} interval="preserveStartEnd" />
              <YAxis yAxisId="left" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 10 }} />
              <Tooltip content={<ChartTooltip />} />
              <Legend />
              <Line yAxisId="left" type="monotone" dataKey="carbon" name="gCO₂" stroke="#10b981" strokeWidth={2} dot={false} />
              <Line yAxisId="right" type="monotone" dataKey="intensity" name="Intensity (gCO₂/kWh)" stroke="#818cf8" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Provider cost breakdown */}
      {costData?.breakdown_by_provider && (
        <div className="card">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 size={16} color="var(--indigo-400)" />
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>Cost by Provider</h3>
          </div>
          <div className="flex gap-4 flex-wrap">
            {Object.entries(costData.breakdown_by_provider).map(([p, v]) => (
              <motion.div key={p} className="card" style={{ padding: '12px 16px', minWidth: 120 }} whileHover={{ scale: 1.03 }}>
                <div className="text-xs text-muted mb-1" style={{ textTransform: 'uppercase', fontWeight: 700 }}>{p}</div>
                <div className="font-mono text-amber" style={{ fontSize: 20, fontWeight: 800 }}>${(v as number).toFixed(2)}</div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
