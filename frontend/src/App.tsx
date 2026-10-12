import React, { useCallback, useEffect, useRef, useState } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { Activity, AlertTriangle, LogOut, RefreshCw } from 'lucide-react'
import Sidebar from './components/Layout/Sidebar'
import TopBar from './components/Layout/TopBar'
import NotificationsPanel from './components/Layout/NotificationsPanel'
import DashboardPage from './pages/DashboardPage'
import CloudResourcesPage from './pages/CloudResourcesPage'
import PredictionsPage from './pages/PredictionsPage'
import CostOptimizationPage from './pages/CostOptimizationPage'
import CarbonIntelligencePage from './pages/CarbonIntelligencePage'
import RecommendationsPage from './pages/RecommendationsPage'
import AgentsPage from './pages/AgentsPage'
import DigitalTwinPage from './pages/DigitalTwinPage'
import CopilotPage from './pages/CopilotPage'
import AnalyticsPage from './pages/AnalyticsPage'
import SettingsPage from './pages/SettingsPage'
import AuthPage, { AuthCallbackPage } from './pages/AuthPage'
import LegalPage from './pages/LegalPage'
import { useAuth } from './auth/AuthContext'
import { testBackendConnection } from './api/client'
import { useAppStore } from './store'
import type { BackendHealthCheckResult } from './api/client'

const pageTransition = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.25 },
}

function AuthLoadingScreen({ label }: { label: string }) {
  return (
    <main className="auth-loading" role="status" aria-live="polite">
      <span className="auth-spinner" aria-hidden="true" />
      <span>{label}</span>
    </main>
  )
}

function RequireAuth() {
  const { loading, session } = useAuth()
  const location = useLocation()

  if (loading) return <AuthLoadingScreen label="Restoring your session…" />
  if (!session) return <Navigate to="/login" replace state={{ from: location }} />
  return <Outlet />
}

function BackendConnectionGate() {
  const { session, signOut } = useAuth()
  const [checking, setChecking] = useState(true)
  const [attempt, setAttempt] = useState(1)
  const [result, setResult] = useState<BackendHealthCheckResult | null>(null)
  const runId = useRef(0)

  const connect = useCallback(async () => {
    const currentRun = ++runId.current
    setChecking(true)
    setResult(null)

    for (let currentAttempt = 1; currentAttempt <= 3; currentAttempt += 1) {
      if (runId.current !== currentRun) return
      setAttempt(currentAttempt)
      const nextResult = await testBackendConnection()
      if (runId.current !== currentRun) return
      setResult(nextResult)
      if (nextResult.connected) {
        setChecking(false)
        return
      }

      // Configuration problems need a deploy-time fix; retrying cannot repair them.
      if (nextResult.auth_configured === false || nextResult.backend_url_trusted === false) break
      if (currentAttempt < 3) {
        await new Promise(resolve => window.setTimeout(resolve, 12_000))
      }
    }

    if (runId.current === currentRun) setChecking(false)
  }, [])

  useEffect(() => {
    void connect()
    return () => { runId.current += 1 }
  }, [connect, session?.user.id])

  if (checking || !result?.connected) {
    const configurationIssue = result?.auth_configured === false || result?.backend_url_trusted === false
    return (
      <main className="connection-shell">
        <section className="connection-card">
          <div className={`connection-icon ${checking ? 'is-checking' : 'has-error'}`}>
            {checking ? <Activity size={24} /> : <AlertTriangle size={24} />}
          </div>
          <p className="auth-eyebrow">GREENMIND AI</p>
          <h1>{checking ? 'Connecting your workspace' : 'Could not connect to GreenMind'}</h1>
          <p className="connection-copy">
            {checking
              ? 'Your sign in is ready. Checking the configured API connection.'
              : result?.error || 'The backend did not respond. Try again in a moment.'}
          </p>
          {checking && <p className="connection-attempt">Connection check {attempt} of 3 The service may take a moment to start.</p>}
          {!checking && configurationIssue && (
            <div className="auth-alert auth-alert-error" role="alert">
              Deploy the updated backend and set its Supabase Auth environment variables on the hosting service. Your dashboard stays locked until the backend verifies sessions.
            </div>
          )}
          <div className="connection-actions">
            {!checking && (
              <button type="button" className="auth-submit-button" onClick={() => void connect()}>
                <RefreshCw size={16} /> Retry connection
              </button>
            )}
            <button type="button" className="auth-secondary-button" onClick={() => void signOut()}>
              <LogOut size={16} /> Sign out
            </button>
          </div>
        </section>
      </main>
    )
  }

  return <Outlet />
}

function DashboardLayout() {
  const { sidebarCollapsed } = useAppStore()
  const sidebarWidth = sidebarCollapsed ? 64 : 240
  const location = useLocation()
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    const onApiError = (event: Event) => {
      const message = (event as CustomEvent<{ message?: string }>).detail?.message
      if (message) setApiError(message)
    }
    window.addEventListener('greenmind-api-error', onApiError)
    return () => window.removeEventListener('greenmind-api-error', onApiError)
  }, [])

  return (
    <div className="main-layout" style={{ '--sidebar-width': `${sidebarWidth}px` } as React.CSSProperties}>
      <Sidebar />
      <div className="content-area">
        <TopBar />
        <NotificationsPanel />
        {apiError && (
          <div className="auth-alert auth-alert-error" role="alert" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, margin: '12px 20px 0' }}>
            <span><AlertTriangle size={14} aria-hidden="true" /> {apiError}</span>
            <button type="button" className="btn btn-secondary text-xs" onClick={() => setApiError(null)}>Dismiss</button>
          </div>
        )}
        <a className="skip-link" href="#main-content">Skip to content</a>
        <main id="main-content" className="page-content">
          <AnimatePresence mode="wait">
            <motion.div key={location.pathname} {...pageTransition}>
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/privacy" element={<LegalPage kind="privacy" />} />
      <Route path="/terms" element={<LegalPage kind="terms" />} />
      <Route path="/login" element={<AuthPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route element={<RequireAuth />}>
        <Route element={<BackendConnectionGate />}>
          <Route element={<DashboardLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="cloud-resources" element={<CloudResourcesPage />} />
            <Route path="predictions" element={<PredictionsPage />} />
            <Route path="cost-optimization" element={<CostOptimizationPage />} />
            <Route path="carbon-intelligence" element={<CarbonIntelligencePage />} />
            <Route path="recommendations" element={<RecommendationsPage />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="digital-twin" element={<DigitalTwinPage />} />
            <Route path="copilot" element={<CopilotPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
