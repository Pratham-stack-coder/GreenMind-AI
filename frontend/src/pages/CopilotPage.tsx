import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, MessageSquare, Sparkles, User, Bot, Zap } from 'lucide-react'
import { sendCopilotMessage, fetchCopilotSuggestions, fetchLiveMetrics, fetchScores } from '../api/client'
import { useAppStore } from '../store'
import type { CopilotMessage } from '../types'

/** Full markdown renderer: headings, bold, italic, code blocks, inline code, bullets, numbered lists */
function MarkdownText({ content }: { content: string }) {
  const html = content
    // Code blocks (```...```) — process first to avoid other transforms inside
    .replace(/```([^`]*?)```/gs, '<pre style="background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.1);padding:10px 12px;border-radius:8px;font-family:JetBrains Mono,monospace;font-size:12px;overflow-x:auto;margin:6px 0;white-space:pre-wrap">$1</pre>')
    // Headings
    .replace(/^### (.*)/gm, '<div style="font-size:13px;font-weight:700;color:var(--text-primary);margin:10px 0 4px">$1</div>')
    .replace(/^## (.*)/gm, '<div style="font-size:15px;font-weight:700;color:var(--text-primary);margin:12px 0 4px">$1</div>')
    .replace(/^# (.*)/gm, '<div style="font-size:17px;font-weight:800;color:var(--text-primary);margin:14px 0 6px">$1</div>')
    // Bold + italic
    .replace(/\*\*\*(.*?)\*\*\*/g, '<strong><em>$1</em></strong>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // Inline code
    .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:3px;font-family:JetBrains Mono,monospace;font-size:0.85em;color:var(--emerald-400)">$1</code>')
    // Bullets
    .replace(/^- (.*)/gm, '<li style="margin-left:16px;list-style:disc;margin-bottom:2px">$1</li>')
    // Numbered list
    .replace(/^\d+\. (.*)/gm, '<li style="margin-left:16px;list-style:decimal;margin-bottom:2px">$1</li>')
    // Horizontal rule
    .replace(/^---$/gm, '<hr style="border:none;border-top:1px solid var(--border);margin:10px 0" />')
    // Newlines → br (skip inside pre)
    .replace(/\n/g, '<br />')

  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

/** Animated 3-dot typing indicator */
function TypingDots() {
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', padding: '4px 0' }}>
      {[0, 1, 2].map(i => (
        <motion.div
          key={i}
          animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }}
          transition={{ duration: 0.7, delay: i * 0.15, repeat: Infinity, ease: 'easeInOut' }}
          style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--emerald-400)' }}
        />
      ))}
    </div>
  )
}

const QUICK_PROMPTS = [
  { label: '💰 Reduce AWS costs', prompt: 'How can I reduce my AWS costs right now?' },
  { label: '🌱 Carbon hotspots', prompt: 'What are my carbon emission hotspots?' },
  { label: '🔒 Security score', prompt: 'Explain my current security score and how to improve it.' },
  { label: '⚡ CPU spike', prompt: 'My CPU is spiking — what should I do?' },
  { label: '🚀 Performance tips', prompt: 'Give me top 3 performance optimization tips.' },
  { label: '📊 Cost forecast', prompt: 'What will my cloud costs look like next month?' },
]

export default function CopilotPage() {
  const { provider, region } = useAppStore()
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: suggestionsData } = useQuery({
    queryKey: ['copilotSuggestions'],
    queryFn: fetchCopilotSuggestions,
  })

  const { data: liveMetrics } = useQuery({
    queryKey: ['liveMetrics', provider, region],
    queryFn: () => fetchLiveMetrics(provider, region),
    refetchInterval: 30_000,
  })

  const { data: scores } = useQuery({
    queryKey: ['scores', provider, region],
    queryFn: () => fetchScores(provider, region),
    refetchInterval: 60_000,
  })

  const { mutate: send, isPending } = useMutation({
    mutationFn: (message: string) => sendCopilotMessage(message, messages, {
      provider,
      region,
      cpu: liveMetrics?.cpu,
      cost_usd_per_hour: liveMetrics?.cost_usd_per_hour,
      carbon_gco2_per_hour: liveMetrics?.carbon_gco2_per_hour,
      overall_score: scores?.overall,
    }),
    onSuccess: (data, message) => {
      setMessages(prev => [
        ...prev,
        { role: 'user', content: message },
        { role: 'assistant', content: data.reply },
      ])
    },
  })

  const handleSend = (msg?: string) => {
    const text = (msg || input).trim()
    if (!text || isPending) return
    setInput('')
    send(text)
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isPending])

  return (
    <div className="animate-fade-in copilot-page-layout">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3" style={{ flexShrink: 0 }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Sparkles size={22} color="var(--emerald-400)" />
            AI Cloud Copilot
          </h1>
          <p className="text-secondary text-sm mt-1">
            Natural language interface to your cloud environment
          </p>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
          <div className="badge badge-emerald">
            <span className="status-dot online animate-pulse-glow" style={{ width: 6, height: 6 }} />
            Rule-based · No API key needed
          </div>
          {liveMetrics && (
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
              Context: {provider.toUpperCase()} · {region} · CPU {liveMetrics.cpu.toFixed(0)}% · ${liveMetrics.cost_usd_per_hour.toFixed(4)}/hr
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div
        className="card flex-1"
        style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}
      >
        <div
          style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 16, padding: '20px 20px 8px' }}
        >
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ textAlign: 'center', padding: '32px 0' }}
            >
              <div style={{
                width: 60, height: 60, borderRadius: '50%',
                background: 'linear-gradient(135deg, rgba(16,185,129,0.2), rgba(99,102,241,0.2))',
                border: '2px solid rgba(16,185,129,0.3)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px',
              }}>
                <Bot size={28} color="var(--emerald-400)" />
              </div>
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                Hello! I'm GreenMind Copilot
              </div>
              <div className="text-secondary text-sm" style={{ maxWidth: 440, margin: '0 auto 28px' }}>
                Ask me anything about <strong style={{ color: 'var(--text-primary)' }}>cost</strong>,{' '}
                <strong style={{ color: 'var(--text-primary)' }}>sustainability</strong>,{' '}
                <strong style={{ color: 'var(--text-primary)' }}>performance</strong>, or{' '}
                <strong style={{ color: 'var(--text-primary)' }}>security</strong> in your cloud environment.
              </div>

              {/* Quick prompt chips */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginBottom: 16 }}>
                {QUICK_PROMPTS.map(p => (
                  <motion.button
                    key={p.label}
                    className="btn btn-secondary btn-sm"
                    whileHover={{ scale: 1.04, borderColor: 'rgba(16,185,129,0.4)' }}
                    whileTap={{ scale: 0.97 }}
                    onClick={() => handleSend(p.prompt)}
                    style={{ fontSize: 12, gap: 5 }}
                  >
                    {p.label}
                  </motion.button>
                ))}
              </div>

              {/* From API suggestions */}
              {suggestionsData && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, justifyContent: 'center' }}>
                  <span style={{ fontSize: 11, color: 'var(--text-muted)', padding: '4px 0', width: '100%' }}>More questions:</span>
                  {suggestionsData.suggestions.slice(0, 4).map(s => (
                    <button
                      key={s}
                      className="btn btn-ghost btn-sm"
                      onClick={() => handleSend(s)}
                      style={{ fontSize: 11 }}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}
              >
                <div className="flex items-center gap-2" style={{ flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    background: msg.role === 'user' ? 'var(--indigo-500)' : 'rgba(16,185,129,0.15)',
                    border: '1px solid ' + (msg.role === 'user' ? 'var(--indigo-600)' : 'rgba(16,185,129,0.3)'),
                    display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>
                    {msg.role === 'user' ? <User size={14} /> : <Bot size={14} color="var(--emerald-400)" />}
                  </div>
                  <span className="text-xs text-muted">{msg.role === 'user' ? 'You' : 'GreenMind AI'}</span>
                </div>
                <div className={`chat-bubble ${msg.role}`}>
                  <MarkdownText content={msg.content} />
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing indicator */}
          {isPending && (
            <motion.div
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ alignSelf: 'flex-start' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.3)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Bot size={14} color="var(--emerald-400)" />
                </div>
                <span className="text-xs text-muted">GreenMind AI</span>
              </div>
              <div className="chat-bubble assistant" style={{ padding: '12px 16px' }}>
                <TypingDots />
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Inline suggestion chips during conversation */}
        {messages.length > 0 && (
          <div style={{ padding: '8px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
            <Zap size={12} color="var(--emerald-400)" />
            <span className="text-xs text-muted" style={{ flexShrink: 0 }}>Quick:</span>
            {QUICK_PROMPTS.slice(0, 4).map(p => (
              <button
                key={p.label}
                className="btn btn-ghost btn-sm"
                style={{ fontSize: 11, padding: '3px 8px' }}
                onClick={() => handleSend(p.prompt)}
              >
                {p.label}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 10 }}>
          <input
            id="copilot-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask about cost, carbon, performance, security…"
            style={{ flex: 1 }}
            disabled={isPending}
          />
          <button
            id="copilot-send-btn"
            className="btn btn-primary"
            style={{ flexShrink: 0, padding: '9px 16px' }}
            onClick={() => handleSend()}
            disabled={isPending || !input.trim()}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
