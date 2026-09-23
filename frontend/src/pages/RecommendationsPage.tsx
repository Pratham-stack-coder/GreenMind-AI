import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  DollarSign, Zap, Leaf, Shield, Activity, Filter,
  ChevronDown, ChevronUp, RefreshCw, CheckCircle2, RotateCcw,
  Sparkles, Play, Check, AlertTriangle, X, Terminal, ArrowRight,
  Info, Loader2
} from 'lucide-react'
import { useAppStore } from '../store'
import {
  fetchRecommendations,
  fetchExplain,
  applyRecommendation,
  rollbackRecommendation,
  batchApplyRecommendations
} from '../api/client'
import type { RecommendationItem, ExplainResponse } from '../types'

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

// ── Explain & Apply Modal ───────────────────────────────────────────────────
interface ExplainModalProps {
  rec: RecommendationItem
  onClose: () => void
  onApplySuccess: () => void
}

function ExplainModal({ rec, onClose, onApplySuccess }: ExplainModalProps) {
  const { addNotification } = useAppStore()
  const [dryRun, setDryRun] = useState(false)
  const [applying, setApplying] = useState(false)
  const [applyResult, setApplyResult] = useState<{ message: string; steps: string[]; status: string } | null>(null)

  const { data: explainData, isLoading: explainLoading } = useQuery({
    queryKey: ['explain', rec.id],
    queryFn: () => fetchExplain(rec.id),
  })

  const handleApply = async () => {
    try {
      setApplying(true)
      const res = await applyRecommendation(rec.id, { dry_run: dryRun })
      setApplyResult({
        message: res.message,
        steps: res.steps_taken,
        status: res.status,
      })
      if (!dryRun) {
        addNotification({
          title: 'Optimization Applied',
          body: `${rec.title} was successfully executed. Score improved to ${res.new_score || 85}/100.`,
          priority: rec.priority === 'critical' ? 'critical' : 'high',
        })
        onApplySuccess()
      }
    } catch (err: unknown) {
      console.error('Failed to apply recommendation', err)
    } finally {
      setApplying(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
      }}
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="card"
        style={{
          width: '100%',
          maxWidth: 680,
          maxHeight: '90vh',
          overflowY: 'auto',
          background: 'var(--bg-panel-solid, #11141c)',
          borderColor: 'var(--border-focus, rgba(16, 185, 129, 0.4))',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          padding: 24,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <span className={`badge badge-${categoryColors[rec.category] || 'muted'}`}>
              {categoryIcons[rec.category]}
              {rec.category}
            </span>
            <span className={`badge badge-${rec.priority === 'critical' ? 'red' : rec.priority === 'high' ? 'amber' : 'muted'}`}>
              {rec.priority} priority
            </span>
          </div>
          <button
            onClick={onClose}
            className="btn btn-secondary btn-sm"
            style={{ padding: 6, borderRadius: '50%' }}
          >
            <X size={16} />
          </button>
        </div>

        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>{rec.title}</h2>
        <p className="text-secondary text-sm mb-4">{rec.description}</p>

        {explainLoading ? (
          <div className="flex-col gap-2 my-6">
            <div className="skeleton" style={{ height: 60 }} />
            <div className="skeleton" style={{ height: 100 }} />
          </div>
        ) : (
          <div className="flex-col gap-4 mb-5">
            {/* Why flagged */}
            <div className="card" style={{ padding: '12px 16px', background: 'rgba(255,255,255,0.02)' }}>
              <div className="flex items-center gap-2 mb-1" style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                <Info size={14} color="var(--blue-400)" />
                Why was this flagged?
              </div>
              <p className="text-secondary text-xs" style={{ lineHeight: 1.5 }}>
                {explainData?.why_flagged || 'Identified via automated agent metric correlation.'}
              </p>
            </div>

            {/* Counterfactual analysis */}
            <div className="card" style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.04)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
              <div className="flex items-center gap-2 mb-1" style={{ fontSize: 12, fontWeight: 700, color: 'var(--red-400)' }}>
                <AlertTriangle size={14} />
                Risk if left unaddressed (Counterfactual)
              </div>
              <p className="text-secondary text-xs" style={{ lineHeight: 1.5 }}>
                {explainData?.counterfactual || 'Ongoing resource degradation and unoptimized spend.'}
              </p>
            </div>

            {/* Evidence & Expected Outcome */}
            <div className="grid-2 gap-3" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="card" style={{ padding: '12px 16px', background: 'rgba(255,255,255,0.02)' }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 6 }}>
                  Evidence
                </div>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {rec.evidence.map((e, idx) => (
                    <li key={idx} className="text-xs text-secondary flex items-center gap-2">
                      <span style={{ color: 'var(--emerald-400)', fontWeight: 700 }}>•</span> {e}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="card" style={{ padding: '12px 16px', background: 'rgba(16, 185, 129, 0.04)', borderColor: 'rgba(16, 185, 129, 0.2)' }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--emerald-400)', marginBottom: 6 }}>
                  Expected Impact
                </div>
                <div className="text-xs text-secondary mb-2">{rec.impact_summary}</div>
                <div className="flex gap-2 flex-wrap">
                  {rec.estimated_monthly_savings_usd > 0 && (
                    <span className="badge badge-emerald font-mono">+${rec.estimated_monthly_savings_usd.toFixed(0)}/mo</span>
                  )}
                  {rec.estimated_carbon_reduction_pct > 0 && (
                    <span className="badge badge-emerald">-{rec.estimated_carbon_reduction_pct.toFixed(0)}% CO₂</span>
                  )}
                </div>
              </div>
            </div>

            {/* Execution / Dry Run Result Console */}
            {applyResult && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
                style={{
                  background: 'rgba(0, 0, 0, 0.5)',
                  borderColor: applyResult.status === 'applied' ? 'var(--emerald-500)' : 'var(--blue-400)',
                  padding: 14,
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Terminal size={14} color={applyResult.status === 'applied' ? 'var(--emerald-400)' : 'var(--blue-400)'} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {applyResult.status === 'applied' ? 'Remediation Workflow Executed' : 'Dry-Run Simulation Complete'}
                  </span>
                  <span className={`badge ${applyResult.status === 'applied' ? 'badge-emerald' : 'badge-blue'}`} style={{ marginLeft: 'auto' }}>
                    {applyResult.status}
                  </span>
                </div>
                <div className="text-xs text-secondary mb-2">{applyResult.message}</div>
                <div className="flex-col gap-1">
                  {applyResult.steps.map((st, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs font-mono" style={{ color: 'var(--emerald-400)' }}>
                      <Check size={12} /> {st}
                    </div>
                  ))}
                </div>
              </motion.div>
            )}
          </div>
        )}

        {/* Modal Footer Controls */}
        <div className="flex items-center justify-between pt-3" style={{ borderTop: '1px solid var(--border)' }}>
          <label className="flex items-center gap-2" style={{ cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              style={{ accentColor: 'var(--emerald-500)', cursor: 'pointer' }}
            />
            <span className="text-xs text-secondary">Dry-Run (Simulate without changing cloud state)</span>
          </label>

          <div className="flex gap-2">
            <button className="btn btn-secondary btn-sm" onClick={onClose}>
              Close
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleApply}
              disabled={applying || (rec.status === 'applied' && !dryRun)}
            >
              {applying ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Executing...
                </>
              ) : rec.status === 'applied' && !dryRun ? (
                <>
                  <CheckCircle2 size={14} color="#fff" />
                  Already Applied
                </>
              ) : dryRun ? (
                <>
                  <Play size={14} />
                  Run Simulation
                </>
              ) : (
                <>
                  <Sparkles size={14} />
                  Apply Optimization
                </>
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}

// ── Recommendation Card ─────────────────────────────────────────────────────
function RecCard({
  rec,
  onExplain,
  onApplySuccess,
}: {
  rec: RecommendationItem
  onExplain: (rec: RecommendationItem) => void
  onApplySuccess: () => void
}) {
  const { addNotification } = useAppStore()
  const [expanded, setExpanded] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [isRollingBack, setIsRollingBack] = useState(false)

  const isApplied = rec.status === 'applied'
  const color = categoryColors[rec.category] || 'muted'
  const prioColor =
    rec.priority === 'critical' ? 'red' : rec.priority === 'high' ? 'amber' : rec.priority === 'medium' ? 'blue' : 'muted'

  const handleApplyNow = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      setIsApplying(true)
      const res = await applyRecommendation(rec.id, { dry_run: false })
      addNotification({
        title: 'Optimization Applied',
        body: `${rec.title} applied successfully. Optimization score is now ${res.new_score || 85}/100.`,
        priority: rec.priority === 'critical' ? 'critical' : 'high',
      })
      onApplySuccess()
    } catch (err: unknown) {
      console.error('Failed to apply recommendation', err)
    } finally {
      setIsApplying(false)
    }
  }

  const handleRollbackNow = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      setIsRollingBack(true)
      await rollbackRecommendation(rec.id)
      addNotification({
        title: 'Optimization Rolled Back',
        body: `Reverted ${rec.title} back to open state.`,
        priority: 'medium',
      })
      onApplySuccess()
    } catch (err: unknown) {
      console.error('Failed to rollback recommendation', err)
    } finally {
      setIsRollingBack(false)
    }
  }

  return (
    <motion.div
      className={`card priority-${rec.priority}`}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        borderColor: isApplied ? 'rgba(16, 185, 129, 0.4)' : undefined,
        background: isApplied ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.06), rgba(15, 23, 42, 0.8))' : undefined,
      }}
    >
      <div
        className="flex items-center gap-3"
        style={{ cursor: 'pointer' }}
        onClick={() => setExpanded((v) => !v)}
      >
        <div className={`badge badge-${color}`} style={{ flexShrink: 0 }}>
          {categoryIcons[rec.category]}
          {rec.category}
        </div>

        <div className="flex-1 truncate">
          <div className="flex items-center gap-2">
            <span style={{ fontWeight: 600, fontSize: 14 }}>{rec.title}</span>
            {isApplied && (
              <span className="badge badge-emerald" style={{ fontSize: 10, padding: '1px 6px' }}>
                <CheckCircle2 size={11} /> Applied
              </span>
            )}
          </div>
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

          {/* Quick Apply / Rollback Buttons right in row */}
          {!isApplied ? (
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 10px', fontSize: 12 }}
                onClick={() => onExplain(rec)}
              >
                Explain
              </button>
              <button
                className="btn btn-primary btn-sm"
                style={{ padding: '4px 12px', fontSize: 12 }}
                onClick={handleApplyNow}
                disabled={isApplying}
              >
                {isApplying ? (
                  <Loader2 size={13} className="animate-spin" />
                ) : (
                  <Play size={12} />
                )}
                Apply
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 10px', fontSize: 12, color: 'var(--text-muted)' }}
                onClick={handleRollbackNow}
                disabled={isRollingBack}
              >
                {isRollingBack ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <RotateCcw size={12} />
                )}
                Rollback
              </button>
            </div>
          )}

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

            {/* If applied, display execution steps checklist */}
            {isApplied && rec.steps_taken && rec.steps_taken.length > 0 && (
              <div
                className="card mb-3"
                style={{
                  background: 'rgba(16, 185, 129, 0.04)',
                  borderColor: 'rgba(16, 185, 129, 0.25)',
                  padding: '12px 16px',
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 size={14} color="var(--emerald-400)" />
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--emerald-400)' }}>
                    Automated Remediation Execution Log
                  </span>
                  {rec.applied_at && (
                    <span className="text-xs text-muted" style={{ marginLeft: 'auto' }}>
                      {new Date(rec.applied_at).toLocaleTimeString()}
                    </span>
                  )}
                </div>
                <div className="flex-col gap-1">
                  {rec.steps_taken.map((step, idx) => (
                    <div key={idx} className="flex items-center gap-2 text-xs text-secondary font-mono">
                      <span style={{ color: 'var(--emerald-400)' }}>✓</span> {step}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {rec.evidence.length > 0 && (
              <div className="mb-3">
                <div className="text-xs text-muted mb-1" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Evidence
                </div>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {rec.evidence.map((e, i) => (
                    <li key={i} className="text-xs text-secondary flex items-center gap-2">
                      <span style={{ color: 'var(--emerald-400)', fontWeight: 700 }}>·</span> {e}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex items-center justify-between mt-3 flex-wrap gap-2">
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted">
                  Confidence: <strong style={{ color: 'var(--text-primary)' }}>{(rec.confidence * 100).toFixed(0)}%</strong>
                </span>
                <span className="text-xs text-muted">
                  Action:{' '}
                  <code
                    style={{
                      background: 'rgba(255,255,255,0.06)',
                      padding: '1px 6px',
                      borderRadius: 4,
                      color: 'var(--emerald-400)',
                    }}
                  >
                    {rec.action}
                  </code>
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: 12 }}
                  onClick={() => onExplain(rec)}
                >
                  Deep Explain & Dry-Run
                </button>
                {!isApplied && (
                  <button
                    className="btn btn-primary btn-sm"
                    style={{ fontSize: 12 }}
                    onClick={handleApplyNow}
                    disabled={isApplying}
                  >
                    {isApplying ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                    Apply Now
                  </button>
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

// ── Main Recommendations Page ───────────────────────────────────────────────
export default function RecommendationsPage() {
  const { provider, region, addNotification } = useAppStore()
  const queryClient = useQueryClient()

  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [priorityFilter, setPriorityFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [selectedExplainRec, setSelectedExplainRec] = useState<RecommendationItem | null>(null)
  const [isBatchApplying, setIsBatchApplying] = useState(false)

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['recommendations', provider, region],
    queryFn: () => fetchRecommendations({ provider, region }),
  })

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['recommendations'] })
    queryClient.invalidateQueries({ queryKey: ['scores'] })
    queryClient.invalidateQueries({ queryKey: ['liveMetrics'] })
  }

  const allRecs = data?.recommendations || []
  const openRecs = allRecs.filter((r) => r.status !== 'applied')
  const appliedRecs = allRecs.filter((r) => r.status === 'applied')

  const filtered = allRecs.filter((r) => {
    const matchCat = categoryFilter === 'all' || r.category === categoryFilter
    const matchPrio = priorityFilter === 'all' || r.priority === priorityFilter
    const matchStatus =
      statusFilter === 'all' ||
      (statusFilter === 'applied' && r.status === 'applied') ||
      (statusFilter === 'open' && r.status !== 'applied')
    return matchCat && matchPrio && matchStatus
  })

  const openSavings = openRecs.reduce((s, r) => s + r.estimated_monthly_savings_usd, 0)
  const openCarbon = openRecs.reduce((s, r) => s + r.estimated_carbon_reduction_pct, 0)
  const criticalOpenCount = openRecs.filter((r) => r.priority === 'critical').length

  const handleBatchApply = async (priority?: string) => {
    try {
      setIsBatchApplying(true)
      const res = await batchApplyRecommendations({ priority, dry_run: false })
      addNotification({
        title: 'Batch Optimizations Applied',
        body: `Applied ${res.applied_count} recommendations. Saved $${res.total_monthly_savings_usd}/mo. New score: ${res.new_score}/100.`,
        priority: 'high',
      })
      refreshAll()
    } catch (err: unknown) {
      console.error('Batch apply error', err)
    } finally {
      setIsBatchApplying(false)
    }
  }

  const categories = ['all', 'cost', 'performance', 'sustainability', 'security', 'reliability']
  const priorities = ['all', 'critical', 'high', 'medium', 'low']
  const statuses = [
    { id: 'all', label: `All (${allRecs.length})` },
    { id: 'open', label: `Open (${openRecs.length})` },
    { id: 'applied', label: `Applied (${appliedRecs.length})` },
  ]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1>AI Recommendations & Remediation</h1>
          <p className="text-secondary text-sm mt-1">
            {openRecs.length} actionable optimizations available ·
            {openSavings > 0 && <span className="text-emerald"> ${openSavings.toFixed(0)}/month potential savings</span>}
            {appliedRecs.length > 0 && (
              <span className="text-muted"> · {appliedRecs.length} already applied</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary btn-sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {/* Batch Apply Quick Action Banner */}
      {openRecs.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          className="card card-accent-emerald mb-4"
          style={{
            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(99, 102, 241, 0.05) 100%)',
            borderColor: 'rgba(16, 185, 129, 0.35)',
            padding: '16px 20px',
          }}
        >
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3">
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: 8,
                  background: 'var(--gradient-emerald)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff',
                }}
              >
                <Zap size={18} />
              </div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 14 }}>
                  Automate Infrastructure Optimization ({openRecs.length} Open)
                </div>
                <div className="text-secondary text-xs mt-0.5">
                  Execute AI-verified remediation workflows to capture ${openSavings.toFixed(0)}/mo FinOps savings & reduce carbon intensity.
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {criticalOpenCount > 0 && (
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: 'var(--red-400)' }}
                  onClick={() => handleBatchApply('critical')}
                  disabled={isBatchApplying}
                >
                  <AlertTriangle size={13} />
                  Apply All Critical ({criticalOpenCount})
                </button>
              )}
              <button
                className="btn btn-primary btn-sm"
                onClick={() => handleBatchApply()}
                disabled={isBatchApplying}
              >
                {isBatchApplying ? (
                  <>
                    <Loader2 size={14} className="animate-spin" />
                    Executing Batch Remediation...
                  </>
                ) : (
                  <>
                    <Sparkles size={14} />
                    Apply All Open ({openRecs.length})
                  </>
                )}
              </button>
            </div>
          </div>
        </motion.div>
      )}

      {/* Score banner */}
      {data && (
        <div
          className="card mb-4"
          style={{ padding: '12px 20px', borderColor: 'rgba(16,185,129,0.2)', background: 'rgba(16,185,129,0.04)' }}
        >
          <div className="flex items-center gap-4 flex-wrap justify-between">
            <div className="flex items-center gap-4">
              <div>
                <div className="text-xs text-muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Optimization Score
                </div>
                <div
                  style={{
                    fontSize: 32,
                    fontWeight: 900,
                    color: data.optimization_score >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)',
                  }}
                >
                  {data.optimization_score}/100
                </div>
              </div>
              <div className="flex gap-2 flex-wrap">
                {(['critical', 'high', 'medium', 'low'] as const).map((p) => {
                  const count = openRecs.filter((r) => r.priority === p).length
                  if (count === 0) return null
                  const c = p === 'critical' ? 'red' : p === 'high' ? 'amber' : p === 'medium' ? 'blue' : 'muted'
                  return (
                    <div key={p} className={`badge badge-${c}`}>
                      {count} {p} open
                    </div>
                  )
                })}
              </div>
            </div>

            {appliedRecs.length > 0 && (
              <div className="badge badge-emerald" style={{ padding: '6px 12px', fontSize: 12 }}>
                <CheckCircle2 size={14} />
                {appliedRecs.length} optimizations actively enforced
              </div>
            )}
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex gap-3 mb-4 flex-wrap items-center">
        {/* Status Tab (All / Open / Applied) */}
        <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--border)' }}>
          {statuses.map((st) => (
            <button
              key={st.id}
              className={`badge ${statusFilter === st.id ? 'badge-emerald' : 'badge-muted'}`}
              style={{ cursor: 'pointer', padding: '4px 10px', fontSize: 12, textTransform: 'none' }}
              onClick={() => setStatusFilter(st.id)}
            >
              {st.label}
            </button>
          ))}
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter size={13} color="var(--text-muted)" />
          <span className="text-xs text-muted">Category:</span>
          {categories.map((c) => (
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

        {/* Priority Pills */}
        <div className="flex items-center gap-1.5 ml-auto flex-wrap">
          <span className="text-xs text-muted">Priority:</span>
          {priorities.map((p) => (
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

      {/* Recommendation List */}
      {isLoading ? (
        <div className="flex-col gap-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="skeleton" style={{ height: 80 }} />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="text-secondary">No recommendations match the current filters.</div>
        </div>
      ) : (
        <div className="flex-col gap-3">
          {filtered.map((rec) => (
            <RecCard
              key={rec.id}
              rec={rec}
              onExplain={(r) => setSelectedExplainRec(r)}
              onApplySuccess={refreshAll}
            />
          ))}
        </div>
      )}

      {/* Explain & Apply Drawer/Modal */}
      <AnimatePresence>
        {selectedExplainRec && (
          <ExplainModal
            rec={selectedExplainRec}
            onClose={() => setSelectedExplainRec(null)}
            onApplySuccess={() => {
              refreshAll()
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}
