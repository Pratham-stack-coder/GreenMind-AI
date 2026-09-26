import React, { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Settings, Cloud, Brain, Shield, RefreshCw, CheckCircle2,
  AlertCircle, Info, Lock, Eye, EyeOff, Trash2, Zap, Server, Database,
  Globe, ExternalLink, Activity, ArrowRight
} from 'lucide-react'
import {
  fetchSettingsStatus,
  testProviderConnection,
  configureProvider,
  disconnectProvider,
  getActiveBackendUrl,
  setActiveBackendUrl,
  resetActiveBackendUrl,
  testBackendConnection,
  normalizeApiBaseUrl,
  type BackendHealthCheckResult,
} from '../api/client'
import type { ProviderConnectionStatus, TestConnectionResponse } from '../types'

export default function SettingsPage() {
  const queryClient = useQueryClient()

  // ── Fetch real status from backend ──────────────────────────────────────────
  const { data: statusData, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['settings-status'],
    queryFn: fetchSettingsStatus,
    refetchInterval: 15000,
  })

  // ── Backend API & Deployment State ──────────────────────────────────────────
  const [backendUrlInput, setBackendUrlInput] = useState(getActiveBackendUrl())
  const [backendTesting, setBackendTesting] = useState(false)
  const [backendTestResult, setBackendTestResult] = useState<BackendHealthCheckResult | null>(null)
  const [backendSuccessMsg, setBackendSuccessMsg] = useState<string | null>(null)

  const handleTestBackend = async (urlToTest?: string) => {
    setBackendTesting(true)
    setBackendSuccessMsg(null)
    try {
      const result = await testBackendConnection(urlToTest ?? backendUrlInput)
      setBackendTestResult(result)
      if (result.connected) {
        setBackendSuccessMsg(`Backend connected (${result.latencyMs}ms)! FastAPI v${result.version} running in ${result.cloud_mode?.toUpperCase() || 'DEMO'} mode.`)
      }
    } finally {
      setBackendTesting(false)
    }
  }

  const handleSaveBackend = async () => {
    setBackendSuccessMsg(null)
    setActiveBackendUrl(backendUrlInput)
    await handleTestBackend(backendUrlInput)
    queryClient.invalidateQueries({ queryKey: ['health'] })
    queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    queryClient.invalidateQueries({ queryKey: ['topbar-live'] })
    setBackendSuccessMsg(`Active backend URL updated to: ${normalizeApiBaseUrl(backendUrlInput)}`)
  }

  const handleResetBackend = () => {
    resetActiveBackendUrl()
    const envUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) || ''
    setBackendUrlInput(envUrl)
    setBackendTestResult(null)
    setBackendSuccessMsg(envUrl ? `Reset to environment variable: ${envUrl}` : 'Reset to relative proxy default (/api/v1)')
    queryClient.invalidateQueries({ queryKey: ['health'] })
    queryClient.invalidateQueries({ queryKey: ['settings-status'] })
  }

  // ── AWS Form State ──────────────────────────────────────────────────────────
  const [awsKeyId, setAwsKeyId] = useState('')
  const [awsSecretKey, setAwsSecretKey] = useState('')
  const [awsRegion, setAwsRegion] = useState('us-east-1')
  const [showAwsSecret, setShowAwsSecret] = useState(false)

  // ── Azure Form State ────────────────────────────────────────────────────────
  const [azureSubId, setAzureSubId] = useState('')
  const [azureTenantId, setAzureTenantId] = useState('')
  const [azureClientId, setAzureClientId] = useState('')
  const [azureClientSecret, setAzureClientSecret] = useState('')
  const [showAzureSecret, setShowAzureSecret] = useState(false)

  // ── GCP Form State ──────────────────────────────────────────────────────────
  const [gcpProjectId, setGcpProjectId] = useState('')
  const [gcpServiceAccountJson, setGcpServiceAccountJson] = useState('')
  const [showGcpSecret, setShowGcpSecret] = useState(false)

  // ── LLM Form State ──────────────────────────────────────────────────────────
  const [geminiKey, setGeminiKey] = useState('')
  const [openaiKey, setOpenaiKey] = useState('')
  const [showLlmSecret, setShowLlmSecret] = useState(false)

  // ── Async Action States ─────────────────────────────────────────────────────
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [testResults, setTestResults] = useState<Record<string, TestConnectionResponse>>({})
  const [actionMessage, setActionMessage] = useState<{ provider: string; type: 'success' | 'error'; text: string } | null>(null)

  // Helper for provider status badge
  const renderStatusBadge = (providerStatus?: ProviderConnectionStatus) => {
    if (!providerStatus) return <span className="badge badge-muted">UNKNOWN</span>
    const { status, mode } = providerStatus

    if (status === 'connected') {
      return (
        <span className="badge badge-emerald flex items-center gap-1">
          <CheckCircle2 size={11} /> LIVE CONNECTED
        </span>
      )
    }
    if (status === 'auth_failed') {
      return (
        <span className="badge badge-red flex items-center gap-1">
          <AlertCircle size={11} /> AUTH FAILED
        </span>
      )
    }
    if (status === 'permission_denied') {
      return (
        <span className="badge badge-amber flex items-center gap-1">
          <AlertCircle size={11} /> PERMISSION DENIED
        </span>
      )
    }
    if (status === 'service_unavailable') {
      return (
        <span className="badge badge-amber flex items-center gap-1">
          <AlertCircle size={11} /> UNAVAILABLE
        </span>
      )
    }
    if (mode === 'DEMO' || status === 'demo') {
      return (
        <span className="badge badge-blue flex items-center gap-1">
          DEMO MODE
        </span>
      )
    }
    return <span className="badge badge-muted">NOT CONFIGURED</span>
  }

  // ── AWS Actions ─────────────────────────────────────────────────────────────
  const handleTestAws = async () => {
    setActionLoading('aws-test')
    setActionMessage(null)
    try {
      const creds: Record<string, string> = {}
      if (awsKeyId) creds.aws_access_key_id = awsKeyId
      if (awsSecretKey) creds.aws_secret_access_key = awsSecretKey
      if (awsRegion) creds.aws_default_region = awsRegion

      const res = await testProviderConnection('aws', creds)
      setTestResults(prev => ({ ...prev, aws: res }))
      if (res.status === 'connected') {
        setActionMessage({ provider: 'aws', type: 'success', text: `AWS verified: ${res.message}` })
      } else {
        setActionMessage({ provider: 'aws', type: 'error', text: res.message })
      }
    } catch (err: any) {
      setActionMessage({
        provider: 'aws',
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'AWS connection test failed'
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleSaveAws = async () => {
    if (!awsKeyId || !awsSecretKey) {
      setActionMessage({ provider: 'aws', type: 'error', text: 'Please enter both Access Key ID and Secret Access Key.' })
      return
    }
    setActionLoading('aws-save')
    setActionMessage(null)
    try {
      const res = await configureProvider('aws', {
        aws_access_key_id: awsKeyId,
        aws_secret_access_key: awsSecretKey,
        aws_default_region: awsRegion,
      })
      setActionMessage({
        provider: 'aws',
        type: res.test_result?.status === 'connected' ? 'success' : 'error',
        text: res.message
      })
      if (res.test_result) {
        setTestResults(prev => ({ ...prev, aws: res.test_result! }))
      }
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
      queryClient.invalidateQueries({ queryKey: ['cloud-providers'] })
    } catch (err: any) {
      setActionMessage({
        provider: 'aws',
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'Failed to save AWS configuration'
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDisconnectAws = async () => {
    setActionLoading('aws-disconnect')
    setActionMessage(null)
    try {
      const res = await disconnectProvider('aws')
      setAwsKeyId('')
      setAwsSecretKey('')
      setActionMessage({ provider: 'aws', type: 'success', text: res.message })
      setTestResults(prev => {
        const copy = { ...prev }
        delete copy.aws
        return copy
      })
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    } catch (err: any) {
      setActionMessage({ provider: 'aws', type: 'error', text: err.message })
    } finally {
      setActionLoading(null)
    }
  }

  // ── Azure Actions ───────────────────────────────────────────────────────────
  const handleTestAzure = async () => {
    setActionLoading('azure-test')
    setActionMessage(null)
    try {
      const creds: Record<string, string> = {}
      if (azureSubId) creds.azure_subscription_id = azureSubId
      if (azureTenantId) creds.azure_tenant_id = azureTenantId
      if (azureClientId) creds.azure_client_id = azureClientId
      if (azureClientSecret) creds.azure_client_secret = azureClientSecret

      const res = await testProviderConnection('azure', creds)
      setTestResults(prev => ({ ...prev, azure: res }))
      if (res.status === 'connected') {
        setActionMessage({ provider: 'azure', type: 'success', text: `Azure verified: ${res.message}` })
      } else {
        setActionMessage({ provider: 'azure', type: 'error', text: res.message })
      }
    } catch (err: any) {
      setActionMessage({
        provider: 'azure',
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'Azure connection test failed'
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleSaveAzure = async () => {
    if (!azureSubId || !azureTenantId || !azureClientId || !azureClientSecret) {
      setActionMessage({ provider: 'azure', type: 'error', text: 'All 4 Azure fields are required for live integration.' })
      return
    }
    setActionLoading('azure-save')
    setActionMessage(null)
    try {
      const res = await configureProvider('azure', {
        azure_subscription_id: azureSubId,
        azure_tenant_id: azureTenantId,
        azure_client_id: azureClientId,
        azure_client_secret: azureClientSecret,
      })
      setActionMessage({
        provider: 'azure',
        type: res.test_result?.status === 'connected' ? 'success' : 'error',
        text: res.message
      })
      if (res.test_result) {
        setTestResults(prev => ({ ...prev, azure: res.test_result! }))
      }
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    } catch (err: any) {
      setActionMessage({
        provider: 'azure',
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'Failed to save Azure configuration'
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDisconnectAzure = async () => {
    setActionLoading('azure-disconnect')
    setActionMessage(null)
    try {
      const res = await disconnectProvider('azure')
      setAzureSubId('')
      setAzureTenantId('')
      setAzureClientId('')
      setAzureClientSecret('')
      setActionMessage({ provider: 'azure', type: 'success', text: res.message })
      setTestResults(prev => {
        const copy = { ...prev }
        delete copy.azure
        return copy
      })
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    } catch (err: any) {
      setActionMessage({ provider: 'azure', type: 'error', text: err.message })
    } finally {
      setActionLoading(null)
    }
  }

  // ── GCP Actions ─────────────────────────────────────────────────────────────
  const handleTestGcp = async () => {
    setActionLoading('gcp-test')
    setActionMessage(null)
    try {
      const creds: Record<string, string> = {}
      if (gcpProjectId) creds.gcp_project_id = gcpProjectId
      if (gcpServiceAccountJson) creds.gcp_service_account_json = gcpServiceAccountJson

      const res = await testProviderConnection('gcp', creds)
      setTestResults(prev => ({ ...prev, gcp: res }))
      if (res.status === 'connected') {
        setActionMessage({ provider: 'gcp', type: 'success', text: `GCP verified: ${res.message}` })
      } else {
        setActionMessage({ provider: 'gcp', type: 'error', text: res.message })
      }
    } catch (err: any) {
      setActionMessage({
        provider: 'gcp',
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'GCP connection test failed'
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleSaveGcp = async () => {
    if (!gcpProjectId) {
      setActionMessage({ provider: 'gcp', type: 'error', text: 'GCP Project ID is required.' })
      return
    }
    setActionLoading('gcp-save')
    setActionMessage(null)
    try {
      const res = await configureProvider('gcp', {
        gcp_project_id: gcpProjectId,
        gcp_service_account_json: gcpServiceAccountJson,
      })
      setActionMessage({
        provider: 'gcp',
        type: res.test_result?.status === 'connected' ? 'success' : 'error',
        text: res.message
      })
      if (res.test_result) {
        setTestResults(prev => ({ ...prev, gcp: res.test_result! }))
      }
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    } catch (err: any) {
      setActionMessage({
        provider: 'gcp',
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'Failed to save GCP configuration'
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDisconnectGcp = async () => {
    setActionLoading('gcp-disconnect')
    setActionMessage(null)
    try {
      const res = await disconnectProvider('gcp')
      setGcpProjectId('')
      setGcpServiceAccountJson('')
      setActionMessage({ provider: 'gcp', type: 'success', text: res.message })
      setTestResults(prev => {
        const copy = { ...prev }
        delete copy.gcp
        return copy
      })
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    } catch (err: any) {
      setActionMessage({ provider: 'gcp', type: 'error', text: err.message })
    } finally {
      setActionLoading(null)
    }
  }

  // ── LLM Actions ─────────────────────────────────────────────────────────────
  const handleSaveLlm = async () => {
    setActionLoading('llm-save')
    setActionMessage(null)
    try {
      const creds: Record<string, string> = {}
      if (geminiKey) creds.gemini_api_key = geminiKey
      if (openaiKey) creds.openai_api_key = openaiKey

      const res = await configureProvider('llm', creds)
      setActionMessage({ provider: 'llm', type: 'success', text: res.message })
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    } catch (err: any) {
      setActionMessage({
        provider: 'llm',
        type: 'error',
        text: err?.response?.data?.detail || err.message || 'Failed to configure AI keys'
      })
    } finally {
      setActionLoading(null)
    }
  }

  const handleDisconnectLlm = async () => {
    setActionLoading('llm-disconnect')
    setActionMessage(null)
    try {
      const res = await disconnectProvider('llm')
      setGeminiKey('')
      setOpenaiKey('')
      setActionMessage({ provider: 'llm', type: 'success', text: res.message })
      queryClient.invalidateQueries({ queryKey: ['settings-status'] })
    } catch (err: any) {
      setActionMessage({ provider: 'llm', type: 'error', text: err.message })
    } finally {
      setActionLoading(null)
    }
  }

  const awsStatus = statusData?.providers?.aws
  const azureStatus = statusData?.providers?.azure
  const gcpStatus = statusData?.providers?.gcp
  const isDemo = statusData?.system_mode === 'DEMO'

  return (
    <div className="animate-fade-in" style={{ paddingBottom: 60 }}>
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 style={{ fontSize: 24, fontWeight: 800 }}>Multi-Cloud Settings & Security</h1>
            <span
              className={`badge ${isDemo ? 'badge-blue' : 'badge-emerald'}`}
              style={{ fontSize: 12, padding: '4px 10px' }}
            >
              {isDemo ? 'SYSTEM MODE: DEMO (Synthetic)' : 'SYSTEM MODE: LIVE TELEMETRY'}
            </span>
          </div>
          <p className="text-secondary text-sm mt-1">
            Configure real AWS, Azure, and GCP read-only telemetry, AI keys, and inspect system health.
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isFetching}
          className="btn btn-secondary btn-sm flex items-center gap-2"
        >
          <RefreshCw size={14} className={isFetching ? 'spin' : ''} />
          {isFetching ? 'Refreshing...' : 'Refresh Status'}
        </button>
      </div>

      {/* ── Security Model & Safe Mode Guarantee ─────────────────────────────── */}
      <div
        className="card mb-6"
        style={{
          background: 'linear-gradient(135deg, rgba(16,185,129,0.08) 0%, rgba(10,18,30,0.85) 100%)',
          borderColor: 'rgba(16,185,129,0.3)',
          padding: '16px 20px',
        }}
      >
        <div className="flex items-start gap-3">
          <Shield size={20} color="var(--emerald-400)" style={{ flexShrink: 0, marginTop: 2 }} />
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 style={{ fontSize: 14, fontWeight: 700, color: 'var(--emerald-400)' }}>
                Safe Mode Policy & Zero-Secret-Leakage Guarantee
              </h4>
              <span className="badge badge-emerald" style={{ fontSize: 10 }}>READ-ONLY ENFORCED</span>
            </div>
            <p className="text-xs text-secondary mt-1 leading-relaxed">
              GreenMind AI runs under a strict <strong>read-only telemetry policy</strong>. It will never modify, terminate,
              or resize live cloud infrastructure without explicit future operator sign-off.
              All credentials tested or saved in this session are validated directly with cloud provider APIs in-memory,
              never written in plaintext to databases, and never exposed in client API responses.
            </p>
          </div>
        </div>
      </div>

      <div className="flex-col gap-6" style={{ maxWidth: 880 }}>

        {/* ── Render Backend & Deployment Connection ─────────────────────────── */}
        <div className="card" style={{ borderColor: 'rgba(56, 189, 248, 0.35)', background: 'linear-gradient(180deg, rgba(14, 165, 233, 0.04) 0%, rgba(15, 23, 42, 0.4) 100%)' }}>
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Server size={18} color="var(--sky-400, #38bdf8)" />
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>FastAPI Backend Connection (Render.com)</h3>
            </div>
            {backendTestResult ? (
              backendTestResult.connected ? (
                <span className="badge badge-emerald flex items-center gap-1">
                  <CheckCircle2 size={11} /> LIVE CONNECTED ({backendTestResult.latencyMs}ms)
                </span>
              ) : (
                <span className="badge badge-red flex items-center gap-1">
                  <AlertCircle size={11} /> UNREACHABLE / ERROR
                </span>
              )
            ) : statusData ? (
              <span className="badge badge-emerald flex items-center gap-1">
                <CheckCircle2 size={11} /> ACTIVE ({getActiveBackendUrl() ? 'RENDER' : 'LOCAL'})
              </span>
            ) : (
              <span className="badge badge-blue flex items-center gap-1">
                DEMO FALLBACK
              </span>
            )}
          </div>

          <p className="text-xs text-secondary mb-4 leading-relaxed">
            Connect this Vercel-deployed frontend cockpit to your FastAPI backend running on Render.com
            (or local dev server). You can test connectivity, update the target URL on the fly, or configure build-time variables.
          </p>

          {/* Active URL Status Box */}
          <div
            style={{
              padding: '10px 14px',
              borderRadius: 8,
              background: 'rgba(0, 0, 0, 0.3)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              marginBottom: 16,
              fontSize: 12,
            }}
            className="flex items-center justify-between flex-wrap gap-2"
          >
            <div>
              <span className="text-muted" style={{ fontWeight: 600, marginRight: 8 }}>EFFECTIVE API ENDPOINT:</span>
              <code style={{ color: 'var(--sky-400, #38bdf8)', background: 'transparent', padding: 0 }}>
                {normalizeApiBaseUrl(getActiveBackendUrl())}
              </code>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-secondary">Source:</span>
              <span className="badge badge-muted" style={{ fontSize: 10 }}>
                {typeof window !== 'undefined' && localStorage.getItem('greenmind_backend_url')
                  ? 'Runtime Override (Local Storage)'
                  : (import.meta.env.VITE_API_BASE_URL ? 'Vite Environment Variable' : 'Default / Relative Proxy')}
              </span>
            </div>
          </div>

          {/* Input & Action Buttons */}
          <div className="flex-col gap-3">
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: 6 }}>
                Render Backend Service URL
              </label>
              <div className="flex gap-2 flex-wrap">
                <input
                  type="text"
                  placeholder="https://greenmind-backend.onrender.com"
                  value={backendUrlInput}
                  onChange={(e) => setBackendUrlInput(e.target.value)}
                  style={{
                    flex: '1 1 320px',
                    padding: '8px 12px',
                    borderRadius: 6,
                    fontSize: 13,
                    background: 'rgba(15, 23, 42, 0.6)',
                    border: '1px solid rgba(255, 255, 255, 0.12)',
                    color: 'var(--text-primary)',
                  }}
                />
                <button
                  type="button"
                  onClick={() => handleTestBackend(backendUrlInput)}
                  disabled={backendTesting}
                  className="btn btn-secondary btn-sm flex items-center gap-1.5"
                >
                  <RefreshCw size={13} className={backendTesting ? 'spin' : ''} />
                  {backendTesting ? 'Pinging...' : 'Test Connection'}
                </button>
                <button
                  type="button"
                  onClick={handleSaveBackend}
                  disabled={backendTesting}
                  className="btn btn-primary btn-sm flex items-center gap-1.5"
                >
                  <Zap size={13} />
                  Save & Connect
                </button>
                <button
                  type="button"
                  onClick={handleResetBackend}
                  disabled={backendTesting}
                  className="btn btn-ghost btn-sm text-muted"
                  title="Reset to environment variable or default relative route"
                >
                  Reset
                </button>
              </div>
              <span className="text-xs text-muted mt-1 block">
                Trailing slashes and duplicate <code>/api/v1</code> suffixes are normalized automatically.
              </span>
            </div>

            {/* Test Feedback Messages */}
            <AnimatePresence>
              {backendSuccessMsg && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="p-3 rounded text-xs flex items-center gap-2"
                  style={{ background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', color: '#34d399' }}
                >
                  <CheckCircle2 size={14} style={{ flexShrink: 0 }} />
                  <span>{backendSuccessMsg}</span>
                </motion.div>
              )}
              {backendTestResult && !backendTestResult.connected && (
                <motion.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="p-3 rounded text-xs flex items-start gap-2"
                  style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}
                >
                  <AlertCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
                  <div>
                    <div style={{ fontWeight: 600 }}>Backend Connection Failed</div>
                    <div className="mt-1 leading-relaxed">{backendTestResult.error}</div>
                    <div className="mt-2 text-muted" style={{ color: '#fca5a5' }}>
                      💡 <strong>Render Cold Starts:</strong> Render free-tier services spin down after 15 minutes of inactivity and take 30–50 seconds to boot up on the first request. Click <em>Test Connection</em> again in ~20 seconds.
                    </div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Quick deployment guide drawer */}
            <div
              style={{
                marginTop: 8,
                padding: '12px 14px',
                borderRadius: 6,
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid rgba(255, 255, 255, 0.06)',
                fontSize: 12,
              }}
            >
              <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 6 }} className="flex items-center gap-1.5">
                <Globe size={13} color="var(--sky-400, #38bdf8)" />
                <span>How Render.com ↔ Vercel.com Communication Works</span>
              </div>
              <ul className="text-muted leading-relaxed" style={{ paddingLeft: 18, listStyleType: 'disc', margin: 0 }}>
                <li>
                  <strong>On Vercel (Frontend):</strong> In your Vercel Project Settings &rarr; <em>Environment Variables</em>, add <code style={{ color: '#e2e8f0' }}>VITE_API_BASE_URL=https://your-app.onrender.com</code>, then trigger a redeploy.
                </li>
                <li>
                  <strong>On Render (Backend):</strong> GreenMind's backend automatically permits all <code style={{ color: '#e2e8f0' }}>*.vercel.app</code> domains out-of-the-box. For custom domains, set <code style={{ color: '#e2e8f0' }}>CORS_ORIGINS=https://mycustomapp.com</code> in Render's environment dashboard.
                </li>
                <li>
                  <strong>Instant Preview Testing:</strong> You don't have to wait for a Vercel rebuild! Enter your Render URL above and click <em>Save & Connect</em> to switch immediately in this browser.
                </li>
              </ul>
            </div>
          </div>
        </div>

        {/* ── AWS Connector ─────────────────────────────────────────────────── */}
        <div className="card">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Cloud size={18} color="var(--blue-400)" />
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Amazon Web Services (AWS)</h3>
            </div>
            {renderStatusBadge(awsStatus)}
          </div>

          <p className="text-xs text-secondary mb-4">
            Collects real EC2 instance utilization and CloudWatch telemetry (CPUUtilization, NetworkIn, NetworkOut).
          </p>

          <div className="flex-col gap-3">
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                AWS Access Key ID
              </label>
              <input
                type="text"
                placeholder={awsStatus?.configured_keys?.includes('aws_access_key_id') ? '•••••••••••••••••••• (Configured via env/session)' : 'e.g. AKIAIOSFODNN7EXAMPLE'}
                value={awsKeyId}
                onChange={e => setAwsKeyId(e.target.value)}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
                  AWS Secret Access Key
                </label>
                <button
                  type="button"
                  onClick={() => setShowAwsSecret(!showAwsSecret)}
                  className="btn btn-ghost btn-sm"
                  style={{ padding: '2px 6px', fontSize: 11 }}
                >
                  {showAwsSecret ? <EyeOff size={12} /> : <Eye size={12} />}
                  <span style={{ marginLeft: 4 }}>{showAwsSecret ? 'Hide' : 'Show'}</span>
                </button>
              </div>
              <input
                type={showAwsSecret ? 'text' : 'password'}
                placeholder={awsStatus?.configured_keys?.includes('aws_secret_access_key') ? '•••••••••••••••••••••••••••••••••••••••• (Configured)' : 'Enter AWS Secret Key'}
                value={awsSecretKey}
                onChange={e => setAwsSecretKey(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                AWS Default Region
              </label>
              <select
                value={awsRegion}
                onChange={e => setAwsRegion(e.target.value)}
              >
                <option value="us-east-1">US East (N. Virginia) — us-east-1</option>
                <option value="us-east-2">US East (Ohio) — us-east-2</option>
                <option value="us-west-1">US West (N. California) — us-west-1</option>
                <option value="us-west-2">US West (Oregon) — us-west-2</option>
                <option value="eu-west-1">Europe (Ireland) — eu-west-1</option>
                <option value="ap-southeast-1">Asia Pacific (Singapore) — ap-southeast-1</option>
                <option value="ca-central-1">Canada (Central) — ca-central-1</option>
                <option value="ap-south-1">Asia Pacific (Mumbai) — ap-south-1</option>
              </select>
            </div>

            {/* Action buttons */}
            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <button
                type="button"
                onClick={handleTestAws}
                disabled={actionLoading === 'aws-test'}
                className="btn btn-secondary btn-sm"
              >
                {actionLoading === 'aws-test' ? <RefreshCw size={13} className="spin" /> : <Zap size={13} />}
                Test Connection
              </button>

              <button
                type="button"
                onClick={handleSaveAws}
                disabled={actionLoading === 'aws-save'}
                className="btn btn-primary btn-sm"
              >
                {actionLoading === 'aws-save' ? <RefreshCw size={13} className="spin" /> : <CheckCircle2 size={13} />}
                Save & Connect
              </button>

              {awsStatus?.status === 'connected' && (
                <button
                  type="button"
                  onClick={handleDisconnectAws}
                  disabled={actionLoading === 'aws-disconnect'}
                  className="btn btn-ghost btn-sm text-secondary"
                  style={{ marginLeft: 'auto' }}
                >
                  <Trash2 size={13} />
                  Disconnect to Demo
                </button>
              )}
            </div>

            {/* Test result / feedback alert */}
            {testResults.aws && (
              <div
                className="card mt-2"
                style={{
                  padding: '10px 14px',
                  borderColor: testResults.aws.status === 'connected' ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)',
                  background: testResults.aws.status === 'connected' ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)'
                }}
              >
                <div className="text-xs">
                  <strong>Result:</strong> {testResults.aws.message}
                  {testResults.aws.caller_arn && (
                    <div className="text-muted mt-1 font-mono">Caller: {testResults.aws.caller_arn}</div>
                  )}
                </div>
              </div>
            )}

            <div className="text-xs text-muted mt-2">
              Minimum IAM Permissions required: <code>ec2:DescribeInstances</code>, <code>cloudwatch:GetMetricData</code>, <code>cloudwatch:ListMetrics</code>
            </div>
          </div>
        </div>

        {/* ── Azure Connector ───────────────────────────────────────────────── */}
        <div className="card">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Server size={18} color="var(--indigo-400)" />
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Microsoft Azure</h3>
            </div>
            {renderStatusBadge(azureStatus)}
          </div>

          <p className="text-xs text-secondary mb-4">
            Connects to Azure Monitor & Azure Resource Manager for VM metrics and resource telemetry.
          </p>

          <div className="flex-col gap-3">
            <div className="grid-2 gap-3">
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Azure Subscription ID
                </label>
                <input
                  type="text"
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  value={azureSubId}
                  onChange={e => setAzureSubId(e.target.value)}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Azure Tenant ID (Directory ID)
                </label>
                <input
                  type="text"
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  value={azureTenantId}
                  onChange={e => setAzureTenantId(e.target.value)}
                />
              </div>
            </div>

            <div className="grid-2 gap-3">
              <div>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  Azure Client ID (Application ID)
                </label>
                <input
                  type="text"
                  placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                  value={azureClientId}
                  onChange={e => setAzureClientId(e.target.value)}
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
                    Azure Client Secret
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowAzureSecret(!showAzureSecret)}
                    className="btn btn-ghost btn-sm"
                    style={{ padding: '2px 6px', fontSize: 11 }}
                  >
                    {showAzureSecret ? <EyeOff size={12} /> : <Eye size={12} />}
                    <span style={{ marginLeft: 4 }}>{showAzureSecret ? 'Hide' : 'Show'}</span>
                  </button>
                </div>
                <input
                  type={showAzureSecret ? 'text' : 'password'}
                  placeholder="Client secret value"
                  value={azureClientSecret}
                  onChange={e => setAzureClientSecret(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <button
                type="button"
                onClick={handleTestAzure}
                disabled={actionLoading === 'azure-test'}
                className="btn btn-secondary btn-sm"
              >
                {actionLoading === 'azure-test' ? <RefreshCw size={13} className="spin" /> : <Zap size={13} />}
                Test Azure Connection
              </button>

              <button
                type="button"
                onClick={handleSaveAzure}
                disabled={actionLoading === 'azure-save'}
                className="btn btn-primary btn-sm"
              >
                {actionLoading === 'azure-save' ? <RefreshCw size={13} className="spin" /> : <CheckCircle2 size={13} />}
                Save & Connect Azure
              </button>

              {azureStatus?.status === 'connected' && (
                <button
                  type="button"
                  onClick={handleDisconnectAzure}
                  disabled={actionLoading === 'azure-disconnect'}
                  className="btn btn-ghost btn-sm text-secondary"
                  style={{ marginLeft: 'auto' }}
                >
                  <Trash2 size={13} />
                  Disconnect to Demo
                </button>
              )}
            </div>

            {testResults.azure && (
              <div
                className="card mt-2"
                style={{
                  padding: '10px 14px',
                  borderColor: testResults.azure.status === 'connected' ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)',
                  background: testResults.azure.status === 'connected' ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)'
                }}
              >
                <div className="text-xs">
                  <strong>Result:</strong> {testResults.azure.message}
                </div>
              </div>
            )}

            <div className="text-xs text-muted mt-2">
              Minimum Role: <code>Monitoring Reader</code> assigned to your Service Principal App on the target subscription.
            </div>
          </div>
        </div>

        {/* ── GCP Connector ─────────────────────────────────────────────────── */}
        <div className="card">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <Cloud size={18} color="var(--sky-400)" />
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>Google Cloud Platform (GCP)</h3>
            </div>
            {renderStatusBadge(gcpStatus)}
          </div>

          <p className="text-xs text-secondary mb-4">
            Connects to Google Cloud Monitoring v3 API for Compute Engine instance utilization.
          </p>

          <div className="flex-col gap-3">
            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                GCP Project ID
              </label>
              <input
                type="text"
                placeholder={gcpStatus?.configured_keys?.includes('gcp_project_id') ? 'Configured in backend' : 'e.g. greenmind-prod-12345'}
                value={gcpProjectId}
                onChange={e => setGcpProjectId(e.target.value)}
              />
            </div>

            <div>
              <div className="flex items-center justify-between mb-1">
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
                  GCP Service Account JSON Key
                </label>
                <button
                  type="button"
                  onClick={() => setShowGcpSecret(!showGcpSecret)}
                  className="btn btn-ghost btn-sm"
                  style={{ padding: '2px 6px', fontSize: 11 }}
                >
                  {showGcpSecret ? <EyeOff size={12} /> : <Eye size={12} />}
                  <span style={{ marginLeft: 4 }}>{showGcpSecret ? 'Hide' : 'Show'}</span>
                </button>
              </div>
              <textarea
                rows={3}
                style={{ fontFamily: 'monospace', fontSize: 12 }}
                placeholder={gcpStatus?.configured_keys?.includes('gcp_service_account_json') ? '•••• Service Account JSON configured ••••' : '{"type": "service_account", "project_id": "...", ...}'}
                value={gcpServiceAccountJson}
                onChange={e => setGcpServiceAccountJson(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-3 mt-2 flex-wrap">
              <button
                type="button"
                onClick={handleTestGcp}
                disabled={actionLoading === 'gcp-test'}
                className="btn btn-secondary btn-sm"
              >
                {actionLoading === 'gcp-test' ? <RefreshCw size={13} className="spin" /> : <Zap size={13} />}
                Test GCP Connection
              </button>

              <button
                type="button"
                onClick={handleSaveGcp}
                disabled={actionLoading === 'gcp-save'}
                className="btn btn-primary btn-sm"
              >
                {actionLoading === 'gcp-save' ? <RefreshCw size={13} className="spin" /> : <CheckCircle2 size={13} />}
                Save & Connect GCP
              </button>

              {gcpStatus?.status === 'connected' && (
                <button
                  type="button"
                  onClick={handleDisconnectGcp}
                  disabled={actionLoading === 'gcp-disconnect'}
                  className="btn btn-ghost btn-sm text-secondary"
                  style={{ marginLeft: 'auto' }}
                >
                  <Trash2 size={13} />
                  Disconnect to Demo
                </button>
              )}
            </div>

            {testResults.gcp && (
              <div
                className="card mt-2"
                style={{
                  padding: '10px 14px',
                  borderColor: testResults.gcp.status === 'connected' ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)',
                  background: testResults.gcp.status === 'connected' ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)'
                }}
              >
                <div className="text-xs">
                  <strong>Result:</strong> {testResults.gcp.message}
                </div>
              </div>
            )}

            <div className="text-xs text-muted mt-2">
              Minimum IAM Roles: <code>roles/monitoring.viewer</code>, <code>roles/compute.viewer</code>
            </div>
          </div>
        </div>

        {/* ── AI Copilot LLM Engines ────────────────────────────────────────── */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Brain size={18} color="var(--emerald-400)" />
              <h3 style={{ fontSize: 16, fontWeight: 700 }}>AI Copilot Language Models</h3>
            </div>
            <span
              className={`badge ${statusData?.llm?.openai_configured || statusData?.llm?.gemini_configured ? 'badge-emerald' : 'badge-blue'}`}
            >
              {statusData?.llm?.gemini_configured ? 'GEMINI ACTIVE' : statusData?.llm?.openai_configured ? 'OPENAI ACTIVE' : 'DETERMINISTIC FALLBACK'}
            </span>
          </div>

          <p className="text-xs text-secondary mb-4">
            Powers contextual natural language responses in AI Copilot. When absent, a zero-cost deterministic rule engine answers queries.
          </p>

          <div className="flex-col gap-3">
            <div>
              <div className="flex items-center justify-between mb-1">
                <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Google Gemini API Key
                </label>
                <button
                  type="button"
                  onClick={() => setShowLlmSecret(!showLlmSecret)}
                  className="btn btn-ghost btn-sm"
                  style={{ padding: '2px 6px', fontSize: 11 }}
                >
                  {showLlmSecret ? <EyeOff size={12} /> : <Eye size={12} />}
                  <span style={{ marginLeft: 4 }}>{showLlmSecret ? 'Hide' : 'Show'}</span>
                </button>
              </div>
              <input
                type={showLlmSecret ? 'text' : 'password'}
                placeholder={statusData?.llm?.gemini_configured ? '•••••••••••••••••••• (Configured)' : 'AIzaSy...'}
                value={geminiKey}
                onChange={e => setGeminiKey(e.target.value)}
              />
            </div>

            <div>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                OpenAI API Key (Alternative)
              </label>
              <input
                type={showLlmSecret ? 'text' : 'password'}
                placeholder={statusData?.llm?.openai_configured ? '•••••••••••••••••••• (Configured)' : 'sk-...'}
                value={openaiKey}
                onChange={e => setOpenaiKey(e.target.value)}
              />
            </div>

            <div className="flex items-center gap-3 mt-2">
              <button
                type="button"
                onClick={handleSaveLlm}
                disabled={actionLoading === 'llm-save'}
                className="btn btn-primary btn-sm"
              >
                {actionLoading === 'llm-save' ? <RefreshCw size={13} className="spin" /> : <CheckCircle2 size={13} />}
                Save AI Keys
              </button>

              {(statusData?.llm?.gemini_configured || statusData?.llm?.openai_configured) && (
                <button
                  type="button"
                  onClick={handleDisconnectLlm}
                  disabled={actionLoading === 'llm-disconnect'}
                  className="btn btn-ghost btn-sm text-secondary"
                  style={{ marginLeft: 'auto' }}
                >
                  <Trash2 size={13} />
                  Reset to Deterministic Fallback
                </button>
              )}
            </div>
          </div>
        </div>

        {/* ── System Architecture & Health ─────────────────────────────────── */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div className="flex items-center gap-2 mb-4">
            <Settings size={18} color="var(--text-muted)" />
            <h3 style={{ fontSize: 16, fontWeight: 700 }}>System Deployment Architecture</h3>
          </div>

          <div className="grid-2 gap-4">
            <div>
              <div className="text-xs text-muted font-bold uppercase tracking-wider">Database Engine</div>
              <div className="text-sm text-primary font-medium mt-1 flex items-center gap-2">
                <Database size={14} color="var(--emerald-400)" />
                {statusData?.database === 'postgresql' ? 'PostgreSQL (Managed Production)' : 'SQLite (Local Development / Fallback)'}
              </div>
            </div>

            <div>
              <div className="text-xs text-muted font-bold uppercase tracking-wider">Redis Cache</div>
              <div className="text-sm text-primary font-medium mt-1 flex items-center gap-2">
                <Server size={14} color={statusData?.redis ? 'var(--emerald-400)' : 'var(--text-muted)'} />
                {statusData?.redis ? 'Redis Cluster Connected' : 'In-Memory Cache (Graceful Fallback)'}
              </div>
            </div>

            <div>
              <div className="text-xs text-muted font-bold uppercase tracking-wider">ML Forecasting Stack</div>
              <div className="text-sm text-secondary mt-1">
                5 Scikit-Learn Multi-Step Models (CPU, Memory, Network, Cost, Carbon)
              </div>
            </div>

            <div>
              <div className="text-xs text-muted font-bold uppercase tracking-wider">Autonomous Agent Team</div>
              <div className="text-sm text-secondary mt-1">
                Cost, Performance, Sustainability, Security, Reliability + Conflict Engine
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
