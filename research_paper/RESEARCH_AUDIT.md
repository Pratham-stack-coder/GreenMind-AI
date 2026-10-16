# GreenMind AI Research Paper — Technical Audit and Verification Report

**Date of Audit:** October 15, 2026  
**Auditor Roles:** Senior ML Engineer, Research-Paper Reviewer, Cloud Computing Researcher, IEEE Manuscript Editor  
**Repository Inspected:** `https://github.com/Pratham-stack-coder/GreenMind-AI`  
**Target Manuscript Package:** `research_paper/` (`.tex`, `.docx`, `.pdf`)

---

## 1. Executive Summary

This audit conducted an end-to-end technical, empirical, and architectural review of GreenMind AI and its IEEE-style manuscript. The repository implements a functional prototype combining:
- A 5-target machine learning forecasting module (Gradient Boosting) for 1-hour-ahead predictions;
- A 5-domain multi-agent analysis engine (Cost, Performance, Sustainability, Security, Reliability) with deterministic conflict arbitration;
- A non-destructive Digital Twin simulation engine supporting 5 optimization scenarios;
- An Explainable AI Copilot grounded in 8 platform tools;
- Cloud connector classes for AWS, Azure, and Google Cloud Platform.

### Key Audit Findings:
1. **Model Metrics Verification:** All reported held-out metrics in `backend/app/ml/metrics.json` were reproduced identically from `generate_dataset.py` (seed 42, 60 days, 15-minute intervals) and `train.py`. Relative MAE improvements over a one-hour forecast-origin persistence baseline range from **25.4% to 45.4%** across all 5 targets.
2. **Methodological Discovery (Rolling Baseline Alignment):** The stored `rolling_mae` baseline in the repository (`backend/app/ml/baseline.py`) evaluated a **1-step-ahead (15-minute) moving average on unshifted test data ($N=1{,}148$)**, rather than a true 4-step-ahead (1-hour) projection from the forecast origin ($N=1{,}152$). Evaluating the true 4-step-ahead rolling baseline from origin $t$ increases the baseline error significantly (e.g., CPU MAE rises from 4.622% to 7.263%), performing worse than persistence (6.500%) due to phase-shift lag during diurnal cycles.
3. **Carbon Target Definition & Dimensionality:** The carbon target in `generate_dataset.py` is defined as grams of $\text{CO}_2$ per 15-minute step ($\text{gCO}_2/\text{15-min}$) based on a fixed server power consumption assumption ($0.35\text{ kW} \times 0.25\text{ h} = 0.0875\text{ kWh}$) multiplied by the regional grid carbon intensity curve ($\text{gCO}_2/\text{kWh}$). It is a synthetic proxy, not a physical power-meter or market-based Scope 2 accounting footprint.
4. **Recursive Forecasting Inconsistency:** In `backend/app/ml/predictor.py`, the `forecast_multi_step` function applies 5-minute recursive extrapolation using models trained on 1-hour direct shifts. Moreover, predicted carbon ($\text{gCO}_2/\text{15-min}$, $\sim$30--40) is fed back into subsequent steps as `carbon_intensity`, which was trained on grid values ($\text{gCO}_2/\text{kWh}$, $\sim$350--450), introducing a $\sim$10$\times$ scale mismatch during multi-step chaining.
5. **Live Cloud Remediation Boundary:** As designed in `backend/app/integrations/cloud_actions.py`, all non-dry-run remediation and rollback calls return an explicit **HTTP 501 Not Implemented**. Live cloud mutations are intentionally protected; the system operates strictly in decision-support and preview modes.
6. **Literature & DOI Verification:** All 8 cited academic references (Friedman 2001, Bergmeir et al. 2018, Rossi et al. 2025, Henderson et al. 2020, Lannelongue et al. 2021, Radovanovic et al. 2023, Calheiros et al. 2015, Dodge et al. 2022) were independently verified against publisher databases (IEEE, ACM, JMLR, Springer, Wiley, Elsevier).

---

## 2. Machine Learning Pipeline Verification & Metrics Reproduction

