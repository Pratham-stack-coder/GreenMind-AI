# Contributing to GreenMind AI

Thanks for taking a look. GreenMind AI is an early-stage prototype, so small, focused changes with clear validation notes are easiest to review.

## Development setup

Prerequisites: Python 3.11 or 3.12 and Node.js 22. Cloud credentials are not needed for the local test suite.

1. Create a virtual environment and install backend dependencies from the repository root:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r backend/requirements.txt
   ```

   On macOS or Linux, activate it with `source .venv/bin/activate`.

2. Install frontend dependencies:

   ```powershell
   cd frontend
   npm ci
   ```

3. Copy the appropriate `.env.example` only if you need to run the app. Keep `DEMO_MODE=true` for a local demo. Never commit `.env` files, cloud credentials, personal data, or service-role keys.

## Checks

Run from the repository root unless noted:

```powershell
python -m pytest backend/tests -v
cd frontend
npm run lint
npm run build
```

The GitHub Actions workflow also validates Docker Compose configuration and builds both images. To reproduce that check locally, copy `.env.example` to `.env` and run `docker compose config`.

## Pull requests

- Keep the change focused and explain the user-visible behavior or bug.
- Describe the checks you ran and include failures or environment limits.
- Label generated, demo, estimated, and live values accurately. The checked-in ML evaluation uses synthetic telemetry; it is not a real workload benchmark.
- For cloud-related changes, describe provider coverage, required permissions, and whether an operation reads, previews, or mutates infrastructure.
- Add or update tests for behavior changes. Do not include credentials, account identifiers, or production data in tests or screenshots.