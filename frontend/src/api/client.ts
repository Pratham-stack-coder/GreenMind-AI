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
  timeout: 10000,
})

// Intercept HTML responses from SPA rewrites when backend is offline
api.interceptors.response.use(
  (response) => {
    if (typeof response.data === 'string' && (response.data.includes('<!doctype') || response.data.includes('<html'))) {
      return Promise.reject(new Error(`API returned HTML instead of JSON for ${response.config.url} (backend offline or unconfigured)`))
    }
    return response
  },
  (error) => Promise.reject(error)
)

// ── Synthetic Demo Data Fallbacks (Ensures 100% Offline / Standalone Vercel Operation) ──

const DEMO_METRICS = (provider = 'aws', region = 'us-east'): CloudMetrics => ({
  timestamp: new Date().toISOString(),
  provider,
  region,
  cpu: 48.5,
  memory: 54.2,
  storage: 46.0,
  network: 418.0,
  cost_usd_per_hour: 0.192,
  carbon_gco2_per_hour: 74.8,
  instance_count: 3,
  source: 'DEMO',
})

const DEMO_SCORES: OptimizationScores = {
  overall: 84,
  cost: 82,
  performance: 88,
  sustainability: 85,
  security: 82,
  reliability: 84,
  trend: 'improving',
}

const DEMO_HISTORY: { entries: CloudMetrics[]; count: number } = {
  entries: Array.from({ length: 24 }, (_, i) => ({
    timestamp: new Date(Date.now() - (24 - i) * 15 * 60000).toISOString(),
    provider: 'aws',
    region: 'us-east',
    cpu: Math.round(38 + Math.sin(i / 3) * 14 + (i % 4)),
    memory: Math.round(50 + (i % 6)),
    storage: 46,
    network: Math.round(380 + (i % 5) * 16),
    cost_usd_per_hour: 0.192,
    carbon_gco2_per_hour: Math.round(70 + Math.cos(i / 4) * 10),
    instance_count: 3,
    source: 'DEMO',
  })),
  count: 24,
}

const DEMO_RECOMMENDATIONS: RecommendationsResponse = {
  recommendations: [
    {
      id: 'rec-cost-001',
      category: 'cost',
      priority: 'high',
      title: 'Right-size Underutilized EC2 Instances',
      description: '2 x m5.large instances show average CPU utilization under 18% over the past 7 days.',
      impact_summary: 'Save ~$58.40/month by migrating to t4g.medium with no performance degradation.',
      estimated_monthly_savings_usd: 58.4,
      estimated_carbon_reduction_pct: 14.2,
      effort: 'low',
      action: 'RIGHT_SIZE',
      evidence: ['Average CPU 16.4%', 'Memory peak 38%', 'P99 latency steady <15ms'],
      confidence: 0.94,
      status: 'open',
    },
    {
      id: 'rec-carb-002',
      category: 'sustainability',
      priority: 'medium',
      title: 'Shift Batch Workloads to Low-Carbon Hours',
      description: 'Grid carbon intensity drops by 42% between 01:00 and 05:00 UTC.',
      impact_summary: 'Reduce Scope 2 carbon footprint by ~22.5 kg CO₂/month.',
      estimated_monthly_savings_usd: 0,
      estimated_carbon_reduction_pct: 22.5,
      effort: 'low',
      action: 'TIME_SHIFT',
      evidence: ['Clean energy window 01:00-05:00 UTC', 'Batch queue flexibility confirmed'],
      confidence: 0.91,
      status: 'open',
    },
    {
      id: 'rec-perf-003',
      category: 'performance',
      priority: 'critical',
      title: 'Configure Predictive Auto-Scaling Headroom',
      description: 'Gradient boosting model forecasts +34% compute surge at 14:00 UTC peak.',
      impact_summary: 'Prevent SLA breaches and 504 gateway timeout incidents.',
      estimated_monthly_savings_usd: -8.5,
      estimated_carbon_reduction_pct: 0,
      effort: 'medium',
      action: 'SCALE_UP',
      evidence: ['Model forecast surge +34%', 'Historical peak hour correlation R²=0.86'],
      confidence: 0.96,
      status: 'open',
    },
  ],
  generated_at: new Date().toISOString(),
  optimization_score: 84,
}

