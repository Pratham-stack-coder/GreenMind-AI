import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Bot, Play, ChevronDown, ChevronUp, CheckCircle, Clock, Loader2, Circle } from 'lucide-react'
import { useAppStore } from '../store'
import { runAgents, fetchAgentStatus } from '../api/client'
import type { AgentRunResponse, AgentResult } from '../types'

const agentColors: Record<string, string> = {
  CostAgent: 'amber', PerformanceAgent: 'blue', SustainabilityAgent: 'emerald',
  SecurityAgent: 'red', ReliabilityAgent: 'indigo',
}

const AGENT_ORDER = ['CostAgent', 'PerformanceAgent', 'SustainabilityAgent', 'SecurityAgent', 'ReliabilityAgent']

function AgentCard({ agent }: { agent: AgentResult }) {
  const [expanded, setExpanded] = useState(false)
  const color = agentColors[agent.agent] || 'muted'
  const prioColors: Record<string, string> = { critical: 'red', high: 'amber', medium: 'blue', low: 'muted' }

  return (
    <motion.div className={`card`} layout initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
      <div className="agent-card-header" onClick={() => setExpanded(v => !v)}>
        <div className="agent-card-meta">
          <div className={`badge badge-${color}`}>
            <Bot size={12} />
            {agent.agent}
          </div>
          <span className="badge badge-emerald">{agent.recommendations.length} recs</span>
          <div className="agent-card-mobile-toggle">
            {expanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
          </div>
        </div>

        <div className="agent-card-info">
          <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
            {agent.findings[0] || 'Analysis complete'}
          </div>
        </div>

        <div className="agent-card-score-area">
          <div style={{ textAlign: 'right' }}>
            <div className="text-xs text-muted">Domain Score</div>
            <div style={{ fontWeight: 800, fontSize: 20, color: agent.score >= 70 ? 'var(--emerald-400)' : agent.score >= 50 ? 'var(--amber-400)' : 'var(--red-400)' }}>
              {agent.score}
            </div>
          </div>
          <div className="agent-card-desktop-toggle">
            {expanded ? <ChevronUp size={16} color="var(--text-muted)" /> : <ChevronDown size={16} color="var(--text-muted)" />}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} style={{ overflow: 'hidden' }}>
            <div className="divider" />
            <div className="mb-3">
              <div className="text-xs text-muted mb-2" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Findings</div>
              {agent.findings.map((f, i) => (
                <div key={i} className="flex items-start gap-2 text-sm text-secondary mb-1">
                  <CheckCircle size={12} color="var(--emerald-400)" style={{ flexShrink: 0, marginTop: 3 }} />
                  {f}
                </div>
              ))}
            </div>
            {agent.recommendations.length > 0 && (
              <div>
                <div className="text-xs text-muted mb-2" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Recommendations</div>
                <div className="flex-col gap-2">
                  {agent.recommendations.map(r => (
                    <div key={r.id} className={`card priority-${r.priority}`} style={{ padding: '10px 14px' }}>
                      <div className="flex items-center justify-between">
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{r.title}</div>
                          <div className="text-xs text-secondary mt-1">{r.impact_summary}</div>
                        </div>
                        <span className={`badge badge-${prioColors[r.priority] || 'muted'}`}>{r.priority}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

/** Live orchestration timeline shown while agents are running */
function AgentTimeline({ isPending, doneAgents }: { isPending: boolean, doneAgents: string[] }) {
  return (
    <div className="card mb-4" style={{ padding: '20px 24px' }}>
      <div className="text-xs text-muted mb-4" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        Orchestration Pipeline
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {AGENT_ORDER.map((agentName, idx) => {
          const isDone = doneAgents.includes(agentName)
          const isRunning = isPending && !isDone && doneAgents.length === idx
          const isPendingStep = !isDone && !isRunning
          const color = agentColors[agentName] || 'muted'
          const shortName = agentName.replace('Agent', '')

          return (
            <div key={agentName} style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
              {/* Connector line + dot */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 20 }}>
                <motion.div
                  animate={isDone ? { scale: [1, 1.3, 1], backgroundColor: ['#10b981', '#34d399', '#10b981'] } : {}}
                  transition={{ duration: 0.5 }}
                  style={{
                    width: 20, height: 20, borderRadius: '50%', flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: isDone
                      ? 'var(--emerald-500)'
                      : isRunning
                        ? 'rgba(99,102,241,0.3)'
                        : 'rgba(255,255,255,0.06)',
                    border: `2px solid ${isDone ? 'var(--emerald-500)' : isRunning ? 'var(--indigo-400)' : 'var(--border)'}`,
                    transition: 'all 0.4s ease',
                  }}
                >
                  {isDone && <CheckCircle size={11} color="#fff" />}
                  {isRunning && <Loader2 size={11} color="var(--indigo-400)" className="animate-spin" />}
                  {isPendingStep && <Circle size={8} color="var(--text-muted)" />}
                </motion.div>
                {idx < AGENT_ORDER.length - 1 && (
                  <div style={{
                    width: 2, height: 28, flexShrink: 0,
                    background: isDone ? 'var(--emerald-500)' : 'var(--border)',
                    transition: 'background 0.4s ease',
                  }} />
                )}
              </div>

              {/* Label */}
              <div style={{ paddingTop: 1, paddingBottom: idx < AGENT_ORDER.length - 1 ? 20 : 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: isDone ? 600 : 500,
                  color: isDone ? 'var(--text-primary)' : isRunning ? 'var(--indigo-400)' : 'var(--text-muted)',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}>
                  <span className={`badge badge-${isDone ? 'emerald' : isRunning ? 'indigo' : 'muted'}`} style={{ fontSize: 10 }}>
                    {isDone ? '✓' : isRunning ? '…' : idx + 1}
                  </span>
                  {shortName}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                  {isDone ? 'Analysis complete' : isRunning ? 'Running analysis…' : 'Waiting'}
                </div>
              </div>
            </div>
          )
        })}

        {/* Orchestrator */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, marginTop: 8 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 20 }}>
            <div style={{ width: 2, height: 12, background: doneAgents.length === AGENT_ORDER.length ? 'var(--emerald-500)' : 'var(--border)' }} />
            <div style={{
              width: 20, height: 20, borderRadius: 6, flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: doneAgents.length === AGENT_ORDER.length ? 'var(--gradient-emerald)' : 'rgba(255,255,255,0.06)',
              border: `2px solid ${doneAgents.length === AGENT_ORDER.length ? 'var(--emerald-500)' : 'var(--border)'}`,
            }}>
              <Bot size={10} color={doneAgents.length === AGENT_ORDER.length ? '#fff' : 'var(--text-muted)'} />
            </div>
          </div>
          <div style={{ paddingTop: 14 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: doneAgents.length === AGENT_ORDER.length ? 'var(--emerald-400)' : 'var(--text-muted)' }}>
              Orchestrator → Unified Plan
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default function AgentsPage() {
  const { provider, region } = useAppStore()
  const [result, setResult] = useState<AgentRunResponse | null>(null)
  const [doneAgents, setDoneAgents] = useState<string[]>([])
  const timelineRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const { data: lastRun } = useQuery({
    queryKey: ['agentStatus'],
    queryFn: fetchAgentStatus,
  })

  const { mutate: run, isPending } = useMutation({
    mutationFn: () => runAgents({ provider, region }),
    onMutate: () => {
      setDoneAgents([])
      // Simulate agent-by-agent progress (sequential, ~800ms each)
      let i = 0
      timelineRef.current = setInterval(() => {
        if (i < AGENT_ORDER.length) {
          setDoneAgents(prev => [...prev, AGENT_ORDER[i]])
          i++
        } else {
          if (timelineRef.current) clearInterval(timelineRef.current)
        }
      }, 900)
    },
    onSuccess: (data) => {
      setResult(data)
      setDoneAgents(AGENT_ORDER) // ensure all shown as done
      if (timelineRef.current) clearInterval(timelineRef.current)
    },
    onError: () => {
      if (timelineRef.current) clearInterval(timelineRef.current)
    },
  })

  useEffect(() => () => { if (timelineRef.current) clearInterval(timelineRef.current) }, [])

  const display = result || lastRun

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <h1>Multi-Agent AI</h1>
          <p className="text-secondary text-sm mt-1">5 specialized agents collaborate to produce unified optimization plans</p>
        </div>
        <button className="btn btn-primary" onClick={() => run()} disabled={isPending} id="run-agents-btn">
          {isPending ? (
            <><Loader2 size={14} className="animate-spin" /> Analyzing…</>
          ) : (
            <><Play size={14} /> Run Full Analysis</>
          )}
        </button>
      </div>

      {/* Live orchestration timeline */}
      {(isPending || (display && doneAgents.length > 0)) && (
        <AgentTimeline isPending={isPending} doneAgents={doneAgents} />
      )}

      {/* Static architecture diagram when not running and no history */}
      {!isPending && doneAgents.length === 0 && (
        <div className="card mb-4" style={{ padding: '16px 20px' }}>
          <div className="text-xs text-muted mb-3" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Agent Architecture</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            {AGENT_ORDER.map(a => (
              <div key={a} className={`badge badge-${agentColors[a] || 'muted'}`}>
                <Bot size={11} /> {a.replace('Agent', '')}
              </div>
            ))}
            <div className="text-secondary" style={{ fontSize: 18, display: 'flex', alignItems: 'center', padding: '0 4px' }}>→</div>
            <div className="badge badge-emerald">Orchestrator</div>
            <div className="text-secondary" style={{ fontSize: 18, display: 'flex', alignItems: 'center', padding: '0 4px' }}>→</div>
            <div className="badge badge-indigo">Unified Plan</div>
          </div>
        </div>
      )}

      {/* Run summary */}
      {display && (
        <>
          <div className="card card-accent-emerald mb-4">
            <div className="flex items-center gap-4 flex-wrap">
              <div>
                <div className="text-xs text-muted mb-1" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>Overall Score</div>
                <div style={{ fontSize: 40, fontWeight: 900, color: display.overall_score >= 70 ? 'var(--emerald-400)' : 'var(--amber-400)', lineHeight: 1 }}>
                  {display.overall_score}
                  <span style={{ fontSize: 16, color: 'var(--text-muted)', fontWeight: 400 }}>/100</span>
                </div>
              </div>
              <div className="flex-1" style={{ minWidth: 200 }}>
                <p className="text-secondary text-sm" style={{ lineHeight: 1.6 }}>{display.summary}</p>
                <div className="flex gap-2 mt-2">
                  <div className="flex items-center gap-1 text-xs text-muted">
                    <Clock size={11} /> Run: {display.run_id}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted mb-1">Agents Run</div>
                <div style={{ fontWeight: 800, fontSize: 28, color: 'var(--text-primary)' }}>{display.agents.length}</div>
              </div>
            </div>
          </div>

          <div className="flex-col gap-3">
            {display.agents.map(a => <AgentCard key={a.agent} agent={a} />)}
          </div>
        </>
      )}

      {!display && !isPending && (
        <div className="card" style={{ textAlign: 'center', padding: 60 }}>
          <Bot size={40} color="var(--text-muted)" style={{ margin: '0 auto 16px' }} />
          <div className="text-secondary" style={{ fontSize: 16, fontWeight: 500, marginBottom: 8 }}>No analysis run yet</div>
          <div className="text-muted text-sm">Click "Run Full Analysis" to trigger all 5 agents</div>
        </div>
      )}
    </div>
  )
}
