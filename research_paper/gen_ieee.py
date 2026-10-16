"""
GreenMind AI - IEEE 5-page PDF Generator
Uses ReportLab to produce a publication-quality IEEE-style two-column PDF.
"""
from __future__ import annotations
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.flowables import HRFlowable

HERE = Path(__file__).resolve().parent
ARCH = HERE / "greenmind_architecture.png"
IEEE_BLUE = colors.HexColor("#003087")
DARK = colors.HexColor("#111111")
MID  = colors.HexColor("#555555")
LIGHT= colors.HexColor("#888888")
ALT  = colors.HexColor("#EEF2F8")

def S():
    """Build style dict."""
    st = {}
    def add(name, **kw):
        base = dict(fontName="Times-Roman", fontSize=8.5, leading=10.5,
                    textColor=DARK, spaceAfter=3, spaceBefore=2,
                    alignment=TA_JUSTIFY)
        base.update(kw)
        st[name] = ParagraphStyle(name, **base)
    add("body")
    add("title", fontName="Times-Bold", fontSize=13, leading=16,
        alignment=TA_CENTER, textColor=IEEE_BLUE, spaceAfter=3)
    add("auth", fontName="Times-Italic", fontSize=8.5, leading=11,
        alignment=TA_CENTER, textColor=MID, spaceAfter=4)
    add("abs", fontName="Times-Italic", fontSize=7.8, leading=9.8,
        leftIndent=5, rightIndent=5, spaceAfter=5)
    add("h1", fontName="Times-Bold", fontSize=8.5, leading=10.5,
        alignment=TA_CENTER, textColor=IEEE_BLUE, spaceBefore=8, spaceAfter=4)
    add("h2", fontName="Times-BoldItalic", fontSize=8.2, leading=10,
        spaceBefore=5, spaceAfter=2)
    add("bul", fontName="Times-Roman", fontSize=8.5, leading=10.5,
        leftIndent=9, firstLineIndent=-7, spaceAfter=2)
    add("en", fontName="Times-Roman", fontSize=8.5, leading=10.5,
        leftIndent=11, firstLineIndent=-9, spaceAfter=2)
    add("cap", fontName="Times-Italic", fontSize=7.2, leading=9,
        alignment=TA_CENTER, textColor=MID, spaceAfter=4)
    add("ref", fontName="Times-Roman", fontSize=7.2, leading=9,
        leftIndent=9, firstLineIndent=-9, spaceAfter=2)
    add("th", fontName="Times-Bold", fontSize=6.8, leading=8.5,
        alignment=TA_CENTER, textColor=colors.white)
    add("td", fontName="Times-Roman", fontSize=6.8, leading=8.5,
        alignment=TA_CENTER)
    add("tdl", fontName="Times-Roman", fontSize=6.8, leading=8.5,
        alignment=TA_LEFT)
    return st

def p(t, style): return Paragraph(t, style)
def sp(n=4): return Spacer(1, n)

def results_table(st):
    hdr = ["Target", "MAE", "RMSE", "R2", "Persist.", "Roll-4\n(Stored)", "Roll-4\n(True)", "Gain%"]
    rows = [
        ["CPU Util. (%)",       "3.809",  "4.811",  "0.855", "6.500",  "4.622", "7.263",  "41.4"],
        ["Memory Util. (%)",    "2.979",  "3.704",  "0.636", "3.996",  "3.025", "4.153",  "25.4"],
        ["Net Traffic (Mbps)", "43.876", "55.328", "0.871", "80.346", "56.727","90.816", "45.4"],
        ["Hourly Cost ($/h)",   "0.009",  "0.011",  "0.474", "0.013",  "0.010", "N/A",    "29.7"],
        ["Carbon (gCO2/15m)",  "4.061",  "5.087",  "0.391", "5.846",  "4.571", "N/A",    "30.5"],
    ]
    data = [[p(h, st["th"]) for h in hdr]]
    for i, r in enumerate(rows):
        row = [p(r[0], st["tdl"])] + [p(v, st["td"]) for v in r[1:]]
        data.append(row)
    cw = [1.45*inch, 0.53*inch, 0.58*inch, 0.48*inch,
          0.58*inch, 0.63*inch, 0.63*inch, 0.48*inch]
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0),(-1,0), IEEE_BLUE),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, ALT]),
        ("GRID",(0,0),(-1,-1),0.2,colors.HexColor("#BBBBBB")),
        ("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("ALIGN",(0,1),(0,-1),"LEFT"),
        ("TOPPADDING",(0,0),(-1,-1),1.5),
        ("BOTTOMPADDING",(0,0),(-1,-1),1.5),
        ("LEFTPADDING",(0,0),(-1,-1),2),
        ("RIGHTPADDING",(0,0),(-1,-1),2),
        ("LINEBELOW",(0,0),(-1,0),0.8,IEEE_BLUE),
        ("LINEBELOW",(0,-1),(-1,-1),0.8,IEEE_BLUE),
    ]))
    return t

