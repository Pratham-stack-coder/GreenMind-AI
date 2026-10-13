/**
 * GreenMind AI – Theme System
 *
 * Provides three modes: 'dark' | 'light' | 'system'
 *   - Persisted in localStorage under 'greenmind-theme'
 *   - System mode respects prefers-color-scheme and reacts to OS changes
 *   - Applies data-theme="dark"|"light" on <html> before first paint (see index.html script)
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react'

export type ThemeMode = 'dark' | 'light' | 'system'
export type ResolvedTheme = 'dark' | 'light'

const STORAGE_KEY = 'greenmind-theme'

function getSystemTheme(): ResolvedTheme {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function resolveTheme(mode: ThemeMode): ResolvedTheme {
  if (mode === 'system') return getSystemTheme()
  return mode
}

function applyTheme(resolved: ResolvedTheme) {
  const html = document.documentElement
  html.setAttribute('data-theme', resolved)
  // Also set color-scheme for native controls (scrollbars, inputs)
  html.style.colorScheme = resolved
}

// ── Context ──────────────────────────────────────────────────────────────────
interface ThemeContextValue {
  /** User's stored preference: 'dark' | 'light' | 'system' */
  themeMode: ThemeMode
  /** The actual resolved theme applied to the DOM: 'dark' | 'light' */
  resolvedTheme: ResolvedTheme
  /** Change the theme mode */
  setThemeMode: (mode: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextValue>({
  themeMode: 'dark',
  resolvedTheme: 'dark',
  setThemeMode: () => undefined,
})

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | null
      if (stored === 'dark' || stored === 'light' || stored === 'system') return stored
    } catch {
      // localStorage unavailable (private mode, etc.)
    }
    return 'dark'
  })

  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    resolveTheme(themeMode)
  )

  // Apply resolved theme to <html> whenever it changes
  useEffect(() => {
    const resolved = resolveTheme(themeMode)
    setResolvedTheme(resolved)
    applyTheme(resolved)
  }, [themeMode])

  // Listen for OS color-scheme changes when in system mode
  useEffect(() => {
    if (themeMode !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = (e: MediaQueryListEvent) => {
      const resolved: ResolvedTheme = e.matches ? 'dark' : 'light'
      setResolvedTheme(resolved)
      applyTheme(resolved)
    }
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [themeMode])

  const setThemeMode = useCallback((mode: ThemeMode) => {
    setThemeModeState(mode)
    try {
      localStorage.setItem(STORAGE_KEY, mode)
    } catch {
      // ignore
    }
  }, [])

  return (
    <ThemeContext.Provider value={{ themeMode, resolvedTheme, setThemeMode }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
