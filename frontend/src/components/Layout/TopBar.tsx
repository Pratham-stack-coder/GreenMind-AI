import { useQuery } from '@tanstack/react-query'
import { Bell, Globe, RefreshCw } from 'lucide-react'
import { useAppStore } from '../../store'
import { fetchHealth } from '../../api/client'

export default function TopBar() {
  const { provider, region, setProvider, setRegion } = useAppStore()
  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 30_000,
  })

  const providers = ['aws', 'azure', 'gcp']
  const regions: Record<string, string[]> = {
    aws: ['us-east', 'us-west', 'eu-west', 'ap-southeast', 'ca-central', 'in-north'],
    azure: ['us-east', 'eu-west', 'ap-southeast'],
    gcp: ['us-east', 'us-west', 'eu-west'],
  }

  return (
    <header className="topbar">
      <Globe size={16} color="var(--emerald-400)" />

      {/* Provider selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Provider</span>
        <select
          value={provider}
          onChange={e => { setProvider(e.target.value); setRegion(regions[e.target.value]?.[0] || 'us-east') }}
          style={{ width: 'auto', padding: '4px 8px', fontSize: 13 }}
        >
          {providers.map(p => <option key={p} value={p}>{p.toUpperCase()}</option>)}
        </select>
      </div>

      {/* Region selector */}
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted" style={{ textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Region</span>
        <select
          value={region}
          onChange={e => setRegion(e.target.value)}
          style={{ width: 'auto', padding: '4px 8px', fontSize: 13 }}
        >
          {(regions[provider] || regions.aws).map(r => (
            <option key={r} value={r}>{r}</option>
          ))}
        </select>
      </div>

      <div className="flex-1" />

      {/* Status */}
      {health && (
        <div className="flex items-center gap-2">
          <span className={`status-dot ${health.status === 'ok' ? 'online' : 'error'}`} />
          <span className="text-xs text-secondary">
            v{health.version} · {health.demo_mode ? 'Demo' : 'Live'}
          </span>
        </div>
      )}

      {/* Notification bell */}
      <button className="btn btn-ghost btn-sm" style={{ padding: '6px 8px' }}>
        <Bell size={16} />
      </button>
    </header>
  )
}
