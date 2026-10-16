"""
GreenMind AI - DOCX Generator
Generates both IEEE and Academic DOCX files using python-docx.
"""
from __future__ import annotations
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
ARCH = HERE / "greenmind_architecture.png"
BLUE = RGBColor(0, 48, 135)


def add_heading(doc, text, level=1, blue=True):
    h = doc.add_heading(text, level=level)
    h.alignment = WD_ALIGN_PARAGRAPH.LEFT
    h.paragraph_format.space_before = Pt(10 if level == 1 else 6)
    h.paragraph_format.space_after  = Pt(4)
    for run in h.runs:
        run.font.name = "Times New Roman"
        if blue:
            run.font.color.rgb = BLUE


def add_para(doc, text, bold=False, italic=False, size=10, indent=None):
    para = doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    para.paragraph_format.space_after = Pt(4)
    if indent is not None:
        para.paragraph_format.left_indent = Inches(indent)
    run = para.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Times New Roman"
    return para


def add_bullet_list(doc, items, size=10):
    for text in items:
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.font.name = "Times New Roman"


def add_enum_list(doc, items, size=10, start=1):
    for i, text in enumerate(items, start):
        p = doc.add_paragraph(style="List Number")
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run(text)
        run.font.size = Pt(size)
        run.font.name = "Times New Roman"


def add_results_table(doc, size=8):
    headers = ["Target", "MAE", "RMSE", "R²",
               "Persistence MAE", "Stored Roll-4", "True Roll-4", "Gain (%)"]
    rows = [
        ["CPU Util. (%)",        "3.809",  "4.811",  "0.855", "6.500",  "4.622", "7.263",  "41.4"],
        ["Memory Util. (%)",     "2.979",  "3.704",  "0.636", "3.996",  "3.025", "4.153",  "25.4"],
        ["Net Traffic (Mbps)",   "43.876", "55.328", "0.871", "80.346", "56.727","90.816", "45.4"],
        ["Hourly Cost ($/h)",    "0.009",  "0.011",  "0.474", "0.013",  "0.010", "N/A",    "29.7"],
        ["Carbon (gCO₂/15-min)", "4.061",  "5.087",  "0.391", "5.846",  "4.571", "N/A",    "30.5"],
    ]
    tbl = doc.add_table(rows=1 + len(rows), cols=8)
    tbl.style = "Table Grid"
    # Header row
    hdr_cells = tbl.rows[0].cells
    for j, h in enumerate(headers):
        hdr_cells[j].text = h
        run = hdr_cells[j].paragraphs[0].runs[0]
        run.bold = True
        run.font.size = Pt(size)
        run.font.name = "Times New Roman"
        # Blue background via XML
        from docx.oxml import OxmlElement
        tc = hdr_cells[j]._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:val'), 'clear')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:fill'), '003087')
        tcPr.append(shd)
        hdr_cells[j].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    # Data rows
    for i, row_data in enumerate(rows):
        cells = tbl.rows[i + 1].cells
        for j, val in enumerate(row_data):
            cells[j].text = val
            run = cells[j].paragraphs[0].runs[0] if cells[j].paragraphs[0].runs else \
                  cells[j].paragraphs[0].add_run(val)
            run.font.size = Pt(size)
            run.font.name = "Times New Roman"
    return tbl


