"""
GreenMind AI - IEEE 5-page Two-Column PDF Generator
Calibrated to generate EXACTLY 5 pages with professional IEEE styling.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
import pypdfium2 as pdfium

HERE = Path(__file__).resolve().parent
ARCH_IMG = HERE / "greenmind_architecture.png"
EVAL_IMG = HERE / "empirical_evaluation.png"

IEEE_BLUE = colors.HexColor("#003087")
DARK_GRAY = colors.HexColor("#1A1A1A")
TEXT_COLOR = colors.HexColor("#222222")
MUTED_GRAY = colors.HexColor("#555555")
BORDER_COLOR = colors.HexColor("#BDC3C7")
ALT_ROW_BG = colors.HexColor("#F4F6F9")

def build_styles(base_font_size=7.6, base_leading=9.2):
    st = {}
    def add(name, **kw):
        cfg = dict(
            fontName="Times-Roman",
            fontSize=base_font_size,
            leading=base_leading,
            textColor=TEXT_COLOR,
            spaceAfter=2.0,
            spaceBefore=1.0,
            alignment=TA_JUSTIFY,
        )
        cfg.update(kw)
        st[name] = ParagraphStyle(name, **cfg)

    add("body")
    add("body_bold", fontName="Times-Bold")
    add("title", fontName="Times-Bold", fontSize=12.2, leading=14.0,
        alignment=TA_CENTER, textColor=IEEE_BLUE, spaceAfter=2.0, spaceBefore=0)
    add("subtitle", fontName="Times-BoldItalic", fontSize=8.5, leading=10.2,
        alignment=TA_CENTER, textColor=DARK_GRAY, spaceAfter=2.0)
    add("auth", fontName="Times-Italic", fontSize=7.6, leading=9.2,
        alignment=TA_CENTER, textColor=MUTED_GRAY, spaceAfter=2.5)
    add("abs", fontName="Times-Italic", fontSize=7.0, leading=8.4,
        alignment=TA_JUSTIFY, spaceAfter=2.0, spaceBefore=1.0)
    add("keywords", fontName="Times-Roman", fontSize=7.0, leading=8.4,
        alignment=TA_JUSTIFY, spaceAfter=2.5)
    add("h1", fontName="Times-Bold", fontSize=8.0, leading=9.5,
        alignment=TA_CENTER, textColor=IEEE_BLUE, spaceBefore=4.0, spaceAfter=1.5,
        keepWithNext=True)
    add("h2", fontName="Times-BoldItalic", fontSize=7.6, leading=9.0,
        spaceBefore=2.8, spaceAfter=1.2, keepWithNext=True)
    add("h3", fontName="Times-Italic", fontSize=7.3, leading=8.7,
        spaceBefore=1.8, spaceAfter=0.8, keepWithNext=True)
    add("en", fontName="Times-Roman", fontSize=7.3, leading=8.7,
        leftIndent=8, firstLineIndent=-8, spaceAfter=1.2, spaceBefore=0.4)
    add("cap", fontName="Times-Italic", fontSize=6.6, leading=7.9,
        alignment=TA_CENTER, textColor=MUTED_GRAY, spaceBefore=1.2, spaceAfter=2.0)
    add("ref", fontName="Times-Roman", fontSize=6.4, leading=7.4,
        leftIndent=9, firstLineIndent=-9, spaceAfter=1.0, spaceBefore=0.3)
    
    # Table styles
    add("th", fontName="Times-Bold", fontSize=6.2, leading=7.4,
        alignment=TA_CENTER, textColor=colors.white)
    add("td", fontName="Times-Roman", fontSize=6.0, leading=7.1,
        alignment=TA_CENTER)
    add("tdl", fontName="Times-Roman", fontSize=6.0, leading=7.1,
        alignment=TA_LEFT)
    add("td_bold", fontName="Times-Bold", fontSize=6.0, leading=7.1,
        alignment=TA_CENTER)
    return st

def make_table_results(st):
    hdr = ["Target Metric", "MAE", "RMSE", "R2", "Persist.\nMAE", "Stored\nRoll-4", "True\nRoll-4", "Gain\n(%)"]
    rows = [
        ["CPU Util. (%)",       "3.809",  "4.811",  "0.855", "6.500",  "4.622", "7.263",  "41.4%"],
        ["Memory Util. (%)",    "2.979",  "3.704",  "0.636", "3.996",  "3.025", "4.153",  "25.4%"],
        ["Network (Mbps)",     "43.876", "55.328", "0.871", "80.346", "56.727","90.816", "45.4%"],
        ["Hourly Cost ($/h)",   "0.009",  "0.011",  "0.474", "0.013",  "0.010", "N/A",    "29.7%"],
        ["Carbon (gCO2/15m)",  "4.061",  "5.087",  "0.391", "5.846",  "4.571", "N/A",    "30.5%"],
    ]
    data = [[Paragraph(h, st["th"]) for h in hdr]]
    for r in rows:
        row = [Paragraph(r[0], st["tdl"])] + [Paragraph(v, st["td_bold"] if j == 7 else st["td"]) for j, v in enumerate(r[1:], 1)]
        data.append(row)
    cw = [54, 25, 27, 23, 27, 28, 28, 25] # total ~237 pt
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), IEEE_BLUE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, ALT_ROW_BG]),
        ("GRID", (0,0), (-1,-1), 0.3, BORDER_COLOR),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("ALIGN", (0,1), (0,-1), "LEFT"),
        ("TOPPADDING", (0,0), (-1,-1), 0.8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0.8),
        ("LEFTPADDING", (0,0), (-1,-1), 1.0),
        ("RIGHTPADDING", (0,0), (-1,-1), 1.0),
        ("LINEBELOW", (0,0), (-1,0), 0.8, IEEE_BLUE),
        ("LINEBELOW", (0,-1), (-1,-1), 0.8, IEEE_BLUE),
    ]))
    return t

def make_table_features(st):
    hdr = ["Target", "Primary Lag (t)", "Imp.", "Cyclic Time", "Imp.", "Secondary Feature", "Imp."]
    rows = [
        ["CPU",    "cpu_lag (t)",       "69.4%", "hour_of_day",   "22.3%", "day_of_week",     "4.8%"],
        ["Memory", "memory_lag (t)",    "45.5%", "hour_of_day",   "35.7%", "mem_roll_avg_1h", "17.7%"],
        ["Network","network_lag (t)",   "67.7%", "hour_of_day",   "26.0%", "day_of_week",     "4.0%"],
        ["Cost",   "cpu_utilization",   "67.1%", "hour_of_day",   "21.9%", "day_of_week",     "5.3%"],
        ["Carbon", "grid_carbon_intens","71.1%", "hour_of_day",   "20.0%", "cpu_utilization", "8.5%"],
    ]
    data = [[Paragraph(h, st["th"]) for h in hdr]]
    for r in rows:
        row = [Paragraph(r[0], st["td_bold"])] + [Paragraph(v, st["tdl"] if j%2==1 else st["td"]) for j, v in enumerate(r[1:], 1)]
        data.append(row)
    cw = [32, 50, 22, 45, 22, 43, 23] # total = 237 pt
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), IEEE_BLUE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, ALT_ROW_BG]),
        ("GRID", (0,0), (-1,-1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0,0), (-1,-1), 0.8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0.8),
        ("LEFTPADDING", (0,0), (-1,-1), 1.0),
        ("RIGHTPADDING", (0,0), (-1,-1), 1.0),
    ]))
    return t

def make_table_scenarios(st):
    hdr = ["Simulated Scenario", "Monthly Cost", "Cost Delta", "Monthly Carbon", "Carbon Delta", "Score Delta"]
    rows = [
        ["Right-Size Instances", "$604.80", "-30.0%", "75.6 kg", "-30.0%", "+15 pts"],
        ["Scale-Down Capacity",  "$691.20", "-20.0%", "86.4 kg", "-20.0%", "+10 pts"],
        ["Scale-Up Capacity",    "$1,080.00","+25.0%","135.0 kg", "+25.0%", "-8 pts"],
        ["Workload Consolidation","$648.00", "-25.0%", "81.0 kg", "-25.0%", "+12 pts"],
        ["Region Migration (ca)", "$864.00", "0.0%",   "14.4 kg", "-86.7%", "+22 pts"],
    ]
    data = [[Paragraph(h, st["th"]) for h in hdr]]
    for r in rows:
        row = [Paragraph(r[0], st["tdl"])] + [Paragraph(v, st["td"]) for v in r[1:]]
        data.append(row)
    cw = [62, 36, 34, 38, 35, 32] # total = 237 pt
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), IEEE_BLUE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, ALT_ROW_BG]),
        ("GRID", (0,0), (-1,-1), 0.3, BORDER_COLOR),
        ("TOPPADDING", (0,0), (-1,-1), 0.8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0.8),
        ("LEFTPADDING", (0,0), (-1,-1), 1.0),
        ("RIGHTPADDING", (0,0), (-1,-1), 1.0),
    ]))
    return t

def generate_story(st, spacer_scale=1.0):
    s = []
    p = lambda t, style_name="body": Paragraph(t, st[style_name])
    sp = lambda h=2.0: Spacer(1, h * spacer_scale)

    # ── HEADER & TITLE ───────────────────────────────────────────────────────
    s.append(p("GreenMind AI: An Explainable Multi-Agent Framework for Sustainable Cloud Resource Optimization Using Machine Learning and Digital Twin Simulation", "title"))
    s.append(p("Pratham Patel<sup>1</sup>, Cloud Computing &amp; Machine Learning Research Group", "subtitle"))
    s.append(p("<sup>1</sup>GreenMind AI Project, https://github.com/Pratham-stack-coder/GreenMind-AI", "auth"))
    s.append(HRFlowable(width="100%", thickness=0.8, color=IEEE_BLUE, spaceBefore=1, spaceAfter=2.0))

    # ── ABSTRACT & INDEX TERMS ───────────────────────────────────────────────
    s.append(p("<b><i>Abstract</i>—Hyperscale cloud data centers consume significant electrical energy and produce millions of tons of operational carbon emissions. While autonomous autoscaling and rightsizing algorithms promise efficiency, operators resist autonomous mutation due to opaque decisions, siloed objectives, and fear of service disruptions. This paper presents GreenMind AI, an open-source, explainable decision-support framework that unifies: (1) five gradient-boosted time-series models forecasting CPU, memory, network, cost, and carbon intensity 1 hour ahead; (2) a five-domain multi-agent analysis engine (Cost, Performance, Sustainability, Security, Reliability) orchestrated via a LangGraph state graph; (3) a deterministic conflict resolution engine enforcing explicit priority matrices with transparent audit logs; (4) a non-destructive Digital Twin simulation engine modeling 5 optimization scenarios with 4-pillar efficiency scoring; and (5) an eight-tool conversational AI Copilot grounded in verified system telemetry. Empirical evaluation across a 60-day deterministic synthetic dataset (5,756 observations, strict 80/20 chronological holdout) demonstrates MAE reductions over a 1-hour persistence baseline ranging from 25.4% (memory) to 45.4% (network), with CPU utilization achieving an MAE of 3.809% (R2=0.855). Our technical audit identified a critical temporal horizon mismatch in the stored rolling baseline (15-min lookahead vs. 1-hour target); true 4-step rolling averages from forecast origin exhibit higher error (7.263% MAE) than persistence due to diurnal phase lag. All evaluations derive from synthetic generator dynamics; live cloud connectors operate in emulation, and production mutations are safely sandboxed behind an HTTP 501 boundary. This research establishes rigorous empirical bounds for explainable, carbon-aware cloud decision support.</b>", "abs"))
    s.append(p("<b><i>Index Terms</i>—Cloud computing, GreenOps, FinOps, workload forecasting, gradient tree boosting, multi-agent systems, deterministic conflict resolution, digital twin simulation, explainable AI.</b>", "keywords"))
    s.append(HRFlowable(width="100%", thickness=0.4, color=BORDER_COLOR, spaceBefore=1.5, spaceAfter=2.5))

    # ── I. INTRODUCTION ──────────────────────────────────────────────────────
    s.append(p("I. INTRODUCTION", "h1"))
    s.append(p("Global cloud data centers consume an estimated 200 to 250 terawatt-hours of electrical energy annually, representing approximately 1.0% to 1.5% of worldwide electricity consumption [4, 6, 10]. Driven by the explosive proliferation of large language models, streaming analytics, and deep learning training clusters, infrastructure capacity is expanding exponentially. Consequently, enterprise cloud operations have experienced an urgent convergence of two critical management disciplines: FinOps (financial operations focused on unit cost economics) and GreenOps (environmentally sustainable operations focused on minimizing operational greenhouse gas emissions)."))
    s.append(p("However, achieving operational equilibrium between financial thrift and carbon efficiency is notoriously complex. In modern multi-tenant environments, operational priorities are in constant structural conflict. Aggressive compute rightsizing reduces monetary waste and idle energy dissipation, but severely degrades service headroom, triggering latency spikes or cascading SLA breaches during sudden traffic bursts [11, 12]. Conversely, maintaining conservative capacity buffers protects reliability but inflates capital expense and drives unnecessary Scope 2 emissions."))
    s.append(p("Geographic workload shifting introduces further friction: migrating compute from fossil-dominated regions (e.g., coal-heavy grids exceeding 700 gCO2/kWh) to renewable-rich regions (e.g., hydroelectric grids below 100 gCO2/kWh) reduces operational carbon by over 85%, yet frequently violates national data residency mandates or adds cross-region latency [8, 18]. Furthermore, existing commercial monitoring tools (e.g., Datadog, AWS Compute Optimizer) generate siloed, closed-box recommendations without reconciling cross-domain impacts."))
    s.append(p("When an autonomous agent alters cluster configuration without exposing its underlying trade-off rationale, Site Reliability Engineers (SREs) routinely disable automated execution out of concern for operational safety. Trustworthy cloud optimization requires three foundational pillars: (1) forward-looking telemetry forecasts that predict capacity requirements prior to saturation; (2) explainable multi-agent coordination with deterministic, auditable conflict resolution; and (3) a non-destructive Digital Twin simulation layer where proposed interventions can be rigorously modeled before execution [14]. GreenMind AI is designed and implemented to provide this comprehensive capability."))
    s.append(sp())
    s.append(p("<b>Principal Contributions:</b>", "body_bold"))
    s.append(p("1) <i>Modular End-to-End Architecture:</i> We present an open-source platform integrating telemetry ingestion, multi-metric Gradient Boosted Regression (GBR), multi-agent orchestration via LangGraph, deterministic conflict arbitration, Digital Twin simulation, and a tool-grounded AI copilot.", "en"))
    s.append(p("2) <i>Empirical Forecasting Verification:</i> We re-train and independently verify five 1-hour-ahead predictive models across 5,756 chronologically partitioned observations, achieving 25.4% to 45.4% MAE improvements over persistence.", "en"))
    s.append(p("3) <i>Discovery of Baseline Horizon Mismatch:</i> We expose a critical methodological anomaly in the stored rolling baseline, mathematically demonstrating that true multi-step rolling averages underperform persistence due to diurnal sinusoidal phase shift.", "en"))
    s.append(p("4) <i>Mathematical Formalization:</i> We formalize the multi-agent arbitration utility functions, digital twin state transition models, and 4-pillar optimization scoring mechanics.", "en"))
    s.append(p("5) <i>Rigorous Empirical Scoping:</i> We formalize the empirical boundaries of the platform, explicitly distinguishing synthetic benchmark accuracy from unvalidated production savings and documenting the HTTP 501 live-remediation boundary.", "en"))

    # ── II. RELATED WORK ─────────────────────────────────────────────────────
    s.append(p("II. RELATED WORK", "h1"))
    s.append(p("<i>Workload and Telemetry Forecasting:</i> Proactive cloud autoscaling relies heavily on time-series forecasting to overcome provisioning lags. Early frameworks utilized autoregressive integrated moving average (ARIMA) models [7], which perform well on stationary processes but fail to capture non-linear diurnal shifts and multi-metric interactions. Deep sequence models, including LSTMs, GRUs, and Temporal Fusion Transformers, have been widely investigated [3, 16]. However, Rossi et al. [3] benchmarked deep sequence models across production cluster traces (Google Borg, Alibaba), revealing that heavy computational overhead, susceptibility to overfitting on non-stationary shifts, and poor out-of-distribution transfer undermine real-world deployment. In contrast, Friedman's Gradient Boosting Machine (GBM) [1] provides optimal performance for tabular, lag-engineered telemetry, combining high non-linear expressiveness with rapid training and interpretable feature splits."))
    s.append(p("<i>Carbon-Aware Computing:</i> Quantifying and minimizing data center carbon emissions has matured from theoretical modeling to production infrastructure. Henderson et al. [4] and Lannelongue et al. [5] established rigorous accounting methodologies for algorithmic carbon footprints. Radovanovic et al. [6] operationalized carbon-aware batch scheduling at Google, demonstrating that shifting delay-tolerant computations across time and space tracks renewable generation peaks. Dodge et al. [8] showed that operational carbon intensity varies by up to 10x depending on geographic region and execution schedule. Akoush et al. [19] introduced 'free lunch' architectures utilizing intermittent renewables. GreenMind AI builds directly upon these paradigms by embedding regional grid emission curves into multi-agent optimization."))
    s.append(p("<i>Multi-Agent Systems &amp; Autonomous Cloud Management:</i> Multi-agent reinforcement learning (MARL) has been explored for cloud resource allocation [13, 17]. However, MARL agents frequently suffer from policy instability, non-stationarity, and uninterpretable action spaces that violate enterprise safety mandates. GreenMind AI deliberately eschews black-box reinforcement learning in favor of a LangGraph StateGraph coupled with deterministic priority arbitration, guaranteeing predictable, auditable decision paths."))
    s.append(p("<i>Digital Twin Simulation in Infrastructure Engineering:</i> Digital twins provide high-fidelity, non-destructive sandboxes for systems engineering [14]. In cloud computing, simulating counterfactual resource topologies allows operators to quantify the impact of rightsizing, consolidation, and geographic migration without incurring downtime or financial penalties. GreenMind AI implements a dedicated digital twin simulation engine that outputs formal before/after state snapshots and composite efficiency scores."))

    # ── III. SYSTEM ARCHITECTURE AND IMPLEMENTATION ──────────────────────────
    s.append(p("III. SYSTEM ARCHITECTURE AND IMPLEMENTATION", "h1"))
    s.append(p("GreenMind AI is implemented as a modular microservices platform comprising an asynchronous Python FastAPI (Python 3.12) backend, a React/TypeScript administrative dashboard, and SQLite/PostgreSQL telemetry persistence."))
    
    if ARCH_IMG.exists():
        cw = 240 # points
        s.append(Image(str(ARCH_IMG), width=cw, height=cw*0.37))
        s.append(p("Fig. 1. GreenMind AI end-to-end architecture: Telemetry ingestion -> GBR forecasting -> LangGraph multi-agent analysis -> deterministic arbitration -> Digital Twin simulation -> Explainable Copilot.", "cap"))

    s.append(p("A. Telemetry Ingestion and Multi-Cloud Abstraction Layer", "h2"))
    s.append(p("The ingestion pipeline processes 15-minute telemetry intervals encompassing five operational dimensions: CPU utilization (%), memory saturation (%), network ingress/egress (Mbps), hourly cost (USD/h), and carbon footprint proxy (gCO2/15-min). Multi-cloud connector classes interface with AWS CloudWatch (via boto3), Azure Monitor (via REST), and Google Cloud Monitoring (v3 API). In environments lacking active cloud credentials, connectors gracefully fall back to deterministic synthetic generators to guarantee system testability."))

    s.append(p("B. Multi-Metric Gradient-Boosted Forecaster", "h2"))
    s.append(p("Forecasting is powered by five independent GradientBoostingRegressor models trained to predict system state 1 hour ahead (4 steps of 15 minutes). For a sequence of observations {(x_i, y_i)}_{i=1}^N, the model constructs an additive ensemble:"))
    s.append(p("F_M(x) = F_0(x) + sum_{m=1}^M gamma_m h_m(x)", "h3"))
    s.append(p("where h_m(x) are regression trees fit to pseudo-residuals r_{im} = -[d L(y_i, F(x_i)) / d F(x_i)]_{F=F_{m-1}} under mean squared error loss. Hyperparameters were tuned to 150 estimators, maximum tree depth 3, learning rate 0.08, and friedman_mse split criterion. Feature vectors incorporate autoregressive lags (y_t), cyclical time encodings (hour of day, day of week), and 1-hour backward rolling statistics (mean mu_{t,4} and standard deviation sigma_{t,4}):"))
    s.append(p("mu_{t,4} = (1/4) * sum_{k=0}^3 y_{t-k},   sigma_{t,4} = sqrt((1/4) * sum_{k=0}^3 (y_{t-k} - mu_{t,4})^2)", "h3"))
    s.append(p("An anomaly detection subsystem flags telemetry exceeding 2.5 rolling z-score standard deviations: |y_t - mu_{rolling}| / sigma_{rolling} > 2.5."))

    s.append(p("C. Multi-Agent Orchestration via LangGraph StateGraph", "h2"))
    s.append(p("To prevent uncoordinated recommendations, GreenMind AI decomposes optimization into five specialized agents organized within a LangGraph StateGraph. The orchestrator state is defined as a tuple S = <M_t, C_t, R_t, A_t>, where M_t represents telemetry, C_t context, R_t domain recommendations, and A_t arbitration decisions. Each agent evaluates state independently:"))
    s.append(p("• <b>CostAgent:</b> Scans for over-provisioned compute, evaluates Spot/Reserved Instance feasibility, and targets underutilized idle resources.", "en"))
    s.append(p("• <b>PerformanceAgent:</b> Monitors CPU/memory headroom, detects saturation anomalies, and generates horizontal/vertical scaling proposals.", "en"))
    s.append(p("• <b>SustainabilityAgent:</b> Correlates regional grid carbon intensity with workload execution, identifying green temporal windows (01:00-06:00 UTC).", "en"))
    s.append(p("• <b>SecurityAgent:</b> Audits public security groups, open sensitive ports, unencrypted storage volumes, and IAM least-privilege compliance.", "en"))
    s.append(p("• <b>ReliabilityAgent:</b> Enforces multi-AZ redundancy, backup recovery point objectives (RPO), and health check tolerances.", "en"))
    s.append(p("If LangGraph dependencies are uninstalled, an execution fallback runs agents sequentially with unique ID deduplication to maintain high availability."))

    s.append(p("D. Deterministic Conflict Resolution Engine", "h2"))
    s.append(p("When domain agents produce opposing recommendations, an explicit arbitration engine executes three deterministic rules:"))
    s.append(p("1) <i>Performance vs. Cost Rule:</i> If PerformanceAgent requests scale-up but CostAgent identifies underutilization within a moderate band (35% <= CPU < 75%), the system issues a combined rightsizing and predictive autoscaling action with a 60-second cooldown buffer (confidence 0.88).", "en"))
    s.append(p("2) <i>Reliability vs. Cost Rule:</i> When CPU < 35% but high availability is mandatory, downscaling is approved only alongside automated multi-AZ failover configuration (confidence 0.92).", "en"))
    s.append(p("3) <i>Carbon vs. Execution Rule:</i> Non-critical batch jobs flagged by SustainabilityAgent are deferred to low-carbon grid intervals (confidence 0.87).", "en"))
    s.append(p("Every resolution emits an auditable trace capturing competing proposals, arbitration rule IDs, and confidence scores."))

    s.append(p("E. Non-Destructive Digital Twin Simulation Layer", "h2"))
    s.append(p("Before changes touch infrastructure, the Digital Twin engine simulates counterfactual infrastructure states S_{after} = f_{scenario}(S_{before}, Theta) across five core scenarios: Right-Size, Scale-Down, Scale-Up, Workload Consolidation, and Region Migration. The engine computes before/after state snapshots and recalculates a unified Optimization Score (0-100):"))
    s.append(p("Score = 0.30 S_cost + 0.25 S_perf + 0.25 S_sust + 0.20 S_rel", "h3"))
    s.append(p("Every simulated response is strictly tagged with is_simulated=True and label='SIMULATED / ESTIMATED' to prevent operator confusion."))

    s.append(p("F. Explainable AI Copilot and Operational Safety Boundary", "h2"))
    s.append(p("An AI Copilot provides interactive natural-language explanations grounded in eight system tools: get_cloud_metrics, get_history, get_predictions, get_cost_analysis, get_carbon_analysis, get_recommendations, get_cloud_health, and run_digital_twin_simulation. Crucially, a strict architectural safety boundary is enforced: live remediation mutation endpoints (/api/remediation/apply) and rollback endpoints are hard-coded to return HTTP 501 Not Implemented, guaranteeing that the platform operates strictly in decision-support mode."))

    # ── IV. EXPERIMENTAL METHODOLOGY AND SETUP ──────────────────────────────
    s.append(p("IV. EXPERIMENTAL METHODOLOGY AND EMPIRICAL SETUP", "h1"))
    s.append(p("A. Synthetic Telemetry Generator Dynamics", "h2"))
    s.append(p("To ensure reproducible benchmarking, generate_dataset.py generates 5,760 observations at 15-minute intervals (60 simulated days starting 2026-06-01, seed 42). The generator equations formalize diurnal, weekly, and stochastic cloud dynamics:"))
    s.append(p("• <i>CPU (%):</i> y_cpu(t) = clip(35 + 30*sin^2((h_t-7)/24*2*pi)*W_t + tau_t + epsilon_t, 2, 98), where W_t=0.7 on weekends, tau_t in [0, 5]% linear drift, epsilon_t ~ N(0, 16).", "en"))
    s.append(p("• <i>Memory (%):</i> y_mem(t) = clip(40 + 20*sin^2((h_t-8)/24*2*pi) + cumsum(N(0, 0.04)) + epsilon_t, 5, 95), modeling long-term process leak drift.", "en"))
    s.append(p("• <i>Network (Mbps):</i> y_net(t) = clip(300 + 400*sin^2((h_t-9)/24*2*pi)*W_t + epsilon_t, 10, 1000), epsilon_t ~ N(0, 2500).", "en"))
    s.append(p("• <i>Cost (USD/h):</i> Modeled as an AWS m5.xlarge baseline ($0.192/h) modulated by CPU load: y_cost(t) = 0.192*(1 + y_cpu(t)/100*0.5) + N(0, 1e-4).", "en"))
    s.append(p("• <i>Carbon (gCO2/15-min):</i> y_carb(t) = clip(I_reg(h_t)*P_srv*Delta_t + N(0, 25), 0, 500), with server power P_srv=0.35 kW, Delta_t=0.25 h, and regional grid carbon intensity I_reg(h_t) parameterized from 24-hour empirical diurnal curves across 5 regions (us-east: 320-470, eu-west: 180-290, ca-central: 79-120, in-north: 635-740, ap-southeast: 460-565 gCO2/kWh).", "en"))

    s.append(p("B. Chronological Partitioning and Holdout Discipline", "h2"))
    s.append(p("Targets are shifted by Delta=4 steps (1-hour forward horizon). Trailing NaN rows are dropped, yielding 5,756 aligned records. Following Bergmeir et al. [2], data is partitioned chronologically into an 80% training set (N_train=4,604; days 1-48) and a 20% test set (N_test=1,152; days 49-60). Random k-fold cross-validation is strictly avoided to prevent serial auto-correlation leakage."))

    s.append(p("C. Evaluation Metrics and Baseline Formulations", "h2"))
    s.append(p("Performance is measured via Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Coefficient of Determination (R2). Relative improvement is defined as Gain(%) = 100*(1 - MAE_model / MAE_baseline). Three baselines are benchmarked: (1) 1-Hour Persistence (y-hat_{t+4} = y_t); (2) Stored Rolling Baseline (evaluating mu_{t,4} on unshifted test data); and (3) True Rolling Baseline from forecast origin (y-hat_{t+4} = mu_{t,4})."))

    # ── V. EXPERIMENTAL RESULTS AND TECHNICAL VERIFICATION ───────────────────
    s.append(p("V. EXPERIMENTAL RESULTS AND TECHNICAL VERIFICATION", "h1"))
    s.append(p("A. Forecasting Performance Across Telemetry Targets", "h2"))
    s.append(p("Re-running train.py independently verified all model artifacts. Table I presents the test set metrics across all five models. Gradient boosting consistently outperforms the 1-hour persistence baseline across all dimensions, with relative MAE reductions ranging from 25.4% (memory) to 45.4% (network)."))
    
    s.append(p("<b>TABLE I.</b> Empirical Forecasting Metrics on Chronological Test Set (N=1,152). True Roll-4 reflects 1-hour origin projection; Stored Roll-4 reflects 1-step lookahead.", "cap"))
    s.append(make_table_results(st))
    s.append(sp(2))

    s.append(p("B. Baseline Horizon Alignment Discovery &amp; Mathematical Proof", "h2"))
    s.append(p("A major contribution of our technical audit is resolving a baseline alignment discrepancy. In the original repository, baseline.py computed rolling MAE on unshifted test series, effectively evaluating a 15-minute prediction (mu_{t,4} -> y_{t+1}) rather than the true 1-hour horizon (y_{t+4}). When the 4-step rolling mean is correctly evaluated as a 1-hour forecast origin predictor, its MAE degrades significantly (CPU: 7.263% vs. 6.500% for persistence; network: 90.816 vs. 80.346 Mbps)."))
    s.append(p("We formalize this mathematically. Let the diurnal signal be approximated by y(t) = A sin(omega t) + C, where omega = 2*pi / 24 rad/h. The true 1-hour ahead value is y(t+1) = A sin(omega(t+1)) + C. The point persistence forecast is y-hat_{persist} = y(t), incurring phase error Delta theta_{persist} = omega * 1 = pi/12 rad (~15 deg). The 4-step moving average over [t-0.75, t] has an effective centroid at t - 0.375 h, yielding mu_{t,4} approx A sin(omega(t - 0.375)) + C. When projected 1 hour forward, the total phase lag becomes Delta theta_{roll} = omega * (1 + 0.375) = 1.375 * (pi/12) approx 20.6 deg. During steep diurnal ascent (07:00-11:00 UTC), |sin(Delta theta_{roll})| > |sin(Delta theta_{persist})|, proving analytically why the rolling mean underperforms point persistence."))

    if EVAL_IMG.exists():
        cw = 240
        s.append(Image(str(EVAL_IMG), width=cw, height=cw*0.38))
        s.append(p("Fig. 2. Empirical verification: (a) Predictive accuracy gain over persistence; (b) Baseline alignment audit showing phase-lag degradation in true 4-step rolling baseline.", "cap"))

    s.append(p("C. Feature Attribution Dynamics", "h2"))
    s.append(p("Table II details feature importances extracted via tree split gain. Across all models, the instantaneous target lag y_t and hour_of_day dominate predictive decisions, accounting for over 85% of total feature importance."))
    s.append(p("<b>TABLE II.</b> Feature Importance Attribution Across 5 GBR Models.", "cap"))
    s.append(make_table_features(st))
    s.append(sp(2))

    s.append(p("D. Digital Twin Counterfactual Simulation Analysis", "h2"))
    s.append(p("Table III summarizes the impact of five simulated optimization scenarios evaluated against an enterprise baseline of 4 instances (monthly cost: $864.00, monthly carbon: 108.0 kg CO2). Region migration from high-carbon in-north (650 gCO2/kWh) to hydro-rich ca-central (90 gCO2/kWh) achieves an 86.7% operational carbon abatement without financial penalty, lifting the platform Optimization Score by +22 points."))
    s.append(p("<b>TABLE III.</b> Digital Twin Scenario Simulation Projections (Baseline: 4 Instances, $864/mo, 108 kg CO2/mo, Optimization Score 65/100).", "cap"))
    s.append(make_table_scenarios(st))

    # ── VI. DISCUSSION, LIMITATIONS, AND THREATS TO VALIDITY ─────────────────
    s.append(p("VI. DISCUSSION AND THREATS TO VALIDITY", "h1"))
    s.append(p("A. Synthetic Trace Fidelity vs. Real-World Dynamics", "h2"))
    s.append(p("The high coefficients of determination (R2=0.855 for CPU, R2=0.871 for network) reflect the ability of gradient-boosted decision trees to approximate smooth sinusoidal generator functions. In production cloud environments, workload traces from Google Borg, Alibaba, or Azure Functions exhibit bursty traffic, abrupt job preemptions, long-tailed memory spikes, and non-stationary regime shifts [3, 15, 16]. Consequently, synthetic benchmark metrics establish algorithmic convergence under ideal cyclical conditions, not guaranteed real-world accuracy."))

    s.append(p("B. Multi-Step Autoregressive Feedback and Scale Mismatch", "h2"))
    s.append(p("Our audit revealed an implementation inconsistency in backend/app/ml/predictor.py within forecast_multi_step(). The function executes recursive multi-step forecasting with 5-minute step increments using models trained on direct 1-hour targets. Furthermore, the feedback loop feeds predicted carbon output (~30-40 gCO2/15-min) into an input feature expecting grid carbon intensity (~320-470 gCO2/kWh), introducing an order-of-magnitude scale mismatch. In production, this must be refactored into direct multi-horizon models (t+1, ..., t+H) with explicit unit checking."))

    s.append(p("C. Cloud Connector Emulation and Sandboxing", "h2"))
    s.append(p("Cloud provider connectors (AWS, Azure, GCP) currently fall back to synthetic data generators when run in test harnesses. While schema parsing is verified, live API authentication, IAM rate limits, and network jitter have not been tested against production cloud subscriptions. The HTTP 501 boundary ensures safety but confirms that closed-loop automated execution remains unvalidated."))

    s.append(p("D. Threats to Validity Taxonomy", "h2"))
    s.append(p("• <i>Internal Validity:</i> Potential feature leakage was eliminated via strict chronological holdout partitioning. However, the recursive feedback in forecast_multi_step introduces drift that is absent in single-step evaluation.", "en"))
    s.append(p("• <i>External Validity:</i> Results are conditioned on synthetic generator parameters (seed 42, 60 days, us-east). Generalization across heterogeneous hardware architectures (e.g. ARM Graviton vs x86) remains unmeasured.", "en"))
    s.append(p("• <i>Construct Validity:</i> The carbon calculation models static server draw (350 W) and regional grid averages. It omits dynamic power scaling, Power Usage Effectiveness (PUE) fluctuations, and Scope 3 embodied hardware emissions [5, 8].", "en"))
    s.append(p("• <i>Conclusion Validity:</i> Point forecast accuracy does not automatically translate to operational cost reductions. In live environments, cloud billing quantization (e.g. hourly commitments, minimum instance billing increments) modulates actual realized dollar savings.", "en"))

    # ── VII. CONCLUSION AND FUTURE ROADMAP ───────────────────────────────────
    s.append(p("VII. CONCLUSION AND FUTURE WORK", "h1"))
    s.append(p("GreenMind AI provides a coherent, audited architecture unifying machine learning forecasting, multi-agent domain analysis, deterministic conflict arbitration, non-destructive simulation, and an explainable AI copilot. Evaluated on a 60-day synthetic benchmark, gradient boosted models reduce MAE by 25.4% to 45.4% over persistence. Our audit exposed critical baseline horizon alignment effects and established transparent empirical boundaries."))
    s.append(p("Future work will focus on: (1) benchmarking models on public cluster traces (Alibaba 2020, Google Borg); (2) integrating live grid APIs (Electricity Maps, WattTime) for dynamic marginal emissions; (3) refactoring recursive forecasting into direct multi-horizon estimators; and (4) deploying an isolated canary cloud environment to validate actual billing and carbon reductions."))

    s.append(sp())
    s.append(p("ACKNOWLEDGMENT", "h1"))
    s.append(p("The author thanks the open-source cloud computing and GreenOps research communities for open datasets, benchmarks, and architectural feedback that informed this work.", "body"))

    # ── REFERENCES ───────────────────────────────────────────────────────────
    s.append(HRFlowable(width="100%", thickness=0.4, color=BORDER_COLOR, spaceBefore=2.0, spaceAfter=1.8))
    s.append(p("REFERENCES", "h1"))
    refs = [
        "[1] J. H. Friedman, \"Greedy function approximation: A gradient boosting machine,\" Ann. Statist., vol. 29, no. 5, pp. 1189-1232, 2001.",
        "[2] C. Bergmeir, R. J. Hyndman, and B. Koo, \"A note on the validity of cross-validation for evaluating autoregressive time series prediction,\" Comput. Stat. Data Anal., vol. 120, pp. 70-83, 2018.",
        "[3] A. Rossi, A. Visentin, D. Carraro, S. Prestwich, and K. N. Brown, \"Forecasting workload in cloud computing: Towards uncertainty-aware predictions and transfer learning,\" Cluster Comput., vol. 28, art. 258, 2025.",
        "[4] P. Henderson, J. Hu, J. Romoff, E. Brunskill, D. Jurafsky, and J. Pineau, \"Towards the systematic reporting of the energy and carbon footprints of machine learning,\" J. Mach. Learn. Res., vol. 21, no. 248, pp. 1-43, 2020.",
        "[5] L. Lannelongue, J. Grealey, and M. Inouye, \"Green algorithms: Quantifying the carbon footprint of computation,\" Adv. Sci., vol. 8, no. 12, art. 2100707, 2021.",
        "[6] A. Radovanovic et al., \"Carbon-aware computing for datacenters,\" IEEE Trans. Power Syst., vol. 38, no. 2, pp. 1270-1280, 2023.",
        "[7] R. N. Calheiros, E. Masoumi, R. Ranjan, and R. Buyya, \"Workload prediction using ARIMA model and its impact on cloud applications QoS,\" IEEE Trans. Cloud Comput., vol. 3, no. 4, pp. 449-458, 2015.",
        "[8] J. Dodge et al., \"Measuring the carbon intensity of AI in cloud instances,\" in Proc. ACM Conf. Fairness Accountability Transparency (FAccT), 2022, pp. 1536-1546.",
        "[9] U. Hoelzle, \"Data centers are more energy efficient than ever, but our work is not done,\" Google Cloud Blog, 2021.",
        "[10] A. Shehabi et al., \"United States data center energy usage report,\" Lawrence Berkeley National Laboratory, Tech. Rep. LBNL-1005775, 2016.",
        "[11] M. Armbrust et al., \"A view of cloud computing,\" Commun. ACM, vol. 53, no. 4, pp. 50-58, 2010.",
        "[12] J. Dean and L. A. Barroso, \"The tail at scale,\" Commun. ACM, vol. 56, no. 2, pp. 74-80, 2013.",
        "[13] Z. Song et al., \"Energy-efficient workload consolidation in cloud datacenters,\" IEEE Trans. Parallel Distrib. Syst., vol. 32, no. 8, pp. 1952-1965, 2021.",
        "[14] M. Dayarathna, Y. Wen, and R. Fan, \"Data center energy consumption modeling: A survey,\" IEEE Commun. Surveys Tuts., vol. 18, no. 1, pp. 732-794, 2016.",
        "[15] C. Reiss, A. Tumanov, G. R. Ganger, R. H. Katz, and M. A. Kozuch, \"Heterogeneity and dynamicity of clouds at scale: Google trace analysis,\" in Proc. ACM SoCC, 2012, pp. 1-13.",
        "[16] W. Lu et al., \"Large-scale cluster trace analysis for deep learning workloads,\" in Proc. USENIX ATC, 2020, pp. 751-764.",
        "[17] S. Ilager, M. Muralidhar, and R. Buyya, \"Artificial intelligence for datacenter thermal management: A survey,\" ACM Comput. Surv., vol. 54, no. 7, pp. 1-38, 2021.",
        "[18] F. Hao, M. Kodialam, and T. V. Lakshman, \"Optimizing energy costs for geo-distributed cloud applications,\" IEEE/ACM Trans. Netw., vol. 25, no. 2, pp. 747-758, 2017.",
        "[19] S. Akoush et al., \"Free lunch: Harnessing renewable energy for computing,\" in Proc. HotOS, 2011, pp. 1-6.",
        "[20] Pratham Patel, \"GreenMind-AI: Explainable Multi-Agent Framework for Sustainable Cloud Optimization,\" GitHub, 2026. [Online]. Available: https://github.com/Pratham-stack-coder/GreenMind-AI.",
        "[21] D. G. Feitelson, \"Workload Modeling for Computer Systems Performance Evaluation,\" Cambridge University Press, 2015.",
        "[22] Y. Mansouri, A. N. Toosi, and R. Buyya, \"Brokering algorithms for optimizing the availability and cost of cloud storage services,\" IEEE Trans. Parallel Distrib. Syst., vol. 28, no. 10, pp. 2883-2895, 2017.",
        "[23] T. Chen and C. Guestrin, \"XGBoost: A scalable tree boosting system,\" in Proc. ACM SIGKDD, 2016, pp. 785-794.",
        "[24] G. Ke et al., \"LightGBM: A highly efficient gradient boosting decision tree,\" in Proc. NeurIPS, 2017, pp. 3146-3154.",
        "[25] S. M. Lundberg and S.-I. Lee, \"A unified approach to interpreting model predictions,\" in Proc. NeurIPS, 2017, pp. 4765-4774."
    ]
    for r in refs:
        s.append(p(r, "ref"))

    return s

def compile_pdf(font_size=7.6, leading=9.2, spacer_scale=1.0, title_h=105, margin_in=0.65):
    PAGE_W, PAGE_H = letter # 612 x 792
    M = margin_in * inch # 46.8 pt margin
    G = 0.22 * inch # 15.84 pt gap
    CW = (PAGE_W - 2*M - G) / 2 # ~241.5 pt

    styles = build_styles(base_font_size=font_size, base_leading=leading)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Times-Roman", 7.0)
        canvas.setFillColor(MUTED_GRAY)
        canvas.drawCentredString(
            PAGE_W / 2.0, 0.35 * inch,
            f"GreenMind AI — IEEE Conference on Cloud Computing and GreenOps — Page {doc.page} of 5"
        )
        canvas.restoreState()

    # Layout frames
    tf = Frame(M, PAGE_H - M - title_h, PAGE_W - 2*M, title_h, id="title_frame",
               leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    
    b1_h = PAGE_H - 2*M - title_h - 10
    lf1 = Frame(M, M + 15, CW, b1_h, id="left_col_p1",
                leftPadding=0, rightPadding=0, topPadding=4, bottomPadding=0)
    rf1 = Frame(M + CW + G, M + 15, CW, b1_h, id="right_col_p1",
                leftPadding=0, rightPadding=0, topPadding=4, bottomPadding=0)

    # Subsequent pages: full height two columns
    b_rest_h = PAGE_H - 2*M - 15
    lf_rest = Frame(M, M + 15, CW, b_rest_h, id="left_col_rest",
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    rf_rest = Frame(M + CW + G, M + 15, CW, b_rest_h, id="right_col_rest",
                    leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    p1 = PageTemplate(id="first_page", frames=[tf, lf1, rf1], onPageEnd=footer)
    pn = PageTemplate(id="rest_pages", frames=[lf_rest, rf_rest], onPageEnd=footer)

    out_path = HERE / "GreenMind_AI_IEEE_5_Page.pdf"
    doc = BaseDocTemplate(
        str(out_path),
        pagesize=letter,
        leftMargin=M,
        rightMargin=M,
        topMargin=M,
        bottomMargin=M
    )
    doc.addPageTemplates([p1, pn])
    
    story = generate_story(styles, spacer_scale=spacer_scale)
    doc.build(story)
    
    pdf = pdfium.PdfDocument(str(out_path))
    num_pages = len(pdf)
    return num_pages, out_path

def main():
    print("Calibrating IEEE 5-page PDF with expanded mathematical text and 25 references...")
    # Search for parameters yielding EXACTLY 5 pages
    found = False
    for ld in [9.2, 9.4, 9.6, 9.8, 10.0, 10.2, 10.4, 10.6]:
        for fs in [7.4, 7.6, 7.8, 8.0]:
            try:
                pages, out_path = compile_pdf(font_size=fs, leading=ld, spacer_scale=1.0, title_h=105, margin_in=0.65)
                print(f"  fs={fs}, ld={ld}: {pages} pages")
                if pages == 5:
                    print(f"SUCCESS! Exactly 5 pages achieved with fs={fs}, ld={ld}!")
                    found = True
                    break
            except Exception as e:
                pass
        if found:
            break

    if not found:
        print("Tuning margin and leading...")
        for m in [0.62, 0.65, 0.68, 0.70]:
            for ld in [9.0, 9.3, 9.6, 9.9, 10.2]:
                pages, out_path = compile_pdf(font_size=7.6, leading=ld, spacer_scale=1.0, title_h=105, margin_in=m)
                print(f"  margin={m}, ld={ld}: {pages} pages")
                if pages == 5:
                    print(f"SUCCESS! Exactly 5 pages achieved with margin={m}, ld={ld}!")
                    found = True
                    break
            if found:
                break

    pdf = pdfium.PdfDocument(str(HERE / "GreenMind_AI_IEEE_5_Page.pdf"))
    print(f"Final verified IEEE PDF page count: {len(pdf)} pages")

if __name__ == "__main__":
    main()
