import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Bell, Globe, Menu, Leaf } from 'lucide-react'
import { useAppStore } from '../../store'
import { fetchHealth, fetchRecommendations, fetchLiveMetrics, getActiveBackendUrl } from '../../api/client'
import { useEffect, useRef, useState } from 'react'

function LiveClock() {
  const [time, setTime] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  return (
    <span style={{ fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: 'var(--text-muted)', letterSpacing: '0.05em' }}>
      {time.toUTCString().slice(17, 25)} UTC
    </span>
  )
}

export default function TopBar() {
  const navigate = useNavigate()
  const {
    provider, region, setProvider, setRegion,
    notifPanelOpen, setNotifPanelOpen,
    notifications, addNotification,
    sidebarOpen, setSidebarOpen,
  } = useAppStore()
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  const { data: recs } = useQuery({
    queryKey: ['topbar-recs', provider, region],
    queryFn: () => fetchRecommendations({ provider, region }),
    refetchInterval: 120_000,
  })

  const { data: liveMetrics } = useQuery({
    queryKey: ['topbar-live', provider, region],
    queryFn: () => fetchLiveMetrics(provider, region),
    refetchInterval: 15_000,
  })

  // ── Source 1: Critical/High recommendations ──────────────────────────────
  useEffect(() => {
    if (!Array.isArray(recs?.recommendations)) return
    const urgent = recs.recommendations.filter(r => r.priority === 'critical' || r.priority === 'high')
    urgent.slice(0, 4).forEach(r => {
      addNotification({
        title: `💡 ${r.title}`,
        body: r.impact_summary,
        priority: r.priority as any,
      })
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recs])

  // ── Source 2: Live metric threshold alerts ───────────────────────────────
  const prevMetricsRef = useRef<{ cpu?: number; cost?: number }>({})
  useEffect(() => {
    if (!liveMetrics || typeof liveMetrics.cpu !== 'number') return
    const prev = prevMetricsRef.current

    // CPU spike alert (>85% and not already alerted in this session)
    if (liveMetrics.cpu > 85 && (prev.cpu == null || prev.cpu <= 85)) {
      addNotification({
        title: `⚡ CPU Spike Detected`,
        body: `${provider.toUpperCase()} ${region}: CPU at ${liveMetrics.cpu.toFixed(1)}% — consider scaling up or checking for runaway processes.`,
        priority: liveMetrics.cpu > 95 ? 'critical' : 'high',
      })
    }

    // Cost spike alert (>20% above baseline $0.22/hr)
    const baseline = 0.22
    if (liveMetrics.cost_usd_per_hour > baseline * 1.2 && (prev.cost == null || prev.cost <= baseline * 1.2)) {
      addNotification({
        title: `💰 Cost Spike Alert`,
        body: `${provider.toUpperCase()} ${region}: cost at $${liveMetrics.cost_usd_per_hour.toFixed(4)}/hr — ${((liveMetrics.cost_usd_per_hour / baseline - 1) * 100).toFixed(0)}% above baseline.`,
        priority: 'high',
      })
    }

    // High carbon intensity alert
    if (liveMetrics.carbon_gco2_per_hour > 150) {
      addNotification({
        title: `🌿 High Carbon Intensity`,
        body: `${region}: ${liveMetrics.carbon_gco2_per_hour.toFixed(1)} gCO₂/hr — consider deferring non-urgent batch workloads.`,
        priority: 'medium',
      })
    }

    prevMetricsRef.current = { cpu: liveMetrics.cpu, cost: liveMetrics.cost_usd_per_hour }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [liveMetrics])

  // ── Source 3: Backend health status ─────────────────────────────────────
  useEffect(() => {
    if (health && health.status !== 'ok') {
      addNotification({
        title: '🔴 Backend Health Degraded',
        body: `API returned status: ${health.status}. Some features may be unavailable.`,
        priority: 'critical',
      })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [health?.status])


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
          <div className="hidden-md">
            <LiveClock />
          </div>

          {health && (
            <button
              onClick={() => navigate('/settings')}
              className="btn btn-ghost btn-sm topbar-status-btn"
              title={`Backend: ${getActiveBackendUrl() || 'Local Proxy (/api/v1)'} (${health.demo_mode ? 'Demo Mode' : 'Live Mode'}) · Click to configure`}
            >
              <span
                className={`status-dot ${health.status === 'ok' ? 'online animate-pulse-glow' : 'error'}`}
              />
              <span className="text-xs text-secondary status-text">
                <span className="hidden-sm">v{health.version} · </span>{health.demo_mode ? 'Demo' : 'Live'}
              </span>
            </button>
          )}

          <button
            id="notif-bell-btn"
            className="btn btn-ghost btn-sm notif-btn"
            onClick={() => setNotifPanelOpen(!notifPanelOpen)}
            title="Notifications"
            aria-label="Notifications"
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
