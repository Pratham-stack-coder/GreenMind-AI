# GreenMind AI IEEE manuscript checklist

## Included in this package

- IEEE-style two-column manuscript in DOCX, PDF, and editable LaTeX source.
- This factual and submission-readiness checklist.
- The ZIP package contains those four files.

## Evidence and claim audit

- [x] Forecast scores copied from backend/app/ml/metrics.json and cross-checked against the repository README.
- [x] Training setup checked against generate_dataset.py, train.py, and baseline.py.
- [x] The 60-day, 15-minute data generator is identified as synthetic; the test set is the final chronological 20%.
- [x] All five targets, units, MAE, RMSE, R-squared, persistence MAE, rolling-mean MAE, and reported persistence improvement are shown.
- [x] Carbon error is labeled per 15-minute sample and the target is described as a synthetic proxy, not measured Scope 2 emissions.
- [x] No claim of realized cost savings, emissions reductions, or production effectiveness is made.
- [x] Live cloud connector behavior is explicitly left unverified end to end for this study.
- [x] Direct live remediation is identified as unavailable (HTTP 501); simulations and estimated outputs are not treated as provider-side changes.
- [x] Research citations are included for gradient boosting, time-series evaluation, cloud workload forecasting, and carbon accounting.

## Complete before conference or journal submission

- [ ] Replace “Anonymous submission draft” with verified author names, affiliations, and corresponding-author details.
- [ ] Confirm the venue's IEEE template, page limit, anonymity policy, and reference requirements.
- [ ] Freeze and identify the exact repository commit used for the manuscript; preserve the metrics artifact and model-generation environment.
- [ ] Decide whether to keep the current synthetic-only study as a prototype paper or add a real, legally usable workload trace evaluation.
- [ ] For a stronger empirical study, add rolling-origin evaluation, repeated seeds, uncertainty intervals, seasonal baselines, and additional models.
- [ ] Validate AWS, Azure, and GCP paths end to end with documented test resources and permissions before making live-connector claims.
- [ ] Revisit the remediation status against the exact submission commit; do not state provider-side execution unless it is independently verified.
- [ ] If making cost or carbon impact claims, measure before-and-after outcomes and specify the energy, location, time, and accounting boundaries.
- [ ] Confirm all cited publication metadata and add any venue-required data, code, ethics, and funding statements.
- [ ] Have all authors review the manuscript and approve the final version.

## Scope note

The saved metrics support a single synthetic holdout comparison only. They do not establish performance on real telemetry, transfer across providers or regions, or realized operational savings. The supplied source checkout was clean when inspected; no tests or new experiments were run for this document task.
