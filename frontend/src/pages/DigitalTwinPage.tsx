import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { GitFork, Play, ArrowRight, AlertTriangle, TrendingDown, TrendingUp } from 'lucide-react'
import { useAppStore } from '../store'
import { simulateChange, fetchLiveMetrics } from '../api/client'
import type { SimulationResult } from '../types'

const INSTANCES = ['t3.micro', 't3.small', 't3.medium', 'm5.large', 'm5.xlarge', 'm5.2xlarge', 'c5.large', 'c5.xlarge', 'r5.large', 'r5.xlarge']
const ACTIONS = ['resize', 'scale_out', 'scale_in', 'migrate', 'consolidate', 'terminate']
const REGIONS = ['us-east', 'us-west', 'eu-west', 'ap-southeast', 'ca-central', 'in-north']

function DeltaCell({ value, suffix = '%', invert = false }: { value: number; suffix?: string; invert?: boolean }) {
  const positive = invert ? value < 0 : value > 0
  return (
    <span style={{ color: positive ? 'var(--red-400)' : value < 0 ? 'var(--emerald-400)' : 'var(--text-muted)', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', fontSize: 13 }}>
      {value > 0 ? '+' : ''}{value.toFixed(1)}{suffix}
    </span>
  )
}

export default function DigitalTwinPage() {
  const { provider, region } = useAppStore()
  const [action, setAction] = useState('resize')
  const [toInstance, setToInstance] = useState('m5.large')
  const [scaleFactor, setScaleFactor] = useState(2)
  const [targetRegion, setTargetRegion] = useState('ca-central')
  const [result, setResult] = useState<SimulationResult | null>(null)

  const { data: metrics } = useQuery({
    queryKey: ['liveMetrics', provider, region],
    queryFn: () => fetchLiveMetrics(provider, region),
    refetchInterval: 15_000,
  })

  const { mutate: simulate, isPending } = useMutation({
    mutationFn: () => simulateChange({
      baseline_metrics: metrics || {
        timestamp: new Date().toISOString(), provider, region,
        cpu: 45, memory: 55, storage: 50, network: 500,
        cost_usd_per_hour: 0.192, carbon_gco2_per_hour: 35, instance_count: 1, source: 'DEMO',
      },
      changes: [{
        action,
        instance_type_from: 'm5.xlarge',
        instance_type_to: action === 'resize' ? toInstance : undefined,
        scale_factor: action === 'scale_out' || action === 'scale_in' ? scaleFactor : 1,
        target_region: action === 'migrate' ? targetRegion : undefined,
      }],
      simulation_hours: 24,
    }),
    onSuccess: (data) => setResult(data),
  })

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1>Digital Twin Simulator</h1>
          <p className="text-secondary text-sm mt-1">Simulate infrastructure changes and estimate impact before applying</p>
        </div>
        <div className="badge badge-indigo">
          <GitFork size={12} />
          SIMULATION MODE
        </div>
      </div>

      <div className="grid-2 gap-4" style={{ alignItems: 'start' }}>
        {/* Configuration panel */}
        <div className="card">
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>Configure Change</h3>

          <div className="flex-col gap-4">
            <div>
              <label className="text-xs text-muted mb-1" style={{ display: 'block', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Action</label>
              <select value={action} onChange={e => setAction(e.target.value)}>
                {ACTIONS.map(a => <option key={a} value={a}>{a.replace('_', ' ')}</option>)}
              </select>
            </div>

            {action === 'resize' && (
              <div>
                <label className="text-xs text-muted mb-1" style={{ display: 'block', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Target Instance Type</label>
                <select value={toInstance} onChange={e => setToInstance(e.target.value)}>
                  {INSTANCES.map(i => <option key={i} value={i}>{i}</option>)}
                </select>
              </div>
            )}

            {(action === 'scale_out' || action === 'scale_in') && (
              <div>
                <label className="text-xs text-muted mb-1" style={{ display: 'block', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Scale Factor: {scaleFactor}×
                </label>
                <input type="range" min={1.5} max={5} step={0.5} value={scaleFactor} onChange={e => setScaleFactor(Number(e.target.value))} />
              </div>
            )}

            {action === 'migrate' && (
              <div>
                <label className="text-xs text-muted mb-1" style={{ display: 'block', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Target Region</label>
                <select value={targetRegion} onChange={e => setTargetRegion(e.target.value)}>
                  {REGIONS.map(r => <option key={r} value={r}>{r}</option>)}
                </select>
              </div>
            )}

            {/* Baseline metrics */}
            {metrics && (
              <div className="card" style={{ padding: '12px 14px', background: 'rgba(255,255,255,0.03)' }}>
                <div className="text-xs text-muted mb-2" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Current Baseline</div>
                <div className="grid-2 gap-2">
                  {[
                    ['CPU', `${metrics.cpu.toFixed(1)}%`],
                    ['Memory', metrics.memory != null ? `${metrics.memory.toFixed(1)}%` : 'UNAVAILABLE'],
                    ['Cost', `$${metrics.cost_usd_per_hour.toFixed(4)}/hr`],
                    ['Carbon', `${metrics.carbon_gco2_per_hour.toFixed(1)}gCO₂/hr`],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <div className="text-xs text-muted">{k}</div>
                      <div className="text-sm font-mono" style={{ fontWeight: 600 }}>{v}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button className="btn btn-primary w-full" onClick={() => simulate()} disabled={isPending}>
              {isPending ? '⟳ Simulating…' : <><Play size={14} /> Run Simulation</>}
            </button>
          </div>
        </div>

        {/* Results panel */}
        <div>
          <AnimatePresence mode="wait">
            {result ? (
              <motion.div
                key={result.simulation_id}
                className="card"
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0 }}
              >
                <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
                  <h3 style={{ fontSize: 14, fontWeight: 700 }}>Simulation Results</h3>
                  <div className="flex gap-2">
                    <span className="badge badge-muted">ID: {result.simulation_id}</span>
                    <span className="badge badge-indigo">Confidence: {(result.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* Before / After comparison */}
                <div className="grid-2 gap-3 mb-4">
                  {[
                    { label: 'Monthly Cost', before: `$${result.before.monthly_cost_usd.toFixed(0)}`, after: `$${result.after.monthly_cost_usd.toFixed(0)}`, delta: result.delta.monthly_cost_pct },
                    { label: 'Monthly Carbon', before: `${result.before.monthly_carbon_kgco2.toFixed(2)}kg`, after: `${result.after.monthly_carbon_kgco2.toFixed(2)}kg`, delta: result.delta.monthly_carbon_pct },
                    { label: 'Hourly Cost', before: `$${result.before.cost_usd_per_hour.toFixed(4)}`, after: `$${result.after.cost_usd_per_hour.toFixed(4)}`, delta: result.delta.cost_pct },
                    { label: 'Hourly Carbon', before: `${result.before.carbon_gco2_per_hour.toFixed(1)}g`, after: `${result.after.carbon_gco2_per_hour.toFixed(1)}g`, delta: result.delta.carbon_pct },
                  ].map(({ label, before, after, delta }) => (
                    <div key={label} className="card" style={{ padding: '12px 14px' }}>
                      <div className="text-xs text-muted mb-2" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono text-secondary" style={{ fontSize: 13 }}>{before}</span>
                        <ArrowRight size={12} color="var(--text-muted)" />
                        <span className="font-mono text-primary" style={{ fontSize: 13, fontWeight: 700 }}>{after}</span>
                      </div>
                      <div className="mt-1"><DeltaCell value={delta} /></div>
                    </div>
                  ))}
                </div>

                {/* Recommendation */}
                <div className="card" style={{ padding: '14px 16px', borderColor: 'rgba(16,185,129,0.2)', background: 'rgba(16,185,129,0.05)' }}>
                  <div className="text-xs text-emerald mb-1" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>AI Recommendation</div>
                  <p className="text-sm" style={{ lineHeight: 1.6 }}>{result.recommendation}</p>
                </div>

                {result.warnings.length > 0 && (
                  <div className="card mt-3" style={{ padding: '12px 14px', borderColor: 'rgba(245,158,11,0.2)', background: 'rgba(245,158,11,0.05)' }}>
                    {result.warnings.map((w, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm text-amber">
                        <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 2 }} />
                        {w}
                      </div>
                    ))}
                  </div>
                )}
              </motion.div>
            ) : (
              <motion.div
                key="empty"
                className="card"
                style={{ textAlign: 'center', padding: 60 }}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
              >
                <GitFork size={40} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
                <div className="text-secondary" style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>Configure and run a simulation</div>
                <div className="text-muted text-sm">Results will show before/after comparisons<br />with cost and carbon impact estimates</div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}