def build_story(st):
    s = []
    hr = lambda: HRFlowable(width="100%", thickness=0.6, color=IEEE_BLUE, spaceAfter=4)

    s += [
        p("GreenMind AI: A Multi-Metric Forecasting and Decision-Support Platform for Cloud GreenOps", st["title"]),
        p("Anonymous Submission Draft — Author affiliations to be inserted for camera-ready submission", st["auth"]),
        hr(),
        p("<i><b>Abstract—</b>Modern cloud operations require optimizing resource utilization, cost, "
          "and environmental footprint simultaneously. GreenMind AI is an open-source decision-support "
          "prototype integrating five one-hour-ahead gradient-boosted forecasters, a five-domain "
          "multi-agent analysis engine (Cost, Performance, Sustainability, Security, Reliability), "
          "deterministic conflict arbitration, a non-destructive Digital Twin simulator, and an "
          "eight-tool explainable AI copilot. Evaluation on a deterministic 60-day synthetic dataset "
          "(5,756 records; 80/20 chronological split: N_train=4,604, N_test=1,152) shows MAE "
          "improvements of 25.4%-45.4% over a one-hour persistence baseline. Our audit reveals the "
          "stored rolling baseline reflects a 15-min prediction rather than the 1-hour target; the "
          "true four-step rolling baseline yields higher error than persistence (CPU: 7.263% vs. "
          "6.500%) due to diurnal phase shift. All evaluations derive from synthetic generator "
          "equations; live remediation is guarded by HTTP 501. Synthetic accuracy must not be "
          "conflated with verified production savings.</i>", st["abs"]),
        p("<b>Index Terms</b>—cloud computing; workload forecasting; gradient boosting; "
          "carbon-aware computing; multi-agent systems; digital twin; GreenOps.", st["abs"]),
        hr(),
    ]

    # I. Introduction
    s.append(p("I. INTRODUCTION", st["h1"]))
    s.append(p("Cloud data centers consume a substantial and growing share of global electricity, "
               "driving GreenOps and FinOps disciplines [4, 6]. Proactive workload forecasting "
               "supports right-sizing, autoscaling, and carbon-aware scheduling, but high historical "
               "accuracy does not guarantee realized savings in production systems [3, 8]. Existing "
               "platforms treat cost, performance, sustainability, and reliability as siloed concerns. "
               "GreenMind AI addresses this by unifying: (i) multi-metric gradient boosted forecasting, "
               "(ii) five-domain multi-agent orchestration via a state graph, (iii) deterministic "
               "conflict resolution with explicit audit logs, (iv) non-destructive Digital Twin "
               "simulation, and (v) an eight-tool AI copilot grounded in live application state.", st["body"]))
    s.append(sp())
    s.append(p("<b>Contributions:</b>", st["body"]))
    for n, t in enumerate([
        "End-to-end architecture linking telemetry ingestion, multi-metric forecasting, multi-agent arbitration, Digital Twin simulation, and decision-support interfaces.",
        "Verified forecasting performance on five targets with a baseline alignment audit identifying a 15-min vs. 1-hour horizon discrepancy in the stored rolling baseline.",
        "Explicit empirical scope boundaries: synthetic data provenance, unverified live connectors, and the HTTP 501 live-remediation safety guard.",
    ], 1):
        s.append(p(f"{n}. {t}", st["en"]))

    # II. Related Work
    s.append(p("II. RELATED WORK", st["h1"]))
    s.append(p("Calheiros et al. [7] showed ARIMA-based proactive scaling reduces QoS violations. "
               "Friedman's Gradient Boosting Machine [1] constructs additive tree models suited to "
               "structured lag features. Rossi et al. [3] evaluated probabilistic LSTMs on real "
               "cluster traces, showing point forecasts miss operational uncertainty and accuracy "
               "degrades under cross-provider transfer. Bergmeir et al. [2] established chronological "
               "holdout as standard practice. Henderson et al. [4] and Lannelongue et al. [5] "
               "formalized ML energy and carbon reporting standards. Radovanovic et al. [6] deployed "
               "carbon-aware scheduling at Google datacenters using day-ahead grid predictions. "
               "Dodge et al. [8] measured operational carbon intensity across cloud instances. "
               "GreenMind AI extends these with a unified prototype evaluated on synthetic telemetry.", st["body"]))

    # III. Architecture
    s.append(p("III. PLATFORM ARCHITECTURE AND IMPLEMENTATION", st["h1"]))
    if ARCH.exists():
        try:
            cw = 3.2 * inch
            s.append(Image(str(ARCH), width=cw, height=cw*0.56))
            s.append(p("Fig. 1. GreenMind AI pipeline: telemetry ingestion -> ML forecasting -> "
                       "multi-agent analysis -> conflict resolution -> Digital Twin -> decision support.", st["cap"]))
        except Exception:
            pass

    for label, text in [
        ("A. Telemetry and Service Layer",
         "FastAPI (Python 3.12; SQLite/PostgreSQL) ingests five 15-min signals: CPU (%), memory (%), "
         "network (Mbps), cost (USD/h), carbon proxy (gCO2/15-min). AWS CloudWatch (boto3), Azure "
         "Monitor REST, GCP Cloud Monitoring v3 connectors fall back to synthetic generator when credentials absent."),
        ("B. Multi-Metric ML Predictor",
         "Five GradientBoostingRegressor models: 150 estimators, depth 3, lr=0.08, seed 42. Backward-looking "
         "features: current value y_t, hour, day, rolling mean mu_{t,4}, rolling sigma_{t,4}. "
         "Cost: CPU, memory, cost, hour, day. Carbon: grid intensity (gCO2/kWh), hour, day, CPU. "
         "Anomaly flag: z-score > 2.5."),
        ("C. Multi-Agent Analysis Engine",
         "Five agents in a LangGraph StateGraph: CostAgent (right-sizing, Spot/RI), PerformanceAgent "
         "(saturation, autoscaling), SustainabilityAgent (green windows 01:00-06:00 UTC), "
         "SecurityAgent (IAM, TLS, ports), ReliabilityAgent (multi-AZ, backup RPO). "
         "Graceful sequential fallback with ID deduplication when LangGraph unavailable."),
        ("D. Deterministic Conflict Resolution",
         "Three arbitration rules: (i) Performance vs. Cost (35% <= CPU < 75%): right-size + "
         "predictive autoscaling, 60-s buffer, confidence 0.88; (ii) Reliability vs. Cost (CPU < 35%): "
         "downsize + automated failover, confidence 0.92; (iii) Carbon deferral vs. Execution: "
         "shift non-critical batches to green windows, confidence 0.87. Each emits a full audit record."),
        ("E. Digital Twin Simulator",
         "Five non-destructive scenarios: Right-Size, Scale-Up/Down, Consolidate, Region Migration "
         "(e.g., in-north ~650 gCO2/kWh to ca-central ~90 gCO2/kWh). Recomputes Optimization Score "
         "(0-100) before/after. All outputs: is_simulated=True, label='SIMULATED / ESTIMATED'."),
        ("F. AI Copilot and Remediation Boundary",
         "Eight grounded tools: get_cloud_metrics, get_history, get_predictions, get_cost_analysis, "
         "get_carbon_analysis, get_recommendations, get_cloud_health, run_digital_twin_simulation. "
         "Non-dry-run and rollback endpoints return HTTP 501 Not Implemented."),
    ]:
        s.append(p(label, st["h2"]))
        s.append(p(text, st["body"]))

    # IV. Methodology
    s.append(p("IV. EXPERIMENTAL METHODOLOGY", st["h1"]))
    for label, text in [
        ("A. Synthetic Dataset",
         "generate_dataset.py: 5,760 observations at 15-min intervals from 2026-06-01, seed 42. "
         "CPU = clip(35 + 30*sin^2((h-7)/24*2*pi)*W_t + tau_t + epsilon_t, 2, 98), W_t=0.7 weekends, "
         "tau_t in [0,5]%, epsilon_t~N(0,16). Memory: [0,8]% drift. Network: 300+400*sin^2(.) Mbps. "
         "Cost: $0.192*(1+cpu/100*0.5) + N(0,0.0001) [m5.xlarge baseline]."),
        ("B. Carbon Target",
         "us-east grid intensity I(h_t) in 320-470 gCO2/kWh. Server power P=0.35 kW, step dt=0.25 h. "
         "C_t = clip(I(h_t)*P*dt + N(0,25), 0, 500) [gCO2/15-min]. "
         "Excludes dynamic PUE, server power states, Scope 3 emissions."),
        ("C. Chronological Split and Baselines",
         "Targets shifted delta=4 steps; 4 trailing rows dropped -> 5,756 aligned records. "
         "80/20 chronological split: N_train=4,604 (48d), N_test=1,152 (12d). No shuffling. "
         "Persistence: y-hat_{t+4}=y_t. Stored Roll-4: evaluates y-hat_{t+1}=mu_{t,4} on "
         "unshifted test (N=1,148) - a 15-min prediction. True Roll-4 from origin: yields higher "
         "error than persistence (CPU: 7.263% vs. 6.500%) due to diurnal phase lag. "
         "Metrics: MAE, RMSE, R2, Gain(%)=100*(1-MAE_model/MAE_persist)."),
    ]:
        s.append(p(label, st["h2"]))
        s.append(p(text, st["body"]))

    # V. Results
    s.append(p("V. EXPERIMENTAL RESULTS", st["h1"]))
    s.append(p("Table I reports verified held-out metrics from re-running train.py (seed 42, 6.4 s). "
               "Gradient boosting outperforms persistence on all five targets: MAE gains 25.4% "
               "(memory) to 45.4% (network). CPU/network achieve R2=0.855/0.871, capturing "
               "sinusoidal generator patterns. Cost (R2=0.474) and carbon (R2=0.391) are "
               "noise-limited. Feature importances: CPU lag 69.4%, hour 22.3% for CPU; "
               "grid intensity 71.1%, hour 20.0% for carbon.", st["body"]))
    s.append(p("<b>Table I.</b> Verified Test-Set Metrics (N=1,152). True Roll-4 yields higher error "
               "than persistence due to diurnal phase lag.", st["cap"]))
    s.append(results_table(st))
    s.append(sp())

    # VI. Discussion
    s.append(p("VI. DISCUSSION AND LIMITATIONS", st["h1"]))
    s.append(p("<b>A. Synthetic vs. Real Generalization.</b> "
               "High R2 reflects recovery of smooth sinusoidal generator formulas. Real cluster traces "
               "(Google Borg, Alibaba, Azure Functions) exhibit heavy-tailed distributions, preemptions, "
               "and non-stationary shifts absent from the synthetic series [3]. "
               "Reported metrics establish synthetic benchmark performance only.", st["body"]))
    s.append(sp())
    s.append(p("<b>B. Documented Limitations.</b>", st["body"]))
    for n, t in enumerate([
        "Data provenance: single generator configuration (seed 42, 60-day, us-east).",
        "Recursive multi-step inconsistency: forecast_multi_step applies 5-min steps on 1-h models; feeds carbon output (~30-40 gCO2/15-min) into carbon_intensity trained on ~350-450 gCO2/kWh (~10x mismatch).",
        "Live connectors: fall back to synthetic data; end-to-end live polling not validated.",
        "HTTP 501 live remediation: all cloud mutations blocked; Digital Twin savings are projections only.",
        "Carbon proxy: fixed 350 W, excludes dynamic power states, PUE, Scope 3 [5].",
    ], 1):
        s.append(p(f"{n}. {t}", st["en"]))

    # VII. Conclusion
    s.append(p("VII. CONCLUSION", st["h1"]))
    s.append(p("GreenMind AI couples five gradient boosted forecasters with five-domain multi-agent "
               "orchestration, deterministic conflict arbitration, Digital Twin simulation, and an "
               "eight-tool AI copilot. On a 60-day synthetic benchmark, MAE improves 25.4%-45.4% "
               "over persistence. These results reflect synthetic-generator learning. Production "
               "validation requires open cluster traces (Google Borg, Alibaba, Azure Functions), "
               "real-time grid feeds (Electricity Maps, WattTime), recursive horizon refactoring, "
               "and end-to-end canary cloud testing.", st["body"]))

    # References
    s.append(HRFlowable(width="100%", thickness=0.5, color=IEEE_BLUE, spaceBefore=5, spaceAfter=3))
    s.append(p("REFERENCES", st["h1"]))
    refs = [
        "[1] J. H. Friedman, \"Greedy function approximation: A gradient boosting machine,\" Ann. Statistics, vol. 29, no. 5, pp. 1189-1232, 2001. doi: 10.1214/aos/1013203451.",
        "[2] C. Bergmeir, R. J. Hyndman, and B. Koo, \"A note on the validity of cross-validation for evaluating autoregressive time series prediction,\" CSDA, vol. 120, pp. 70-83, 2018. doi: 10.1016/j.csda.2017.11.003.",
        "[3] A. Rossi et al., \"Forecasting workload in cloud computing: Towards uncertainty-aware predictions and transfer learning,\" Cluster Comput., vol. 28, art. 258, 2025. doi: 10.1007/s10586-024-04933-2.",
        "[4] P. Henderson et al., \"Towards the systematic reporting of the energy and carbon footprints of machine learning,\" JMLR, vol. 21, no. 248, 2020.",
        "[5] L. Lannelongue, J. Grealey, and M. Inouye, \"Green algorithms: Quantifying the carbon footprint of computation,\" Adv. Sci., vol. 8, no. 12, 2100707, 2021. doi: 10.1002/advs.202100707.",
        "[6] A. Radovanovic et al., \"Carbon-aware computing for datacenters,\" IEEE Trans. Power Syst., vol. 38, no. 2, pp. 1270-1280, 2023. doi: 10.1109/TPWRS.2022.3173250.",
        "[7] R. N. Calheiros et al., \"Workload prediction using ARIMA model and its impact on cloud applications QoS,\" IEEE Trans. Cloud Comput., vol. 3, no. 4, pp. 449-458, 2015. doi: 10.1109/TCC.2014.2350475.",
        "[8] J. Dodge et al., \"Measuring the carbon intensity of AI in cloud instances,\" in Proc. ACM FAccT 2022, pp. 1536-1546. doi: 10.1145/3531146.3533147.",
        "[9] Pratham-stack-coder, \"GreenMind-AI,\" GitHub, 2026. [Online]. Available: https://github.com/Pratham-stack-coder/GreenMind-AI.",
    ]
    for r in refs:
        s.append(p(r, st["ref"]))

    return s

