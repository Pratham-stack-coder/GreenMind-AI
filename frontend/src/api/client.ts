import axios from 'axios'
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

const RAW_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || ''
const API_BASE = RAW_BASE ? `${RAW_BASE.replace(/\/+$/, '')}/api/v1` : '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

// ── Telemetry ──────────────────────────────────────────────────────────────
export const fetchLiveMetrics = (provider = 'aws', region = 'us-east'): Promise<CloudMetrics> =>
  api.get('/telemetry/live', { params: { provider, region } }).then(r => r.data)

export const fetchAllLiveMetrics = (): Promise<{ providers: CloudMetrics[] }> =>
  api.get('/telemetry/live/all').then(r => r.data)

export const fetchTelemetryHistory = (limit = 100): Promise<{ entries: CloudMetrics[]; count: number }> =>
  api.get('/telemetry/history', { params: { limit } }).then(r => r.data)

// ── Predictions ────────────────────────────────────────────────────────────
export const fetchForecast = (payload: {
  cpu: number; memory: number; network: number
  hour: number; day_of_week: number; region: string
}): Promise<PredictResponse> =>
  api.post('/predictions/forecast', payload).then(r => r.data)

export const fetchModelInfo = (): Promise<{ models: Record<string, unknown>; status: string }> =>
  api.get('/predictions/model-info').then(r => r.data)

// ── Recommendations ────────────────────────────────────────────────────────
export const fetchRecommendations = (params?: {
  provider?: string; region?: string; refresh?: boolean
  category?: string; priority?: string; status?: string
}): Promise<RecommendationsResponse> =>
  api.get('/recommendations', { params }).then(r => r.data)

export const fetchExplain = (id: string): Promise<ExplainResponse> =>
  api.get(`/recommendations/${id}/explain`).then(r => r.data)

export const applyRecommendation = (
  id: string,
  options?: { dry_run?: boolean; operator_notes?: string }
): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/apply`, options || {}).then(r => r.data)

export const rollbackRecommendation = (id: string): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/rollback`).then(r => r.data)

export const dismissRecommendation = (id: string): Promise<{ status: string; recommendation_id: string }> =>
  api.post(`/recommendations/${id}/dismiss`).then(r => r.data)

export const batchApplyRecommendations = (payload?: {
  category?: string; priority?: string; recommendation_ids?: string[]; dry_run?: boolean
}): Promise<BatchApplyResponse> =>
  api.post('/recommendations/apply-batch', payload || {}).then(r => r.data)

export const fetchAppliedRecommendations = (): Promise<ApplyResponse[]> =>
  api.get('/recommendations/applied').then(r => r.data)

// ── Agents ─────────────────────────────────────────────────────────────────
export const runAgents = (payload: { provider: string; region: string }): Promise<AgentRunResponse> =>
  api.post('/agents/run', payload).then(r => r.data)

export const fetchAgentStatus = (): Promise<AgentRunResponse | null> =>
  api.get('/agents/status').then(r => r.data)

// ── Digital Twin ───────────────────────────────────────────────────────────
export const simulateChange = (payload: unknown): Promise<SimulationResult> =>
  api.post('/digital-twin/simulate', payload).then(r => r.data)

// ── Analytics ──────────────────────────────────────────────────────────────
export const fetchCostAnalytics = (days = 7): Promise<{ period_days: number; total_usd: number; data_points: CostDataPoint[]; breakdown_by_provider: Record<string, number>; top_cost_drivers: string[] }> =>
  api.get('/analytics/cost', { params: { days } }).then(r => r.data)

export const fetchCarbonAnalytics = (days = 7, region = 'us-east'): Promise<{ period_days: number; total_gco2: number; data_points: CarbonDataPoint[]; breakdown_by_region: Record<string, number>; green_hours_pct: number }> =>
  api.get('/analytics/carbon', { params: { days, region } }).then(r => r.data)

export const fetchScores = (provider = 'aws', region = 'us-east'): Promise<OptimizationScores> =>
  api.get('/analytics/score', { params: { provider, region } }).then(r => r.data)

// ── Copilot ────────────────────────────────────────────────────────────────
export const sendCopilotMessage = (
  message: string,
  history: CopilotMessage[],
  context?: Record<string, unknown>
): Promise<CopilotResponse> =>
  api.post('/copilot/chat', { message, history, context: context ?? {} }).then(r => r.data)

export const fetchCopilotSuggestions = (): Promise<{ suggestions: string[] }> =>
  api.get('/copilot/suggestions').then(r => r.data)

// ── Carbon / System ────────────────────────────────────────────────────────
export const fetchCarbonCurve = (region = 'us-east'): Promise<{ region: string; curve: CarbonPoint[]; green_score: number }> =>
  api.get('/carbon-curve', { params: { region } }).then(r => r.data)

export const fetchRegions = (): Promise<{ regions: string[] }> =>
  api.get('/regions').then(r => r.data)

export const fetchHealth = (): Promise<{ status: string; version: string; demo_mode: boolean; cloud_mode?: string }> =>
  api.get('/health').then(r => r.data)

// ── Cloud Providers & Resources ────────────────────────────────────────────
export const fetchCloudResources = (
  provider = 'aws',
  region = 'us-east'
): Promise<{ provider: string; region: string; resources: any[]; count: number }> =>
  api.get('/cloud/resources', { params: { provider, region } }).then(r => r.data)

export const fetchCloudProviders = (): Promise<{ providers: any[]; default_mode: string }> =>
  api.get('/cloud/providers').then(r => r.data)

export const simulateScenario = (payload: {
  scenario: string
  current_state?: any
  region?: string
}): Promise<any> =>
  api.post('/digital-twin/scenario', payload).then(r => r.data)

// ── Settings & Multi-Cloud Provider Management ──────────────────────────────
export const fetchSettingsStatus = (): Promise<SettingsStatusResponse> =>
  api.get('/settings/status').then(r => r.data)

export const testProviderConnection = (
  provider: string,
  credentials?: Record<string, string>
): Promise<TestConnectionResponse> =>
  api.post('/settings/test-connection', { provider, credentials: credentials || {} }).then(r => r.data)

export const configureProvider = (
  provider: string,
  credentials: Record<string, string>
): Promise<{ status: string; provider: string; message: string; test_result?: TestConnectionResponse }> =>
  api.post('/settings/configure', { provider, credentials }).then(r => r.data)

export const disconnectProvider = (
  provider: string
): Promise<{ status: string; provider: string; message: string }> =>
  api.post('/settings/disconnect', { provider }).then(r => r.data)
