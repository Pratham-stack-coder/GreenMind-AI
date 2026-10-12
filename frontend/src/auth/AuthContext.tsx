import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { useQueryClient } from '@tanstack/react-query'
import { isSupabaseConfigured, supabase } from './supabase'

interface AuthContextValue {
  session: Session | null
  loading: boolean
  configError: string | null
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [configError, setConfigError] = useState<string | null>(null)

  useEffect(() => {
    if (!isSupabaseConfigured || !supabase) {
      setConfigError('Add VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY to the frontend environment to enable sign in.')
      setLoading(false)
      return
    }

    let active = true
    let previousUserId: string | null = null
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!active) return
      const nextUserId = nextSession?.user.id ?? null
      if (previousUserId !== nextUserId) queryClient.clear()
      previousUserId = nextUserId
      setSession(nextSession)
      setConfigError(null)
      setLoading(false)
    })

    void supabase.auth.getSession().then(({ data, error }) => {
      if (!active) return
      if (error) setConfigError(error.message)
      const nextUserId = data.session?.user.id ?? null
      if (previousUserId !== nextUserId) queryClient.clear()
      previousUserId = nextUserId
      setSession(data.session)
      setLoading(false)
    }).catch((error: unknown) => {
      if (!active) return
      setConfigError(error instanceof Error ? error.message : 'Unable to restore your sign-in session.')
      setLoading(false)
    })

    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [queryClient])

  const value = useMemo<AuthContextValue>(() => ({
    session,
    loading,
    configError,
    signOut: async () => {
      if (supabase) await supabase.auth.signOut()
      queryClient.clear()
      setSession(null)
    },
  }), [session, loading, configError, queryClient])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
