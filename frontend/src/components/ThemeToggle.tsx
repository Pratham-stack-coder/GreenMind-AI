/**
 * ThemeToggle – compact sun/moon/system toggle for the TopBar.
 * Cycles: dark → light → system → dark, or opens a small popover with all 3 options.
 */
import React, { useEffect, useRef, useState } from 'react'
import { Moon, Sun, Monitor } from 'lucide-react'
import { useTheme, type ThemeMode } from '../theme/ThemeContext'

const OPTIONS: { mode: ThemeMode; label: string; Icon: React.ElementType }[] = [
  { mode: 'dark',   label: 'Dark',   Icon: Moon    },
  { mode: 'light',  label: 'Light',  Icon: Sun     },
  { mode: 'system', label: 'System', Icon: Monitor },
]

function CurrentIcon({ mode }: { mode: ThemeMode }) {
  const M = OPTIONS.find(o => o.mode === mode)?.Icon ?? Moon
  return <M size={16} aria-hidden="true" />
}

export default function ThemeToggle() {
  const { themeMode, setThemeMode } = useTheme()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Close popover on outside click
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        type="button"
        className="btn btn-ghost btn-sm theme-toggle-btn"
        onClick={() => setOpen(o => !o)}
        aria-label={`Theme: ${themeMode}. Click to change.`}
        aria-haspopup="listbox"
        aria-expanded={open}
        title={`Theme: ${themeMode}`}
      >
        <CurrentIcon mode={themeMode} />
      </button>

      {open && (
        <div
          className="theme-popover"
          role="listbox"
          aria-label="Theme selection"
        >
          {OPTIONS.map(({ mode, label, Icon }) => (
            <button
              key={mode}
              type="button"
              role="option"
              aria-selected={themeMode === mode}
              className={`theme-option${themeMode === mode ? ' theme-option-active' : ''}`}
              onClick={() => { setThemeMode(mode); setOpen(false) }}
            >
              <Icon size={14} aria-hidden="true" />
              <span>{label}</span>
              {themeMode === mode && (
                <svg
                  className="theme-option-check"
                  viewBox="0 0 12 12"
                  fill="none"
                  aria-hidden="true"
                >
                  <path d="M2 6l3 3 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
