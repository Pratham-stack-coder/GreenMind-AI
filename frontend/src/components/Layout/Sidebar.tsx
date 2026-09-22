import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard, TrendingUp, Lightbulb, Bot, GitFork,
  MessageSquare, BarChart3, Settings, Leaf, Activity, Zap
} from 'lucide-react'

const navSections = [
  {
    label: 'Overview',
    items: [
      { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
      { to: '/analytics', icon: BarChart3, label: 'Analytics' },
    ],
  },
  {
    label: 'AI Intelligence',
    items: [
      { to: '/predictions', icon: TrendingUp, label: 'Predictions' },
      { to: '/recommendations', icon: Lightbulb, label: 'Recommendations' },
      { to: '/agents', icon: Bot, label: 'Multi-Agent AI' },
    ],
  },
  {
    label: 'Optimization',
    items: [
      { to: '/digital-twin', icon: GitFork, label: 'Digital Twin' },
      { to: '/copilot', icon: MessageSquare, label: 'AI Copilot' },
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
  return (
    <motion.aside
      className="sidebar"
      initial={{ x: -20, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">
          <Leaf size={20} color="#fff" />
        </div>
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, lineHeight: 1.2, color: 'var(--text-primary)' }}>
            GreenMind
          </div>
          <div style={{ fontSize: 10, color: 'var(--emerald-400)', fontWeight: 600, letterSpacing: '0.05em' }}>
            AI CLOUD OS
          </div>
        </div>
      </div>

      {/* Live indicator */}
      <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <span className="status-dot online animate-pulse-glow" />
          <span style={{ fontSize: 11, color: 'var(--text-secondary)', fontWeight: 500 }}>
            Demo Mode • 6 Regions
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navSections.map(section => (
          <div key={section.label}>
            <div className="sidebar-section-label">{section.label}</div>
            {section.items.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <item.icon size={16} className="nav-icon" />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {/* Bottom card */}
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
    </motion.aside>
  )
}
