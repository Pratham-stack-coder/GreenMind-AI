import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  DollarSign, Zap, Leaf, Shield, Activity, Filter,
  ChevronDown, ChevronUp, RefreshCw, CheckCircle2, RotateCcw,
  Sparkles, Play, Check, AlertTriangle, X, Terminal,
  Info, Loader2, ArrowRight
} from 'lucide-react'
import { useAppStore } from '../store'
import {
  fetchRecommendations,
  fetchExplain,
  applyRecommendation,
  batchApplyRecommendations,
  simulateRecommendation,
  resetSimulation,
  rollbackRecommendation,
} from '../api/client'
import type { RecommendationItem, ApplyResponse } from '../types'

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
}

function ExplainModal({ rec, onClose }: ExplainModalProps) {
  const { provider, region, addNotification } = useAppStore()
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'preview' | 'live'>('preview')
  const [applying, setApplying] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [rollingBack, setRollingBack] = useState(false)
  const [applyResult, setApplyResult] = useState<ApplyResponse | null>(null)

  // Live action compatibility
  const isResize = rec.action === 'right_size_down' || rec.action === 'right_size'
  const isStopIdle = rec.action === 'terminate_idle' || rec.action === 'stop_idle'
  const isAwsProvider = (provider || '').toLowerCase() === 'aws'
  const isLiveSupported = isAwsProvider && (isResize || isStopIdle)

  // Extract EC2 instance ID if mentioned in evidence/description or default
  const defaultInstanceId = (() => {
    const text = `${rec.description} ${(rec.evidence || []).join(' ')}`
    const match = text.match(/\b(i-[0-9a-fA-F]{8,17})\b/)
    return match ? match[1] : 'i-0123456789abcdef0'
  })()

  const [resourceId, setResourceId] = useState(defaultInstanceId)
  const [targetInstanceType, setTargetInstanceType] = useState('t3.small')
  const [confirmedLive, setConfirmedLive] = useState(false)
  const [confirmInput, setConfirmInput] = useState('')

  const { data: explainData, isLoading: explainLoading } = useQuery({
    queryKey: ['explain', rec.id],
    queryFn: () => fetchExplain(rec.id),
  })

  const invalidateData = () => {
    queryClient.invalidateQueries({ queryKey: ['scores', provider, region] })
    queryClient.invalidateQueries({ queryKey: ['recommendations', provider, region] })
    queryClient.invalidateQueries({ queryKey: ['scores'] })
    queryClient.invalidateQueries({ queryKey: ['recommendations'] })
  }

  const handlePreview = async () => {
    try {
      setApplying(true)
      const res = await applyRecommendation(rec.id, { dry_run: true })
      setApplyResult(res)
      invalidateData()
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'The dry-run request failed.'
      setApplyResult({
        recommendation_id: rec.id,
        title: rec.title,
        status: 'failed',
        message: `Dry-run preview failed: ${message}`,
        steps_taken: [],
        applied_at: new Date().toISOString(),
        estimated_monthly_savings_usd: 0,
        estimated_carbon_reduction_pct: 0,
      })
    } finally {
      setApplying(false)
    }
  }

  const handleSimulate = async () => {
    try {
      setSimulating(true)
      const res = await simulateRecommendation(rec.id)
      setApplyResult(res)
      invalidateData()
      addNotification({
        title: 'Recommendation Simulated in Twin',
        body: res.message,
        priority: 'high',
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'The simulation request failed.'
      setApplyResult({
        recommendation_id: rec.id,
        title: rec.title,
        status: 'failed',
        message: `Simulation failed: ${message}`,
        steps_taken: [],
        applied_at: new Date().toISOString(),
        estimated_monthly_savings_usd: 0,
        estimated_carbon_reduction_pct: 0,
      })
    } finally {
      setSimulating(false)
    }
  }

  const handleLiveApply = async () => {
    if (!confirmedLive) {
      addNotification({
        title: 'Safeguard Authorization Required',
        body: 'Please check the authorization box before executing live mutations.',
        priority: 'high',
      })
      return
    }
    if (confirmInput.trim().toUpperCase() !== 'APPLY') {
      addNotification({
        title: 'Confirmation Keyword Required',
        body: 'Please type APPLY in the confirmation box to authorize live remediation.',
        priority: 'high',
      })
      return
    }
    if (!resourceId.trim() || !resourceId.trim().startsWith('i-')) {
      addNotification({
        title: 'Invalid Instance ID',
        body: 'Please enter a valid AWS EC2 instance identifier (e.g. i-0123456789abcdef0).',
        priority: 'high',
      })
      return
    }

    try {
      setApplying(true)
      const res = await applyRecommendation(rec.id, {
        dry_run: false,
        confirm_live: true,
        resource_id: resourceId.trim(),
        target_instance_type: isResize ? targetInstanceType.trim() : undefined,
        provider: 'aws',
        region: region || 'us-east-1',
      })
      setApplyResult(res)
      invalidateData()
      addNotification({
        title: res.verified ? 'Live Action Applied & Verified' : 'Live Action Completed',
        body: res.message,
        priority: 'high',
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'The live remediation request failed.'
      setApplyResult({
        recommendation_id: rec.id,
        title: rec.title,
        status: 'failed',
        message: `Live apply error: ${message}`,
        steps_taken: ['Pre-flight checks failed or cloud provider rejected the request'],
        applied_at: new Date().toISOString(),
        estimated_monthly_savings_usd: 0,
        estimated_carbon_reduction_pct: 0,
        verified: false,
        verification_status: 'failed',
      })
      addNotification({
        title: 'Live Remediation Failed',
        body: message,
        priority: 'critical',
      })
    } finally {
      setApplying(false)
    }
  }

  const handleRollback = async () => {
    try {
      setRollingBack(true)
      const res = await rollbackRecommendation(rec.id, { provider, region })
      setApplyResult(res)
      invalidateData()
      addNotification({
        title: 'Remediation Rolled Back',
        body: res.message,
        priority: 'high',
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'The rollback request failed.'
      addNotification({
        title: 'Rollback Failed',
        body: message,
        priority: 'critical',
      })
    } finally {
      setRollingBack(false)
    }
  }

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 10 }}
        className="modal-card"
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
            {rec.status === 'applied' && (
              <span className="badge badge-emerald" style={{ fontSize: 10 }}>
                <CheckCircle2 size={11} /> Applied
              </span>
            )}
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
            <div className="card" style={{ padding: '12px 16px', background: 'var(--bg-hover)' }}>
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
            <div className="grid-2 gap-3">
              <div className="card" style={{ padding: '12px 16px', background: 'var(--bg-hover)' }}>
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

            {/* Quantitative Telemetry Comparison Table */}
            {explainData?.data_evidence && explainData.data_evidence.length > 0 && (
              <div className="card" style={{ padding: '12px 16px', background: 'var(--bg-hover)' }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Activity size={13} color="var(--blue-400)" />
                  Quantitative Telemetry Evidence (Observed vs Threshold)
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border)', color: 'var(--text-muted)', textAlign: 'left' }}>
                        <th style={{ padding: '6px 8px', fontWeight: 600 }}>Metric</th>
                        <th style={{ padding: '6px 8px', fontWeight: 600 }}>Observed Value</th>
                        <th style={{ padding: '6px 8px', fontWeight: 600 }}>Threshold</th>
                        <th style={{ padding: '6px 8px', fontWeight: 600, textAlign: 'right' }}>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {explainData.data_evidence.map((ev, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                          <td style={{ padding: '6px 8px', color: 'var(--text-primary)', fontWeight: 500 }}>
                            {ev.metric || ev.key || 'Metric'}
                          </td>
                          <td style={{ padding: '6px 8px', fontFamily: 'monospace', color: 'var(--amber-400)' }}>
                            {ev.observed || ev.value || 'N/A'}
                          </td>
                          <td style={{ padding: '6px 8px', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                            {ev.threshold || 'N/A'}
                          </td>
                          <td style={{ padding: '6px 8px', textAlign: 'right' }}>
                            <span className={`badge ${ev.status === 'FLAGGED' ? 'badge-red' : 'badge-emerald'}`} style={{ fontSize: 10, padding: '2px 6px' }}>
                              {ev.status || 'EVALUATED'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Steps to Implement */}
            {explainData?.steps_to_implement && explainData.steps_to_implement.length > 0 && (
              <div className="card" style={{ padding: '12px 16px', background: 'var(--bg-hover)' }}>
                <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Terminal size={13} color="var(--emerald-400)" />
                  Suggested Implementation Steps
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {explainData.steps_to_implement.map((step, idx) => (
                    <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: 12 }}>
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        minWidth: 18,
                        height: 18,
                        borderRadius: '50%',
                        background: 'rgba(16, 185, 129, 0.15)',
                        color: 'var(--emerald-400)',
                        fontSize: 10,
                        fontWeight: 700,
                      }}>
                        {idx + 1}
                      </span>
                      <span className="text-secondary" style={{ lineHeight: 1.4 }}>{step}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Mode Selector Tabs */}
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                type="button"
                className={`btn btn-sm ${activeTab === 'preview' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('preview')}
                style={{ flex: 1, justifyContent: 'center' }}
              >
                <Play size={13} />
                Preview & Simulation
              </button>
              <button
                type="button"
                className={`btn btn-sm ${activeTab === 'live' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('live')}
                style={{
                  flex: 1,
                  justifyContent: 'center',
                  borderColor: activeTab === 'live' ? 'var(--emerald-600)' : 'rgba(217, 119, 6, 0.4)',
                }}
              >
                <Shield size={13} />
                Live Cloud Remediation
              </button>
            </div>

            {/* Live Action Configuration Area (when activeTab === 'live') */}
            {activeTab === 'live' && (
              <div
                className="card"
                style={{
                  padding: '14px 16px',
                  background: '#FFFBEB',
                  borderColor: '#FDE68A',
                }}
              >
                <div className="flex items-center gap-2 mb-2">
                  <Shield size={15} color="var(--amber-500)" />
                  <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                    Production Cloud Remediation (AWS EC2)
                  </span>
                  <span className="badge badge-amber" style={{ marginLeft: 'auto', fontSize: 10 }}>
                    Safeguards Active
                  </span>
                </div>

                {!isAwsProvider ? (
                  <div className="text-xs text-secondary mb-2" style={{ lineHeight: 1.5 }}>
                    <strong>Provider Safeguard Notice:</strong> Direct API mutations are currently automated and verified for <strong>AWS EC2</strong>.
                    Your active scope is set to <strong>{provider.toUpperCase()}</strong>. To prevent unverified operations, live mutations on {provider.toUpperCase()} are blocked.
                    Please test using Digital Twin simulation or apply changes manually using the implementation steps above.
                  </div>
                ) : !isLiveSupported ? (
                  <div className="text-xs text-secondary mb-2" style={{ lineHeight: 1.5 }}>
                    <strong>Action Limitation:</strong> Direct automated mutation for action <code>{rec.action}</code> is not supported.
                    GreenMind AI provides verified automated execution for stopping idle instances (<code>terminate_idle</code>) and downsizing compute tiers (<code>right_size_down</code>).
                    Please review the suggested implementation steps above.
                  </div>
                ) : (
                  <div className="flex-col gap-3">
                    <p className="text-xs text-secondary" style={{ lineHeight: 1.5 }}>
                      Automated pre-flight checks verify instance running status, prohibit ephemeral instance-store data loss, reject spot instance disruptions, and wait for AWS API confirmation before updating scores.
                    </p>

                    <div className="grid-2 gap-3">
                      <div>
                        <label className="text-xs font-semibold text-primary block mb-1">
                          Target EC2 Instance ID:
                        </label>
                        <input
                          type="text"
                          value={resourceId}
                          onChange={(e) => setResourceId(e.target.value)}
                          placeholder="i-0123456789abcdef0"
                          className="font-mono text-xs"
                          style={{
                            width: '100%',
                            padding: '6px 10px',
                            borderRadius: 6,
                            border: '1px solid var(--border)',
                            background: '#FFFFFF',
                          }}
                        />
                      </div>

                      {isResize ? (
                        <div>
                          <label className="text-xs font-semibold text-primary block mb-1">
                            Target Downsized Instance Type:
                          </label>
                          <select
                            value={targetInstanceType}
                            onChange={(e) => setTargetInstanceType(e.target.value)}
                            className="font-mono text-xs"
                            style={{
                              width: '100%',
                              padding: '6px 10px',
                              borderRadius: 6,
                              border: '1px solid var(--border)',
                              background: '#FFFFFF',
                            }}
                          >
                            <option value="t3.nano">t3.nano (2 vCPU, 0.5 GiB)</option>
                            <option value="t3.micro">t3.micro (2 vCPU, 1 GiB)</option>
                            <option value="t3.small">t3.small (2 vCPU, 2 GiB)</option>
                            <option value="t3.medium">t3.medium (2 vCPU, 4 GiB)</option>
                            <option value="t3.large">t3.large (2 vCPU, 8 GiB)</option>
                            <option value="c5.large">c5.large (2 vCPU, 4 GiB)</option>
                          </select>
                        </div>
                      ) : (
                        <div>
                          <label className="text-xs font-semibold text-primary block mb-1">
                            Operation Mode:
                          </label>
                          <div
                            className="text-xs font-mono"
                            style={{
                              padding: '6px 10px',
                              borderRadius: 6,
                              background: 'var(--bg-hover)',
                              border: '1px solid var(--border)',
                            }}
                          >
                            Safe Stop Idle Instance (EBS Preserved)
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Safeguard Confirmation */}
                    <div
                      className="p-3 rounded"
                      style={{ background: '#FFFFFF', border: '1px solid #FCD34D' }}
                    >
                      <label className="flex items-start gap-2 mb-2" style={{ cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={confirmedLive}
                          onChange={(e) => setConfirmedLive(e.target.checked)}
                          style={{ marginTop: 2, accentColor: 'var(--emerald-600)' }}
                        />
                        <span className="text-xs text-primary" style={{ lineHeight: 1.4 }}>
                          <strong>Explicit User Approval:</strong> I authorize GreenMind AI to modify live AWS instance <code>{resourceId || 'selected'}</code> in region <code>{region}</code>.
                        </span>
                      </label>

                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-muted" style={{ whiteSpace: 'nowrap' }}>
                          Type <strong>APPLY</strong> to authorize:
                        </span>
                        <input
                          type="text"
                          value={confirmInput}
                          onChange={(e) => setConfirmInput(e.target.value)}
                          placeholder="APPLY"
                          className="font-mono text-xs"
                          style={{
                            width: 90,
                            padding: '4px 8px',
                            borderRadius: 4,
                            border: '1px solid var(--border)',
                            textAlign: 'center',
                            textTransform: 'uppercase',
                          }}
                        />
                        <button
                          className="btn btn-primary btn-sm"
                          onClick={handleLiveApply}
                          disabled={
                            applying ||
                            !confirmedLive ||
                            confirmInput.trim().toUpperCase() !== 'APPLY' ||
                            !resourceId.trim()
                          }
                          style={{ marginLeft: 'auto' }}
                        >
                          {applying ? (
                            <>
                              <Loader2 size={13} className="animate-spin" />
                              Executing & Verifying...
                            </>
                          ) : (
                            <>
                              <Zap size={13} />
                              Apply & Verify on AWS
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Execution / Dry Run / Simulation Result Console */}
            {applyResult && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="card"
                style={{
                  background: '#F9FAFB',
                  borderColor:
                    applyResult.status === 'failed'
                      ? 'var(--red-500)'
                      : applyResult.status === 'applied' && applyResult.verified
                      ? 'var(--emerald-600)'
                      : 'var(--border)',
                  padding: 14,
                }}
              >
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <Terminal
                    size={14}
                    color={
                      applyResult.status === 'failed'
                        ? 'var(--red-600)'
                        : 'var(--emerald-600)'
                    }
                  />
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {applyResult.status === 'failed'
                      ? 'Action Failed'
                      : applyResult.status === 'rolled_back'
                      ? 'Rollback Executed & Verified'
                      : applyResult.verified
                      ? 'Live Action Verified on Cloud Provider'
                      : applyResult.status === 'simulated'
                      ? 'Digital Twin Simulation Applied'
                      : applyResult.dry_run
                      ? 'Dry-Run Preview Complete'
                      : 'Operation Completed (Pending Verification)'}
                  </span>
                  <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
                    {applyResult.verified !== undefined && (
                      <span
                        className={`badge ${applyResult.verified ? 'badge-emerald' : 'badge-amber'}`}
                        style={{ fontSize: 10 }}
                      >
                        {applyResult.verified ? <CheckCircle2 size={11} /> : <AlertTriangle size={11} />}
                        {applyResult.verified ? 'Provider Verified' : 'Pending Verification'}
                      </span>
                    )}
                    <span
                      className={`badge ${
                        applyResult.status === 'failed'
                          ? 'badge-red'
                          : applyResult.status === 'applied'
                          ? 'badge-emerald'
                          : applyResult.status === 'simulated'
                          ? 'badge-emerald'
                          : 'badge-muted'
                      }`}
                    >
                      {applyResult.status}
                    </span>
                  </div>
                </div>
                <div className="text-xs text-secondary mb-2">{applyResult.message}</div>

                {/* Resource State Transition */}
                {applyResult.previous_state && applyResult.current_state && (
                  <div
                    className="p-2.5 rounded mb-3 flex items-center justify-between flex-wrap gap-2 text-xs"
                    style={{ background: '#F0FDF4', border: '1px solid #BBF7D0' }}
                  >
                    <div>
                      <span className="font-semibold text-primary">Target: </span>
                      <code className="text-emerald font-mono">{applyResult.resource_id}</code>
                    </div>
                    <div className="flex items-center gap-2 font-mono">
                      <span className="badge badge-muted">{applyResult.previous_state}</span>
                      <ArrowRight size={12} />
                      <span className="badge badge-emerald">{applyResult.current_state}</span>
                    </div>
                  </div>
                )}

                {/* Score Projection Details */}
                {(applyResult.baseline_score !== undefined || applyResult.new_score !== undefined || applyResult.projected_score !== undefined) && (
                  <div
                    className="p-2.5 rounded mb-3 flex items-center justify-between flex-wrap gap-2"
                    style={{ background: '#F0FDF4', border: '1px solid #BBF7D0' }}
                  >
                    <div>
                      <div className="text-xs font-semibold text-emerald">
                        {applyResult.verified ? 'Verified Optimization Score Recalculation' : 'Projected Score Impact'}
                      </div>
                      <div className="text-xs text-secondary">
                        Baseline: {applyResult.baseline_score ?? 70}/100 → {applyResult.verified ? 'Verified Score' : 'Projected'}:{' '}
                        {applyResult.new_score ?? applyResult.projected_score ?? 70}/100
                      </div>
                    </div>
                    <span
                      className={`badge ${
                        (applyResult.score_delta ?? 0) > 0
                          ? 'badge-emerald'
                          : (applyResult.score_delta ?? 0) < 0
                          ? 'badge-red'
                          : 'badge-muted'
                      }`}
                      style={{ fontSize: 11 }}
                    >
                      {(applyResult.score_delta ?? 0) > 0 ? `+${applyResult.score_delta}` : applyResult.score_delta} pts
                    </span>
                  </div>
                )}

                {/* Assumptions */}
                {applyResult.assumptions && applyResult.assumptions.length > 0 && (
                  <div className="mb-2 p-2 rounded" style={{ background: 'var(--bg-hover)', fontSize: 11 }}>
                    <div className="text-muted font-semibold mb-1">Assumptions & Score Dimensions:</div>
                    <ul style={{ paddingLeft: 16, margin: 0 }}>
                      {applyResult.assumptions.map((asm, idx) => (
                        <li key={idx} className="text-secondary">{asm}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Execution Steps */}
                {applyResult.steps_taken && applyResult.steps_taken.length > 0 && (
                  <div className="flex-col gap-1 mb-2">
                    {applyResult.steps_taken.map((st, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs font-mono" style={{ color: 'var(--emerald-600)' }}>
                        <Check size={12} /> {st}
                      </div>
                    ))}
                  </div>
                )}

                {/* Direct Rollback in Console */}
                {applyResult.status === 'applied' && !applyResult.dry_run && (
                  <div className="flex justify-end mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handleRollback}
                      disabled={rollingBack}
                      style={{ color: 'var(--amber-600)', borderColor: 'var(--amber-300)' }}
                    >
                      {rollingBack ? (
                        <>
                          <Loader2 size={12} className="animate-spin" />
                          Rolling back on cloud provider...
                        </>
                      ) : (
                        <>
                          <RotateCcw size={12} />
                          Rollback This Cloud Action
                        </>
                      )}
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </div>
        )}

        {/* Modal Footer Controls */}
        <div className="modal-footer-row">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">
              Scope: <strong>{provider.toUpperCase()}</strong> ({region})
            </span>
          </div>

          <div className="modal-footer-buttons">
            <button className="btn btn-secondary btn-sm" onClick={onClose}>
              Close
            </button>
            {activeTab === 'preview' && (
              <>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={handlePreview}
                  disabled={applying || simulating || rec.status === 'applied'}
                >
                  {applying ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      Previewing...
                    </>
                  ) : (
                    <>
                      <Play size={13} />
                      Preview (Dry-Run)
                    </>
                  )}
                </button>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleSimulate}
                  disabled={applying || simulating || rec.status === 'applied'}
                >
                  {simulating ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      Simulating...
                    </>
                  ) : (
                    <>
                      <Sparkles size={13} />
                      Simulate in Twin
                    </>
                  )}
                </button>
              </>
            )}
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
}: {
  rec: RecommendationItem
  onExplain: (rec: RecommendationItem) => void
}) {
  const { provider, region, addNotification } = useAppStore()
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState(false)
  const [isApplying, setIsApplying] = useState(false)
  const [isSimulating, setIsSimulating] = useState(false)

  const isApplied = rec.status === 'applied'
  const isSimulated = rec.status === 'simulated'
  const color = categoryColors[rec.category] || 'muted'
  const prioColor =
    rec.priority === 'critical' ? 'red' : rec.priority === 'high' ? 'amber' : rec.priority === 'medium' ? 'blue' : 'muted'

  const invalidateData = () => {
    queryClient.invalidateQueries({ queryKey: ['scores', provider, region] })
    queryClient.invalidateQueries({ queryKey: ['recommendations', provider, region] })
    queryClient.invalidateQueries({ queryKey: ['scores'] })
    queryClient.invalidateQueries({ queryKey: ['recommendations'] })
  }

  const handleApplyNow = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      setIsApplying(true)
      const res = await applyRecommendation(rec.id, { dry_run: true })
      invalidateData()
      addNotification({
        title: 'Dry-Run Preview Ready',
        body: res.message,
        priority: rec.priority === 'critical' ? 'critical' : 'high',
      })
    } catch (err: unknown) {
      console.error('Failed to prepare recommendation preview', err)
      addNotification({
        title: 'Dry-Run Preview Failed',
        body: err instanceof Error ? err.message : 'The dry-run request failed.',
        priority: 'high',
      })
    } finally {
      setIsApplying(false)
    }
  }

  const handleSimulateNow = async (e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      setIsSimulating(true)
      const res = await simulateRecommendation(rec.id)
      invalidateData()
      addNotification({
        title: 'Simulated in Digital Twin',
        body: res.message,
        priority: 'medium',
      })
    } catch (err: unknown) {
      console.error('Failed to simulate recommendation', err)
      addNotification({
        title: 'Simulation Failed',
        body: err instanceof Error ? err.message : 'The simulation request failed.',
        priority: 'high',
      })
    } finally {
      setIsSimulating(false)
    }
  }

  const handleRollbackNow = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm(`Are you sure you want to rollback the changes for "${rec.title}" on the connected cloud provider?`)) {
      return
    }
    try {
      setIsApplying(true)
      const res = await rollbackRecommendation(rec.id, { provider, region })
      invalidateData()
      addNotification({
        title: 'Action Rolled Back',
        body: res.message,
        priority: 'high',
      })
    } catch (err: unknown) {
      console.error('Failed to rollback recommendation', err)
      addNotification({
        title: 'Rollback Failed',
        body: err instanceof Error ? err.message : 'The rollback request failed.',
        priority: 'critical',
      })
    } finally {
      setIsApplying(false)
    }
  }

  return (
    <motion.div
      className={`card priority-${rec.priority}`}
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        borderColor: isApplied ? 'rgba(22, 163, 74, 0.4)' : isSimulated ? 'rgba(22, 163, 74, 0.4)' : undefined,
        background: isApplied
          ? '#F0FDF4'
          : isSimulated
          ? '#F0FDF4'
          : undefined,
      }}
    >
      <div
        className="rec-card-header"
        onClick={() => setExpanded((v) => !v)}
      >
        <div className="rec-card-meta">
          <div className={`badge badge-${color}`}>
            {categoryIcons[rec.category]}
            {rec.category}
          </div>
          <span className={`badge badge-${prioColor}`}>{rec.priority}</span>
          {isApplied && (
            <span className="badge badge-emerald" style={{ fontSize: 10, padding: '1px 6px' }}>
              <CheckCircle2 size={11} /> Applied & Verified
            </span>
          )}
          {isSimulated && (
            <span className="badge badge-emerald" style={{ fontSize: 10, padding: '1px 6px' }}>
              <Sparkles size={11} /> Simulated
            </span>
          )}
          <div className="rec-card-mobile-toggle">
            {expanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
          </div>
        </div>

        <div className="rec-card-info">
          <div className="rec-card-title">{rec.title}</div>
          <div className="text-secondary text-xs mt-0.5">{rec.impact_summary}</div>
        </div>

        <div className="rec-card-actions">
          <div className="rec-card-metrics">
            {rec.estimated_monthly_savings_usd > 0 && (
              <span className="text-emerald font-mono" style={{ fontWeight: 700, fontSize: 13 }}>
                ${rec.estimated_monthly_savings_usd.toFixed(0)}/mo
              </span>
            )}
            {rec.estimated_carbon_reduction_pct > 0 && (
              <span className="text-emerald text-xs">-{rec.estimated_carbon_reduction_pct.toFixed(0)}% CO₂</span>
            )}
          </div>

          {/* Quick Actions */}
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
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 10px', fontSize: 12 }}
                onClick={handleApplyNow}
                disabled={isApplying || isSimulating}
              >
                {isApplying ? <Loader2 size={12} className="animate-spin" /> : <Play size={12} />}
                Preview
              </button>
              {!isSimulated && (
                <button
                  className="btn btn-primary btn-sm"
                  style={{ padding: '4px 12px', fontSize: 12 }}
                  onClick={handleSimulateNow}
                  disabled={isApplying || isSimulating}
                >
                  {isSimulating ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                  Simulate
                </button>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
              <button
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 10px', fontSize: 12 }}
                onClick={() => onExplain(rec)}
              >
                Inspect Audit
              </button>
              <button
                className="btn btn-secondary btn-sm"
                style={{ padding: '4px 10px', fontSize: 12, color: 'var(--amber-600)', borderColor: 'var(--amber-300)' }}
                onClick={handleRollbackNow}
                disabled={isApplying}
                title="Rollback this applied recommendation on connected cloud provider"
              >
                {isApplying ? <Loader2 size={12} className="animate-spin" /> : <RotateCcw size={12} />}
                Rollback
              </button>
            </div>
          )}

          <div className="rec-card-desktop-toggle">
            {expanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
          </div>
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
                    Recorded Action Details
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
                      background: '#DCFCE7',
                      padding: '1px 6px',
                      borderRadius: 4,
                      color: 'var(--emerald-700)',
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
                {!isApplied && !isSimulated && (
                  <button
                    className="btn btn-primary btn-sm"
                    style={{ fontSize: 12 }}
                    onClick={handleSimulateNow}
                    disabled={isSimulating}
                  >
                    {isSimulating ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                    Simulate in Twin
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
  const [isResettingSim, setIsResettingSim] = useState(false)

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
  const appliedRecs = allRecs.filter((r) => r.status === 'applied')
  const simulatedRecs = allRecs.filter((r) => r.status === 'simulated')
  const openRecs = allRecs.filter((r) => r.status !== 'applied' && r.status !== 'simulated')

  const filtered = allRecs.filter((r) => {
    const matchCat = categoryFilter === 'all' || r.category === categoryFilter
    const matchPrio = priorityFilter === 'all' || r.priority === priorityFilter
    const matchStatus =
      statusFilter === 'all' ||
      (statusFilter === 'applied' && r.status === 'applied') ||
      (statusFilter === 'simulated' && r.status === 'simulated') ||
      (statusFilter === 'open' && r.status !== 'applied' && r.status !== 'simulated')
    return matchCat && matchPrio && matchStatus
  })

  const openSavings = openRecs.reduce((s, r) => s + r.estimated_monthly_savings_usd, 0)
  const criticalOpenCount = openRecs.filter((r) => r.priority === 'critical').length

  const handleResetSim = async () => {
    try {
      setIsResettingSim(true)
      await resetSimulation()
      refreshAll()
      addNotification({
        title: 'Simulation Reset',
        body: 'Digital Twin simulation state cleared; restored to baseline.',
        priority: 'medium',
      })
    } catch (err: unknown) {
      console.error('Failed to reset simulation', err)
    } finally {
      setIsResettingSim(false)
    }
  }

  const handleBatchApply = async (priority?: string) => {
    try {
      setIsBatchApplying(true)
      const res = await batchApplyRecommendations({ priority, dry_run: true })
      addNotification({
        title: 'Dry-Run Previews Ready',
        body: `Prepared ${res.results.length} previews. No cloud resources were changed.`,
        priority: 'high',
      })
      refreshAll()
    } catch (err: unknown) {
      console.error('Batch preview error', err)
      addNotification({
        title: 'Batch Dry-Run Failed',
        body: err instanceof Error ? err.message : 'The batch preview request failed.',
        priority: 'high',
      })
    } finally {
      setIsBatchApplying(false)
    }
  }

  const categories = ['all', 'cost', 'performance', 'sustainability', 'security', 'reliability']
  const priorities = ['all', 'critical', 'high', 'medium', 'low']
  const statuses = [
    { id: 'all', label: `All (${allRecs.length})` },
    { id: 'open', label: `Open (${openRecs.length})` },
    { id: 'simulated', label: `Simulated (${simulatedRecs.length})` },
    { id: 'applied', label: `Applied (${appliedRecs.length})` },
  ]

  return (
    <div className="animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1>AI Recommendations & Twin Simulation</h1>
          <p className="text-secondary text-sm mt-1">
            {openRecs.length} actionable optimizations available ·
            {openSavings > 0 && <span className="text-emerald"> ${openSavings.toFixed(0)}/month potential savings</span>}
            {simulatedRecs.length > 0 && (
              <span className="text-emerald"> · {simulatedRecs.length} simulated in twin</span>
            )}
            {appliedRecs.length > 0 && (
              <span className="text-muted"> · {appliedRecs.length} recorded applied</span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          {simulatedRecs.length > 0 && (
            <button
              className="btn btn-secondary btn-sm"
              onClick={handleResetSim}
              disabled={isResettingSim}
              title="Reset Twin Simulation"
            >
              <RotateCcw size={14} className={isResettingSim ? 'animate-spin' : ''} />
              Reset Simulation
            </button>
          )}
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
            background: '#F0FDF4',
            borderColor: 'rgba(22, 163, 74, 0.3)',
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
                  background: 'var(--emerald-600)',
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
                  Preview Optimization Recommendations ({openRecs.length} Open)
                </div>
                <div className="text-secondary text-xs mt-0.5">
                  Review estimated savings of ${openSavings.toFixed(0)}/mo and carbon impact. Dry runs do not modify cloud resources.
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
                  Dry-Run Critical ({criticalOpenCount})
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
                    Preparing dry-run previews...
                  </>
                ) : (
                  <>
                    <Sparkles size={14} />
                    Dry-Run All Open ({openRecs.length})
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
                {appliedRecs.length} recommendations marked as applied
              </div>
            )}
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="rec-filters-container">
        {/* Status Tab (All / Open / Applied) */}
        <div className="rec-filter-group" style={{ background: 'var(--bg-hover)', border: '1px solid var(--border)', borderRadius: 8, padding: 4 }}>
          {statuses.map((st) => (
            <button
              key={st.id}
              className={`badge ${statusFilter === st.id ? 'badge-emerald' : 'badge-muted'}`}
              style={{ cursor: 'pointer', padding: '5px 10px', fontSize: 12, textTransform: 'none' }}
              onClick={() => setStatusFilter(st.id)}
            >
              {st.label}
            </button>
          ))}
        </div>

        {/* Category Pills */}
        <div className="rec-filter-group">
          <Filter size={13} color="var(--text-muted)" style={{ flexShrink: 0 }} />
          <span className="text-xs text-muted" style={{ flexShrink: 0 }}>Category:</span>
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
        <div className="rec-filter-group">
          <span className="text-xs text-muted" style={{ flexShrink: 0 }}>Priority:</span>
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
          />
        )}
      </AnimatePresence>
    </div>
  )
}