def generate_ieee_docx(out_path: Path):
    doc = Document()
    # Margins
    for section in doc.sections:
        section.top_margin    = Cm(2.0)
        section.bottom_margin = Cm(2.0)
        section.left_margin   = Cm(2.0)
        section.right_margin  = Cm(2.0)

    # Title
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(
        "GreenMind AI: A Multi-Metric Forecasting and Decision-Support Platform for Cloud GreenOps")
    run.bold = True
    run.font.size = Pt(14)
    run.font.name = "Times New Roman"
    run.font.color.rgb = BLUE

    auth = doc.add_paragraph()
    auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
    auth_run = auth.add_run(
        "Anonymous Submission Draft — Author affiliations to be inserted for camera-ready submission")
    auth_run.italic = True
    auth_run.font.size = Pt(10)
    auth_run.font.name = "Times New Roman"

    # Abstract
    add_heading(doc, "Abstract", 1)
    add_para(doc,
        "Modern cloud operations require optimizing resource utilization, cost, and environmental "
        "footprint simultaneously. GreenMind AI is an open-source decision-support prototype integrating "
        "five one-hour-ahead gradient-boosted forecasters, a five-domain multi-agent analysis engine "
        "(Cost, Performance, Sustainability, Security, Reliability), deterministic conflict arbitration, "
        "a non-destructive Digital Twin simulator, and an eight-tool explainable AI copilot. Evaluation "
        "on a deterministic 60-day synthetic dataset (5,756 records; strict 80/20 chronological split: "
        "N_train=4,604, N_test=1,152) shows MAE improvements of 25.4%–45.4% over a one-hour persistence "
        "baseline. Our audit reveals the stored rolling baseline reflects a 15-min prediction (not 1-hour); "
        "the true four-step rolling baseline yields higher error than persistence (CPU: 7.263% vs. 6.500%) "
        "due to diurnal phase shift. All evaluations derive from synthetic generator equations; live "
        "remediation is guarded by HTTP 501.", italic=True)

    add_para(doc, "Index Terms: cloud computing; workload forecasting; gradient boosting; "
             "carbon-aware computing; multi-agent systems; digital twin; GreenOps.", italic=True)

    # I. Introduction
    add_heading(doc, "I. Introduction", 1)
    add_para(doc,
        "Cloud data centers consume a rising share of global electricity, driving GreenOps and FinOps "
        "disciplines [4, 6]. Proactive workload forecasting supports right-sizing, autoscaling, and "
        "carbon-aware scheduling, but high historical accuracy does not guarantee realized savings or "
        "SLO preservation [3, 8]. GreenMind AI addresses these challenges by unifying multi-metric "
        "gradient boosted forecasting, five-domain multi-agent orchestration, deterministic conflict "
        "resolution, Digital Twin simulation, and an eight-tool AI copilot.")
    add_para(doc, "Contributions:", bold=True)
    add_enum_list(doc, [
        "End-to-end architecture linking telemetry ingestion, multi-metric forecasting, multi-agent "
        "arbitration, Digital Twin simulation, and decision-support interfaces.",
        "Verified forecasting performance on five targets with a baseline alignment audit identifying "
        "a 15-min vs. 1-hour horizon discrepancy in the stored rolling baseline.",
        "Explicit empirical boundaries: synthetic data provenance, unverified live connectors, "
        "and the HTTP 501 live-remediation safety guard.",
    ])

    # II. Related Work
    add_heading(doc, "II. Related Work", 1)
    add_para(doc,
        "Calheiros et al. [7] demonstrated ARIMA-based proactive scaling reducing QoS violations. "
        "Friedman's Gradient Boosting Machine [1] excels on structured tabular lag features. "
        "Rossi et al. [3] showed point forecasts miss operational uncertainty and accuracy degrades "
        "under cross-provider transfer. Bergmeir et al. [2] established chronological holdout as "
        "standard practice. Henderson et al. [4] and Lannelongue et al. [5] formalized ML carbon "
        "reporting. Radovanovic et al. [6] deployed carbon-aware scheduling at Google datacenters. "
        "Dodge et al. [8] measured carbon intensity across cloud instance types.")

    # III. Architecture
    add_heading(doc, "III. Platform Architecture and Implementation", 1)
    if ARCH.exists():
        try:
            doc.add_picture(str(ARCH), width=Inches(6.0))
            cap = doc.add_paragraph(
                "Figure 1. GreenMind AI pipeline: telemetry ingestion → ML forecasting → "
                "multi-agent analysis → conflict resolution → Digital Twin → decision support.")
            cap.runs[0].italic = True
            cap.runs[0].font.size = Pt(9)
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass

    for subhead, text in [
        ("A. Telemetry Ingestion",
         "FastAPI (Python 3.12; SQLite/PostgreSQL) ingests five 15-min signals: CPU (%), memory (%), "
         "network (Mbps), cost (USD/h), carbon proxy (gCO₂/15-min). AWS CloudWatch (boto3), Azure Monitor "
         "REST, GCP Cloud Monitoring v3 — each falls back to synthetic generator when credentials absent."),
        ("B. Multi-Metric ML Predictor",
         "Five GradientBoostingRegressor models: 150 estimators, depth 3, lr=0.08, seed 42. "
         "Strictly backward-looking features: y_t, hour, day, rolling mean μ_{t,4}, rolling σ_{t,4}. "
         "Anomaly detection: z-score > 2.5."),
        ("C. Multi-Agent Engine",
         "Five agents in a LangGraph StateGraph: CostAgent (right-sizing, Spot/RI), PerformanceAgent "
         "(saturation thresholds), SustainabilityAgent (green windows 01:00–06:00 UTC), SecurityAgent "
         "(IAM, TLS, ports), ReliabilityAgent (multi-AZ, backup RPO). Graceful sequential fallback."),
        ("D. Conflict Resolution",
         "Three arbitration rules: Performance vs. Cost (right-size + autoscaling, 60-s buffer, conf. 0.88); "
         "Reliability vs. Cost (downsize + failover, conf. 0.92); Carbon deferral vs. Execution "
         "(green windows, conf. 0.87). Each emits a full audit record."),
        ("E. Digital Twin Simulator",
         "Five non-destructive scenarios: Right-Size, Scale-Up/Down, Consolidate, Region Migration. "
         "Recomputes Optimization Score (0–100). All outputs: is_simulated=True, 'SIMULATED / ESTIMATED'."),
        ("F. AI Copilot",
         "Eight grounded tools grounded in live application state. Non-dry-run and rollback calls "
         "return HTTP 501 Not Implemented."),
    ]:
        add_heading(doc, subhead, 2)
        add_para(doc, text)

    # IV. Methodology
    add_heading(doc, "IV. Experimental Methodology", 1)
    for subhead, text in [
        ("A. Synthetic Dataset",
         "generate_dataset.py: 5,760 observations at 15-min intervals, seed 42. "
         "CPU = clip(35 + 30·sin²((h−7)/24·2π)·W_t + τ_t + ε_t, 2, 98). "
         "Memory: [0,8]% drift. Network: 300+400·sin²(·) Mbps. Cost: $0.192·(1+cpu/100·0.5)."),
        ("B. Carbon Target",
         "us-east intensity I(h_t) in 320–470 gCO₂/kWh. C_t = clip(I(h_t)·0.35·0.25 + N(0,25), 0, 500) "
         "[gCO₂/15-min]. Excludes PUE, dynamic power states, Scope 3."),
        ("C. Split and Baselines",
         "Targets shifted Δ=4 steps; 5,756 aligned records. Chronological 80/20: N_train=4,604, N_test=1,152. "
         "Persistence: ŷ_{t+4}=y_t. Stored Roll-4 evaluates ŷ_{t+1}=μ_{t,4} on unshifted data (N=1,148) — "
         "a 15-min prediction. True Roll-4 from origin yields higher error than persistence "
         "(CPU: 7.263% vs. 6.500%)."),
    ]:
        add_heading(doc, subhead, 2)
        add_para(doc, text)

    # V. Results
    add_heading(doc, "V. Experimental Results", 1)
    add_para(doc,
        "Table I reports verified held-out metrics (train.py re-executed; seed 42; 6.4 s wall-clock). "
        "Gradient boosting outperforms persistence on all five targets. MAE gains: 25.4% (memory) "
        "to 45.4% (network). CPU/network: R²=0.855/0.871.")
    add_para(doc,
        "Table I. Verified Test-Set Metrics (N=1,152). Persistence: ŷ_{t+4}=y_t. "
        "Stored Roll-4: repository 1-step MA on unshifted data. "
        "True Roll-4: four-step rolling mean from origin t.", italic=True)
    add_results_table(doc)

    # VI. Discussion and Limitations
    add_heading(doc, "VI. Discussion and Limitations", 1)
    add_para(doc,
        "High R² reflects recovery of smooth sinusoidal generator formulas, not real-world generalization. "
        "Real cluster traces exhibit heavy-tailed distributions, preemptions, and non-stationary shifts [3]. "
        "Reported metrics establish synthetic benchmark performance only.")
    add_heading(doc, "Documented Limitations", 2)
    add_enum_list(doc, [
        "Data provenance: single generator configuration (seed 42, 60-day, us-east).",
        "Recursive multi-step inconsistency: 5-min steps on 1-h models; carbon output "
        "(~30–40 gCO₂/15-min) fed as carbon_intensity (~350–450 gCO₂/kWh) — ~10× mismatch.",
        "Live connectors: fall back to synthetic data in test environments.",
        "HTTP 501: all cloud mutations blocked; Digital Twin savings are static projections.",
        "Carbon proxy: fixed 350 W server, excludes dynamic power states, PUE, Scope 3.",
    ])

    # VII. Conclusion
    add_heading(doc, "VII. Conclusion", 1)
    add_para(doc,
        "GreenMind AI implements a complete prototype coupling five gradient boosted forecasters "
        "with five-domain multi-agent orchestration, deterministic conflict arbitration, Digital Twin "
        "simulation, and an eight-tool AI copilot. On a 60-day synthetic benchmark, MAE improves "
        "25.4%–45.4% over persistence. Production validation requires open cluster traces, real-time "
        "grid feeds, recursive horizon refactoring, and canary cloud testing.")

    # References
    add_heading(doc, "References", 1)
    refs = [
        "[1] J. H. Friedman, \"Greedy function approximation: A gradient boosting machine,\" "
        "Ann. Statistics, vol. 29, no. 5, pp. 1189–1232, 2001. doi: 10.1214/aos/1013203451.",
        "[2] C. Bergmeir, R. J. Hyndman, and B. Koo, \"Cross-validation for autoregressive "
        "prediction,\" CSDA, vol. 120, pp. 70–83, 2018. doi: 10.1016/j.csda.2017.11.003.",
        "[3] A. Rossi et al., \"Forecasting workload in cloud computing,\" Cluster Comput., "
        "vol. 28, art. 258, 2025. doi: 10.1007/s10586-024-04933-2.",
        "[4] P. Henderson et al., \"Reporting energy/carbon footprints of ML,\" JMLR, vol. 21, "
        "no. 248, 2020.",
        "[5] L. Lannelongue et al., \"Green algorithms,\" Adv. Sci., vol. 8, art. 2100707, 2021. "
        "doi: 10.1002/advs.202100707.",
        "[6] A. Radovanovic et al., \"Carbon-aware computing for datacenters,\" IEEE Trans. Power "
        "Syst., vol. 38, no. 2, pp. 1270–1280, 2023. doi: 10.1109/TPWRS.2022.3173250.",
        "[7] R. N. Calheiros et al., \"Workload prediction using ARIMA,\" IEEE Trans. Cloud "
        "Comput., vol. 3, no. 4, pp. 449–458, 2015. doi: 10.1109/TCC.2014.2350475.",
        "[8] J. Dodge et al., \"Measuring carbon intensity of AI in cloud instances,\" "
        "in Proc. ACM FAccT 2022, pp. 1536–1546. doi: 10.1145/3531146.3533147.",
        "[9] Pratham-stack-coder, \"GreenMind-AI,\" GitHub, 2026. "
        "https://github.com/Pratham-stack-coder/GreenMind-AI.",
    ]
    for r in refs:
        add_para(doc, r, size=9)

    doc.save(str(out_path))
    print(f"IEEE DOCX: {out_path.name} ({out_path.stat().st_size//1024} KB)")


