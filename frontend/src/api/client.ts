import axios from 'axios'
import { supabase } from '../auth/supabase'
import type {
  CloudMetrics,
  PredictResponse,
  RecommendationsResponse,
  ApplyResponse,
  BatchApplyResponse,
  ExplainResponse,
  AgentRunResponse,
  OptimizationScores,
  SimulationResult,
  CopilotResponse,
  CopilotMessage,
  CostDataPoint,
  CarbonDataPoint,
  CarbonPoint,
  SettingsStatusResponse,
  TestConnectionResponse,
} from '../types'

// ── Backend URL Management & Multi-Host Normalization ──────────────────────────
const BACKEND_STORAGE_KEY = 'greenmind_backend_url'

/**
 * Normalizes any backend URL so that:
 * - Empty/undefined string -> '/api/v1' (local dev proxy / relative route)
 * - Trailing slashes are stripped
 * - Avoids duplicate '/api/v1' if the user provides https://your-app.onrender.com/api/v1
 * - Example: 'https://my-backend.onrender.com' -> 'https://my-backend.onrender.com/api/v1'
 * - Example: 'https://my-backend.onrender.com/api/v1/' -> 'https://my-backend.onrender.com/api/v1'
 */
export function normalizeApiBaseUrl(rawUrl?: string): string {
  const trimmed = (rawUrl || '').trim().replace(/\/+$/, '')
  if (!trimmed) return '/api/v1'
  if (trimmed.endsWith('/api/v1')) return trimmed
  return `${trimmed}/api/v1`
}

export const DEFAULT_PRODUCTION_BACKEND = 'https://greenmind-backend-zqn5.onrender.com'

export function isLocalNetworkHost(hostname: string): boolean {
  if (!hostname) return true
  const lower = hostname.toLowerCase().trim()
  if (
    lower === 'localhost' ||
    lower === '127.0.0.1' ||
    lower === '0.0.0.0' ||
    lower === '::1' ||
    lower === '[::1]' ||
    lower.endsWith('.local') ||
    lower.endsWith('.internal') ||
    lower.endsWith('.lan')
  ) {
    return true
  }
  // Check private / link-local IPv4 addresses
  if (
    /^10\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(lower) ||
    /^172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}$/.test(lower) ||
    /^192\.168\.\d{1,3}\.\d{1,3}$/.test(lower) ||
    /^169\.254\.\d{1,3}\.\d{1,3}$/.test(lower)
  ) {
    return true
  }
  return false
}

export function isCloudDeployedHost(hostname: string): boolean {
  if (!hostname) return false
  const lower = hostname.toLowerCase().trim()
  return lower.endsWith('.vercel.app') || lower.includes('vercel.app')
}

/**
 * Returns the currently active backend URL.
 * Priority:
 * 1. User runtime override saved in localStorage
 * 2. Build-time environment variable import.meta.env.VITE_API_BASE_URL
 * 3. Default deployed Render backend (when running in deployed browser environments like Vercel)
 * 4. Empty string '' (when running locally or over LAN, falling back to Vite/Nginx proxy /api/v1)
 */
export function getActiveBackendUrl(): string {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem(BACKEND_STORAGE_KEY)
    if (saved && saved.trim()) {
      if (isTrustedBackendUrl(saved.trim())) return saved.trim()
      localStorage.removeItem(BACKEND_STORAGE_KEY)
    }
  }

  const envUrl = ((import.meta.env.VITE_API_BASE_URL as string | undefined) || '').trim()
  if (envUrl) return envUrl

  // In deployed browser environments (e.g. *.vercel.app), default to the live Render backend
  if (
    typeof window !== 'undefined' &&
    window.location.hostname &&
    isCloudDeployedHost(window.location.hostname)
  ) {
    return DEFAULT_PRODUCTION_BACKEND
  }

  return ''
}

/**
 * Saves a dynamic backend URL override to localStorage and updates Axios baseURL immediately.
 */
export function setActiveBackendUrl(url: string): void {
  if (typeof window !== 'undefined') {
    const trimmed = url.trim()
    if (trimmed) {
      localStorage.setItem(BACKEND_STORAGE_KEY, trimmed)
    } else {
      localStorage.removeItem(BACKEND_STORAGE_KEY)
    }
  }
  api.defaults.baseURL = normalizeApiBaseUrl(getActiveBackendUrl())
}

/**
 * Clears any dynamic backend URL override from localStorage, reverting to VITE_API_BASE_URL.
 */
