import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('GreenMind AI Uncaught Error:', error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            minHeight: '100vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'var(--bg-base, #F7F8F3)',
            color: 'var(--text-primary, #111827)',
            fontFamily: 'Inter, system-ui, sans-serif',
            padding: 24,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: 550,
              width: '100%',
              background: 'var(--card-bg, #FFFFFF)',
              border: '1px solid var(--border, #E5E7EB)',
              borderRadius: 16,
              padding: 32,
              textAlign: 'center',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.06)',
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                background: '#FEE2E2',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                color: '#DC2626',
                fontSize: 24,
              }}
            >
              ⚠️
            </div>

            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8, color: 'var(--text-primary)' }}>
              Temporary Rendering Notice
            </h2>

            <p style={{ color: 'var(--text-secondary, #6B7280)', fontSize: 14, marginBottom: 20, lineHeight: 1.5 }}>
              GreenMind AI encountered an unexpected rendering condition. The system is operating in safe Demo mode.
            </p>

            {this.state.error && (
              <pre
                style={{
                  background: '#F9FAFB',
                  border: '1px solid #E5E7EB',
                  padding: 12,
                  borderRadius: 8,
                  fontSize: 12,
                  color: '#DC2626',
                  textAlign: 'left',
                  overflowX: 'auto',
                  marginBottom: 20,
                  maxHeight: 120,
                }}
              >
                {this.state.error.message}
              </pre>
            )}

            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="btn btn-primary"
            >
              Retry
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

interface PageErrorBoundaryProps {
  children: ReactNode
  resetKey?: string
}

interface PageErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

export class PageErrorBoundary extends Component<PageErrorBoundaryProps, PageErrorBoundaryState> {
  public state: PageErrorBoundaryState = {
    hasError: false,
    error: null,
  }

  public static getDerivedStateFromError(error: Error): PageErrorBoundaryState {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('GreenMind AI Page Error:', error, errorInfo)
  }

  public componentDidUpdate(prevProps: PageErrorBoundaryProps) {
    if (prevProps.resetKey !== this.props.resetKey && this.state.hasError) {
      this.setState({ hasError: false, error: null })
    }
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div
          className="card"
          style={{
            maxWidth: 520,
            margin: '40px auto',
            padding: 32,
            textAlign: 'center',
            border: '1px solid var(--border)',
            background: 'var(--card-bg, #FFFFFF)',
            borderRadius: 'var(--radius-lg, 14px)',
          }}
        >
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: '50%',
              background: '#FEE2E2',
              color: '#DC2626',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              fontSize: 22,
            }}
          >
            ⚠️
          </div>

          <h2 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 8 }}>
            Unable to display this view
          </h2>

          <p style={{ color: 'var(--text-secondary)', fontSize: 13, marginBottom: 20, lineHeight: 1.5 }}>
            An unexpected error occurred while rendering this page. You can try reloading this view or select another page from the sidebar.
          </p>

          {this.state.error && (
            <pre
              style={{
                background: '#F9FAFB',
                border: '1px solid #E5E7EB',
                padding: '10px 14px',
                borderRadius: 8,
                fontSize: 12,
                color: '#DC2626',
                textAlign: 'left',
                overflowX: 'auto',
                marginBottom: 20,
                maxHeight: 120,
                fontFamily: 'monospace',
              }}
            >
              {this.state.error.message}
            </pre>
          )}

          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="btn btn-primary"
          >
            Try again
          </button>
        </div>
      )
    }

    return this.props.children
  }
}

