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

/**
 * Returns the currently active backend URL.
 * Priority:
 * 1. User runtime override saved in localStorage
 * 2. Build-time environment variable import.meta.env.VITE_API_BASE_URL
 * 3. Default deployed Render backend (when running in deployed browser environments like Vercel)
 * 4. Empty string '' (when running locally, falling back to Vite dev proxy /api/v1)
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
    !window.location.hostname.includes('localhost') &&
    !window.location.hostname.includes('127.0.0.1')
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
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return window.location.origin
  }
  return new URL(DEFAULT_PRODUCTION_BACKEND).origin
}

export function isTrustedBackendUrl(rawUrl = getActiveBackendUrl()): boolean {
  try {
    return new URL(normalizeApiBaseUrl(rawUrl), window.location.origin).origin === expectedBackendOrigin()
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
      return { ...healthResult, error: 'Supabase browser authentication is not configured for this frontend.' }
    }

    const { data, error } = await supabase.auth.getSession()
    if (error || !data.session?.access_token) {
      return { ...healthResult, error: error?.message || 'Sign in again to validate your backend session.' }
    }

    try {
      await axios.get(`${base}/auth/session`, {
        timeout: 20000,
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${data.session.access_token}`,
        },
      })
      return { ...healthResult, connected: true, error: undefined }
    } catch (authError: any) {
      return {
        ...healthResult,
        error: authError?.response?.data?.detail || authError?.message || 'The backend could not verify this Supabase session.',
      }
    }
  } catch (err: any) {
    const latencyMs = Date.now() - startTime
    const message =
      err?.code === 'ECONNABORTED' || err?.code === 'ETIMEDOUT'
        ? 'Connection timed out. If your Render free instance is sleeping, it takes ~30-50 seconds to warm up. Please retry in a few moments.'
        : err?.response?.data?.detail || err?.message || 'Failed to connect to backend server'
    return {
      connected: false,
      url: base,
      latencyMs,
      backend_url_trusted: isTrustedBackendUrl(rawUrl),
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
    if (data.session?.access_token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${data.session.access_token}`
    }
  }
  return config
})

// Intercept HTML responses from SPA rewrites when backend is offline
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
  (error) => {
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


export const fetchExplain = (id: string, provider = 'aws', region = 'us-east'): Promise<ExplainResponse> =>
  api.get(`/recommendations/${id}/explain`, { params: { provider, region } })
    .then(r => r.data)


export const applyRecommendation = (
  id: string,
  options?: { dry_run?: boolean; operator_notes?: string },
  provider = 'aws',
  region = 'us-east'
): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/apply`, options || {}, { params: { provider, region } })
    .then(r => r.data)

export const rollbackRecommendation = (id: string, provider = 'aws', region = 'us-east'): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/rollback`, {}, { params: { provider, region } })
    .then(r => r.data)

export const dismissRecommendation = (id: string, provider = 'aws', region = 'us-east'): Promise<{ status: string; recommendation_id: string }> =>
  api.post(`/recommendations/${id}/dismiss`, {}, { params: { provider, region } })
    .then(r => r.data)

export const batchApplyRecommendations = (
  payload?: { category?: string; priority?: string; recommendation_ids?: string[]; dry_run?: boolean },
  provider = 'aws',
  region = 'us-east'
): Promise<BatchApplyResponse> =>
  api.post('/recommendations/apply-batch', payload || {}, { params: { provider, region } })
    .then(r => r.data)

export const fetchAppliedRecommendations = (provider = 'aws', region = 'us-east'): Promise<ApplyResponse[]> =>
  api.get('/recommendations/applied', { params: { provider, region } })
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
export const fetchCostAnalytics = (days = 7, provider = 'aws', region = 'us-east'): Promise<{
  period_days: number
  total_usd: number
  data_points: CostDataPoint[]
  breakdown_by_provider: Record<string, number>
  top_cost_drivers: string[]
  source: string
  estimation_method?: string | null
  confidence: number
}> =>
  api.get('/analytics/cost', { params: { days, provider, region } })
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

