// ── API Types ──────────────────────────────────────────────────────────────

/** Data source types — non-negotiable data truth labels */
export type DataSourceType =
  | 'LIVE'
  | 'LIVE_AWS'
  | 'LIVE_AZURE'
  | 'LIVE_GCP'
  | 'DEMO'
  | 'ESTIMATED'
  | 'SIMULATED'
  | 'UNAVAILABLE'
  | 'ERROR'

export interface CloudMetrics {
  timestamp: string
  provider: string
  region: string
  resource_id?: string | null
  account_id?: string | null
  resource_type?: string
  cpu: number
  /** Null when UNAVAILABLE (requires CloudWatch Agent / google-cloud-ops-agent) */
  memory: number | null
  /** Null when UNAVAILABLE (requires CloudWatch Agent) */
  storage: number | null
  /** Null when UNAVAILABLE (provider did not return network data) */
  network: number | null
  network_in?: number | null
  network_out?: number | null
  cost_usd_per_hour: number
  carbon_gco2_per_hour: number
  instance_count: number
  status?: string
  source: DataSourceType
  /** Source of memory metric specifically (may differ from main source) */
  memory_source?: DataSourceType
  /** Explains why memory may be UNAVAILABLE */
  memory_note?: string
  /** Source of cost data (LIVE_AWS if Cost Explorer, ESTIMATED otherwise) */
  cost_source?: DataSourceType
  /** Source of network data specifically */
  network_source?: DataSourceType
  last_updated?: string | null
}


export interface MetricForecast {
  current: number
  predicted: number
  delta_pct: number
  anomaly: boolean
  confidence: number
}

export interface PredictResponse {
  cpu: MetricForecast
  memory: MetricForecast
  network: MetricForecast
  cost_usd_per_hour: MetricForecast
  carbon_gco2_per_hour: MetricForecast
  risk: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
  model_mae: number | null
  horizon_minutes: number
}

export interface RecommendationItem {
  id: string
  category: 'cost' | 'performance' | 'sustainability' | 'security' | 'reliability'
  priority: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  impact_summary: string
  estimated_monthly_savings_usd: number
  estimated_carbon_reduction_pct: number
  effort: 'low' | 'medium' | 'high'
  action: string
  evidence: string[]
  confidence: number
  status?: 'open' | 'applied' | 'dismissed'
  applied_at?: string
  steps_taken?: string[]
}

export interface RecommendationsResponse {
  recommendations: RecommendationItem[]
  generated_at: string
  optimization_score: number
}

export interface ApplyResponse {
  recommendation_id: string
  title: string
  status: 'applied' | 'failed' | 'pending' | 'rolled_back' | 'simulated'
  message: string
  estimated_monthly_savings_usd: number
  estimated_carbon_reduction_pct: number
  applied_at: string
  steps_taken: string[]
  dry_run?: boolean
  new_score?: number
}

export interface BatchApplyResponse {
  applied_count: number
  total_monthly_savings_usd: number
  total_carbon_reduction_pct: number
  results: ApplyResponse[]
  new_score: number
}

export interface ExplainResponse {
  recommendation_id: string
  title: string
  why_flagged: string
  data_evidence: { key: string; value: string }[]
  counterfactual: string
  steps_to_implement: string[]
  expected_outcome: string
}

export interface AgentResult {
  agent: string
  status: 'completed' | 'skipped' | 'error'
  findings: string[]
  recommendations: RecommendationItem[]
  score: number
}

export interface AgentRunResponse {
  run_id: string
  started_at: string
  completed_at: string
  agents: AgentResult[]
  unified_recommendations: RecommendationItem[]
  overall_score: number
  summary: string
}

export interface OptimizationScores {
  overall: number
  cost: number
  performance: number
  sustainability: number
  security: number
  reliability: number
  trend: 'improving' | 'stable' | 'declining'
  source?: DataSourceType
}

export interface SimulationResult {
  simulation_id: string
  before: {
    cpu: number
    memory: number | null
    cost_usd_per_hour: number
    carbon_gco2_per_hour: number
    monthly_cost_usd: number
    monthly_carbon_kgco2: number
    source?: DataSourceType
  }
  after: {
    cpu: number
    memory: number | null
    cost_usd_per_hour: number
    carbon_gco2_per_hour: number
    monthly_cost_usd: number
    monthly_carbon_kgco2: number
    source?: DataSourceType
  }
  delta: Record<string, number>
  recommendation: string
  confidence: number
  warnings: string[]
  source?: DataSourceType
  baseline_source?: DataSourceType
}

export interface CarbonPoint {
  hour: number
  carbon_intensity_gco2_per_kwh: number
}

export interface CopilotMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface CopilotResponse {
  reply: string
  actions: { label: string; endpoint: string; method: string }[]
  charts: unknown[]
  follow_up_suggestions: string[]
}

export interface CostDataPoint {
  timestamp: string
  cost_usd: number
  provider: string
  region: string
  category: string
}

export interface CarbonDataPoint {
  timestamp: string
  carbon_gco2: number
  provider: string
  region: string
  intensity_gco2_per_kwh: number
}

export interface CloudResource {
  id: string
  name: string
  type: string
  provider: string
  region: string
  status: string
  cpu_utilization: number
  memory_utilization: number
  cost_per_hour: number
  carbon_intensity: number
  tags: Record<string, string>
  right_size_candidate: boolean
}

export interface ConflictResolutionItem {
  conflict_type: string
  description: string
  conflicting_agents: string[]
  agent_recommendations: Record<string, string>
  reconciliation_rationale: string
  final_decision: string
  confidence: number
}

export interface ScenarioSimulationResult {
  simulation_id: string
  scenario: string
  is_simulated: boolean
  label: string
  before: {
    cpu: number
    memory: number
    cost: number
    carbon: number
    instance_count: number
    monthly_cost: number
    monthly_carbon_kg: number
  }
  after: {
    cpu: number
    memory: number
    cost: number
    carbon: number
    instance_count: number
    monthly_cost: number
    monthly_carbon_kg: number
  }
  estimated_saving: number
  estimated_carbon_reduction: number
  performance_impact: string
  risk: 'LOW' | 'MEDIUM' | 'HIGH'
  recommendation: string
  confidence: number
  warnings: string[]
}

export interface ProviderConnectionStatus {
  provider: string
  mode: 'DEMO' | 'LIVE'
  status: 'connected' | 'not_configured' | 'auth_failed' | 'permission_denied' | 'service_unavailable' | 'demo'
  message: string
  last_checked?: string
  configured_keys?: string[]
}

export interface SettingsStatusResponse {
  system_mode: 'DEMO' | 'LIVE'
  providers: {
    aws: ProviderConnectionStatus
    azure: ProviderConnectionStatus
    gcp: ProviderConnectionStatus
  }
  llm: {
    openai_configured: boolean
    gemini_configured: boolean
  }
  database: string
  redis: boolean
}

export interface TestConnectionResponse {
  provider: string
  status: string
  message: string
  caller_arn?: string
  tested_at: string
}

