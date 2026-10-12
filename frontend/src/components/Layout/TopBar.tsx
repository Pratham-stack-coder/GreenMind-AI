import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Bell, Globe, Menu, Leaf, LogOut } from 'lucide-react'
import { useAppStore } from '../../store'
import { fetchHealth } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

export default function TopBar() {
  const navigate = useNavigate()
  const { session, signOut } = useAuth()
  const {
    provider, region, setProvider, setRegion,
    notifPanelOpen, setNotifPanelOpen,
    notifications,
    sidebarOpen, setSidebarOpen,
  } = useAppStore()
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  const providers = ['aws', 'azure', 'gcp']
  const regions: Record<string, string[]> = {
    aws: ['us-east', 'us-west', 'eu-west', 'ap-southeast', 'ca-central', 'in-north'],
    azure: ['us-east', 'eu-west', 'ap-southeast'],
    gcp: ['us-east', 'us-west', 'eu-west'],
  }

  const unread = notifications.filter(n => !n.read).length

  return (
    <header className="topbar">
      {/* Primary Top Bar Row */}
      <div className="topbar-main">
        {/* Left: Mobile menu toggle + Brand mark */}
        <div className="topbar-left">
          <button
            className="mobile-menu-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            title="Toggle navigation"
            aria-label="Toggle navigation"
          >
            <Menu size={20} color="var(--emerald-400)" />
          </button>

          <div className="topbar-brand">
            <div className="sidebar-logo-icon" style={{ width: 28, height: 28, borderRadius: 7 }}>
              <Leaf size={15} color="#fff" />
            </div>
            <span className="brand-name">GreenMind</span>
          </div>

          <span className="desktop-globe">
            <Globe size={16} color="var(--emerald-400)" />
          </span>
        </div>

        {/* Center: Provider & Region selectors (Desktop only) */}
        <div className="topbar-selectors desktop-selectors">
          <div className="flex items-center gap-1.5">
            <span className="selector-label text-xs text-muted font-bold" style={{ letterSpacing: '0.08em' }}>PROVIDER</span>
            <select
              value={provider}
              onChange={e => { setProvider(e.target.value); setRegion(regions[e.target.value]?.[0] || 'us-east') }}
              className="topbar-select"
            >
              {providers.map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="selector-label text-xs text-muted font-bold" style={{ letterSpacing: '0.08em' }}>REGION</span>
            <select
              value={region}
              onChange={e => setRegion(e.target.value)}
              className="topbar-select"
            >
              {(regions[provider] || regions.aws).map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Right: Clock, Status, Notification Bell */}
        <div className="topbar-right">
          

          {health && (
            <button
              onClick={() => navigate('/settings')}
              className="btn btn-ghost btn-sm topbar-status-btn"
              title={`Backend status: ${health.demo_mode ? 'Demo mode' : 'Live mode'}. Click to configure.`}
            >
              <span
                className={`status-dot ${health.status === 'ok' ? 'online animate-pulse-glow' : 'error'}`}
              />
              <span className="text-xs text-secondary status-text">
                {health.demo_mode ? 'Demo' : 'Live'}
              </span>
            </button>
          )}

          <button
            type="button"
            onClick={() => void signOut()}
            className="btn btn-ghost btn-sm topbar-signout"
            title={`Sign out${session?.user.email ? ` · ${session.user.email}` : ''}`}
            aria-label="Sign out"
          >
            <LogOut size={15} />
            <span className="signout-label">Sign out</span>
          </button>

          <button
            id="notif-bell-btn"
            className="btn btn-ghost btn-sm notif-btn"
            onClick={() => setNotifPanelOpen(!notifPanelOpen)}
            title="Notifications"
            aria-label={`Notifications, ${unread} unread`}
            aria-expanded={notifPanelOpen}
            aria-controls="notifications-panel"
          >
            <Bell size={17} />
            {unread > 0 && (
              <span className="notif-badge">
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Secondary Mobile Sub-Bar: Clean Cloud & Region Selectors (Mobile only < 768px) */}
      <div className="topbar-subbar">
        <div className="mobile-selector-item">
          <span className="text-xs text-muted font-bold">CLOUD:</span>
          <select
            value={provider}
            onChange={e => { setProvider(e.target.value); setRegion(regions[e.target.value]?.[0] || 'us-east') }}
            className="topbar-select mobile-select"
          >
            {providers.map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
          </select>
        </div>

        <div className="mobile-selector-item">
          <span className="text-xs text-muted font-bold">REGION:</span>
          <select
            value={region}
            onChange={e => setRegion(e.target.value)}
            className="topbar-select mobile-select"
          >
            {(regions[provider] || regions.aws).map(r => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
      </div>
    </header>
  )
}
