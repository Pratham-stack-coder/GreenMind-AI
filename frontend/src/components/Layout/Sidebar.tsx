import { useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, TrendingUp, Lightbulb, Bot, GitFork,
  MessageSquare, BarChart3, Settings, Leaf, Zap,
  ChevronLeft, ChevronRight, Server, DollarSign, X
} from 'lucide-react'
import { useAppStore } from '../../store'

const navSections = [
  {
    label: 'Overview',
    items: [
      { to: '/', icon: LayoutDashboard, label: 'Overview' },
      { to: '/cloud-resources', icon: Server, label: 'Cloud Resources' },
      { to: '/analytics', icon: BarChart3, label: 'Analytics' },
    ],
  },
  {
    label: 'AI Intelligence',
    items: [
      { to: '/predictions', icon: TrendingUp, label: 'Predictions' },
      { to: '/recommendations', icon: Lightbulb, label: 'AI Recommendations' },
      { to: '/agents', icon: Bot, label: 'Multi-Agent AI' },
      { to: '/copilot', icon: MessageSquare, label: 'AI Copilot' },
    ],
  },
  {
    label: 'Optimization',
    items: [
      { to: '/cost-optimization', icon: DollarSign, label: 'Cost Optimization' },
      { to: '/carbon-intelligence', icon: Leaf, label: 'Carbon Intelligence' },
      { to: '/digital-twin', icon: GitFork, label: 'Digital Twin' },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/settings', icon: Settings, label: 'Settings' },
    ],
  },
]

export default function Sidebar() {
  const { sidebarCollapsed, toggleSidebarCollapsed, sidebarOpen, setSidebarOpen } = useAppStore()
  const [isMobile, setIsMobile] = useState(() => (typeof window !== 'undefined' ? window.innerWidth < 1024 : false))

  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 1024
      setIsMobile(mobile)
    }
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // On desktop, width is either 64 or 240. On mobile, full drawer.
  const w = isMobile ? 280 : (sidebarCollapsed ? 64 : 240)
  const isRail = !isMobile && sidebarCollapsed

  const handleNavClick = () => {
    if (isMobile) {
      setSidebarOpen(false)
    }
  }

  return (
    <>
      {/* Mobile backdrop */}
      {isMobile && sidebarOpen && (
        <div
          className="sidebar-backdrop"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      <aside
        className={`sidebar ${isMobile ? 'sidebar-mobile' : ''} ${isMobile && sidebarOpen ? 'sidebar-mobile-open' : ''}`}
        style={{
          width: isMobile ? undefined : w,
          overflow: 'hidden',
          transition: isMobile ? undefined : 'width 300ms cubic-bezier(0.4, 0, 0.2, 1)',
        }}
      >
        {/* Logo */}
        <div
          className="sidebar-logo"
          style={{
            padding: isRail ? '20px 14px' : '20px 20px 16px',
            justifyContent: isRail ? 'center' : 'flex-start',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <div className="sidebar-logo-icon" style={{ flexShrink: 0 }}>
            <Leaf size={20} color="#fff" />
          </div>
          {!isRail && (
            <div style={{ overflow: 'hidden', whiteSpace: 'nowrap', flex: 1 }}>
              <div style={{ fontSize: 14, fontWeight: 700, lineHeight: 1.2, color: 'var(--text-primary)', paddingLeft: 10 }}>
                GreenMind
              </div>
              <div style={{ fontSize: 10, color: 'var(--emerald-400)', fontWeight: 600, letterSpacing: '0.05em', paddingLeft: 10 }}>
                AI CLOUD OS
              </div>
            </div>
          )}

          {/* Close button for mobile drawer */}
          {isMobile && (
            <button
              onClick={() => setSidebarOpen(false)}
              className="btn btn-ghost btn-sm"
              style={{ padding: '6px', borderRadius: 8, marginLeft: 'auto' }}
              aria-label="Close navigation"
            >
              <X size={18} color="var(--text-muted)" />
            </button>
          )}
        </div>

        {/* Live indicator */}
        {!isRail && (
          <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2">
              <span className="status-dot online animate-pulse-glow" />
              <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
                Demo Mode • 6 Regions
              </span>
            </div>
          </div>
        )}

        {/* Navigation */}
        <nav className="sidebar-nav" style={{ padding: isRail ? '12px 8px' : '12px 10px' }}>
          {navSections.map(section => (
            <div key={section.label}>
              {!isRail && (
                <div className="sidebar-section-label">{section.label}</div>
              )}
              {section.items.map(item => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  onClick={handleNavClick}
                  className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                  title={isRail ? item.label : undefined}
                  style={{
                    justifyContent: isRail ? 'center' : 'flex-start',
                    padding: isRail ? '9px' : '9px 12px',
                  }}
                >
                  <item.icon size={16} className="nav-icon" />
                  {!isRail && (
                    <span style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}>
                      {item.label}
                    </span>
                  )}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        {/* Bottom card */}
        {!isRail && (
          <div style={{ padding: 16, borderTop: '1px solid var(--border)' }}>
            <div className="card" style={{ padding: '12px 14px', borderColor: 'rgba(16,185,129,0.2)', background: 'rgba(16,185,129,0.05)' }}>
              <div className="flex items-center gap-2 mb-2">
                <Zap size={14} color="var(--emerald-400)" />
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--emerald-400)' }}>5 ML MODELS</span>
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                CPU · Memory · Network<br />Cost · Carbon
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 6 }}>
                All beating naive baseline
              </div>
            </div>
          </div>
        )}

        {/* Desktop collapse toggle button */}
        {!isMobile && (
          <div
            style={{
              padding: '12px',
              borderTop: '1px solid var(--border)',
              display: 'flex',
              justifyContent: isRail ? 'center' : 'flex-end',
            }}
          >
            <button
              onClick={toggleSidebarCollapsed}
              className="btn btn-ghost btn-sm"
              title={isRail ? 'Expand sidebar' : 'Collapse sidebar'}
              style={{ padding: '6px 8px', borderRadius: 8 }}
            >
              {isRail
                ? <ChevronRight size={16} color="var(--text-muted)" />
                : <ChevronLeft size={16} color="var(--text-muted)" />
              }
            </button>
          </div>
        )}
      </aside>
    </>
  )
}
