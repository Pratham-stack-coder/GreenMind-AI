import { Sun, Check } from 'lucide-react'

export default function ThemeSelector() {
  return (
    <div>
      <div className="theme-selector-grid" style={{ gridTemplateColumns: '1fr', maxWidth: 420 }} role="region" aria-label="Theme selection">
        <div
          className="theme-selector-option selected"
          style={{
            alignItems: 'flex-start',
            padding: '16px 18px',
            background: 'var(--bg-hover)',
            borderColor: 'var(--emerald-500)',
            cursor: 'default',
          }}
        >
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2.5">
              <div style={{
                width: 28, height: 28, borderRadius: 8,
                background: 'var(--emerald-50)', display: 'grid', placeItems: 'center',
                color: 'var(--emerald-600)'
              }}>
                <Sun size={16} />
              </div>
              <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                Analytics Metric Flow (Light)
              </span>
            </div>
            <span className="badge badge-emerald flex items-center gap-1" style={{ fontSize: 10 }}>
              <Check size={11} /> ACTIVE
            </span>
          </div>
          <span
            style={{
              fontSize: 12,
              fontWeight: 400,
              color: 'var(--text-secondary)',
              marginTop: 6,
              lineHeight: 1.4,
            }}
          >
            Warm off-white background (#F7F8F3), clean white cards (#FFFFFF), forest green accents, and charcoal typography.
          </span>
        </div>
      </div>
    </div>
  )
}
