## Summary

Describe the change and the problem it addresses.

## Validation

- [ ] Backend tests: `python -m pytest backend/tests -v`
- [ ] Frontend lint: `npm run lint` (from `frontend/`)
- [ ] Frontend build: `npm run build` (from `frontend/`)
- [ ] Docker Compose config/build checks, if relevant

List the checks you ran and their results. If a check could not run, say why.

## Data truth and safety

- [ ] Demo, synthetic, estimated, and live values are distinguished accurately.
- [ ] Cloud changes state whether they read, preview, or mutate resources and identify provider coverage.
- [ ] No credentials, tokens, account IDs, or production data are included.
