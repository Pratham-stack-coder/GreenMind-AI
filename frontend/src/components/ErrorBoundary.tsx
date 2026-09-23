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
            background: 'var(--bg-base, #050a0f)',
            color: 'var(--text-primary, #e8f0fe)',
            fontFamily: 'Inter, system-ui, sans-serif',
            padding: 24,
          }}
        >
          <div
            className="card"
            style={{
              maxWidth: 550,
              width: '100%',
              background: 'rgba(16, 28, 48, 0.95)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: 16,
              padding: 32,
              textAlign: 'center',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5)',
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                background: 'rgba(239, 68, 68, 0.1)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                color: '#ef4444',
                fontSize: 24,
              }}
            >
              ⚠️
            </div>

            <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
              Temporary Rendering Notice
            </h2>

            <p style={{ color: 'var(--text-secondary, #94a3b8)', fontSize: 14, marginBottom: 20, lineHeight: 1.5 }}>
              GreenMind AI encountered an unexpected rendering condition. The system is operating in safe Demo mode.
            </p>

            {this.state.error && (
              <pre
                style={{
                  background: 'rgba(0,0,0,0.4)',
                  padding: 12,
                  borderRadius: 8,
                  fontSize: 12,
                  color: '#f87171',
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
              onClick={() => window.location.reload()}
              className="btn btn-primary"
              style={{
                background: 'var(--emerald-500, #10b981)',
                color: '#fff',
                padding: '10px 24px',
                borderRadius: 8,
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Reload Application
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
