import { motion, AnimatePresence } from 'framer-motion'
import { Bell, X, Trash2, CheckCheck } from 'lucide-react'
import { useAppStore } from '../../store'

const priorityColor: Record<string, string> = {
  critical: 'var(--red-400)',
  high: 'var(--amber-400)',
  medium: 'var(--blue-400)',
  low: 'var(--text-muted)',
}

const priorityBadge: Record<string, string> = {
  critical: 'badge-red',
  high: 'badge-amber',
  medium: 'badge-blue',
  low: 'badge-muted',
}

function timeAgo(ts: number) {
  const diff = Math.floor((Date.now() - ts) / 1000)
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  return `${Math.floor(diff / 3600)}h ago`
}

export default function NotificationsPanel() {
  const { notifPanelOpen, setNotifPanelOpen, notifications, markNotifRead, clearNotifications } = useAppStore()

  const unread = notifications.filter(n => !n.read).length

  return (
    <AnimatePresence>
      {notifPanelOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={() => setNotifPanelOpen(false)}
            style={{
              position: 'fixed', inset: 0, zIndex: 199,
              background: 'rgba(0,0,0,0.4)',
              backdropFilter: 'blur(2px)',
            }}
          />

          {/* Panel */}
          <motion.div
            initial={{ x: '100%', opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
            style={{
              position: 'fixed',
              top: 64, right: 0, bottom: 0,
              width: 'min(360px, 100vw)',
              maxWidth: '100vw',
              zIndex: 200,
              background: 'rgba(5,10,20,0.97)',
              borderLeft: '1px solid var(--border)',
              backdropFilter: 'blur(24px)',
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            {/* Header */}
            <div style={{
              padding: '16px 20px',
              borderBottom: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: 10,
            }}>
              <Bell size={16} color="var(--emerald-400)" />
              <span style={{ fontSize: 15, fontWeight: 700, flex: 1, color: 'var(--text-primary)' }}>
                Notifications
                {unread > 0 && (
                  <span style={{
                    marginLeft: 8, background: 'var(--red-500)',
                    color: '#fff', fontSize: 10, fontWeight: 700,
                    padding: '1px 6px', borderRadius: 99,
                  }}>{unread}</span>
                )}
              </span>
              <button
                className="btn btn-ghost btn-sm"
                onClick={clearNotifications}
                title="Clear all"
                style={{ padding: '4px 8px', gap: 4 }}
              >
                <Trash2 size={13} />
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setNotifPanelOpen(false)}
                style={{ padding: '4px 8px' }}
              >
                <X size={16} />
              </button>
            </div>

            {/* Items */}
            <div style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {notifications.length === 0 ? (
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  justifyContent: 'center', height: '100%', gap: 12,
                  color: 'var(--text-muted)',
                }}>
                  <CheckCheck size={36} strokeWidth={1.5} />
                  <span style={{ fontSize: 14, fontWeight: 500 }}>All clear — no alerts</span>
                </div>
              ) : (
                <AnimatePresence initial={false}>
                  {notifications.map(n => (
                    <motion.div
                      key={n.id}
                      initial={{ opacity: 0, x: 20 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: 20 }}
                      layout
                      onClick={() => markNotifRead(n.id)}
                      style={{
                        background: n.read ? 'rgba(255,255,255,0.02)' : 'rgba(255,255,255,0.05)',
                        border: `1px solid ${n.read ? 'var(--border)' : priorityColor[n.priority] + '40'}`,
                        borderLeft: `3px solid ${priorityColor[n.priority]}`,
                        borderRadius: 10,
                        padding: '12px 14px',
                        cursor: 'pointer',
                        transition: 'background 150ms',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
                        <div style={{ flex: 1 }}>
                          <div style={{
                            fontSize: 13, fontWeight: n.read ? 500 : 700,
                            color: n.read ? 'var(--text-secondary)' : 'var(--text-primary)',
                            marginBottom: 4,
                          }}>
                            {n.title}
                          </div>
                          <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
                            {n.body}
                          </div>
                        </div>
                        {!n.read && (
                          <span style={{
                            width: 7, height: 7, borderRadius: '50%',
                            background: priorityColor[n.priority],
                            flexShrink: 0, marginTop: 4,
                          }} />
                        )}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 8 }}>
                        <span className={`badge ${priorityBadge[n.priority]}`}>{n.priority}</span>
                        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{timeAgo(n.timestamp)}</span>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
