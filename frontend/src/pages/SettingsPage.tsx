import { motion } from 'framer-motion'
import { Settings, Cloud, Brain, Database, Bell, Info } from 'lucide-react'

export default function SettingsPage() {
  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1>Settings</h1>
          <p className="text-secondary text-sm mt-1">Configure providers, alerts, and integrations</p>
        </div>
      </div>

      <div className="flex-col gap-4" style={{ maxWidth: 700 }}>
        {/* Cloud Providers */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Cloud size={16} color="var(--blue-400)" />
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>Cloud Provider Credentials</h3>
            <span className="badge badge-muted" style={{ marginLeft: 'auto' }}>DEMO MODE</span>
          </div>
          <div className="flex-col gap-3">
            {[
              { label: 'AWS Access Key ID', placeholder: 'AKIAIOSFODNN7EXAMPLE', type: 'text' },
              { label: 'AWS Secret Access Key', placeholder: '••••••••••••••••••••', type: 'password' },
              { label: 'Azure Subscription ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', type: 'text' },
              { label: 'GCP Project ID', placeholder: 'my-gcp-project', type: 'text' },
            ].map(({ label, placeholder, type }) => (
              <div key={label}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>{label}</label>
                <input type={type} placeholder={placeholder} disabled style={{ opacity: 0.5 }} />
              </div>
            ))}
            <div className="card" style={{ padding: '10px 14px', borderColor: 'rgba(59,130,246,0.2)', background: 'rgba(59,130,246,0.05)' }}>
              <div className="flex items-start gap-2">
                <Info size={14} color="var(--blue-400)" style={{ flexShrink: 0, marginTop: 2 }} />
                <p className="text-xs text-secondary">
                  Live mode: set credentials as environment variables (AWS_ACCESS_KEY_ID, etc.) in your .env file.
                  GreenMind will automatically switch from Demo to Live mode when credentials are detected.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* AI / LLM */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Brain size={16} color="var(--emerald-400)" />
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>AI Copilot — Language Model</h3>
          </div>
          <div className="flex-col gap-3">
            {[
              { label: 'Gemini API Key', placeholder: 'AIza…', note: 'Enables Gemini-powered Copilot responses' },
              { label: 'OpenAI API Key', placeholder: 'sk-…', note: 'Alternative: GPT-4o-mini powered Copilot' },
            ].map(({ label, placeholder, note }) => (
              <div key={label}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</label>
                <input type="password" placeholder={placeholder} disabled style={{ opacity: 0.5 }} />
                <div className="text-xs text-muted mt-1">{note}</div>
              </div>
            ))}
            <div className="card" style={{ padding: '10px 14px', borderColor: 'rgba(16,185,129,0.2)', background: 'rgba(16,185,129,0.05)' }}>
              <div className="flex items-start gap-2">
                <Info size={14} color="var(--emerald-400)" style={{ flexShrink: 0, marginTop: 2 }} />
                <p className="text-xs text-secondary">
                  Without an API key, the Copilot uses a rule-based engine. Add GEMINI_API_KEY or OPENAI_API_KEY to your .env file to enable real AI responses.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Carbon API */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Database size={16} color="var(--indigo-400)" />
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>Carbon Intensity API</h3>
          </div>
          <div className="flex-col gap-3">
            {[
              { label: 'Electricity Maps API Key', placeholder: 'xxxxxxxxxxxxxxxx', note: 'Real-time grid carbon intensity for 70+ regions' },
              { label: 'WattTime Username', placeholder: 'username', note: 'Alternative carbon data source' },
            ].map(({ label, placeholder, note }) => (
              <div key={label}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 4 }}>{label}</label>
                <input type="text" placeholder={placeholder} disabled style={{ opacity: 0.5 }} />
                <div className="text-xs text-muted mt-1">{note}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Alert thresholds */}
        <div className="card">
          <div className="flex items-center gap-2 mb-4">
            <Bell size={16} color="var(--amber-400)" />
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>Alert Thresholds</h3>
          </div>
          <div className="flex-col gap-3">
            {[
              { label: 'CPU Alert Threshold (%)', value: 85 },
              { label: 'Memory Alert Threshold (%)', value: 88 },
              { label: 'Carbon Budget (gCO₂/hr)', value: 500 },
              { label: 'Cost Alert ($/hr)', value: 1.0 },
            ].map(({ label, value }) => (
              <div key={label}>
                <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 6 }}>
                  {label}
                </label>
                <input type="number" defaultValue={value} disabled style={{ opacity: 0.5 }} />
              </div>
            ))}
          </div>
        </div>

        {/* System info */}
        <div className="card" style={{ padding: '16px 20px' }}>
          <div className="flex items-center gap-2 mb-3">
            <Settings size={16} color="var(--text-muted)" />
            <h3 style={{ fontSize: 14, fontWeight: 700 }}>System Information</h3>
          </div>
          <div className="grid-2 gap-3">
            {[
              ['Version', '2.0.0'],
              ['Mode', 'Demo (Synthetic Data)'],
              ['ML Models', '5 (CPU, Memory, Network, Cost, Carbon)'],
              ['Regions', '6 (us-east, us-west, eu-west, ap-southeast, ca-central, in-north)'],
              ['Agents', 'Cost, Performance, Sustainability, Security, Reliability'],
              ['Backend', 'FastAPI 0.115 · Python 3.12'],
            ].map(([k, v]) => (
              <div key={k}>
                <div className="text-xs text-muted" style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{k}</div>
                <div className="text-sm text-secondary mt-1">{v}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
