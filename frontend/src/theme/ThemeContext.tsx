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

export type ThemeMode = 'light'
export type ResolvedTheme = 'light'

const STORAGE_KEY = 'greenmind-theme'

function applyTheme() {
  const html = document.documentElement
  html.setAttribute('data-theme', 'light')
  html.style.colorScheme = 'light'
}

// ── Context ──────────────────────────────────────────────────────────────────
interface ThemeContextValue {
  /** Current theme mode (light-only) */
  themeMode: ThemeMode
  /** The resolved theme applied to the DOM: 'light' */
  resolvedTheme: ResolvedTheme
  /** Change the theme mode */
  setThemeMode: (mode: ThemeMode) => void
}

const ThemeContext = createContext<ThemeContextValue>({
  themeMode: 'light',
  resolvedTheme: 'light',
  setThemeMode: () => undefined,
})

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeMode, setThemeModeState] = useState<ThemeMode>('light')
  const resolvedTheme: ResolvedTheme = 'light'

  useEffect(() => {
    applyTheme()
    try {
      localStorage.setItem(STORAGE_KEY, 'light')
    } catch {
      // ignore
    }
  }, [])

  const setThemeMode = useCallback((_mode: ThemeMode) => {
    setThemeModeState('light')
    applyTheme()
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
