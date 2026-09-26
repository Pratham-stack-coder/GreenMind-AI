import React from 'react'
import { motion } from 'framer-motion'
import { Bot, CheckCircle2, AlertCircle, ArrowRight } from 'lucide-react'
import type { AgentResult } from '../../types'

interface AgentCardProps {
  agent: AgentResult
}

export default function AgentCard({ agent }: AgentCardProps) {
  const isHealthy = agent.score >= 70

  return (
    <motion.div
      className="card mb-4"
      whileHover={{ y: -2, transition: { duration: 0.2 } }}
    >
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <div
            style={{
              padding: 8,
              borderRadius: 8,
              background: 'rgba(255,255,255,0.05)',
              border: '1px solid var(--border)',
            }}
          >
            <Bot size={18} color="var(--emerald-400)" />
          </div>
          <div>
            <h4 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{agent.agent} Agent</h4>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className="badge badge-emerald">
                <CheckCircle2 size={10} />
                {agent.status.toUpperCase()}
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {agent.recommendations.length} recommendation(s) generated
              </span>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div style={{ fontSize: 24, fontWeight: 800, color: isHealthy ? 'var(--emerald-400)' : 'var(--amber-400)' }}>
            {agent.score}
            <span style={{ fontSize: 14, color: 'var(--text-muted)' }}>/100</span>
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Domain Health
          </div>
        </div>
      </div>

      {/* Findings list */}
      <div className="mb-3">
        <div className="text-xs font-semibold text-secondary uppercase tracking-wider mb-2">
          Key Findings
        </div>
        <div className="space-y-1">
          {agent.findings.map((f, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-secondary" style={{ lineHeight: 1.4 }}>
              <span style={{ color: 'var(--emerald-400)', marginTop: 2 }}>•</span>
              <span>{f}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Top recommendations preview */}
      {agent.recommendations.length > 0 && (
        <div
          className="p-2 rounded"
          style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border)' }}
        >
          <div className="text-xs font-medium text-muted mb-1">Top Reconciled Action:</div>
          <div className="text-xs text-primary font-mono flex items-center justify-between">
            <span>{agent.recommendations[0].action}</span>
            <span className="text-emerald-400 font-bold">
              {agent.recommendations[0].estimated_monthly_savings_usd > 0 &&
                `+$${agent.recommendations[0].estimated_monthly_savings_usd.toFixed(0)}/mo`}
            </span>
          </div>
        </div>
      )}
    </motion.div>
  )
}