### 2.1 Generator & Split Specification
- **Script:** `backend/app/ml/generate_dataset.py`
- **Configuration:** `days=60`, `seed=42`, `STEP_MINUTES=15`, `FORECAST_HORIZON=4` (1 hour ahead), region `us-east`.
- **Raw Observations:** $60 \times \frac{24 \times 60}{15} = 5{,}760$ timestamps.
- **Forward Target Shift:** Targets are shifted by $-4$ steps (`future_col = df[col].shift(-4)`).
- **Post-Shift Cleanup:** Trailing 4 rows without future labels are dropped via `.dropna()`, leaving **5,756 aligned observations**.
- **Chronological Split:**
  - Training set: First 80% ($4{,}604$ samples, 48 days, June 1 to July 18, 2026).
  - Test set: Final 20% ($1{,}152$ samples, 12 days, July 19 to July 30, 2026).
  - Shuffling: Strictly disabled (`iloc[:idx]` and `iloc[idx:]`).

### 2.2 Feature Construction & Leakage Check
- **CPU / Memory / Network Models:**
  - Features: Current target value $y_t$, `hour`, `day_of_week`, `rolling_avg_1h` (4-step rolling mean terminating at $t$), `rolling_std_1h` (4-step rolling standard deviation terminating at $t$).
  - *Leakage assessment:* In pandas, `df[col].rolling(4)` is strictly backward-looking ($[t-3, t-2, t-1, t]$). No future information leaks into the features.
- **Cost Model:**
  - Features: Current `cpu`, `memory`, `cost_usd`, `hour`, `day_of_week`.
- **Carbon Model:**
  - Features: `carbon_intensity_gco2_per_kwh`, `hour`, `day_of_week`, `cpu`.

### 2.3 Recalculated vs. Saved Held-Out Metrics

| Target | Unit | Metric | Model Stored | Model Recalculated | Persist. Baseline | Stored Roll-4 | True Roll-4 (Origin) | Gain over Persist. |
| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **CPU Utilization** | % | MAE<br>RMSE<br>$R^2$ | 3.809<br>4.811<br>0.855 | **3.8092**<br>**4.8106**<br>**0.8554** | 6.4996<br>8.1632<br>0.5843 | 4.6219<br>5.8925<br>0.7836 | 7.2628<br>9.0991<br>0.4851 | **41.39%** (41.4%) |
| **Memory Utilization** | % | MAE<br>RMSE<br>$R^2$ | 2.979<br>3.704<br>0.636 | **2.9793**<br>**3.7042**<br>**0.6363** | 3.9957<br>4.9458<br>0.3512 | 3.0250<br>3.7719<br>0.6231 | 4.1532<br>5.1481<br>0.2970 | **25.44%** (25.4%) |
| **Network Traffic** | Mbps | MAE<br>RMSE<br>$R^2$ | 43.876<br>55.328<br>0.871 | **43.8764**<br>**55.3281**<br>**0.8712** | 80.3458<br>102.329<br>0.5591 | 56.7267<br>72.7661<br>0.7779 | 90.8163<br>115.421<br>0.4398 | **45.39%** (45.4%) |
| **Hourly Cost** | USD/h | MAE<br>RMSE<br>$R^2$ | 0.009<br>0.011<br>0.474 | **0.0091**<br>**0.0113**<br>**0.4738** | 0.0130<br>0.0163<br>-0.0987 | 0.0100<br>0.0125<br>0.3541 | N/A | **29.68%** (29.7%) |
| **Carbon Proxy** | gCO$_2$/15m | MAE<br>RMSE<br>$R^2$ | 4.061<br>5.087<br>0.391 | **4.0609**<br>**5.0866**<br>**0.3914** | 5.8459<br>7.2690<br>-0.2415 | 4.5707<br>5.7171<br>0.2312 | N/A | **30.53%** (30.5%) |

*Note on Carbon and Cost baselines:* Persistence on cost and carbon exhibits negative $R^2$ because the variations in cost and carbon are small and noisy around their mean; predicting current value $y_t$ for $y_{t+4}$ performs worse than the mean prediction.

---

## 3. Methodological Audit: Baseline Alignment Nuance

