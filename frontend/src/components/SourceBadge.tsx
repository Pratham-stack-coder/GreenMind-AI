/**
 * SourceBadge — Data Truth Transparency Component
 *
 * Renders a clearly visible badge indicating the origin of a data value.
 * This is a NON-NEGOTIABLE UI requirement: every metric displayed to the user
 * must be labeled with its true data source.
 *
 * Source types:
 *   LIVE / LIVE_AWS / LIVE_AZURE / LIVE_GCP  — Real-time data from cloud provider API
 *   DEMO       — Synthetic deterministic demo data
 *   ESTIMATED  — Derived calculation (not from billing/monitoring API directly)
 *   SIMULATED  — Digital Twin scenario output (non-destructive simulation)
 *   UNAVAILABLE— Metric not available (e.g., memory without CloudWatch Agent)
 *   ERROR      — Provider configured but API call failed
 */

import React from 'react'

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

interface SourceBadgeProps {
  source: DataSourceType | string
  /** If provided, shows as a tooltip on hover */
  note?: string
  /** Size variant */
  size?: 'sm' | 'md' | 'lg'
  /** Show full label text or icon only */
  variant?: 'full' | 'compact' | 'icon-only'
  className?: string
}

const SOURCE_CONFIG: Record<
  DataSourceType,
  {
    label: string
    shortLabel: string
    icon: string
    colorClass: string
    dotColor: string
    description: string
  }
> = {
  LIVE: {
    label: 'Live',
    shortLabel: 'LIVE',
    icon: '●',
    colorClass: 'source-badge--live',
    dotColor: '#22c55e',
    description: 'Real-time data from cloud provider API',
  },
  LIVE_AWS: {
    label: 'Live · AWS',
    shortLabel: 'AWS',
    icon: '●',
    colorClass: 'source-badge--live',
    dotColor: '#22c55e',
    description: 'Live telemetry from AWS CloudWatch',
  },
  LIVE_AZURE: {
    label: 'Live · Azure',
    shortLabel: 'AZ',
    icon: '●',
    colorClass: 'source-badge--live',
    dotColor: '#22c55e',
    description: 'Live telemetry from Azure Monitor',
  },
  LIVE_GCP: {
    label: 'Live · GCP',
    shortLabel: 'GCP',
    icon: '●',
    colorClass: 'source-badge--live',
    dotColor: '#22c55e',
    description: 'Live telemetry from Google Cloud Monitoring',
  },
  DEMO: {
    label: 'Demo',
    shortLabel: 'DEMO',
    icon: '◆',
    colorClass: 'source-badge--demo',
    dotColor: '#6366f1',
    description: 'Synthetic demo data — configure cloud credentials for live telemetry',
  },
  ESTIMATED: {
    label: 'Estimated',
    shortLabel: 'EST',
    icon: '≈',
    colorClass: 'source-badge--estimated',
    dotColor: '#f59e0b',
    description: 'Derived estimate (not from provider billing/monitoring API)',
  },
  SIMULATED: {
    label: 'Simulated',
    shortLabel: 'SIM',
    icon: '⟳',
    colorClass: 'source-badge--simulated',
    dotColor: '#8b5cf6',
    description: 'Digital Twin simulation — no real infrastructure was modified',
  },
  UNAVAILABLE: {
    label: 'Unavailable',
    shortLabel: 'N/A',
    icon: '—',
    colorClass: 'source-badge--unavailable',
    dotColor: '#6b7280',
    description: 'Metric not available from this provider (may require monitoring agent)',
  },
  ERROR: {
    label: 'Error',
    shortLabel: 'ERR',
    icon: '✕',
    colorClass: 'source-badge--error',
    dotColor: '#ef4444',
    description: 'Provider configured but API call failed',
  },
}

/** Normalize source strings (LIVE_AWS → LIVE_AWS, live → LIVE, etc.) */
function normalizeSource(source: string): DataSourceType {
  const upper = source?.toUpperCase() as DataSourceType
  if (upper in SOURCE_CONFIG) return upper
  if (upper.startsWith('LIVE')) return 'LIVE'
  return 'DEMO'
}

export const SourceBadge: React.FC<SourceBadgeProps> = ({
  source,
  note,
  size = 'sm',
  variant = 'full',
  className = '',
}) => {
  const normalized = normalizeSource(source || 'DEMO')
  const config = SOURCE_CONFIG[normalized]

  const isLive = normalized.startsWith('LIVE')
  const tooltipText = note || config.description

  const sizeClass = {
    sm: 'source-badge--sm',
    md: 'source-badge--md',
    lg: 'source-badge--lg',
  }[size]

  const displayLabel =
    variant === 'icon-only'
      ? config.icon
      : variant === 'compact'
      ? config.shortLabel
      : config.label

  return (
    <span
      className={`source-badge ${config.colorClass} ${sizeClass} ${className}`}
      title={tooltipText}
      role="status"
      aria-label={`Data source: ${config.label}. ${config.description}`}
    >
      <span
        className={`source-badge__dot ${isLive ? 'source-badge__dot--pulse' : ''}`}
        style={{ backgroundColor: config.dotColor }}
        aria-hidden="true"
      />
      {variant !== 'icon-only' && (
        <span className="source-badge__label">{displayLabel}</span>
      )}
      {variant === 'icon-only' && (
        <span className="source-badge__label" aria-hidden="true">
          {config.icon}
        </span>
      )}
    </span>
  )
}

/** Inline note shown beneath a metric when a source has important caveats */
export const SourceNote: React.FC<{
  source: DataSourceType | string
  note?: string
  className?: string
}> = ({ source, note, className = '' }) => {
  const normalized = normalizeSource(source || 'DEMO')
  const config = SOURCE_CONFIG[normalized]
  const displayNote = note || (normalized !== 'LIVE' && normalized !== 'LIVE_AWS' && normalized !== 'LIVE_AZURE' && normalized !== 'LIVE_GCP' ? config.description : null)

  if (!displayNote) return null

  return (
    <p className={`source-note source-note--${normalized.toLowerCase()} ${className}`}>
      <span className="source-note__icon" aria-hidden="true">ⓘ</span>
      {displayNote}
    </p>
  )
}

/** Convenience wrapper for a metric card header with source badge */
export const MetricWithSource: React.FC<{
  label: string
  value: React.ReactNode
  source: DataSourceType | string
  note?: string
  unit?: string
  className?: string
}> = ({ label, value, source, note, unit, className = '' }) => {
  const normalized = normalizeSource(source || 'DEMO')
  const isUnavailable = normalized === 'UNAVAILABLE' || normalized === 'ERROR'

  return (
    <div className={`metric-with-source ${className}`}>
      <div className="metric-with-source__header">
        <span className="metric-with-source__label">{label}</span>
        <SourceBadge source={source} note={note} size="sm" />
      </div>
      <div className={`metric-with-source__value ${isUnavailable ? 'metric-with-source__value--unavailable' : ''}`}>
        {isUnavailable ? (
          <span title={note || SOURCE_CONFIG[normalized].description}>—</span>
        ) : (
          <>
            {value}
            {unit && <span className="metric-with-source__unit">{unit}</span>}
          </>
        )}
      </div>
      {note && normalized !== 'LIVE' && normalized !== 'LIVE_AWS' && normalized !== 'LIVE_AZURE' && normalized !== 'LIVE_GCP' && (
        <SourceNote source={source} note={note} />
      )}
    </div>
  )
}

export default SourceBadge