export function resetActiveBackendUrl(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(BACKEND_STORAGE_KEY)
  }
  api.defaults.baseURL = normalizeApiBaseUrl(getActiveBackendUrl())
}

function expectedBackendOrigin(): string {
  const configuredUrl = ((import.meta.env.VITE_API_BASE_URL as string | undefined) || '').trim()
  if (configuredUrl) return new URL(configuredUrl, window.location.origin).origin
  if (typeof window !== 'undefined' && window.location.hostname && isCloudDeployedHost(window.location.hostname)) {
    return new URL(DEFAULT_PRODUCTION_BACKEND).origin
  }
  return window.location.origin
}

export function isTrustedBackendUrl(rawUrl = getActiveBackendUrl()): boolean {
  try {
    const normalized = normalizeApiBaseUrl(rawUrl)
    const targetUrl = new URL(normalized, window.location.origin)
    const expectedOrigin = expectedBackendOrigin()

    // 1. Direct match with expected origin (same origin or configured production backend)
    if (targetUrl.origin === expectedOrigin) return true

    // 2. Relative URLs or same origin are always trusted
    if (targetUrl.origin === window.location.origin) return true

    // 3. Same hostname on another port (e.g. frontend on 5173, backend on 8000)
    if (targetUrl.hostname === window.location.hostname) return true

    // 4. In local / LAN development environments, allow connecting to any local/LAN backend
    if (isLocalNetworkHost(window.location.hostname) && isLocalNetworkHost(targetUrl.hostname)) {
      return true
    }

    // 5. Default production backend is trusted
    if (targetUrl.origin === new URL(DEFAULT_PRODUCTION_BACKEND).origin) {
      return true
    }

    return false
  } catch {
    return false
  }
}

export interface BackendHealthCheckResult {
  connected: boolean
  url: string
  latencyMs: number
  status?: string
  version?: string
  demo_mode?: boolean
  cloud_mode?: string
  database?: string
  auth_configured?: boolean
  backend_url_trusted?: boolean
  is_auth_error?: boolean
  error?: string
}

/**
 * Tests direct live connectivity to a Render backend health check endpoint.
 */