In `backend/app/ml/baseline.py`, the function `evaluate_rolling_mean` is implemented as:
```python
def evaluate_rolling_mean(series: pd.Series | np.ndarray, window: int = 4) -> BaselineMetrics:
    arr = np.asarray(series, dtype=float)
    ...
    y_true = arr[window:]
    y_pred = np.array([np.mean(arr[i : i + window]) for i in range(len(arr) - window)])
    return compute_metrics(y_true, y_pred)
```
In `train.py`:
```python
rolling_baseline = evaluate_rolling_mean(test[baseline_col].values, window=4)
```
### Audit Insight:
1. `arr` passed to `evaluate_rolling_mean` is `test[baseline_col]` (unshifted metric values), **not** `y_test` (the 4-step forward target).
2. For index `i=0`, `arr[0:4]` predicts `arr[4]`. This corresponds to evaluating a **1-step-ahead (15-minute) rolling mean**, predicting observation $t+1$ using $[t-3, t-2, t-1, t]$.
3. Because 15-minute synthetic intervals have high autocorrelation, this 1-step rolling mean baseline achieves an artificially low MAE (4.622% for CPU).
4. If evaluated as a **true 4-step-ahead baseline** (predicting $y_{t+4}$ using the rolling average available at time $t$), the actual baseline error rises to **7.263%** for CPU, **4.153%** for memory, and **90.816 Mbps** for network.
5. In prospective 1-hour forecasting, rolling averages lag behind rapid diurnal swings, causing the true 4-step rolling baseline to perform worse than simple 1-step persistence. The machine learning models decisively outperform both baselines.

---

## 4. Architectural & Implementation Verification

### 4.1 Multi-Agent System
- **File:** `backend/app/agents/orchestrator.py`
- **Orchestration:** Implemented as a LangGraph `StateGraph` linking `CostAgent`, `PerformanceAgent`, `SustainabilityAgent`, `SecurityAgent`, and `ReliabilityAgent`, followed by `DecisionAggregator`.
- **Graceful Fallback:** If LangGraph is not available, sequentially executes agents and deduplicates recommendations.
- **Conflict Resolution Rules:**
  - *Performance Headroom vs. Cost Downsizing:* When $35\% \le \text{CPU} < 75\%$, reconciles by approving right-sizing with automated predictive autoscaling (60-second headroom buffer).
  - *Reliability Standby vs. Cost Waste:* When $\text{CPU} < 35\%$, downsizes while maintaining standby redundancy policies.
  - *Sustainability Deferral vs. Immediate Execution:* Schedules non-urgent batch tasks to low-carbon windows (1--6 AM UTC) while preserving immediate execution for interactive user APIs.

### 4.2 AI Copilot & Grounded Tools
- **File:** `backend/app/copilot/tools.py`
- **Tool Inventory (8 tools verified):**
  1. `get_cloud_metrics`: Retrieves real-time provider metrics (CPU, Memory, Network, Cost, Carbon).
  2. `get_history`: Fetches sliding-window telemetry ring buffer records.
  3. `get_predictions`: Calls ML predictor across all 5 dimensions.
  4. `get_cost_analysis`: Returns compute spend breakdown and driver analysis.
  5. `get_carbon_analysis`: Returns regional intensity curves and green scheduling windows.
  6. `get_recommendations`: Returns active multi-agent optimization recommendations.
  7. `get_cloud_health`: Returns infrastructure health indicators and optimization scores.
  8. `run_digital_twin_simulation`: Executes non-destructive scenarios against state snapshots.
- **Intent Engine:** Deterministic keyword/pattern matcher with optional Gemini / OpenAI fallback. Grounded in actual database and ring buffer state.

### 4.3 Digital Twin Simulator
- **File:** `backend/app/digital_twin/simulator.py` & `scenarios.py`
- **Scenarios Supported:** `RIGHT_SIZE`, `SCALE_UP`, `SCALE_DOWN`, `CONSOLIDATE`, `REGION_MIGRATION`.
- **Scoring Lifecycle:** Calculates baseline and projected Optimization Scores ($0$--$100$) dynamically using `compute_optimization_scores()`.
- **Output Metadata:** All simulation results explicitly carry `is_simulated=True`, `label="SIMULATED / ESTIMATED"`, and disclaimer warnings.

### 4.4 Cloud Connectors & Credential Security
- **Files:** `backend/app/cloud/aws_provider.py`, `azure_provider.py`, `gcp_provider.py`.
- **Credential Storage:** Scoped per authenticated user, encrypted in-memory via `credential_crypto.py`.
- **Live Status:** Code exists for AWS CloudWatch (`boto3`), Azure Monitor REST API, and GCP Cloud Monitoring v3. When credentials are not supplied or invalid, seamlessly falls back to synthetic data.