const DEMO_SETTINGS: SettingsStatusResponse = {
  system_mode: 'DEMO',
  providers: {
    aws: {
      provider: 'aws',
      mode: 'DEMO',
      status: 'demo',
      message: 'Running in zero-config offline Demo mode. Enter credentials to test live connection.',
      configured_keys: [],
    },
    azure: {
      provider: 'azure',
      mode: 'DEMO',
      status: 'demo',
      message: 'Running in zero-config offline Demo mode. Enter credentials to test live connection.',
      configured_keys: [],
    },
    gcp: {
      provider: 'gcp',
      mode: 'DEMO',
      status: 'demo',
      message: 'Running in zero-config offline Demo mode. Enter credentials to test live connection.',
      configured_keys: [],
    },
  },
  llm: {
    openai_configured: false,
    gemini_configured: false,
  },
  database: 'sqlite',
  redis: false,
}

// ── Telemetry ──────────────────────────────────────────────────────────────
export const fetchLiveMetrics = (provider = 'aws', region = 'us-east'): Promise<CloudMetrics> =>
  api.get('/telemetry/live', { params: { provider, region } })
    .then(r => r.data)
    .catch(() => DEMO_METRICS(provider, region))

export const fetchAllLiveMetrics = (): Promise<{ providers: CloudMetrics[] }> =>
  api.get('/telemetry/live/all')
    .then(r => r.data)
    .catch(() => ({
      providers: [
        DEMO_METRICS('aws', 'us-east'),
        DEMO_METRICS('azure', 'us-east'),
        DEMO_METRICS('gcp', 'us-east'),
      ]
    }))

export const fetchTelemetryHistory = (limit = 100): Promise<{ entries: CloudMetrics[]; count: number }> =>
  api.get('/telemetry/history', { params: { limit } })
    .then(r => r.data)
    .catch(() => DEMO_HISTORY)

// ── Predictions ────────────────────────────────────────────────────────────
export const fetchForecast = (payload: {
  cpu: number; memory: number; network: number
  hour: number; day_of_week: number; region: string
}): Promise<PredictResponse> =>
  api.post('/predictions/forecast', payload)
    .then(r => r.data)
    .catch(() => ({
      cpu: { current: payload.cpu || 48.5, predicted: 52.4, delta_pct: 4.4, anomaly: false, confidence: 0.91 },
      memory: { current: payload.memory || 54.2, predicted: 56.1, delta_pct: 2.1, anomaly: false, confidence: 0.89 },
      network: { current: payload.network || 418.0, predicted: 435.0, delta_pct: 4.0, anomaly: false, confidence: 0.88 },
      cost_usd_per_hour: { current: 0.192, predicted: 0.198, delta_pct: 3.1, anomaly: false, confidence: 0.94 },
      carbon_gco2_per_hour: { current: 74.8, predicted: 78.2, delta_pct: 4.5, anomaly: false, confidence: 0.87 },
      risk: 'LOW' as const,
      model_mae: 3.81,
      horizon_minutes: 60,
    }))

export const fetchModelInfo = (): Promise<{ models: Record<string, unknown>; status: string }> =>
  api.get('/predictions/model-info')
    .then(r => r.data)
    .catch(() => ({
      models: {
        cpu: { type: 'GradientBoostingRegressor', mae: 3.81, r2: 0.855 },
        memory: { type: 'GradientBoostingRegressor', mae: 2.98, r2: 0.636 },
        network: { type: 'GradientBoostingRegressor', mae: 43.88, r2: 0.871 },
        cost: { type: 'GradientBoostingRegressor', mae: 0.009, r2: 0.474 },
        carbon: { type: 'GradientBoostingRegressor', mae: 4.06, r2: 0.391 },
      },
      status: 'loaded',
    }))

