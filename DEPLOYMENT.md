# GreenMind AI Deployment Guide

This guide deploys the React frontend to Vercel and the FastAPI backend to Render.

## Architecture and actual deployment behavior

- Vercel hosts the frontend.
- Render hosts the backend and auto-deploys commits pushed to `main` when the Blueprint's `autoDeploy` setting is enabled.
- The GitHub Actions workflow named **Container Image Publishing** builds and publishes GHCR images for version tags or manual runs. It does not deploy those images to Render.
- Browser API requests require a valid Supabase access token. `/health` remains public for service health checks.
- CORS allows local development origins, the configured project origins, and exact origins listed in `CORS_ORIGINS`. It does not allow every Vercel preview domain automatically.

## 1. Deploy the backend to Render

Create a Render Blueprint for this repository and use `render.yaml`. The backend build installs `backend/requirements.txt` and trains the ML models. A failed install or training step fails the deployment build.

Configure these Render environment variables:

| Variable | Purpose |
| --- | --- |
| `SUPABASE_URL` | Supabase project URL used to verify access tokens |
| `SUPABASE_PUBLISHABLE_KEY` | Required only for legacy HS256 Supabase tokens |
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet key used to encrypt per-user cloud credentials at rest |
| `DATABASE_URL` | Persistent PostgreSQL connection string for production |
| `CORS_ORIGINS` | Comma-separated exact frontend origins, including custom domains and any preview URLs you need |
| `DEMO_MODE` | Use `false` to let configured user credentials query live providers; `true` returns demo data |

Generate `CREDENTIAL_ENCRYPTION_KEY` once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep this key stable and private. Changing it makes already stored provider credentials unreadable. Back it up separately from the database.

AWS, Azure, and GCP credentials entered in Settings are scoped to the signed-in Supabase user and stored encrypted in PostgreSQL. The backend must have the encryption key configured before users can save credentials. Authenticated API requests do not use another user's credentials. Server environment credentials are for backend-managed system operations.

The backend's `/health` endpoint is the Render health check. The `/ready` endpoint requires authentication and reports not-ready when ML models are unavailable.

## 2. Deploy the frontend to Vercel

Import the repository into Vercel. Use `frontend` as the root directory, Node.js 22 or later, `npm run build` as the build command, and `dist` as the output directory.

Set these environment variables for each Vercel deployment environment:

| Variable | Value |
| --- | --- |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Supabase publishable key (or legacy anon key) |
| `VITE_API_BASE_URL` | Render backend URL, such as `https://your-service.onrender.com` |

Only public Supabase project values belong in `VITE_*` variables. Never put service-role keys, signing secrets, cloud credentials, or LLM API keys in frontend variables.

For local frontend setup, copy `frontend/.env.example` to `frontend/.env.local`, set the Supabase URL and publishable key, and leave `VITE_API_BASE_URL` empty to use the Vite proxy.

## 3. Configure exact CORS origins

In Render's Environment page, set `CORS_ORIGINS` to the exact origins that should call the API. For example:

```text
https://greenmind.example.com,https://greenmind-ai.vercel.app
```

Add a preview deployment origin explicitly when you need it. Do not enter paths or trailing API routes; use only the scheme and hostname. Local origins are already configured for Vite development.

## 4. Configure Supabase sign-in

1. Create a Supabase project and set its URL and publishable key in both Vercel and Render as described above.
2. Enable Email sign-in and any OAuth providers you intend to use.
3. Set the production Vercel URL as Supabase's Site URL and add the exact callback URLs used by the frontend.
4. For Google sign-in, configure the OAuth callback URL shown in Supabase. Keep the Google client secret in Supabase only.

The backend validates ES256/RS256 JWTs with Supabase's public JWKS. For legacy HS256 projects, it asks Supabase Auth to validate the token using the publishable key. Never configure a service-role key or JWT signing secret for this flow.

## 5. Connect cloud providers

Users add AWS, Azure, or GCP credentials in the authenticated Settings page. Credentials are stored encrypted and isolated by Supabase user ID. The per-user setting is persistent only when `DATABASE_URL` points to a persistent database such as PostgreSQL.

GreenMind AI currently reads cloud telemetry and generates dry-run previews. Live recommendation apply and rollback are not implemented; those API requests return HTTP 501 and do not modify provider resources.

## 6. Local development

From the repository root:

```bash
cp .env.example .env
# Set SUPABASE_URL and CREDENTIAL_ENCRYPTION_KEY in .env.
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

In a second terminal:

```bash
cd frontend
cp .env.example .env.local
# Set VITE_SUPABASE_URL and VITE_SUPABASE_PUBLISHABLE_KEY; leave VITE_API_BASE_URL blank.
npm ci
npm run lint
npm run dev
```

The Vite proxy forwards local API requests to `http://127.0.0.1:8000`.

## Troubleshooting

- **401 from protected endpoints**: sign in again and confirm that the browser sends the current Supabase bearer token.
- **CORS error**: add the frontend's exact origin to `CORS_ORIGINS` on Render and redeploy the backend.
- **Settings cannot save cloud credentials**: set `CREDENTIAL_ENCRYPTION_KEY` and a persistent `DATABASE_URL`; restart the backend.
- **Credentials cannot be decrypted after a restart**: restore the original encryption key. Do not rotate it without re-encrypting stored credential rows.
- **ML readiness fails**: inspect the Render build log. Image and service builds fail when model training fails, and `/ready` remains false while models are missing.
- **Container tag did not update Render**: the GitHub tag workflow publishes images only. Render's Blueprint currently deploys from `main`.
