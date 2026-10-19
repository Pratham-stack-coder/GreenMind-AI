import { Sun } from 'lucide-react'

export default function ThemeToggle() {
  return (
    <div
      className="btn btn-ghost btn-sm theme-toggle-btn"
      style={{ padding: '6px 10px', gap: 6, color: 'var(--text-secondary)' }}
      title="Light Theme (Active)"
      aria-label="Light Theme Active"
    >
      <Sun size={15} style={{ color: 'var(--emerald-600)' }} />
      <span className="hidden-sm text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Light</span>
    </div>
  )
}