### 4.5 Live Remediation Status (HTTP 501 Safety Guardrail)
- **File:** `backend/app/integrations/cloud_actions.py`
- **Execution Endpoint:** Non-dry-run remediation requests explicitly raise:
  ```python
  raise HTTPException(
      status_code=501,
      detail="Live cloud remediation is not implemented. Use dry_run=true to preview this action."
  )
  ```
- **Rollback Endpoint:** Raises `HTTPException(status_code=501, detail="Cloud remediation rollback is not implemented.")`.
- **Dry-run Mode:** Allows safe preview, updates projected scores, and logs simulated audit events without provider API mutations.

---

## 5. Verification of Academic References

All academic references cited in the manuscript were audited for publisher source, volume, issue, page numbers, and DOIs:

1. **Gradient Boosting:**
   - J. H. Friedman, "Greedy function approximation: A gradient boosting machine," *The Annals of Statistics*, vol. 29, no. 5, pp. 1189--1232, Oct. 2001.
   - **DOI:** `10.1214/aos/1013203451` (Verified via Project Euclid / IMS).
2. **Time Series Cross-Validation:**
   - C. Bergmeir, R. J. Hyndman, and B. Koo, "A note on the validity of cross-validation for evaluating autoregressive time series prediction," *Computational Statistics & Data Analysis*, vol. 120, pp. 70--83, Apr. 2018.
   - **DOI:** `10.1016/j.csda.2017.11.003` (Verified via Elsevier ScienceDirect).
3. **Cloud Workload Forecasting & Uncertainty:**
   - A. Rossi, A. Visentin, D. Carraro, S. Prestwich, and K. N. Brown, "Forecasting workload in cloud computing: Towards uncertainty-aware predictions and transfer learning," *Cluster Computing*, vol. 28, art. no. 258, pp. 1--22, 2025.
   - **DOI:** `10.1007/s10586-024-04933-2` (Verified via Springer).
4. **Machine Learning Carbon Reporting:**
   - P. Henderson, J. Hu, J. Romoff, E. Brunskill, D. Jurafsky, and J. Pineau, "Towards the systematic reporting of the energy and carbon footprints of machine learning," *Journal of Machine Learning Research*, vol. 21, no. 248, pp. 1--43, 2020.
   - (Verified via JMLR).
5. **Green Algorithms Computational Footprint:**
   - L. Lannelongue, J. Grealey, and M. Inouye, "Green algorithms: Quantifying the carbon footprint of computation," *Advanced Science*, vol. 8, no. 12, art. no. 2100707, pp. 1--10, 2021.
   - **DOI:** `10.1002/advs.202100707` (Verified via Wiley Online Library).
6. **Carbon-Aware Datacenter Computing:**
   - A. Radovanovic et al., "Carbon-aware computing for datacenters," *IEEE Transactions on Power Systems*, vol. 38, no. 2, pp. 1270--1280, Mar. 2023.
   - **DOI:** `10.1109/TPWRS.2022.3173250` (Verified via IEEE Xplore).
7. **Proactive Cloud Provisioning (ARIMA Benchmark):**
   - R. N. Calheiros, E. Masoumi, R. Ranjan, and R. Buyya, "Workload prediction using ARIMA model and its impact on cloud applications' QoS," *IEEE Transactions on Cloud Computing*, vol. 3, no. 4, pp. 449--458, Oct.--Dec. 2015.
   - **DOI:** `10.1109/TCC.2014.2350475` (Verified via IEEE Xplore).
