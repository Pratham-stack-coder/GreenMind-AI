import { useState, useRef, useEffect } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, MessageSquare, Sparkles, User, Bot } from 'lucide-react'
import { sendCopilotMessage, fetchCopilotSuggestions } from '../api/client'
import type { CopilotMessage } from '../types'

function MarkdownText({ content }: { content: string }) {
  // Minimal markdown: bold, code, bullets
  const html = content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code style="background:rgba(255,255,255,0.08);padding:1px 5px;border-radius:3px;font-family:JetBrains Mono,monospace;font-size:0.85em">$1</code>')
    .replace(/^- (.*)/gm, '<li style="margin-left:12px;list-style:disc">$1</li>')
    .replace(/\n/g, '<br />')
  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

export default function CopilotPage() {
  const [messages, setMessages] = useState<CopilotMessage[]>([])
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  const { data: suggestionsData } = useQuery({
    queryKey: ['copilotSuggestions'],
    queryFn: fetchCopilotSuggestions,
  })

  const { mutate: send, isPending } = useMutation({
    mutationFn: (message: string) => sendCopilotMessage(message, messages),
    onSuccess: (data, message) => {
      setMessages(prev => [
        ...prev,
        { role: 'user', content: message },
        { role: 'assistant', content: data.reply },
      ])
    },
  })

  const handleSend = () => {
    const msg = input.trim()
    if (!msg || isPending) return
    setInput('')
    send(msg)
  }

  const handleSuggestion = (s: string) => {
    setInput(s)
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 112px)' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4" style={{ flexShrink: 0 }}>
        <div>
          <h1 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Sparkles size={22} color="var(--emerald-400)" />
            AI Cloud Copilot
          </h1>
          <p className="text-secondary text-sm mt-1">
            Natural language interface to your cloud environment
          </p>
        </div>
        <div className="badge badge-emerald">
          <span className="status-dot online" style={{ width: 6, height: 6 }} />
          Rule-based · No API key needed
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
              style={{ textAlign: 'center', padding: '40px 0' }}
            >
              <Bot size={48} color="var(--emerald-400)" style={{ margin: '0 auto 16px' }} />
              <div style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>
                Hello! I'm GreenMind Copilot
              </div>
              <div className="text-secondary text-sm" style={{ maxWidth: 400, margin: '0 auto 24px' }}>
                Ask me about cost optimization, sustainability, performance, security, or how to use any GreenMind feature.
              </div>
              {suggestionsData && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                  {suggestionsData.suggestions.slice(0, 6).map(s => (
                    <button
                      key={s}
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleSuggestion(s)}
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

          {isPending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ alignSelf: 'flex-start' }}>
              <div className="chat-bubble assistant" style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <span className="animate-pulse-glow" style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--emerald-400)', display: 'inline-block' }} />
                <span className="text-secondary text-sm">Analyzing…</span>
              </div>
            </motion.div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Suggestions row */}
        {messages.length > 0 && suggestionsData && (
          <div style={{ padding: '8px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <span className="text-xs text-muted" style={{ padding: '4px 0', flexShrink: 0 }}>Try:</span>
            {suggestionsData.suggestions.slice(0, 3).map(s => (
              <button key={s} className="btn btn-ghost btn-sm" style={{ fontSize: 11, padding: '3px 8px' }} onClick={() => handleSuggestion(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div style={{ padding: '12px 20px', borderTop: '1px solid var(--border)', display: 'flex', gap: 10 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask about cost, carbon, performance, security…"
            style={{ flex: 1 }}
          />
          <button
            className="btn btn-primary"
            style={{ flexShrink: 0, padding: '9px 16px' }}
            onClick={handleSend}
            disabled={isPending || !input.trim()}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
