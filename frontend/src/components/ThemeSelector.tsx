/**
 * ThemeSelector – full 3-option selector (Dark, Light, System) for SettingsPage.
 */
import React from 'react'
import { Moon, Sun, Monitor, Check } from 'lucide-react'
import { useTheme, type ThemeMode } from '../theme/ThemeContext'

interface ThemeOption {
  mode: ThemeMode
  label: string
  description: string
  Icon: React.ElementType
}

const THEME_OPTIONS: ThemeOption[] = [
  {
    mode: 'dark',
    label: 'Dark',
    description: 'Deep navy surfaces with high contrast text and emerald accents',
    Icon: Moon,
  },
  {
    mode: 'light',
    label: 'Light',
    description: 'Clean white surfaces with crisp typography and subtle borders',
    Icon: Sun,
  },
  {
    mode: 'system',
    label: 'System',
    description: 'Automatically synchronizes with your device preferences',
    Icon: Monitor,
  },
]

export default function ThemeSelector() {
  const { themeMode, resolvedTheme, setThemeMode } = useTheme()

  return (
    <div>
      <div className="theme-selector-grid" role="radiogroup" aria-label="Theme selection">
        {THEME_OPTIONS.map(({ mode, label, description, Icon }) => {
          const isSelected = themeMode === mode
          return (
            <button
              key={mode}
              type="button"
              role="radio"
              aria-checked={isSelected}
              className={`theme-selector-option${isSelected ? ' selected' : ''}`}
              onClick={() => setThemeMode(mode)}
            >
              <div className="flex items-center gap-2">
                <Icon size={18} />
                <span>{label}</span>
                {isSelected && <Check size={14} style={{ color: 'var(--emerald-500)' }} />}
              </div>
              <span
                style={{
                  fontSize: 11,
                  fontWeight: 400,
                  color: isSelected ? 'var(--text-primary)' : 'var(--text-muted)',
                  textAlign: 'center',
                  lineHeight: 1.3,
                }}
              >
                {description}
              </span>
            </button>
          )
        })}
      </div>
      {themeMode === 'system' && (
        <p className="text-xs text-muted mt-2" style={{ fontStyle: 'italic' }}>
          Active system appearance: <strong>{resolvedTheme === 'dark' ? 'Dark theme' : 'Light theme'}</strong>
        </p>
      )}
    </div>
  )
}