def generate_academic_docx(out_path: Path):
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Cm(2.5)
        section.bottom_margin = Cm(2.5)
        section.left_margin   = Cm(3.0)
        section.right_margin  = Cm(2.5)

    # Title
    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = t.add_run(
        "GreenMind AI: An Explainable Multi-Agent Framework for Sustainable Cloud Resource "
        "Optimization Using Machine Learning and Digital Twin Simulation")
    run.bold = True
    run.font.size = Pt(16)
    run.font.name = "Times New Roman"
    run.font.color.rgb = BLUE

    auth = doc.add_paragraph()
    auth.alignment = WD_ALIGN_PARAGRAPH.CENTER
    auth_run = auth.add_run(
        "Anonymous Submission Draft\n"
        "[Author 1 Name], [Author 2 Name], [Author 3 Name]\n"
        "[Institution Name], [City, Country] | [contact@institution.edu]")
    auth_run.italic = True
    auth_run.font.size = Pt(11)
    auth_run.font.name = "Times New Roman"

    # Abstract
    add_heading(doc, "Abstract", 1)
    add_para(doc,
        "Modern cloud operations require simultaneous optimization of resource utilization, "
        "infrastructure cost, and environmental footprint. We present GreenMind AI, an open-source "
        "decision-support prototype integrating five one-hour-ahead gradient-boosted machine learning "
        "forecasters, a five-domain multi-agent analysis engine, deterministic conflict arbitration, "
        "a non-destructive Digital Twin simulator, and an eight-tool explainable AI copilot. "
        "Evaluation on a 60-day synthetic dataset (N_train=4,604; N_test=1,152; strict chronological "
        "split) demonstrates MAE improvements of 25.4%–45.4% over a one-hour persistence baseline. "
        "A technical audit corrects a baseline horizon discrepancy (15-min vs. 1-hour) and documents "
        "synthetic data provenance, unverified live connectors, a carbon scale mismatch in the "
        "recursive wrapper, and the HTTP 501 safety guard.", italic=True)
    add_para(doc, "Keywords: cloud computing; workload forecasting; gradient boosting; "
             "carbon-aware computing; multi-agent systems; digital twin; GreenOps; decision support.",
             italic=True)

    # Sections
    for title, text in [
        ("1. Introduction",
         "Global cloud infrastructure consumed ~200–250 TWh in 2023 (~1% global electricity demand). "
         "Proactive workload forecasting supports GreenOps and FinOps by enabling right-sizing, "
         "autoscaling, and carbon-aware scheduling. However, high predictive accuracy on historical "
         "data does not guarantee realized savings, carbon abatement, or SLO preservation in "
         "production [3, 8]. GreenMind AI bridges this gap with a unified prototype combining "
         "multi-metric forecasting, five-domain multi-agent orchestration, deterministic conflict "
         "resolution, Digital Twin simulation, and an eight-tool AI copilot."),
        ("2. Background and Related Work",
         "Calheiros et al. [7] demonstrated ARIMA-based proactive cloud provisioning. Friedman's "
         "Gradient Boosting Machine [1] constructs additive tree models suited to structured lag "
         "features. Rossi et al. [3] showed probabilistic LSTMs miss operational uncertainty and "
         "degrade under cross-provider transfer. Bergmeir et al. [2] established chronological "
         "holdout as standard practice. Henderson et al. [4] and Lannelongue et al. [5] formalized "
         "ML carbon accounting. Radovanovic et al. [6] deployed carbon-aware scheduling at Google "
         "datacenters via day-ahead grid predictions. Dodge et al. [8] measured operational carbon "
         "intensity across cloud instances."),
    ]:
        add_heading(doc, title, 1)
        add_para(doc, text)

    # Architecture section with image
    add_heading(doc, "3. System Architecture and Implementation", 1)
    if ARCH.exists():
        try:
            doc.add_picture(str(ARCH), width=Inches(5.5))
            cap = doc.add_paragraph(
                "Figure 1. GreenMind AI pipeline architecture: telemetry ingestion → "
                "ML forecasting → multi-agent analysis → conflict resolution → "
                "Digital Twin simulation → operator decision support.")
            cap.runs[0].italic = True
            cap.runs[0].font.size = Pt(9)
            cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        except Exception:
            pass

    for subhead, text in [
        ("3.1 Telemetry Ingestion and Service Layer",
         "FastAPI (Python 3.12; SQLite/PostgreSQL) ingests five 15-min signals: CPU (%), memory (%), "
         "network (Mbps), cost (USD/h), carbon proxy (gCO₂/15-min). AWS CloudWatch, Azure Monitor "
         "REST, GCP Cloud Monitoring v3 connectors fall back to synthetic generator when credentials absent. "
         "Credentials scoped per authenticated user, encrypted in-memory via credential_crypto.py."),
        ("3.2 Multi-Metric ML Predictor",
         "Five GradientBoostingRegressor models: 150 estimators, depth 3, lr=0.08, seed 42. "
         "Strictly backward-looking features: current value y_t, hour, day, rolling mean μ_{t,4}, σ_{t,4}. "
         "Cost: CPU, memory, cost, hour, day. Carbon: grid intensity (gCO₂/kWh), hour, day, CPU. "
         "Anomaly detection: z-score > 2.5. Training time: ~6.4 s."),
        ("3.3 Multi-Agent Analysis Engine",
         "Five agents in LangGraph StateGraph: CostAgent (right-sizing, Spot/RI), PerformanceAgent "
         "(saturation thresholds, 75% trigger), SustainabilityAgent (green windows 01:00–06:00 UTC), "
         "SecurityAgent (IAM, TLS, port auditing), ReliabilityAgent (multi-AZ, backup RPO). "
         "Graceful sequential fallback with ID deduplication when LangGraph unavailable."),
        ("3.4 Deterministic Conflict Resolution",
         "Three arbitration rules: Performance vs. Cost (right-size + autoscaling, 60-s buffer, "
         "confidence 0.88); Reliability vs. Cost (downsize + failover, confidence 0.92); "
         "Carbon deferral vs. Execution (green windows, confidence 0.87). "
         "Each emits a ConflictResolutionItem with full audit record."),
        ("3.5 Digital Twin Simulator",
         "Five non-destructive scenarios: RIGHT_SIZE, SCALE_UP/DOWN, CONSOLIDATE, REGION_MIGRATION "
         "(e.g., in-north ~650 gCO₂/kWh → ca-central ~90 gCO₂/kWh). Recomputes Optimization Score "
         "(0–100) from state snapshots. All outputs: is_simulated=True, 'SIMULATED / ESTIMATED'."),
        ("3.6 AI Copilot and Remediation Boundary",
         "Eight grounded tools: get_cloud_metrics, get_history, get_predictions, get_cost_analysis, "
         "get_carbon_analysis, get_recommendations, get_cloud_health, run_digital_twin_simulation. "
         "Non-dry-run and rollback endpoints return HTTP 501 Not Implemented."),
    ]:
        add_heading(doc, subhead, 2)
        add_para(doc, text)

    # Methodology
    add_heading(doc, "4. Forecasting Methodology and Experimental Setup", 1)
    for subhead, text in [
        ("4.1 Synthetic Dataset Generation",
         "5,760 observations at 15-min intervals, 2026-06-01, seed 42. "
         "CPU = clip(35 + 30·sin²((h−7)/24·2π)·W_t + τ_t + ε_t, 2, 98), W_t=0.7 weekends, "
         "τ_t∈[0,5]%, ε_t~N(0,16). Memory: [0,8]% drift. "
         "Network: 300+400·sin²(·) Mbps. Cost: $0.192·(1+cpu/100·0.5)."),
        ("4.2 Carbon Target Formulation",
         "us-east grid intensity I(h_t): 320–470 gCO₂/kWh. Server power P=0.35 kW, dt=0.25 h. "
         "C_t = clip(I(h_t)·P·dt + N(0,25), 0, 500) [gCO₂/15-min]. "
         "Excludes dynamic PUE, server power states, Scope 3."),
        ("4.3 Chronological Split",
         "Targets shifted Δ=4 steps; 5,756 aligned records. 80/20 chronological split: "
         "N_train=4,604 (48 days), N_test=1,152 (12 days). No shuffling."),
        ("4.4 Baselines and Metrics",
         "Persistence: ŷ_{t+4}=y_t. Stored Roll-4: ŷ_{t+1}=μ_{t,4} on unshifted data (N=1,148) — "
         "a 15-min prediction. True Roll-4 from origin yields higher error than persistence "
         "(CPU: 7.263% vs. 6.500%) due to diurnal lag. "
         "Metrics: MAE, RMSE, R², Gain(%)=100·(1−MAE_model/MAE_persist)."),
    ]:
        add_heading(doc, subhead, 2)
        add_para(doc, text)

    # Results
    add_heading(doc, "5. Experimental Results", 1)
    add_para(doc,
        "Table 1 presents verified held-out metrics (train.py, seed 42, 6.4 s). "
        "Gradient boosting outperforms persistence on all five targets. MAE gains: "
        "25.4% (memory) to 45.4% (network). CPU and network: R²=0.855/0.871.")
    add_para(doc,
        "Table 1. Verified Forecasting Metrics on Chronological Test Set (N=1,152). "
        "Persistence: ŷ_{t+4}=y_t. Stored Roll-4: 1-step MA on unshifted data. "
        "True Roll-4: four-step rolling mean from forecast origin t.", italic=True)
    add_results_table(doc, size=9)
    doc.add_paragraph()

    add_heading(doc, "5.2 Feature Importances", 2)
    add_bullet_list(doc, [
        "CPU: current lag (69.4%), hour (22.3%), day of week (4.8%), rolling mean (3.3%).",
        "Memory: current value (45.5%), hour (35.7%), rolling mean (17.7%).",
        "Network: current value (67.7%), hour (26.0%), day of week (4.0%).",
        "Cost: CPU (67.1%), hour (21.9%), day of week (5.3%), memory (3.1%).",
        "Carbon: grid intensity (71.1%), hour (20.0%), CPU (8.5%).",
    ])

    # Discussion
    add_heading(doc, "6. Discussion", 1)
    add_para(doc,
        "High R² on CPU and network reflects recovery of the generator's sinusoidal formulas, "
        "not real-world generalization. Real hyperscale traces (Google Borg, Alibaba, Azure Functions) "
        "exhibit heavy-tailed distributions, preemptions, and non-stationary shifts absent from the "
        "synthetic series [3]. Reported metrics establish synthetic benchmark performance only.")
    add_para(doc, "The system cannot claim: (i) verified production cost savings (HTTP 501); "
             "(ii) measured Scope 2 carbon reductions (synthetic proxy); "
             "(iii) generalization to multi-tenant environments; "
             "(iv) validated live cloud connector behavior.")

    # Limitations
    add_heading(doc, "7. Limitations and Threats to Validity", 1)
    add_enum_list(doc, [
        "Data provenance: single generator configuration (seed 42, 60-day, us-east).",
        "Recursive multi-step inconsistency: 5-min steps on 1-h models; carbon output "
        "(~30–40 gCO₂/15-min) fed as carbon_intensity (~350–450 gCO₂/kWh) — ~10× mismatch.",
        "Unverified live connectors: fall back to synthetic data in test environments.",
        "HTTP 501 remediation guard: Digital Twin savings are static projections.",
        "Carbon proxy: fixed 350 W server, excludes PUE, dynamic power states, Scope 3.",
        "Test distribution: 12-day window; no cross-validation across disjoint periods.",
    ])

    # Future Work
    add_heading(doc, "8. Future Work", 1)
    add_bullet_list(doc, [
        "Real trace evaluation: Google Borg v2.1, Alibaba Cluster Data 2018, Azure Functions.",
        "Horizon alignment refactoring: direct multi-horizon models eliminating error accumulation.",
        "Real-time grid integration: Electricity Maps and WattTime live APIs.",
        "Live canary validation: real billing telemetry with isolated cloud subscription.",
        "Uncertainty quantification: quantile regression or conformal prediction intervals.",
    ])

    # Conclusion
    add_heading(doc, "9. Conclusion", 1)
    add_para(doc,
        "GreenMind AI demonstrates a complete, scientifically audited prototype integrating five "
        "gradient boosted forecasters, five-domain multi-agent orchestration, deterministic conflict "
        "arbitration, Digital Twin simulation, and an eight-tool AI copilot. On a 60-day synthetic "
        "benchmark, MAE improves 25.4%–45.4% over persistence. A thorough audit verified all metrics, "
        "corrected the baseline alignment discrepancy, documented the recursive wrapper scale mismatch, "
        "and established clear scope boundaries for future production validation.")

    # References
    add_heading(doc, "References", 1)
    refs = [
        "[1] J. H. Friedman, \"Greedy function approximation: A gradient boosting machine,\" "
        "The Annals of Statistics, vol. 29, no. 5, pp. 1189–1232, 2001. doi: 10.1214/aos/1013203451.",
        "[2] C. Bergmeir, R. J. Hyndman, and B. Koo, \"A note on the validity of cross-validation "
        "for evaluating autoregressive time series prediction,\" Computational Statistics & Data Analysis, "
        "vol. 120, pp. 70–83, 2018. doi: 10.1016/j.csda.2017.11.003.",
        "[3] A. Rossi, A. Visentin, D. Carraro, S. Prestwich, and K. N. Brown, \"Forecasting workload "
        "in cloud computing: Towards uncertainty-aware predictions and transfer learning,\" "
        "Cluster Computing, vol. 28, art. 258, 2025. doi: 10.1007/s10586-024-04933-2.",
        "[4] P. Henderson et al., \"Towards the systematic reporting of the energy and carbon footprints "
        "of machine learning,\" JMLR, vol. 21, no. 248, 2020.",
        "[5] L. Lannelongue, J. Grealey, and M. Inouye, \"Green algorithms: Quantifying the carbon "
        "footprint of computation,\" Advanced Science, vol. 8, art. 2100707, 2021. "
        "doi: 10.1002/advs.202100707.",
        "[6] A. Radovanovic et al., \"Carbon-aware computing for datacenters,\" IEEE Transactions on "
        "Power Systems, vol. 38, no. 2, pp. 1270–1280, 2023. doi: 10.1109/TPWRS.2022.3173250.",
        "[7] R. N. Calheiros, E. Masoumi, R. Ranjan, and R. Buyya, \"Workload prediction using ARIMA "
        "model and its impact on cloud applications QoS,\" IEEE Transactions on Cloud Computing, "
        "vol. 3, no. 4, pp. 449–458, 2015. doi: 10.1109/TCC.2014.2350475.",
        "[8] J. Dodge, T. Prewitt, R. T. Des Combes, E. Odmark, R. Schwartz, E. Strubell, "
        "A. S. Luccioni, N. A. Smith, N. DeCario, and W. Buchanan, \"Measuring the carbon intensity "
        "of AI in cloud instances,\" in Proc. ACM FAccT 2022, Seoul, 2022, pp. 1536–1546. "
        "doi: 10.1145/3531146.3533147.",
        "[9] Pratham-stack-coder, \"GreenMind-AI repository,\" GitHub, 2026. "
        "[Online]. Available: https://github.com/Pratham-stack-coder/GreenMind-AI.",
    ]
    for r in refs:
        add_para(doc, r, size=9)

    doc.save(str(out_path))
    print(f"Academic DOCX: {out_path.name} ({out_path.stat().st_size//1024} KB)")


def main():
    print("Generating DOCX files...")
    generate_ieee_docx(HERE / "GreenMind_AI_IEEE_5_Page.docx")
    generate_academic_docx(HERE / "GreenMind_AI_Academic_10_Page.docx")
    print("Done.")


if __name__ == "__main__":
    main()
