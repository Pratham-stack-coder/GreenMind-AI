import { FormEvent, useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Chrome, Leaf, LockKeyhole, Mail } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { isSupabaseConfigured, supabase } from '../auth/supabase'

export default function AuthPage() {
  const { session, loading, configError } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const returnTo = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/'

  useEffect(() => {
    if (session) navigate(returnTo, { replace: true })
  }, [session, navigate, returnTo])

  if (loading) return <div className="auth-loading" role="status">Restoring your session…</div>
  if (session) return <Navigate to={returnTo} replace />

  const handleGoogle = async () => {
    if (!supabase) return
    setBusy(true)
    setError(null)
    setMessage(null)
    const { error: signInError } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/auth/callback`,
        queryParams: {
          prompt: 'select_account',
          access_type: 'offline',
        },
      },
    })
    if (signInError) {
      setError(signInError.message)
      setBusy(false)
    }
  }

  const handleEmailSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!supabase) return
    setBusy(true)
    setError(null)
    setMessage(null)

    try {
      if (mode === 'signup') {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
        })
        if (signUpError) throw signUpError
        if (!data.session) {
          setMessage('Check your inbox for a confirmation link. After confirming, you will be signed in automatically.')
        } else {
          setMessage('Your account is ready. Connecting to GreenMind…')
        }
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({ email, password })
        if (signInError) throw signInError
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to complete sign in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="auth-shell">
      <section className="auth-brand-panel" aria-label="GreenMind AI">
        <div className="auth-brand-mark"><Leaf size={22} /></div>
        <div className="auth-brand-name">GreenMind <span>AI</span></div>
        <p>Clarity for every cloud decision.</p>
        <div className="auth-brand-rule" />
        <div className="auth-brand-points">
          <span>Cost intelligence</span>
          <span>Carbon awareness</span>
          <span>Secure by design</span>
        </div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-card">
          <div className="auth-mobile-brand"><Leaf size={18} /> GreenMind AI</div>
          <p className="auth-eyebrow">YOUR CLOUD COCKPIT</p>
          <h1>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
          <p className="auth-subtitle">{mode === 'login' ? 'Sign in to continue to your workspace.' : 'Sign up to start exploring your cloud insights.'}</p>

          {!isSupabaseConfigured && (
            <div className="auth-alert auth-alert-error" role="alert">
              {configError || 'Supabase sign in is not configured.'}
            </div>
          )}
          {error && <div className="auth-alert auth-alert-error" role="alert">{error}</div>}
          {message && <div className="auth-alert auth-alert-success" role="status">{message}</div>}

          <button className="auth-google-button" type="button" onClick={handleGoogle} disabled={busy || !isSupabaseConfigured}>
            <Chrome size={17} />
            Continue with Google
          </button>

          <div className="auth-divider"><span>or use email</span></div>

          <form className="auth-form" onSubmit={handleEmailSubmit}>
            <label htmlFor="auth-email">Email address</label>
            <div className="auth-input-wrap">
              <Mail size={16} aria-hidden="true" />
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                value={email}
                onChange={event => setEmail(event.target.value)}
                required
                disabled={busy || !isSupabaseConfigured}
              />
            </div>

            <label htmlFor="auth-password">Password</label>
            <div className="auth-input-wrap">
              <LockKeyhole size={16} aria-hidden="true" />
              <input
                id="auth-password"
                type="password"
                autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                placeholder="At least 8 characters"
                value={password}
                onChange={event => setPassword(event.target.value)}
                minLength={8}
                required
                disabled={busy || !isSupabaseConfigured}
              />
            </div>

            <button className="auth-submit-button" type="submit" disabled={busy || !isSupabaseConfigured}>
              {busy ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
              {!busy && <ArrowRight size={16} />}
            </button>
          </form>

          <p className="auth-mode-toggle">
            {mode === 'login' ? 'New to GreenMind?' : 'Already have an account?'}{' '}
            <button type="button" onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(null); setMessage(null) }}>
              {mode === 'login' ? 'Create an account' : 'Sign in'}
            </button>
          </p>
          <p className="auth-privacy-note">Your cloud provider credentials stay on the backend and are never used as sign-in credentials.</p>
        </div>
      </section>
    </main>
  )
}

export function AuthCallbackPage() {
  const { session, loading } = useAuth()
  const navigate = useNavigate()
  const [exchangeError, setExchangeError] = useState<string | null>(null)
  const [exchanging, setExchanging] = useState(true)

  useEffect(() => {
    if (session) {
      navigate('/', { replace: true })
      return
    }

    const query = new URLSearchParams(window.location.search)
    const hashParams = new URLSearchParams(window.location.hash.replace(/^#/, ''))
    const errorDescription =
      query.get('error_description') ||
      query.get('error') ||
      hashParams.get('error_description') ||
      hashParams.get('error')

    if (errorDescription) {
      setExchangeError(decodeURIComponent(errorDescription.replace(/\+/g, ' ')))
      setExchanging(false)
      return
    }

    const code = query.get('code')
    if (code && supabase) {
      supabase.auth.exchangeCodeForSession(code).then(({ data, error }) => {
        if (error) {
          // If code was already exchanged by detectSessionInUrl, check if session is active
          supabase?.auth.getSession().then(({ data: sessData }) => {
            if (sessData.session) {
              navigate('/', { replace: true })
            } else {
              setExchangeError(error.message)
              setExchanging(false)
            }
          })
        } else if (data.session) {
          navigate('/', { replace: true })
        }
      }).catch((err: any) => {
        setExchangeError(err?.message || 'Authentication exchange failed.')
        setExchanging(false)
      })
      return
    }

    // Wait a brief period for detectSessionInUrl / onAuthStateChange if not using code query
    const timer = window.setTimeout(async () => {
      if (supabase) {
        const { data } = await supabase.auth.getSession()
        if (data.session) {
          navigate('/', { replace: true })
          return
        }
      }
      if (!loading && !session) {
        setExchangeError('The authentication session was not returned. Please try signing in again.')
        setExchanging(false)
      }
    }, 1500)

    return () => window.clearTimeout(timer)
  }, [session, loading, navigate])

  if (session) return <Navigate to="/" replace />

  return (
    <main className="auth-loading" role="status">
      {exchanging ? 'Finishing your sign in…' : (
        <div className="auth-callback-error">
          <h1>Sign in could not be completed</h1>
          <p>{exchangeError || 'The session was not returned. Please try again.'}</p>
          <a href="/login" className="auth-callback-link">Return to sign in</a>
        </div>
      )}
    </main>
  )
}
