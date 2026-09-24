# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x     | ✅ Active |
| 1.x     | ❌ End of Life |

## Data Security Model

### Non-Negotiable Security Rules

GreenMind AI enforces the following security rules at the application layer:

1. **Credentials NEVER committed to git** — All secrets are managed via environment variables only. No AWS, Azure, or GCP credentials may appear in any source file, configuration file, or Docker build context.

2. **Credentials NEVER logged or printed** — The backend explicitly masks all sensitive values before logging. The `test_connection()` API response returns masked ARNs and account IDs only. No secrets are ever forwarded to the frontend.

3. **Credentials NEVER returned in API responses** — The `/api/v1/settings/status` endpoint returns only non-sensitive metadata (mode, configured status, provider name). It never returns key values, tokens, or secrets.

4. **Data Truth Labels** — Every API response includes a `source` field from the set: `LIVE`, `LIVE_AWS`, `LIVE_AZURE`, `LIVE_GCP`, `DEMO`, `ESTIMATED`, `SIMULATED`, `UNAVAILABLE`, `ERROR`. No data is silently presented as LIVE when it is DEMO or UNAVAILABLE.

5. **No silent DEMO fallback on LIVE error** — When configured in LIVE mode, API errors return `source=ERROR` with a descriptive message rather than silently returning synthetic demo data as if it were live.

### Credential Storage

- **Development**: Use `.env` file (listed in `.gitignore`, never committed)
- **Docker Compose**: Use `.env` file or Docker secrets
- **Render (Backend)**: Use Render dashboard Secret Files or Environment Variables (never the `render.yaml` `value:` field)
- **Vercel (Frontend)**: Use Vercel Environment Variables dashboard
- **CI/CD (GitHub Actions)**: Use GitHub Repository Secrets

### IAM Permissions (Principle of Least Privilege)

#### AWS — Minimum Required Permissions

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:GetMetricData",
        "cloudwatch:ListMetrics",
        "ec2:DescribeInstances",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

**Optional (for Cost Explorer billing data):**
```json
{
  "Effect": "Allow",
  "Action": ["ce:GetCostAndUsage"],
  "Resource": "*"
}
```

> ⚠️ GreenMind AI is READ-ONLY. It never creates, modifies, or deletes AWS resources.

#### Azure — Minimum Required Roles

- `Monitoring Reader` — on the subscription or resource group scope
- **No write permissions required**

#### GCP — Minimum Required IAM Roles

- `roles/monitoring.viewer` — Cloud Monitoring read-only
- **No write permissions required**
- Recommended: scope the service account to the specific project

### Network Security

- Backend to cloud APIs: HTTPS only (TLS 1.2+)
- Frontend to backend: HTTPS only (enforced by Vercel + Render)
- Database: SQLite for demo mode; PostgreSQL with TLS in production
- Redis: Only accessible from within the same Docker network (bound to 127.0.0.1)

### Docker Security

- PostgreSQL port bound to `127.0.0.1:5432` (not `0.0.0.0:5432`)
- Redis port bound to `127.0.0.1:6379`
- No privileged containers
- No root processes (consider adding `USER nonroot` to Dockerfile for production)

## Reporting a Vulnerability

To report a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email: security@greenmind-ai.example.com (replace with actual contact)
3. Include: description, reproduction steps, potential impact
4. We will respond within 48 hours

## Known Security Limitations (Demo Mode)

When running with `DEMO_MODE=true`:
- CORS allows all origins (`*`) — safe for demo, not for production
- No authentication on API endpoints — production deployments should add API key auth or JWT
- SQLite is ephemeral on Render free tier — add PostgreSQL for persistence

## Dependency Security

Dependencies are pinned in `backend/requirements.txt`. Run `pip audit` to check for known CVEs:

```bash
pip install pip-audit
pip-audit -r backend/requirements.txt
```

For frontend:
```bash
cd frontend && npm audit
```