export async function testBackendConnection(targetUrl?: string): Promise<BackendHealthCheckResult> {
  const rawUrl = targetUrl !== undefined ? targetUrl.trim() : getActiveBackendUrl()
  const base = normalizeApiBaseUrl(rawUrl)
  const backendRoot = rawUrl.replace(/\/api\/v1\/?$/, '').replace(/\/+$/, '')
  const healthEndpoint = backendRoot ? `${backendRoot}/health` : '/health'
  const startTime = Date.now()

  try {
    const res = await axios.get(healthEndpoint, {
      timeout: 60000,
      headers: { 'Content-Type': 'application/json' },
    })

    if (typeof res.data === 'string' && (res.data.includes('<!doctype') || res.data.includes('<html'))) {
      throw new Error('Received HTML response instead of JSON. Ensure the URL points to your Render backend.')
    }

    const latencyMs = Date.now() - startTime
    const authConfigured = res.data?.auth_configured === true
    const backendUrlTrusted = isTrustedBackendUrl(rawUrl)
    const healthResult: BackendHealthCheckResult = {
      connected: false,
      url: base,
      latencyMs,
      status: res.data?.status || 'ok',
      version: res.data?.version || '2.0.0',
      demo_mode: Boolean(res.data?.demo_mode),
      cloud_mode: res.data?.cloud_mode,
      database: res.data?.database,
      auth_configured: authConfigured,
      backend_url_trusted: backendUrlTrusted,
      ...(!authConfigured ? {
        error: 'The Render backend does not report Supabase authentication as configured. Deploy the updated backend and set SUPABASE_URL.',
      } : {}),
      ...(authConfigured && !backendUrlTrusted ? {
        error: 'The backend responded, but it does not match this build’s trusted API origin. Set VITE_API_BASE_URL and redeploy before connecting accounts to another host.',
      } : {}),
    }

    if (res.data?.status !== 'ok' || !authConfigured || !backendUrlTrusted) return healthResult
    if (!supabase) {
      return { ...healthResult, is_auth_error: true, error: 'Supabase browser authentication is not configured for this frontend.' }
    }

    const { data, error } = await supabase.auth.getSession()
    let session = data?.session
    if (error || !session?.access_token) {
      return {
        ...healthResult,
        is_auth_error: true,
        error: error?.message || 'Please sign in to access your GreenMind workspace.',
      }
    }

    // Proactively refresh if the access token has expired or is expiring within 60s
    if (session.expires_at && (session.expires_at * 1000 - Date.now() < 60_000)) {
      try {
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
        if (!refreshError && refreshData.session?.access_token) {
          session = refreshData.session
        }
      } catch {
        // Fall back to current session
      }
    }

    try {
      await axios.get(`${base}/auth/session`, {
        timeout: 25000,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`,
        },
      })
      return { ...healthResult, connected: true, error: undefined }
    } catch (authError: any) {
      const status = authError?.response?.status
      const detail = authError?.response?.data?.detail
      let errorMessage = 'The backend could not verify this Supabase session.'
      let isAuthError = false

      if (status === 401) {
        isAuthError = true
        errorMessage = detail
          ? `Authentication rejected (${detail}). Your session may have expired — please sign out and sign in again.`
          : 'Authentication rejected: Invalid or expired access token. Please sign out and sign in again.'
      } else if (status === 403) {
        isAuthError = true
        errorMessage = detail
          ? `Access forbidden (${detail}). Your account is not authorized for this workspace.`
          : 'Access forbidden: Your account does not have permission to access GreenMind.'
      } else if (status && status >= 500) {
        errorMessage = detail
          ? `Backend server error (HTTP ${status}): ${detail}`
          : `Backend server error (HTTP ${status}) while validating session. Please retry in a moment.`
      } else if (authError?.code === 'ECONNABORTED' || authError?.message?.includes('timeout')) {
        errorMessage = 'Session validation timed out. The backend instance may still be warming up.'
      } else if (!authError?.response) {
        errorMessage = 'Unable to complete session verification. The server connection dropped or was interrupted.'
      } else {
        errorMessage = detail || authError?.message || errorMessage
      }

      return {
        ...healthResult,
        is_auth_error: isAuthError,
        error: errorMessage,
      }
    }
  } catch (err: any) {
    const latencyMs = Date.now() - startTime
    const isTimeout = err?.code === 'ECONNABORTED' || err?.code === 'ETIMEDOUT'
    const message = isTimeout
      ? 'Connection timed out. If your Render free instance is sleeping, it takes ~30-50 seconds to warm up. Please retry in a few moments.'
      : err?.response?.data?.detail || (err?.message === 'Network Error' ? 'Could not reach the GreenMind backend service. The instance may be waking up or offline.' : err?.message || 'Failed to connect to backend server')
    return {
      connected: false,
      url: base,
      latencyMs,
      backend_url_trusted: isTrustedBackendUrl(rawUrl),
      is_auth_error: false,
      error: message,
    }
  }
}

const api = axios.create({
  baseURL: normalizeApiBaseUrl(getActiveBackendUrl()),
  headers: { 'Content-Type': 'application/json' },
  timeout: 45000, // 45s accommodates Render free-tier cold starts
})

// Dynamically sync baseURL on each request in case localStorage changed
api.interceptors.request.use(async (config) => {
  const currentBase = normalizeApiBaseUrl(getActiveBackendUrl())
  config.baseURL = currentBase
  if (supabase) {
    // Do not send a bearer token to a runtime URL that differs from the
    // backend selected for this build.
    if (!isTrustedBackendUrl()) {
      throw new Error('The selected backend does not match VITE_API_BASE_URL. Set the trusted backend URL in the deployment environment and rebuild.')
    }

    const { data, error } = await supabase.auth.getSession()
    if (error) throw error
    let session = data.session
    if (session?.access_token) {
      if (session.expires_at && (session.expires_at * 1000 - Date.now() < 60_000)) {
        try {
          const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
          if (!refreshError && refreshData.session?.access_token) {
            session = refreshData.session
          }
        } catch {
          // Proceed with current session
        }
      }
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${session.access_token}`
    }
  }
  return config
})

// Intercept HTML responses from SPA rewrites when backend is offline, and auto-refresh on 401
api.interceptors.response.use(
  (response) => {
    if (typeof response.data === 'string' && (response.data.includes('<!doctype') || response.data.includes('<html'))) {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('greenmind-api-error', {
          detail: { message: 'The backend returned an invalid response. Check the backend URL and deployment configuration.' },
        }))
      }
      return Promise.reject(new Error(`API returned HTML instead of JSON for ${response.config.url} (backend offline or unconfigured)`))
    }
    return response
  },
  async (error) => {
    const originalRequest = error?.config
    if (error?.response?.status === 401 && originalRequest && !originalRequest._retry && supabase) {
      originalRequest._retry = true
      try {
        const { data: refreshData, error: refreshError } = await supabase.auth.refreshSession()
        if (!refreshError && refreshData.session?.access_token) {
          originalRequest.headers = originalRequest.headers || {}
          originalRequest.headers.Authorization = `Bearer ${refreshData.session.access_token}`
          return api(originalRequest)
        }
      } catch {
        // Fall through to error dispatch
      }
    }

    const requestUrl = String(error?.config?.url || '')
    const handledBySettingsForm = /\/settings\/(test-connection|configure|disconnect)/.test(requestUrl)
    if (typeof window !== 'undefined' && !handledBySettingsForm) {
      const status = error?.response?.status
      const message = status
        ? `Backend request failed (HTTP ${status}).`
        : 'Unable to reach the backend. Check your network and backend URL.'
      window.dispatchEvent(new CustomEvent('greenmind-api-error', { detail: { message } }))
    }
    return Promise.reject(error)
  }
)

