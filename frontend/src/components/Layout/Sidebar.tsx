import { NavLink } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, TrendingUp, Lightbulb, Bot, GitFork,
  MessageSquare, BarChart3, Settings, Leaf, Activity, Zap,
  ChevronLeft, ChevronRight, Server, DollarSign
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
  const { sidebarCollapsed, toggleSidebarCollapsed } = useAppStore()
  const w = sidebarCollapsed ? 64 : 240

  return (
    <motion.aside
      className="sidebar"
      animate={{ width: w }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      style={{ width: w, overflow: 'hidden' }}
      initial={false}
    >
      {/* Logo */}
      <div className="sidebar-logo" style={{ padding: sidebarCollapsed ? '20px 14px' : '20px 20px 16px', justifyContent: sidebarCollapsed ? 'center' : 'flex-start' }}>
        <div className="sidebar-logo-icon" style={{ flexShrink: 0 }}>
          <Leaf size={20} color="#fff" />
        </div>
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
            >
              <div style={{ fontSize: 14, fontWeight: 700, lineHeight: 1.2, color: 'var(--text-primary)', paddingLeft: 10 }}>
                GreenMind
              </div>
              <div style={{ fontSize: 10, color: 'var(--emerald-400)', fontWeight: 600, letterSpacing: '0.05em', paddingLeft: 10 }}>
                AI CLOUD OS
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Live indicator */}
      {!sidebarCollapsed && (
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
      <nav className="sidebar-nav" style={{ padding: sidebarCollapsed ? '12px 8px' : '12px 10px' }}>
        {navSections.map(section => (
          <div key={section.label}>
            {!sidebarCollapsed && (
              <div className="sidebar-section-label">{section.label}</div>
            )}
            {section.items.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
                title={sidebarCollapsed ? item.label : undefined}
                style={{ justifyContent: sidebarCollapsed ? 'center' : 'flex-start', padding: sidebarCollapsed ? '9px' : '9px 12px' }}
              >
                <item.icon size={16} className="nav-icon" />
                <AnimatePresence>
                  {!sidebarCollapsed && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      transition={{ duration: 0.2 }}
                      style={{ overflow: 'hidden', whiteSpace: 'nowrap' }}
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Bottom card */}
      {!sidebarCollapsed && (
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

      {/* Collapse toggle button */}
      <div
        style={{
          padding: '12px',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          justifyContent: sidebarCollapsed ? 'center' : 'flex-end',
        }}
      >
        <button
          onClick={toggleSidebarCollapsed}
          className="btn btn-ghost btn-sm"
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{ padding: '6px 8px', borderRadius: 8 }}
        >
          {sidebarCollapsed
            ? <ChevronRight size={16} color="var(--text-muted)" />
            : <ChevronLeft size={16} color="var(--text-muted)" />
          }
        </button>
      </div>
    </motion.aside>
  )
}
