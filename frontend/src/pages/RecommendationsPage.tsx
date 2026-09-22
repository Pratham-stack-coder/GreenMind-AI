import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  DollarSign, Zap, Leaf, Shield, Activity, Filter,
  ChevronDown, ChevronUp, ExternalLink, RefreshCw
} from 'lucide-react'
import { useAppStore } from '../store'
import { fetchRecommendations, fetchExplain } from '../api/client'
import type { RecommendationItem } from '../types'

const categoryIcons: Record<string, React.ReactNode> = {
  cost: <DollarSign size={14} />,
  performance: <Activity size={14} />,
  sustainability: <Leaf size={14} />,
  security: <Shield size={14} />,
  reliability: <Zap size={14} />,
}

const categoryColors: Record<string, string> = {
  cost: 'amber', performance: 'blue', sustainability: 'emerald',
  security: 'red', reliability: 'indigo',
}

function RecCard({ rec }: { rec: RecommendationItem }) {
  const [expanded, setExpanded] = useState(false)
  const color = categoryColors[rec.category] || 'muted'
  const prioColor = rec.priority === 'critical' ? 'red' : rec.priority === 'high' ? 'amber' : rec.priority === 'medium' ? 'blue' : 'muted'

  return (
    <motion.div
      className={`card priority-${rec.priority}`}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div
        className="flex items-center gap-3"
        style={{ cursor: 'pointer' }}
        onClick={() => setExpanded(v => !v)}
      >
        <div className={`badge badge-${color}`} style={{ flexShrink: 0 }}>
          {categoryIcons[rec.category]}
          {rec.category}
        </div>
        <div className="flex-1 truncate">
          <div style={{ fontWeight: 600, fontSize: 14 }}>{rec.title}</div>
          <div className="text-secondary text-xs mt-1">{rec.impact_summary}</div>
        </div>
        <div className="flex items-center gap-3" style={{ flexShrink: 0 }}>
          {rec.estimated_monthly_savings_usd > 0 && (
            <span className="text-emerald font-mono" style={{ fontWeight: 700, fontSize: 13 }}>
              ${rec.estimated_monthly_savings_usd.toFixed(0)}/mo
            </span>
          )}
          {rec.estimated_carbon_reduction_pct > 0 && (
            <span className="text-emerald text-xs">-{rec.estimated_carbon_reduction_pct.toFixed(0)}% CO₂</span>
          )}
          <span className={`badge badge-${prioColor}`}>{rec.priority}</span>
          <span className={`badge badge-${rec.effort === 'low' ? 'emerald' : rec.effort === 'medium' ? 'amber' : 'red'}`}>
            {rec.effort} effort
          </span>
          {expanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{ overflow: 'hidden' }}
          >
            <div className="divider" />
            <p className="text-secondary text-sm mb-3">{rec.description}</p>
            {rec.evidence.length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-muted mb-1" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Evidence</div>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {rec.evidence.map((e, i) => (
                    <li key={i} className="text-xs text-secondary flex items-center gap-2">
                      <span style={{ color: 'var(--emerald-400)', fontWeight: 700 }}>·</span> {e}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted">Confidence: <strong style={{ color: 'var(--text-primary)' }}>{(rec.confidence * 100).toFixed(0)}%</strong></span>
              <span className="text-xs text-muted">Action: <code style={{ background: 'rgba(255,255,255,0.06)', padding: '1px 6px', borderRadius: 4, color: 'var(--emerald-400)' }}>{rec.action}</code></span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default function RecommendationsPage() {
  const { provider, region } = useAppStore()
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['recommendations', provider, region],
    queryFn: () => fetchRecommendations({ provider, region }),
  })

  const categories = ['all', 'cost', 'performance', 'sustainability', 'security', 'reliability']
  const priorities = ['all', 'critical', 'high', 'medium', 'low']

  const filtered = (data?.recommendations || []).filter(r =>
    (categoryFilter === 'all' || r.category === categoryFilter) &&
    (priorityFilter === 'all' || r.priority === priorityFilter)
  )

  const totalSavings = (data?.recommendations || []).reduce((s, r) => s + r.estimated_monthly_savings_usd, 0)

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1>AI Recommendations</h1>
          <p className="text-secondary text-sm mt-1">
            {data?.recommendations.length || 0} optimizations identified ·
            {totalSavings > 0 && <span className="text-emerald"> ${totalSavings.toFixed(0)}/month savings opportunity</span>}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary btn-sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Score banner */}
      {data && (
        <div className="card mb-4" style={{ padding: '12px 20px', borderColor: 'rgba(16,185,129,0.2)', background: 'rgba(16,185,129,0.04)' }}>
          <div className="flex items-center gap-4">
            <div>
              <div className="text-xs text-muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Optimization Score</div>
              <div style={{ fontSize: 32, fontWeight: 900, color: data.optimization_score >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)' }}>
                {data.optimization_score}/100
              </div>
            </div>
            <div className="flex gap-3 flex-wrap">
              {(['critical', 'high', 'medium', 'low'] as const).map(p => {
                const count = data.recommendations.filter(r => r.priority === p).length
                if (count === 0) return null
                const c = p === 'critical' ? 'red' : p === 'high' ? 'amber' : p === 'medium' ? 'blue' : 'muted'
                return <div key={p} className={`badge badge-${c}`}>{count} {p}</div>
              })}
            </div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Filter size={14} color="var(--text-muted)" />
          <span className="text-xs text-muted">Category:</span>
          {categories.map(c => (
            <button
              key={c}
              className={`badge ${categoryFilter === c ? 'badge-emerald' : 'badge-muted'}`}
              style={{ cursor: 'pointer' }}
              onClick={() => setCategoryFilter(c)}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2" style={{ marginLeft: 'auto' }}>
          <span className="text-xs text-muted">Priority:</span>
          {priorities.map(p => (
            <button
              key={p}
              className={`badge ${priorityFilter === p ? 'badge-emerald' : 'badge-muted'}`}
              style={{ cursor: 'pointer' }}
              onClick={() => setPriorityFilter(p)}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {/* Recommendation list */}
      {isLoading ? (
        <div className="flex-col gap-3">
          {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="text-secondary">No recommendations match the current filters.</div>
        </div>
      ) : (
        <div className="flex-col gap-3">
          {filtered.map(rec => <RecCard key={rec.id} rec={rec} />)}
        </div>
      )}
    </div>
  )
}