// ── Telemetry ──────────────────────────────────────────────────────────────
export const fetchLiveMetrics = (provider = 'aws', region = 'us-east'): Promise<CloudMetrics> =>
  api.get('/telemetry/live', { params: { provider, region } })
    .then(r => r.data)


export const fetchAllLiveMetrics = (): Promise<{ providers: CloudMetrics[] }> =>
  api.get('/telemetry/live/all')
    .then(r => r.data)


export const fetchTelemetryHistory = (
  limit = 100,
  provider?: string,
  region?: string
): Promise<{ entries: CloudMetrics[]; count: number }> =>
  api.get('/telemetry/history', { params: { limit, provider, region } })
    .then(r => r.data)


// ── Predictions ────────────────────────────────────────────────────────────
export const fetchForecast = (payload: {
  cpu: number; memory: number; network: number
  hour: number; day_of_week: number; region: string
}): Promise<PredictResponse> =>
  api.post('/predictions/forecast', payload)
    .then(r => r.data)


export const fetchModelInfo = (): Promise<{ models: Record<string, unknown>; status: string }> =>
  api.get('/predictions/model-info')
    .then(r => r.data)


// ── Recommendations ────────────────────────────────────────────────────────
export const fetchRecommendations = (params?: {
  provider?: string; region?: string; refresh?: boolean
  category?: string; priority?: string; status?: string
}): Promise<RecommendationsResponse> =>
  api.get('/recommendations', { params })
    .then(r => r.data)


export const fetchExplain = (id: string): Promise<ExplainResponse> =>
  api.get(`/recommendations/${id}/explain`)
    .then(r => r.data)


export const applyRecommendation = (
  id: string,
  options?: {
    dry_run?: boolean
    simulate?: boolean
    confirm_live?: boolean
    resource_id?: string
    target_instance_type?: string
    operator_notes?: string
    provider?: string
    region?: string
  }
): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/apply`, options || {})
    .then(r => r.data)

export const simulateRecommendation = (
  id: string,
  options?: { operator_notes?: string }
): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/simulate`, options || {})
    .then(r => r.data)

export const resetSimulation = (): Promise<{ status: string; message: string; baseline_score: number; current_score: number }> =>
  api.post('/recommendations/reset-simulation')
    .then(r => r.data)

