// ── API Types ──────────────────────────────────────────────────────────────

export interface CloudMetrics {
  timestamp: string
  provider: string
  region: string
  cpu: number
  memory: number
  storage: number
  network: number
  cost_usd_per_hour: number
  carbon_gco2_per_hour: number
  instance_count: number
  source: 'DEMO' | 'LIVE'
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
}

export interface SimulationResult {
  simulation_id: string
  before: {
    cpu: number
    memory: number
    cost_usd_per_hour: number
    carbon_gco2_per_hour: number
    monthly_cost_usd: number
    monthly_carbon_kgco2: number
  }
  after: {
    cpu: number
    memory: number
    cost_usd_per_hour: number
    carbon_gco2_per_hour: number
    monthly_cost_usd: number
    monthly_carbon_kgco2: number
  }
  delta: Record<string, number>
  recommendation: string
  confidence: number
  warnings: string[]
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