def main():
    PAGE_W, PAGE_H = letter
    M = 0.75 * inch
    G = 0.25 * inch
    CW = (PAGE_W - 2*M - G) / 2

    styles = S()

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 7)
        canvas.setFillColor(LIGHT)
        canvas.drawCentredString(PAGE_W/2, 0.40*inch,
            f"GreenMind AI -- IEEE-Style Conference Paper -- Page {doc.page}")
        canvas.restoreState()

    title_h = 1.95 * inch
    body_h  = PAGE_H - 2*M - title_h - 0.6*inch

    tf = Frame(M, PAGE_H - M - title_h, PAGE_W - 2*M, title_h, id="title")
    lf = Frame(M, M + 0.3*inch, CW, body_h, id="left")
    rf = Frame(M + CW + G, M + 0.3*inch, CW, body_h, id="right")
    lf2= Frame(M, M + 0.3*inch, CW, PAGE_H - 2*M - 0.6*inch, id="left2")
    rf2= Frame(M + CW + G, M + 0.3*inch, CW, PAGE_H - 2*M - 0.6*inch, id="right2")

    p1 = PageTemplate(id="first", frames=[tf, lf, rf], onPageEnd=footer)
    pn = PageTemplate(id="rest",  frames=[lf2, rf2], onPageEnd=footer)

    out = HERE / "GreenMind_AI_IEEE_5_Page.pdf"
    doc = BaseDocTemplate(str(out), pagesize=letter,
                          leftMargin=M, rightMargin=M,
                          topMargin=M, bottomMargin=M)
    doc.addPageTemplates([p1, pn])
    doc.build(build_story(styles))
    size = out.stat().st_size / 1024
    print(f"IEEE PDF: {out.name} ({size:.0f} KB)")

if __name__ == "__main__":
    main()
