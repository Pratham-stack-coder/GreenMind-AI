import React from 'react'
import { motion } from 'framer-motion'
import { ArrowUpRight, DollarSign, Leaf, Shield, Cpu, Activity, Clock } from 'lucide-react'
import type { RecommendationItem } from '../../types'

interface RecommendationCardProps {
  rec: RecommendationItem
  onApply?: (id: string, title: string) => void
  onExplain?: (id: string) => void
  isApplying?: boolean
}

export default function RecommendationCard({
  rec,
  onApply,
  onExplain,
  isApplying,
}: RecommendationCardProps) {
  const categoryIconMap = {
    cost: DollarSign,
    performance: Cpu,
    sustainability: Leaf,
    security: Shield,
    reliability: Activity,
  }

  const Icon = categoryIconMap[rec.category] || Activity

  const priorityColor = {
    critical: 'badge-red',
    high: 'badge-amber',
    medium: 'badge-blue',
    low: 'badge-muted',
  }[rec.priority] || 'badge-muted'

  return (
    <motion.div
      className="card mb-3"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ borderColor: 'var(--emerald-500)', transition: { duration: 0.2 } }}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2">
          <div
            style={{
              padding: 8,
              borderRadius: 8,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border)',
            }}
          >
            <Icon size={16} color="var(--emerald-400)" />
          </div>
          <div>
            <h4 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{rec.title}</h4>
            <div className="flex items-center gap-2 mt-1">
              <span className={`badge ${priorityColor}`}>
                {rec.priority.toUpperCase()}
              </span>
              <span className="badge badge-muted">
                {rec.category.toUpperCase()}
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                Effort: {rec.effort}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {onExplain && (
            <button
              onClick={() => onExplain(rec.id)}
              className="btn btn-secondary text-xs"
              style={{ padding: '6px 10px' }}
            >
              Explain AI
            </button>
          )}
          {onApply && rec.status !== 'applied' && (
            <button
              onClick={() => onApply(rec.id, rec.title)}
              disabled={isApplying}
              className="btn btn-primary text-xs"
              style={{ padding: '6px 12px' }}
            >
              {isApplying ? 'Applying...' : 'Apply Optimization'}
            </button>
          )}
          {rec.status === 'applied' && (
            <span className="badge badge-emerald">APPLIED</span>
          )}
        </div>
      </div>

      <p className="text-secondary text-sm mb-3" style={{ lineHeight: 1.5 }}>
        {rec.description}
      </p>

      {/* Impact strip */}
      <div
        className="flex items-center justify-between p-2 rounded"
        style={{
          background: 'rgba(16, 185, 129, 0.04)',
          border: '1px solid rgba(16, 185, 129, 0.12)',
        }}
      >
        <div className="flex items-center gap-4 text-xs">
          {rec.estimated_monthly_savings_usd > 0 && (
            <div className="flex items-center gap-1 text-emerald-400 font-semibold">
              <DollarSign size={13} />
              <span>${rec.estimated_monthly_savings_usd.toFixed(0)}/mo savings</span>
            </div>
          )}
          {rec.estimated_carbon_reduction_pct > 0 && (
            <div className="flex items-center gap-1 text-emerald-400 font-semibold">
              <Leaf size={13} />
              <span>-{rec.estimated_carbon_reduction_pct.toFixed(0)}% CO₂</span>
            </div>
          )}
          <div className="text-muted">
            Confidence: {(rec.confidence * 100).toFixed(0)}%
          </div>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
          Action: <code style={{ color: 'var(--emerald-300)' }}>{rec.action}</code>
        </div>
      </div>
    </motion.div>
  )
}