export const rollbackRecommendation = (
  id: string,
  params?: { provider?: string; region?: string; operator_notes?: string }
): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/rollback`, null, { params })
    .then(r => r.data)

export const dismissRecommendation = (id: string): Promise<{ status: string; recommendation_id: string }> =>
  api.post(`/recommendations/${id}/dismiss`)
    .then(r => r.data)

export const batchApplyRecommendations = (payload?: {
  category?: string; priority?: string; recommendation_ids?: string[]; dry_run?: boolean
}): Promise<BatchApplyResponse> =>
  api.post('/recommendations/apply-batch', payload || {})
    .then(r => r.data)

export const fetchAppliedRecommendations = (): Promise<ApplyResponse[]> =>
  api.get('/recommendations/applied')
    .then(r => r.data)


// ── Agents ─────────────────────────────────────────────────────────────────
export const runAgents = (payload: { provider: string; region: string }): Promise<AgentRunResponse> =>
  api.post('/agents/run', payload)
    .then(r => r.data)


export const fetchAgentStatus = (): Promise<AgentRunResponse | null> =>
  api.get('/agents/status')
    .then(r => r.data)


// ── Digital Twin ───────────────────────────────────────────────────────────
export const simulateChange = (payload: unknown): Promise<SimulationResult> =>
  api.post('/digital-twin/simulate', payload)
    .then(r => r.data)


// ── Analytics ──────────────────────────────────────────────────────────────
export const fetchCostAnalytics = (days = 7): Promise<{ period_days: number; total_usd: number; data_points: CostDataPoint[]; breakdown_by_provider: Record<string, number>; top_cost_drivers: string[] }> =>
  api.get('/analytics/cost', { params: { days } })
    .then(r => r.data)


export const fetchCarbonAnalytics = (days = 7, region = 'us-east'): Promise<{ period_days: number; total_gco2: number; data_points: CarbonDataPoint[]; breakdown_by_region: Record<string, number>; green_hours_pct: number }> =>
  api.get('/analytics/carbon', { params: { days, region } })
    .then(r => r.data)


export const fetchScores = (provider = 'aws', region = 'us-east'): Promise<OptimizationScores> =>
  api.get('/analytics/score', { params: { provider, region } })
    .then(r => r.data)


// ── Copilot ────────────────────────────────────────────────────────────────
export const sendCopilotMessage = (
  message: string,
  history: CopilotMessage[],
  context?: Record<string, unknown>
): Promise<CopilotResponse> =>
  api.post('/copilot/chat', { message, history, context: context ?? {} })
    .then(r => r.data)


export const fetchCopilotSuggestions = (): Promise<{ suggestions: string[] }> =>
  api.get('/copilot/suggestions')
    .then(r => r.data)
    .catch(() => ({
      suggestions: [
        'What is costing the most this week?',
        'Why was scaling recommended?',
        'Simulate moving this workload to a greener region',
        'Compare AWS vs Azure efficiency',
      ],
    }))

// ── Carbon / System ────────────────────────────────────────────────────────
export const fetchCarbonCurve = (region = 'us-east'): Promise<{ region: string; curve: CarbonPoint[]; green_score: number }> =>
  api.get('/carbon-curve', { params: { region } })
    .then(r => r.data)


export const fetchRegions = (): Promise<{ regions: string[] }> =>
  api.get('/regions')
    .then(r => r.data)


export const fetchHealth = (): Promise<{ status: string; version: string; demo_mode: boolean; cloud_mode?: string }> =>
  api.get('/health')
    .then(r => r.data)


// ── Cloud Providers & Resources ────────────────────────────────────────────
export const fetchCloudResources = (
  provider = 'aws',
  region = 'us-east'
): Promise<{ provider: string; region: string; resources: any[]; count: number }> =>
  api.get('/cloud/resources', { params: { provider, region } })
    .then(r => r.data)


export const fetchCloudProviders = (): Promise<{ providers: any[]; default_mode: string }> =>
  api.get('/cloud/providers')
    .then(r => r.data)


export const simulateScenario = (payload: {
  scenario: string
  current_state?: any
  region?: string
}): Promise<any> =>
  api.post('/digital-twin/scenario', payload)
    .then(r => r.data)


// ── Settings & Multi-Cloud Provider Management ──────────────────────────────
export const fetchSettingsStatus = (): Promise<SettingsStatusResponse> =>
  api.get('/settings/status')
    .then(r => r.data)


export const testProviderConnection = (
  provider: string,
  credentials?: Record<string, string>
): Promise<TestConnectionResponse> =>
  api.post('/settings/test-connection', { provider, credentials: credentials || {} })
    .then(r => r.data)
    .catch((err) => ({
      provider,
      status: 'service_unavailable',
      message: err?.response?.data?.detail || err?.message || 'Backend connection unavailable. Enter backend URL or check status.',
      tested_at: new Date().toISOString(),
    }))

export const configureProvider = (
  provider: string,
  credentials: Record<string, string>
): Promise<{ status: string; provider: string; message: string; test_result?: TestConnectionResponse }> =>
  api.post('/settings/configure', { provider, credentials })
    .then(r => r.data)
    .catch((err) => ({
      status: 'error',
      provider,
      message: err?.response?.data?.detail || err?.message || 'Backend offline. Check the backend URL and retry.',
    }))

export const disconnectProvider = (
  provider: string
): Promise<{ status: string; provider: string; message: string }> =>
  api.post('/settings/disconnect', { provider })
    .then(r => r.data)