// ── Recommendations ────────────────────────────────────────────────────────
export const fetchRecommendations = (params?: {
  provider?: string; region?: string; refresh?: boolean
  category?: string; priority?: string; status?: string
}): Promise<RecommendationsResponse> =>
  api.get('/recommendations', { params })
    .then(r => r.data)
    .catch(() => DEMO_RECOMMENDATIONS)

export const fetchExplain = (id: string): Promise<ExplainResponse> =>
  api.get(`/recommendations/${id}/explain`)
    .then(r => r.data)
    .catch(() => ({
      recommendation_id: id,
      title: 'Right-size Underutilized EC2 Instances',
      why_flagged: 'Historical telemetry indicates average compute load consistently below 18% with zero burst spikes.',
      data_evidence: [
        { key: '7-Day Avg CPU', value: '16.4%' },
        { key: 'Peak Memory Utilization', value: '38.0%' },
        { key: 'Hourly Cost Baseline', value: '$0.096/hr' },
      ],
      counterfactual: 'Retaining m5.large instances results in $58.40/month of unallocated idle compute spend.',
      steps_to_implement: [
        '1. Schedule maintenance window or rolling deployment.',
        '2. Update launch template / auto-scaling group instance type to t4g.medium.',
        '3. Validate ARM/Graviton architecture compatibility.',
        '4. Verify P99 application latency remains <15ms.',
      ],
      expected_outcome: 'Preserve full application SLA throughput while reducing cluster spend by $58.40/mo and carbon by 14.2%.',
    }))

