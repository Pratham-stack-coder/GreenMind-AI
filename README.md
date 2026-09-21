# GreenMind AI — Carbon-and-Cost-Aware Cloud Scheduling

GreenMind AI predicts near-future CPU load for a cloud workload and
recommends not just *how* to size it, but *when* to run it — using
time-of-day carbon intensity — so a deferrable job can run with meaningfully
lower emissions at no extra cost.

**Status: DEMO.** Cloud metrics and carbon-intensity data are synthetic /
illustrative (see [Status](#status) below). No live AWS or grid-carbon
integration is wired up yet — that's the clearly-scoped next step, not
something this README claims is already done.

## Why this exists

Most "cloud cost optimizer" student projects recommend right-sizing an
instance and stop there. GreenMind AI's one real addition: a workload's
carbon footprint depends heavily on *when* it runs, because grid carbon
intensity swings meaningfully by time of day. If a job can be deferred a few
hours, GreenMind quantifies exactly how much that saves — and never
recommends deferring latency-sensitive work.

## Architecture

```
Cloud Metrics (demo)
        |
        v
ML CPU Forecast (GradientBoostingRegressor, chronological train/test split)
        |
        v
Decision Engine  <---  Carbon Intensity Curve (region + hour)
        |
        v
Recommendation: RUN_NOW or DEFER, with cost + carbon numbers
and a comparison against the naive "always run now" baseline
        |
        v
Interactive frontend (single HTML file, no build step)
```

## Repo layout

```
backend/
  app/
    main.py            FastAPI app — all endpoints
    carbon.py           carbon-intensity lookup (DEMO curves + real-API stub)
    decision_engine.py  the core recommendation logic
    schemas.py           request/response models
    ml/
      generate_dataset.py  synthetic CPU time series
      train.py              trains + evaluates the model, reports MAE vs. a
                             naive-persistence baseline
      predictor.py          loads model.pkl, exposes predict()
  requirements.txt
frontend/
  index.html            single-file interactive simulator (fetch + vanilla JS)
```

## Running it

```bash
# 1. Train the model (writes model.pkl + metrics.json)
cd backend/app/ml
pip install -r ../../requirements.txt
python train.py

# 2. Start the API
cd ../..
uvicorn app.main:app --reload
# → http://127.0.0.1:8000/docs for interactive Swagger docs

# 3. Open the frontend
# just open frontend/index.html directly in a browser — no build step
```

## What's actually implemented vs. planned

| Piece | Status |
|---|---|
| CPU forecasting model, chronological eval, beats naive baseline | **Implemented** |
| Carbon-and-time-aware scheduling recommendation | **Implemented** |
| Baseline comparison (naive "run now" vs. GreenMind's recommendation) | **Implemented** |
| Interactive live simulator | **Implemented** |
| Real AWS CloudWatch metrics ingestion | Planned — `app/main.py:cloud_metrics()` is the one function to replace |
| Real carbon-intensity API (Electricity Maps / WattTime) | Planned — `app/carbon.py:get_carbon_intensity()` is the one function to replace |
| Multi-region cost variation (spot pricing) | Not modeled — cost is currently flat on-demand pricing |

## Model evaluation

Run `python backend/app/ml/train.py` to reproduce. Reported metrics use a
**chronological** (not random) train/test split, since random splitting on a
time series leaks future information into training. The model is compared
against a naive persistence baseline ("predict no change") — see
`metrics.json` after running.

## Status

"DEMO" appears in the API response (`source: "DEMO"`) and in the frontend
banner anywhere data isn't from a real cloud account or a real carbon API.
This label is intentional — see the project's own note-to-self: never
present synthetic data as live telemetry.
