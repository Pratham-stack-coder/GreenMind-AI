import { Link } from 'react-router-dom'

type LegalPageProps = { kind: 'privacy' | 'terms' }

export default function LegalPage({ kind }: LegalPageProps) {
  const privacy = kind === 'privacy'
  return (
    <main className="legal-page" id="main-content">
      <header className="legal-header">
        <Link to="/login" className="legal-brand">GreenMind</Link>
        <nav aria-label="Legal pages">
          <Link to="/privacy" aria-current={privacy ? 'page' : undefined}>Privacy</Link>
          <Link to="/terms" aria-current={!privacy ? 'page' : undefined}>Terms</Link>
        </nav>
      </header>
      <article>
        <p className="legal-eyebrow">Draft for deployment review</p>
        <h1>{privacy ? 'Privacy Policy' : 'Terms and Conditions'}</h1>
        <p className="legal-updated">Last reviewed: October 13, 2026</p>
        {privacy ? <>
          <p>This draft describes current GreenMind data flows. The service operator must add its legal name, contact details, governing location, and applicable retention periods before public launch.</p>
          <h2>Information processed</h2>
          <p>Supabase provides account authentication. GreenMind receives the authenticated user identifier and account email. The app processes cloud credentials, provider and region selections, resource identifiers, telemetry, recommendation status, and requested dry-run preview records.</p>
          <h2>Cloud credentials and provider data</h2>
          <p>Credentials are sent to the configured backend to connect to cloud providers. Stored credentials are encrypted only when a valid credential-encryption key is configured; credential writes fail when encryption is unavailable. Cloud APIs receive requests authenticated with configured credentials. Use least-privilege credentials.</p>
          <h2>Copilot and external services</h2>
          <p>When a language-model provider is configured, Copilot questions and relevant selected telemetry context may be sent to it. Otherwise the app uses its deterministic response path. Supabase, hosting, database, and cloud providers may process operational logs according to deployment settings.</p>
          <h2>Storage and retention</h2>
          <p>Persisted telemetry and account records are scoped to the authenticated owner. Recent history may also be held in process memory. Disconnecting credentials does not automatically erase telemetry. This version does not provide self-service data export or account-wide deletion. Retention depends on the operator's database, logs, and backups.</p>
          <h2>Your choices</h2>
          <p>Connect only accounts you are authorized to manage. Contact the service operator to request access, correction, or deletion. Operator contact details must be supplied before publication.</p>
        </> : <>
          <p>These draft terms describe current application behavior. The operator must add its legal name, contact details, governing law, and any required consumer terms before public launch.</p>
          <h2>Authorized use</h2>
          <p>Connect only cloud accounts you are authorized to access. You are responsible for credential permissions, provider charges, and reviewing recommendations.</p>
          <h2>Estimates and recommendations</h2>
          <p>Cost allocations, forecasts, recommendations, and carbon values may be estimates or based on regional reference data. They may be incomplete or inaccurate and are not financial, security, or compliance advice. Verify results with your provider and qualified personnel.</p>
          <h2>Non-destructive behavior</h2>
          <p>Recommendation previews are dry runs. Live cloud resource changes and rollback are not implemented. A preview does not change your cloud environment.</p>
          <h2>Third-party services and availability</h2>
          <p>Cloud providers, authentication, hosting, databases, and optional model services are operated by third parties and may be unavailable or change. No service-level commitment or governing-law terms are specified in this draft.</p>
          <h2>Contact and governing terms</h2>
          <p>The operator's legal identity, contact address, governing law, and complete limitation terms remain pending and must be provided before public launch.</p>
        </>}
        <aside className="legal-readiness" role="note">Public launch requires the operator's legal identity and contact details. The terms also require a governing-law review.</aside>
      </article>
      <footer className="legal-footer"><Link to="/privacy">Privacy</Link><Link to="/terms">Terms</Link><Link to="/login">Sign in</Link></footer>
    </main>
  )
}