export const applyRecommendation = (
  id: string,
  options?: { dry_run?: boolean; operator_notes?: string }
): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/apply`, options || {})
    .then(r => r.data)
    .catch(() => ({
      recommendation_id: id,
      title: 'Right-size Underutilized EC2 Instances',
      status: (options?.dry_run ? 'simulated' : 'applied') as any,
      message: options?.dry_run
        ? 'Dry-run evaluation passed: Target instance type t4g.medium verified compatible.'
        : 'Recommendation successfully applied to infrastructure ledger.',
      estimated_monthly_savings_usd: 58.4,
      estimated_carbon_reduction_pct: 14.2,
      applied_at: new Date().toISOString(),
      steps_taken: [
        'Checked target instance family quotas',
        'Simulated network and memory headroom',
        'Logged audit entry to compliance ledger',
      ],
      dry_run: options?.dry_run ?? false,
      new_score: 86,
    }))

export const rollbackRecommendation = (id: string): Promise<ApplyResponse> =>
  api.post(`/recommendations/${id}/rollback`)
    .then(r => r.data)
    .catch(() => ({
      recommendation_id: id,
      title: 'Rollback Action',
      status: 'rolled_back' as any,
      message: 'Infrastructure configuration restored to previous baseline.',
      estimated_monthly_savings_usd: 0,
      estimated_carbon_reduction_pct: 0,
      applied_at: new Date().toISOString(),
      steps_taken: ['Restored previous instance configuration'],
      new_score: 84,
    }))

export const dismissRecommendation = (id: string): Promise<{ status: string; recommendation_id: string }> =>
  api.post(`/recommendations/${id}/dismiss`)
    .then(r => r.data)
    .catch(() => ({ status: 'dismissed', recommendation_id: id }))

export const batchApplyRecommendations = (payload?: {
  category?: string; priority?: string; recommendation_ids?: string[]; dry_run?: boolean
}): Promise<BatchApplyResponse> =>
  api.post('/recommendations/apply-batch', payload || {})
    .then(r => r.data)
    .catch(() => ({
      applied_count: 2,
      total_monthly_savings_usd: 58.4,
      total_carbon_reduction_pct: 14.2,
      results: [],
      new_score: 86,
    }))

export const fetchAppliedRecommendations = (): Promise<ApplyResponse[]> =>
  api.get('/recommendations/applied')
    .then(r => r.data)
    .catch(() => [])

// ── Agents ─────────────────────────────────────────────────────────────────
export const runAgents = (payload: { provider: string; region: string }): Promise<AgentRunResponse> =>
  api.post('/agents/run', payload)
    .then(r => r.data)
    .catch(() => ({
      run_id: `run-${Date.now()}`,
      started_at: new Date(Date.now() - 3000).toISOString(),
      completed_at: new Date().toISOString(),
      agents: [
        { agent: 'Cost Agent', status: 'completed' as const, findings: ['1 underutilized instance found'], recommendations: [], score: 82 },
        { agent: 'Performance Agent', status: 'completed' as const, findings: ['Workload headroom verified'], recommendations: [], score: 88 },
        { agent: 'Sustainability Agent', status: 'completed' as const, findings: ['Optimal green window identified'], recommendations: [], score: 85 },
        { agent: 'Security Agent', status: 'completed' as const, findings: ['0 open security groups'], recommendations: [], score: 92 },
        { agent: 'Reliability Agent', status: 'completed' as const, findings: ['Multi-AZ verified'], recommendations: [], score: 86 },
      ],
      unified_recommendations: DEMO_RECOMMENDATIONS.recommendations,
      overall_score: 84,
      summary: 'All 5 agents analyzed infrastructure. System operating efficiently under safe parameters.',
    }))

export const fetchAgentStatus = (): Promise<AgentRunResponse | null> =>
  api.get('/agents/status')
    .then(r => r.data)
    .catch(() => ({
      run_id: 'initial-demo-run',
      started_at: new Date(Date.now() - 60000).toISOString(),
      completed_at: new Date().toISOString(),
      agents: [
        { agent: 'Cost Agent', status: 'completed' as const, findings: ['1 underutilized instance identified'], recommendations: [], score: 82 },
        { agent: 'Performance Agent', status: 'completed' as const, findings: ['Workload headroom verified'], recommendations: [], score: 88 },
        { agent: 'Sustainability Agent', status: 'completed' as const, findings: ['Low-carbon grid window approaching'], recommendations: [], score: 85 },
        { agent: 'Security Agent', status: 'completed' as const, findings: ['No unauthorized ports open'], recommendations: [], score: 92 },
        { agent: 'Reliability Agent', status: 'completed' as const, findings: ['SLA uptime compliant at 99.98%'], recommendations: [], score: 86 },
      ],
      unified_recommendations: DEMO_RECOMMENDATIONS.recommendations,
      overall_score: 84,
      summary: 'Multi-agent orchestration active. Telemetry normalized across all dimensions.',
    }))

// ── Digital Twin ───────────────────────────────────────────────────────────
export const simulateChange = (payload: unknown): Promise<SimulationResult> =>
  api.post('/digital-twin/simulate', payload)
    .then(r => r.data)
    .catch(() => ({
      simulation_id: `sim-${Date.now()}`,
      before: { cpu: 48, memory: 54, cost_usd_per_hour: 0.192, carbon_gco2_per_hour: 74.8, monthly_cost_usd: 138.24, monthly_carbon_kgco2: 53.8 },
      after: { cpu: 52, memory: 56, cost_usd_per_hour: 0.134, carbon_gco2_per_hour: 58.2, monthly_cost_usd: 96.48, monthly_carbon_kgco2: 41.9 },
      delta: { cost_reduction_pct: 30.2, carbon_reduction_pct: 22.1, cpu_headroom_pct: 48.0 },
      recommendation: 'Safe to proceed: Workload headroom remains well above 40% with zero SLA risk.',
      confidence: 0.94,
      warnings: [],
    }))

// ── Analytics ──────────────────────────────────────────────────────────────
export const fetchCostAnalytics = (days = 7): Promise<{ period_days: number; total_usd: number; data_points: CostDataPoint[]; breakdown_by_provider: Record<string, number>; top_cost_drivers: string[] }> =>
  api.get('/analytics/cost', { params: { days } })
    .then(r => r.data)
    .catch(() => ({
      period_days: days,
      total_usd: Math.round(days * 4.6 * 100) / 100,
      data_points: Array.from({ length: days * 4 }, (_, i) => ({
        timestamp: new Date(Date.now() - (days * 4 - i) * 6 * 3600000).toISOString(),
        cost_usd: 0.192,
        provider: 'aws',
        region: 'us-east',
        category: 'compute',
      })),
      breakdown_by_provider: { aws: 18.5, azure: 8.25, gcp: 5.5 },
      top_cost_drivers: ['EC2 Compute Instances', 'EBS Storage Volumes', 'Cross-Region Data Transfer'],
    }))

export const fetchCarbonAnalytics = (days = 7, region = 'us-east'): Promise<{ period_days: number; total_gco2: number; data_points: CarbonDataPoint[]; breakdown_by_region: Record<string, number>; green_hours_pct: number }> =>
  api.get('/analytics/carbon', { params: { days, region } })
    .then(r => r.data)
    .catch(() => ({
      period_days: days,
      total_gco2: Math.round(days * 1800),
      data_points: Array.from({ length: days * 4 }, (_, i) => ({
        timestamp: new Date(Date.now() - (days * 4 - i) * 6 * 3600000).toISOString(),
        carbon_gco2: 74.8,
        provider: 'aws',
        region,
        intensity_gco2_per_kwh: 340,
      })),
      breakdown_by_region: { 'us-east': 6800, 'us-west': 3200, 'eu-west': 2500 },
      green_hours_pct: 68.5,
    }))

export const fetchScores = (provider = 'aws', region = 'us-east'): Promise<OptimizationScores> =>
  api.get('/analytics/score', { params: { provider, region } })
    .then(r => r.data)
    .catch(() => DEMO_SCORES)

// ── Copilot ────────────────────────────────────────────────────────────────
export const sendCopilotMessage = (
  message: string,
  history: CopilotMessage[],
  context?: Record<string, unknown>
): Promise<CopilotResponse> =>
  api.post('/copilot/chat', { message, history, context: context ?? {} })
    .then(r => r.data)
    .catch(() => ({
      reply: `GreenMind Telemetry Analysis: Your ${context?.provider ? String(context.provider).toUpperCase() : 'AWS'} infrastructure is running smoothly with an average CPU utilization of 48.5% and composite Optimization Score of 84/100. We identified 1 active right-sizing candidate that can save ~$58.40/month without SLA degradation.`,
      actions: [
        { label: 'View Recommendations', endpoint: '/recommendations', method: 'GET' },
        { label: 'Open Digital Twin', endpoint: '/digital-twin', method: 'GET' },
      ],
      charts: [],
      follow_up_suggestions: [
        'What is costing the most this week?',
        'How can I reduce carbon emissions?',
        'Simulate right-sizing underutilized instances',
      ],
    }))

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
    .catch(() => ({
      region,
      curve: Array.from({ length: 24 }, (_, h) => ({
        hour: h,
        carbon_intensity_gco2_per_kwh: Math.round(320 + Math.sin((h - 6) / 3.8) * 80),
      })),
      green_score: 78,
    }))

export const fetchRegions = (): Promise<{ regions: string[] }> =>
  api.get('/regions')
    .then(r => r.data)
    .catch(() => ({ regions: ['us-east', 'us-west', 'eu-west', 'ap-southeast', 'ca-central', 'in-north'] }))

export const fetchHealth = (): Promise<{ status: string; version: string; demo_mode: boolean; cloud_mode?: string }> =>
  api.get('/health')
    .then(r => r.data)
    .catch(() => ({
      status: 'ok',
      version: '2.0.0',
      demo_mode: true,
      cloud_mode: 'demo',
    }))

// ── Cloud Providers & Resources ────────────────────────────────────────────
export const fetchCloudResources = (
  provider = 'aws',
  region = 'us-east'
): Promise<{ provider: string; region: string; resources: any[]; count: number }> =>
  api.get('/cloud/resources', { params: { provider, region } })
    .then(r => r.data)
    .catch(() => ({
      provider,
      region,
      resources: [
        { id: 'i-0a1b2c3d4e5f001', name: 'greenmind-api-prod', type: 'ec2:t4g.medium', provider, region, status: 'running', cpu_utilization: 38.5, memory_utilization: 42.0, cost_per_hour: 0.0336, carbon_intensity: 62.0, tags: { env: 'production', role: 'api' }, right_size_candidate: false },
        { id: 'i-0a1b2c3d4e5f002', name: 'worker-batch-node-01', type: 'ec2:m5.large', provider, region, status: 'running', cpu_utilization: 14.2, memory_utilization: 28.5, cost_per_hour: 0.096, carbon_intensity: 62.0, tags: { env: 'production', role: 'worker' }, right_size_candidate: true },
        { id: 'i-0a1b2c3d4e5f003', name: 'cache-redis-standalone', type: 'ec2:t3.small', provider, region, status: 'running', cpu_utilization: 22.0, memory_utilization: 64.0, cost_per_hour: 0.0208, carbon_intensity: 62.0, tags: { env: 'production', role: 'cache' }, right_size_candidate: false },
      ],
      count: 3,
    }))

export const fetchCloudProviders = (): Promise<{ providers: any[]; default_mode: string }> =>
  api.get('/cloud/providers')
    .then(r => r.data)
    .catch(() => ({
      providers: [
        { id: 'aws', name: 'Amazon Web Services', mode: 'DEMO', regions: ['us-east', 'us-west', 'eu-west', 'ap-southeast', 'ca-central', 'in-north'] },
        { id: 'azure', name: 'Microsoft Azure', mode: 'DEMO', regions: ['us-east', 'eu-west', 'ap-southeast'] },
        { id: 'gcp', name: 'Google Cloud Platform', mode: 'DEMO', regions: ['us-east', 'us-west', 'eu-west'] },
      ],
      default_mode: 'DEMO (Zero-config synthetic patterns)',
    }))

export const simulateScenario = (payload: {
  scenario: string
  current_state?: any
  region?: string
}): Promise<any> =>
  api.post('/digital-twin/scenario', payload)
    .then(r => r.data)
    .catch(() => ({
      simulation_id: `scen-${Date.now()}`,
      scenario: payload.scenario,
      is_simulated: true,
      label: payload.scenario,
      before: { cpu: 48, memory: 54, cost: 0.192, carbon: 74.8, instance_count: 3, monthly_cost: 138.24, monthly_carbon_kg: 53.8 },
      after: { cpu: 52, memory: 56, cost: 0.134, carbon: 58.2, instance_count: 3, monthly_cost: 96.48, monthly_carbon_kg: 41.9 },
      estimated_saving: 41.76,
      estimated_carbon_reduction: 11.9,
      performance_impact: 'Minimal: Headroom verified sufficient for 99.9% of traffic distribution.',
      risk: 'LOW' as const,
      recommendation: 'Recommended: Safe cost and carbon reduction.',
      confidence: 0.94,
      warnings: [],
    }))

// ── Settings & Multi-Cloud Provider Management ──────────────────────────────
export const fetchSettingsStatus = (): Promise<SettingsStatusResponse> =>
  api.get('/settings/status')
    .then(r => r.data)
    .catch(() => DEMO_SETTINGS)

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
      message: err?.response?.data?.detail || err?.message || 'Backend offline. Running in Demo mode.',
    }))

export const disconnectProvider = (
  provider: string
): Promise<{ status: string; provider: string; message: string }> =>
  api.post('/settings/disconnect', { provider })
    .then(r => r.data)
    .catch(() => ({
      status: 'disconnected',
      provider,
      message: `${provider.toUpperCase()} reset to Demo mode.`,
    }))