8. **Cloud Instance Carbon Intensity & Spatio-Temporal Shifting:**
   - J. Dodge et al., "Measuring the carbon intensity of AI in cloud instances," in *Proceedings of the 2022 ACM Conference on Fairness, Accountability, and Transparency (FAccT '22)*, Seoul, Republic of Korea, 2022, pp. 1536--1546.
   - **DOI:** `10.1145/3531146.3533147` (Verified via ACM Digital Library).
9. **Repository Reference:**
   - Pratham-stack-coder, "GreenMind-AI repository," GitHub, 2026. Available: `https://github.com/Pratham-stack-coder/GreenMind-AI`.

---

## 6. Test Suite Execution & Reproduction Log

### 6.1 Pytest Execution
- **Command:** `& ".venv/Scripts/pytest.exe" backend/tests`
- **Result:** **99 passed, 1 warning in 13.38s (100% pass rate)**.
- **Coverage Summary:**
  - `test_agents.py` (5 tests): Multi-agent execution, orchestration, conflict resolution.
  - `test_api.py` (24 tests): API routing, HTTP 501 remediation guardrails, health checks.
  - `test_auth.py` (3 tests): JWT token signing, verification, and expiration.
  - `test_cloud_connectors.py` (6 tests): Credential handling and connector initialization.
  - `test_cloud_providers.py` (12 tests): AWS, Azure, and GCP provider mock/demo polling.
  - `test_copilot.py` (5 tests): Intent classification, 8 grounded tools execution.
  - `test_cors.py` (1 test): CORS middleware policy.
  - `test_digital_twin.py` (6 tests): Scenario simulation, state snapshot validation.
  - `test_ml.py` (7 tests): Model loading, feature vectors, inference bounds.
  - `test_optimization_score_lifecycle.py` (13 tests): Baseline and projected scoring, HTTP 501 mutations.
  - `test_settings.py` (7 tests): Configuration management and environment variables.
  - `test_telemetry_persistence.py` (3 tests): Database ring buffer insertion and querying.
  - `test_user_data_isolation.py` (7 tests): Multi-tenant scoped credential isolation.

### 6.2 ML Retraining Reproduction
- **Command:** `& ".venv/Scripts/python.exe" -c "import sys; sys.path.insert(0, 'backend/app/ml'); import train; train.main()"`
- **Result:** Successfully trained all 5 forecasters in 6.42 seconds. Serialized models (`cpu_model.pkl`, `memory_model.pkl`, `network_model.pkl`, `cost_model.pkl`, `carbon_model.pkl`) and generated identical `metrics.json` and `feature_importance.json` artifacts.

---

## 7. Deliverables & File Manifest

The following deliverables have been generated in `research_paper/`:
1. **`GreenMind_AI_IEEE_Manuscript.tex`**: Full, updated LaTeX source adhering to standard `IEEEtran` conference styling. Includes complete methodology, architectural analysis, expanded literature citations, mathematical target formulations, verified Table I, and explicit limitation disclosures.
2. **`GreenMind_AI_IEEE_Manuscript.docx`**: Word document adhering to IEEE 2-column formatting (Section 0: 1-column title banner; Section 1: 2-column body with 18 pt column gutter). Formatted with Times New Roman typography, embedded Figure 1 architecture diagram, and styled Table I.
3. **`GreenMind_AI_IEEE_Manuscript.pdf`**: Formatted 2-page IEEE-style PDF rendered via ReportLab with 2-column flowable layout, embedded Figure 1 architecture diagram, clean horizontal-rule Table I, and page numbering.
4. **`greenmind_architecture.png`**: High-resolution (300 DPI) publication-quality architecture diagram illustrating the end-to-end pipeline: telemetry $\rightarrow$ forecasting $\rightarrow$ multi-agent analysis $\rightarrow$ conflict resolution $\rightarrow$ Digital Twin simulation $\rightarrow$ operator recommendations.
5. **`RESEARCH_AUDIT.md`** (this document): Complete audit documentation of findings, baseline corrections, reproducibility, and scope boundaries.

---

## 8. Summary of Verified Fixes, Unresolved Issues, and Items for Human Review

### 8.1 Verified Fixes Applied in the Manuscript
- **Corrected Horizon & Split Reporting:** Explicitly documented the 60-day, 15-minute sampling rate, 4-step forward shift (1-hour ahead), and 80/20 chronological partition ($4{,}604$ train / $1{,}152$ test).
- **Corrected Rolling Baseline Nuance:** Fully disclosed that the repository's stored moving average was evaluated on unshifted test data (1-step-ahead prediction) and contrasted this with the true 4-step rolling baseline from forecast origin.
- **Clarified Carbon Target Definition & Units:** Corrected all ambiguous statements to accurately define the target as a synthetic proxy in $\text{gCO}_2/\text{15-min}$, computed from regional grid intensity multiplied by $0.0875\text{ kWh}$.
- **Accurate Remediation Status:** Prohibited any claim of live cloud remediation or autonomous execution; verified and stated the HTTP 501 safety barrier.
- **Added End-to-End Pipeline Figure:** Generated and embedded a 6-stage architecture diagram illustrating telemetry ingestion, multi-metric ML forecasting, multi-agent analysis, conflict resolution, Digital Twin simulation, and copilot decision support.
- **Verified References & Citations:** Upgraded and verified 8 academic citations and 1 repository citation with accurate metadata and DOIs.

### 8.2 Unresolved Implementation Issues (Documented in Paper Limitations)
- **`forecast_multi_step` Recurrence & Scale Mismatch:** In `backend/app/ml/predictor.py`, the recursive multi-step forecasting function applies a 5-minute step interval to models trained on 1-hour direct targets and feeds back carbon output ($\text{gCO}_2$) into an input feature expecting grid carbon intensity ($\text{gCO}_2/\text{kWh}$). This should be refactored into direct multi-horizon models ($t+1, t+2, \dots, t+H$) in a future release.
- **End-to-End Live Connector Validation:** AWS, Azure, and GCP provider classes currently fall back to synthetic data in test environments. Live API polling against actual cloud accounts requires dedicated credentials and cloud test beds.
- **Real-World Trace Benchmarking:** Models have not yet been evaluated on public open traces (e.g., Google Borg, Alibaba Cluster Data, Azure Functions Traces) to assess robustness under non-stationary real-world distribution shifts.

### 8.3 Items Requiring Human Review Prior to Conference/Journal Submission
1. **Author Affiliations & Venue Formatting:** The current draft specifies `Anonymous submission draft`. The user/authors must insert real author names, institutional affiliations, contact emails, and grant funding disclosures when submitting to a non-blind or camera-ready venue.
2. **Page Limit & Layout Constraints:** The current paper is formatted as a 2-page short paper / work-in-progress report. If submitting to a 4-page, 6-page, or 8-page IEEE conference track, the methodological and experimental discussion sections can be expanded using the detailed findings in this audit report.
3. **Canary Cloud Environment for Live Remediation:** Before claiming closed-loop autonomous optimization in future work, an isolated canary subscription must be established to measure actual pre- and post-intervention billing and telemetry metrics.


---

## 8. Follow-up manuscript correction pass (October 16, 2026)

This addendum records changes made to the IEEE LaTeX source on branch
`fix/ieee-paper-scientific-audit`. It does not replace the original audit
or claim that a final PDF has been compiled.

### Corrections made in the manuscript source

1. **Recursive forecast qualification:** The manuscript now explicitly states
   that `forecast_multi_step` uses 5-minute recursion despite models trained
   for direct one-hour targets, and that carbon proxy values are fed back into
   an input representing grid intensity. Recursive forecasts are described as
   unvalidated and are excluded from the reported one-hour test metrics.
2. **Metrics claim qualified:** Wording now distinguishes the saved held-out
   metrics and the reproduction described in this audit from real-world
   validation. Results remain explicitly limited to the synthetic seed-42
   generator.
3. **Carbon target clarified:** The manuscript distinguishes the synthetic
   emissions proxy (gCO2 per 15-minute step) from grid intensity (gCO2/kWh).
4. **Architecture diagram replaced:** The LaTeX source now draws a compact
   vector pipeline using TikZ instead of embedding the raster architecture
   image whose arrow labels were reported clipped. This is a source-level fix;
   rendered legibility still requires PDF compilation and inspection.
5. **Copilot claims qualified:** The manuscript clarifies that the copilot is
   decision support and that provider access depends on configuration.

### Still requiring validation

- The revised LaTeX has **not been compiled or visually inspected in this
  environment**. Page count, package availability, and final layout are not
  yet verified.
- The five-page target must be checked using the official IEEE conference
  template and its normal body font size; page count must not be forced by
  using nonstandard font sizes or unreadable spacing.
- The 13-item list mentioned in a separate generated audit was not present at
  the paths inspected in this repository. This pass addresses issues
  explicitly supported by the checked-in audit and source, not an unseen list.
- No source-code files or trained model artifacts were changed in this pass.
  The recursive forecasting defect is documented in the paper, not silently
  repaired in the application.
- The reference metadata should be checked again before submission, and
  author/affiliation placeholders must be resolved according to the venue's
  anonymity policy.

### Status

**Manuscript source updated; final PDF not yet verified.** Do not describe the
paper as submission-ready until it has been compiled, every page rendered and
inspected, and the remaining venue-specific and reference checks completed.
