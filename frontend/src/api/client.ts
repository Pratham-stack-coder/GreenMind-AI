import axios from 'axios'
import type {
  CloudMetrics,
  PredictResponse,
  RecommendationsResponse,
  AgentRunResponse,
  OptimizationScores,
  SimulationResult,
  CopilotResponse,
  CopilotMessage,
  CostDataPoint,
  CarbonDataPoint,
  CarbonPoint,
} from '../types'

const api = axios.create({
  baseURL: '/api/v1',
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
  category?: string; priority?: string
}): Promise<RecommendationsResponse> =>
  api.get('/recommendations', { params }).then(r => r.data)

export const fetchExplain = (id: string): Promise<unknown> =>
  api.get(`/recommendations/${id}/explain`).then(r => r.data)

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
export const sendCopilotMessage = (message: string, history: CopilotMessage[]): Promise<CopilotResponse> =>
  api.post('/copilot/chat', { message, history }).then(r => r.data)

export const fetchCopilotSuggestions = (): Promise<{ suggestions: string[] }> =>
  api.get('/copilot/suggestions').then(r => r.data)

// ── Carbon / System ────────────────────────────────────────────────────────
export const fetchCarbonCurve = (region = 'us-east'): Promise<{ region: string; curve: CarbonPoint[]; green_score: number }> =>
  api.get('/carbon-curve', { baseURL: '/', params: { region } }).then(r => r.data)

export const fetchRegions = (): Promise<{ regions: string[] }> =>
  api.get('/regions', { baseURL: '/' }).then(r => r.data)

export const fetchHealth = (): Promise<{ status: string; version: string; demo_mode: boolean }> =>
  axios.get('/health').then(r => r.data)
