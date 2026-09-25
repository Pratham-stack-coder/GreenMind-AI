import React, { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import SourceBadge, { DataSourceType } from '../SourceBadge'

interface MetricCardProps {
  label: string
  value: number | string
  unit: string
  icon: LucideIcon
  color: 'emerald' | 'blue' | 'indigo' | 'amber' | 'purple' | 'red'
  delta?: number
  subtext?: string
  source?: DataSourceType | string
  sourceNote?: string
}

function useCountUp(target: number, duration = 800) {
  const [val, setVal] = useState(0)
  const frame = useRef<number>(0)
  const prev = useRef<number | null>(null)

  useEffect(() => {
    if (target === prev.current) return
    const start = performance.now()
    const from = prev.current ?? 0
    prev.current = target
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const ease = 1 - Math.pow(1 - t, 3)
      setVal(from + (target - from) * ease)
      if (t < 1) frame.current = requestAnimationFrame(tick)
    }
    cancelAnimationFrame(frame.current)
    frame.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame.current)
  }, [target, duration])

  return val
}

export default function MetricCard({
  label,
  value,
  unit,
  icon: Icon,
  color,
  delta,
  subtext,
  source,
  sourceNote,
}: MetricCardProps) {
  const numVal = typeof value === 'number' ? value : 0
  const animated = useCountUp(numVal)
  const deltaClass = delta == null ? '' : delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat'
  const deltaLabel = delta == null ? '' : `${delta > 0 ? '+' : ''}${delta.toFixed(1)}%`

  const colorMap = {
    emerald: 'var(--emerald-400)',
    blue: 'var(--blue-400)',
    indigo: 'var(--indigo-400)',
    amber: 'var(--amber-400)',
    purple: '#a855f7',
    red: 'var(--red-400)',
  }

  return (
    <motion.div
      className={`metric-card ${color}`}
      whileHover={{ y: -3, transition: { duration: 0.2 } }}
    >
      <div className="flex items-center justify-between">
        <span className="metric-label">{label}</span>
        <div className="flex items-center gap-1.5">
          {source && (
            <SourceBadge source={source} note={sourceNote} size="sm" variant="compact" />
          )}
          <Icon size={18} color={colorMap[color] || 'var(--emerald-400)'} />
        </div>
      </div>
      <div className="metric-value">
        {typeof value === 'number'
          ? animated.toFixed(unit.includes('$') || numVal < 10 ? 4 : 1)
          : value}
        <span style={{ fontSize: '0.55em', fontWeight: 400, color: 'var(--text-secondary)', marginLeft: 4 }}>
          {unit}
        </span>
      </div>
      {delta != null && (
        <div className={`metric-delta ${deltaClass}`}>
          {delta > 0 ? '↑' : delta < 0 ? '↓' : '→'} {deltaLabel} vs baseline
        </div>
      )}
      {subtext && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
          {subtext}
        </div>
      )}
    </motion.div>
  )
}
