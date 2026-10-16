"""
Generates the IEEE-style GreenMind AI research paper in DOCX format.
Follows IEEE Transactions / Conference formatting:
- 8.5 x 11 inch paper, 0.64 in side margins, 0.55 in top/bottom margins
- Section 1: Title and Author banner (1 column)
- Section 2: 2-column body (w:cols num="2", space="420")
- Embedded Figure 1 (Architecture diagram)
- Formatted Table I with verified metrics
- Formatted IEEE headings and references
"""

from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

def set_cell_borders(cell, top=None, bottom=None, left=None, right=None):
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = parse_xml(f'<w:tcBorders {nsdecls("w")}>\n'
                          f'  <w:top w:val="{top or "none"}" w:sz="4" w:space="0" w:color="000000"/>\n'
                          f'  <w:left w:val="{left or "none"}" w:sz="4" w:space="0" w:color="000000"/>\n'
                          f'  <w:bottom w:val="{bottom or "none"}" w:sz="4" w:space="0" w:color="000000"/>\n'
                          f'  <w:right w:val="{right or "none"}" w:sz="4" w:space="0" w:color="000000"/>\n'
                          f'</w:tcBorders>')
    tcPr.append(tcBorders)

def build_docx():
    doc = docx.Document()
    
    # Base page settings
    sec0 = doc.sections[0]
    sec0.page_width = Inches(8.5)
    sec0.page_height = Inches(11.0)
    sec0.left_margin = Inches(0.65)
    sec0.right_margin = Inches(0.65)
    sec0.top_margin = Inches(0.60)
    sec0.bottom_margin = Inches(0.60)
    
    # Styles setup
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(9.5)
    font.color.rgb = RGBColor(0, 0, 0)
    
    # --- Title Banner (Section 0: 1 Column) ---
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run("GreenMind AI: A Multi-Metric Forecasting and Decision-Support Platform for Cloud GreenOps")
    run_title.font.name = 'Times New Roman'
    run_title.font.size = Pt(17)
    run_title.bold = True

    p_author = doc.add_paragraph()
    p_author.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_author.paragraph_format.space_before = Pt(0)
    p_author.paragraph_format.space_after = Pt(12)
    run_author = p_author.add_run("Anonymous submission draft")
    run_author.font.name = 'Times New Roman'
    run_author.font.size = Pt(10.5)
    run_author.italic = True

    # --- Section 1: 2-Column Body ---
    sec1 = doc.add_section(docx.enum.section.WD_SECTION.CONTINUOUS)
    sec1.page_width = Inches(8.5)
    sec1.page_height = Inches(11.0)
    sec1.left_margin = Inches(0.65)
    sec1.right_margin = Inches(0.65)
    sec1.top_margin = Inches(0.60)
    sec1.bottom_margin = Inches(0.60)
    
    # Set 2 columns in sec1
    sectPr = sec1._sectPr
    cols = sectPr.xpath('./w:cols')
    if cols:
        sectPr.remove(cols[0])
    cols_xml = parse_xml(f'<w:cols {nsdecls("w")} w:num="2" w:space="360" w:sep="0"/>')
    sectPr.append(cols_xml)

    def add_sec_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(9)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(title)
        r.bold = True
        r.font.size = Pt(9.5)
        return p

    def add_subsec_heading(title):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(title)
        r.italic = True
        r.bold = True
        r.font.size = Pt(9.0)
        return p

    def add_body_p(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.05
        r = p.add_run(text)
        r.font.size = Pt(9.0)
        return p

    # --- Abstract & Keywords ---
    p_abs = doc.add_paragraph()
    p_abs.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_abs.paragraph_format.space_before = Pt(0)
    p_abs.paragraph_format.space_after = Pt(4)
    p_abs.paragraph_format.line_spacing = 1.05
    r_abs_label = p_abs.add_run("Abstract—")
    r_abs_label.bold = True
    r_abs_label.font.size = Pt(8.5)
    r_abs_text = p_abs.add_run(
        "Modern cloud operations require optimizing resource utilization, infrastructure cost, and environmental footprint simultaneously, "
        "yet predictive telemetry alone does not establish operational savings. This paper presents a comprehensive technical audit and architectural "
        "analysis of GreenMind AI, an open-source decision-support prototype for cloud GreenOps. The platform combines five one-hour-ahead machine learning "
        "forecasters with a five-domain multi-agent analysis engine (Cost, Performance, Sustainability, Security, and Reliability), transparent conflict arbitration, "
        "a non-destructive Digital Twin simulator, and an eight-tool explainable copilot. We evaluate the forecasting pipeline using the project's deterministic "
        "60-day, 15-minute multi-metric synthetic dataset (5,756 chronological records) across a strict 80/20 train/test holdout (4,604 train and 1,152 test samples). "
        "GradientBoostingRegressor models achieve mean absolute error (MAE) improvements over a one-hour forecast-origin persistence baseline ranging from 25.4% to 45.4% "
        "across all five targets: CPU (3.809% vs. 6.500%), memory (2.979% vs. 3.996%), network (43.876 vs. 80.346 Mbps), cost ($0.009 vs. $0.013/h), and a synthetic carbon "
        "proxy (4.061 vs. 5.846 gCO2/15-min). Our audit reveals that the stored rolling-mean baseline in the repository evaluates a one-step-ahead (15-minute) prediction on "
        "unshifted test data rather than a true four-step-ahead forecast from origin, which actually yields higher error (e.g., 7.263% for CPU). Furthermore, we establish the "
        "boundaries of the system: the evaluations are derived from synthetic generator equations, cloud connector live behaviors are unverified end-to-end, and direct cloud "
        "remediation is strictly rejected at the API boundary with HTTP 501 (dry-run previews only). GreenMind AI provides an integrated software architecture for proactive "
        "cloud analysis, but synthetic accuracy must not be conflated with validated production cost or emission reductions."
    )
    r_abs_text.font.size = Pt(8.5)

    p_kw = doc.add_paragraph()
    p_kw.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p_kw.paragraph_format.space_before = Pt(2)
    p_kw.paragraph_format.space_after = Pt(6)
    r_kw_label = p_kw.add_run("Index Terms—")
    r_kw_label.bold = True
    r_kw_label.font.size = Pt(8.5)
    r_kw_text = p_kw.add_run("Cloud computing, workload forecasting, gradient boosting, carbon-aware computing, synthetic telemetry, multi-agent systems, digital twin, decision support.")
    r_kw_text.font.size = Pt(8.5)

    # --- Section I: Introduction ---
    add_sec_heading("I. INTRODUCTION")
    add_body_p(
        "Cloud data centers consume substantial global electrical energy, driving both cloud providers and tenants toward carbon-aware computing "
        "and FinOps/GreenOps operational practices [4], [6]. Modern cloud management platforms expose multifaceted observability signals, spanning "
        "CPU and memory utilization, network bandwidth, hourly billing meters, and regional grid carbon-intensity feeds. Proactive workload forecasting can "
        "assist orchestrators in identifying resource bottlenecks, scheduling deferrable batch tasks, and planning right-sizing actions prior to demand spikes. "
        "However, high predictive accuracy on historical data does not inherently translate into realized financial savings, carbon abatement, or preserved "
        "service-level objectives (SLOs) in production systems [3], [8]."
    )
    add_body_p(
        "In environmental accounting, estimating greenhouse gas emissions requires rigorous accounting boundaries, real-time power telemetry, facility "
        "Power Usage Effectiveness (PUE), and time-varying marginal emissions factors [4], [5]. Consequently, a synthetic or static proxy cannot be reported "
        "as an empirical Scope 2 carbon reduction without live meter verification. Similarly, automated remediation must balance conflicting operational trade-offs, "
        "such as performance headroom versus idle cost elimination."
    )
    add_body_p(
        "GreenMind AI is an open-source software prototype developed to bridge the gap between predictive telemetry and operational decision support. "
        "The repository integrates a multi-metric forecasting pipeline, a FastAPI service layer, a TypeScript/React management cockpit, five domain-oriented analysis "
        "agents (Cost, Performance, Sustainability, Security, Reliability) orchestrated via a state graph, a deterministic conflict resolver, an eight-tool explainable "
        "copilot, and a non-destructive Digital Twin simulator. Connector modules exist for Amazon Web Services (AWS), Microsoft Azure, and Google Cloud Platform (GCP)."
    )
    add_body_p(
        "This paper delivers an empirical and architectural audit of the GreenMind AI implementation. We delineate three specific contributions: "
        "(1) We detail the end-to-end software architecture linking multi-source telemetry ingestion, multi-metric gradient boosted forecasting, multi-agent arbitration, "
        "Digital Twin simulation, and decision-support copilot interfaces. (2) We reproduce and verify the held-out forecasting performance across all five targets, analyzing "
        "feature importances and resolving a subtle baseline alignment discrepancy where stored moving averages reflected one-step-ahead predictions rather than four-step horizons. "
        "(3) We explicitly demarcate the empirical evidence boundaries: demonstrating that reported gains stem from a deterministic synthetic generator, clarifying the carbon target "
        "definition, and documenting that live remediation is intentionally disabled via HTTP 501 to prevent unauthorized cloud mutations."
    )

    # --- Section II: Related Work ---
    add_sec_heading("II. RELATED WORK")
    add_body_p(
        "Workload and resource demand forecasting has evolved from classical statistical models to complex deep neural networks. Calheiros et al. [7] "
        "demonstrated proactive cloud provisioning using autoregressive integrated moving average (ARIMA) models, showing that proactive scaling reduces QoS violations "
        "compared to reactive policies. Machine learning ensemble methods, particularly Friedman's Gradient Boosting Machine (GBM) [1], construct additive tree models "
        "that excel on tabular and structured lag features without demanding the compute scale of deep architectures. Recently, Rossi et al. [3] investigated probabilistic "
        "LSTMs and Bayesian neural networks on Google and Alibaba cluster traces, highlighting that point forecasts fail to capture operational uncertainty and that transfer "
        "learning degrades across disparate cloud providers. GreenMind AI utilizes five lightweight GradientBoostingRegressor models; unlike [3], its evaluation is confined to synthetic series."
    )
    add_body_p(
        "Evaluating time-series forecasters requires careful handling of temporal dependencies. Bergmeir, Hyndman, and Koo [2] established that standard cross-validation can be "
        "theoretically valid for purely autoregressive models when errors are uncorrelated, but a single chronological holdout remains standard practice when simulating prospective "
        "deployment. GreenMind AI enforces an 80/20 chronological split to avoid forward-looking data leakage."
    )
    add_body_p(
        "In green computing, Henderson et al. [4] established systematic reporting standards for machine learning energy consumption and grid carbon footprints. Lannelongue, Grealey, "
        "and Inouye [5] formulated the Green Algorithms framework, formalizing carbon calculations across runtime, TDP, PUE, and grid intensity. For hyperscale infrastructure, "
        "Radovanovic et al. [6] deployed carbon-aware computing systems at Google datacenters using day-ahead predictions and Virtual Capacity Curves to temporally shift flexible workloads "
        "to cleaner grid hours. Dodge et al. [8] measured operational carbon intensity across cloud instances, demonstrating that spatial region selection and temporal scheduling significantly "
        "reduce Scope 2 emissions. GreenMind AI incorporates regional intensity curves modeled after these principles, but applies them to synthetic telemetry rather than hardware meter feeds."
    )

    # --- Section III: Platform Architecture ---
    add_sec_heading("III. PLATFORM IMPLEMENTATION AND ARCHITECTURE")
    add_body_p(
        "The GreenMind AI architecture comprises six interconnected components, structured to prevent unauthorized cloud mutations while providing explainable operational intelligence (Fig. 1)."
    )

    # Embed Figure 1
    fig_path = Path("research_paper/greenmind_architecture.png")
    if fig_path.exists():
        p_img = doc.add_paragraph()
        p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_img.paragraph_format.space_before = Pt(4)
        p_img.paragraph_format.space_after = Pt(2)
        doc.add_picture(str(fig_path), width=Inches(3.45))
        p_cap = doc.add_paragraph()
        p_cap.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cap.paragraph_format.space_before = Pt(0)
        p_cap.paragraph_format.space_after = Pt(6)
        r_cap = p_cap.add_run("Fig. 1. End-to-end GreenMind AI pipeline architecture: multi-source telemetry ingestion -> ML multi-metric forecasting -> specialized multi-agent analysis -> deterministic conflict resolution -> Digital Twin simulation -> operator decision support.")
        r_cap.font.size = Pt(8.0)
        r_cap.italic = True

    add_subsec_heading("A. Telemetry Ingestion and Service Layer")
    add_body_p(
        "The backend service is implemented in FastAPI (Python 3.12) with SQLite/PostgreSQL persistence. Telemetry connectors interface with AWS CloudWatch (via boto3), "
        "Azure Monitor REST APIs, and GCP Cloud Monitoring v3. When valid credentials are not configured, each provider falls back to a deterministic synthetic generator. "
        "The system ingests five continuous signals at 15-minute intervals: CPU utilization (%), memory load (%), network traffic (Mbps), hourly compute spend (USD/h), "
        "and estimated carbon emissions proxy (gCO2/15-min)."
    )

    add_subsec_heading("B. Multi-Metric Machine Learning Predictor")
    add_body_p(
        "Five independent GradientBoostingRegressor models are trained for one-hour-ahead (four-step) forecasting. Each model is configured with 150 estimators, maximum tree "
        "depth of 3, learning rate of 0.08, and fixed random seed 42. Input features are structured to avoid forward lookahead: CPU, memory, and network use lag values, hour, "
        "day of week, and backward-looking 1-hour rolling mean and standard deviation. Hourly cost uses CPU, memory, cost lag, hour, and day of week. The carbon model uses "
        "grid carbon intensity, hour, day of week, and CPU utilization. Predictions are clipped to physical limits, and an anomaly z-score threshold (z > 2.5) flags unexpected deviations."
    )

    add_subsec_heading("C. Multi-Agent Analysis and Conflict Resolution")
    add_body_p(
        "Decision intelligence is partitioned into five specialized agents executed as a LangGraph StateGraph: Cost (idle spend, right-sizing), Performance (headroom, saturation), "
        "Sustainability (grid intensity curves, green deferral windows), Security (IAM posture, TLS), and Reliability (multi-zone redundancy). Opposing recommendations are reconciled "
        "by a deterministic conflict resolution engine. For example, when Performance requests headroom while Cost flags idle spend, the engine approves right-sizing paired with predictive "
        "autoscaling, maintaining a 60-second scale-out buffer. Non-urgent batch workloads are deferred to green grid windows, while critical path APIs remain on immediate execution."
    )

    add_subsec_heading("D. Digital Twin Simulation and Safe Remediation Boundary")
    add_body_p(
        "To evaluate operational impact without infrastructure risk, the Digital Twin engine simulates candidate actions against state snapshots. Supported scenarios include right-sizing, "
        "scale-up, scale-down, node consolidation, and region migration. The simulator projects changes in cost, carbon, and a composite Optimization Score (0-100), explicitly labeling outputs "
        "as SIMULATED / ESTIMATED. The AI Copilot provides natural-language access through eight grounded tools. Crucially, live cloud remediation is strictly rejected at the API boundary "
        "via HTTP 501 Not Implemented (dry-run previews only), ensuring that no real provider resources are modified."
    )

    # --- Section IV: Experimental Method ---
    add_sec_heading("IV. EXPERIMENTAL METHODOLOGY")
    add_subsec_heading("A. Synthetic Telemetry Generation")
    add_body_p(
        "The synthetic generator creates 60 days of telemetry at 15-minute intervals starting June 1, 2026 (5,760 timestamps) using NumPy (seed 42). Metrics are generated from parameterized "
        "sinusoidal diurnal patterns, weekend dampening factors (0.7), linear trends, and Gaussian observation noise. Compute cost scales proportionally with CPU load based on an AWS m5.xlarge "
        "baseline ($0.192/h)."
    )

    add_subsec_heading("B. Carbon Target Formulation and Units")
    add_body_p(
        "The carbon target requires dimensional clarity. Regional carbon intensity is looked up from an hourly profile for the us-east grid (320 to 470 gCO2/kWh). An assumed server power draw "
        "of 0.35 kW is integrated over the 15-minute step (0.25 h), yielding an energy consumption of 0.0875 kWh. Multiplying intensity by energy and adding Gaussian noise yields the carbon target "
        "in grams of CO2 per 15-minute sample (gCO2/15-min). It represents a synthetic proxy, omitting dynamic server power states, fan curves, PUE variances, and embodied lifecycle emissions [5]."
    )

    add_subsec_heading("C. Chronological Split and Baselines")
    add_body_p(
        "A four-step forward shift aligns features with one-hour-ahead targets. Dropping the trailing four rows leaves 5,756 records. The dataset is split chronologically into 4,604 training samples "
        "(first 48 days) and 1,152 testing samples (final 12 days) without shuffling. Models are benchmarked against: (1) a forecast-origin persistence baseline (y_{t+4} = y_t), and (2) a four-sample "
        "moving average. Evaluated metrics include MAE, RMSE, R-squared, and relative percentage improvement over persistence."
    )

    # --- Section V: Results ---
    add_sec_heading("V. EXPERIMENTAL RESULTS")
    add_body_p(
        "Table I summarizes the held-out performance across all five targets. All metrics were reproduced identically from the saved model artifacts and audited via independent recomputation."
    )

    # Table I
    p_tcap = doc.add_paragraph()
    p_tcap.paragraph_format.space_before = Pt(6)
    p_tcap.paragraph_format.space_after = Pt(2)
    p_tcap.paragraph_format.keep_with_next = True
    r_tcap = p_tcap.add_run("TABLE I. SAVED HELD-OUT RESULTS ON THE SYNTHETIC DATASET (N=1,152). PERSISTENCE USES METRIC AT FORECAST ORIGIN; STORED ROLL4 IS THE REPOSITORY'S 1-STEP MOVING AVERAGE (N=1,148); TRUE ROLL4 EVALUATES ORIGIN AVERAGE PREDICTING 1H AHEAD.")
    r_tcap.font.size = Pt(7.5)
    r_tcap.bold = True

    table_data = [
        ["Target", "MAE", "RMSE", "R2", "Pers. MAE", "Stored Roll4", "True Roll4", "Gain (%)"],
        ["CPU (%)", "3.809", "4.811", "0.855", "6.500", "4.622", "7.263", "41.4%"],
        ["Memory (%)", "2.979", "3.704", "0.636", "3.996", "3.025", "4.153", "25.4%"],
        ["Network (Mbps)", "43.876", "55.328", "0.871", "80.346", "56.727", "90.816", "45.4%"],
        ["Cost (USD/h)", "0.009", "0.011", "0.474", "0.013", "0.010", "N/A", "29.7%"],
        ["Carbon (g/15m)", "4.061", "5.087", "0.391", "5.846", "4.571", "N/A", "30.5%"],
    ]

    tbl = doc.add_table(rows=len(table_data), cols=len(table_data[0]))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_widths = [Inches(0.70), Inches(0.38), Inches(0.40), Inches(0.35), Inches(0.45), Inches(0.45), Inches(0.45), Inches(0.45)]
    for row_idx, row in enumerate(tbl.rows):
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        for col_idx, cell in enumerate(row.cells):
            cell.text = table_data[row_idx][col_idx]
            cell.width = col_widths[col_idx]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if col_idx > 0 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(1)
            for run in p.runs:
                run.font.name = 'Times New Roman'
                run.font.size = Pt(7.0)
                if row_idx == 0:
                    run.bold = True
            # Borders: top & bottom for header, bottom for last row
            top_b = "single" if row_idx == 0 else "none"
            bot_b = "single" if row_idx == 0 or row_idx == len(table_data) - 1 else "none"
            set_cell_borders(cell, top=top_b, bottom=bot_b)

    add_body_p(
        "Across all five targets, the gradient boosted models outperform persistence on the synthetic holdout, with relative MAE gains ranging from 25.4% (memory) "
        "to 45.4% (network). Network traffic and CPU achieve the highest coefficients of determination (R2 = 0.871 and 0.855). Feature importance rankings show that "
        "current metric lags dominate CPU (69.4%) and network (67.7%), while regional grid intensity drives carbon (71.1%) and CPU utilization drives cost (67.1%)."
    )

    # --- Section VI: Discussion ---
    add_sec_heading("VI. DISCUSSION AND TECHNICAL AUDIT FINDINGS")
    add_body_p(
        "Our audit resolved a critical baseline alignment nuance: the stored rolling-mean baseline in baseline.py evaluates a 1-step-ahead (15-minute) moving average "
        "on unshifted observations. When evaluated as a true four-step-ahead baseline from forecast origin, baseline MAEs rise substantially (e.g., CPU MAE increases "
        "from 4.622% to 7.263%), performing worse than simple persistence (6.500%) due to phase-shift delay during diurnal cycles. The boosted tree models decisively "
        "outperform both baselines."
    )
    add_body_p(
        "However, high synthetic performance must be interpreted with caution. The models effectively learn the smooth mathematical formulas embedded in the generator. "
        "Real-world cluster traces exhibit burstiness, abrupt job terminations, and complex cross-tenant interference that deviate sharply from idealized sinusoids [3]."
    )

    # --- Section VII: Limitations ---
    add_sec_heading("VII. LIMITATIONS AND THREATS TO VALIDITY")
    add_body_p(
        "The primary limitation is data provenance: all results are established on synthetic data. Furthermore, in predictor.py, the forecast_multi_step wrapper applies "
        "5-minute recursion to models trained on 1-hour direct targets and feeds back carbon values scaled ~10x below the training feature distribution. Additionally, "
        "live cloud connectors were not validated across real subscriptions, automated remediation is blocked via HTTP 501, and the carbon proxy assumes constant power, "
        "omitting server dynamic power curves and embodied Scope 3 emissions [4], [5]."
    )

    # --- Section VIII: Conclusion ---
    add_sec_heading("VIII. CONCLUSION")
    add_body_p(
        "GreenMind AI implements a comprehensive decision-support architecture uniting multi-metric forecasting, multi-agent arbitration, Digital Twin simulation, "
        "and copilot interfaces. On a 60-day synthetic benchmark, gradient boosted regressors reduce one-hour-ahead MAE by 25.4% to 45.4% compared to persistence. "
        "These metrics demonstrate successful algorithmic fitting on synthetic telemetry, but do not establish production cloud generalization or realized financial "
        "and carbon savings. Future work will benchmark real-world traces, live grid carbon APIs, and safe canary remediation."
    )

    # --- References ---
    add_sec_heading("REFERENCES")
    refs = [
        "[1] J. H. Friedman, \"Greedy function approximation: A gradient boosting machine,\" The Annals of Statistics, vol. 29, no. 5, pp. 1189-1232, Oct. 2001, doi: 10.1214/aos/1013203451.",
        "[2] C. Bergmeir, R. J. Hyndman, and B. Koo, \"A note on the validity of cross-validation for evaluating autoregressive time series prediction,\" Computational Statistics & Data Analysis, vol. 120, pp. 70-83, Apr. 2018, doi: 10.1016/j.csda.2017.11.003.",
        "[3] A. Rossi, A. Visentin, D. Carraro, S. Prestwich, and K. N. Brown, \"Forecasting workload in cloud computing: Towards uncertainty-aware predictions and transfer learning,\" Cluster Computing, vol. 28, art. no. 258, pp. 1-22, 2025, doi: 10.1007/s10586-024-04933-2.",
        "[4] P. Henderson, J. Hu, J. Romoff, E. Brunskill, D. Jurafsky, and J. Pineau, \"Towards the systematic reporting of the energy and carbon footprints of machine learning,\" Journal of Machine Learning Research, vol. 21, no. 248, pp. 1-43, 2020.",
        "[5] L. Lannelongue, J. Grealey, and M. Inouye, \"Green algorithms: Quantifying the carbon footprint of computation,\" Advanced Science, vol. 8, no. 12, art. no. 2100707, pp. 1-10, 2021, doi: 10.1002/advs.202100707.",
        "[6] A. Radovanovic et al., \"Carbon-aware computing for datacenters,\" IEEE Transactions on Power Systems, vol. 38, no. 2, pp. 1270-1280, Mar. 2023, doi: 10.1109/TPWRS.2022.3173250.",
        "[7] R. N. Calheiros, E. Masoumi, R. Ranjan, and R. Buyya, \"Workload prediction using ARIMA model and its impact on cloud applications' QoS,\" IEEE Transactions on Cloud Computing, vol. 3, no. 4, pp. 449-458, Oct.-Dec. 2015, doi: 10.1109/TCC.2014.2350475.",
        "[8] J. Dodge et al., \"Measuring the carbon intensity of AI in cloud instances,\" in Proceedings of the 2022 ACM Conference on Fairness, Accountability, and Transparency (FAccT '22), 2022, pp. 1536-1546, doi: 10.1145/3531146.3533147.",
        "[9] Pratham-stack-coder, \"GreenMind-AI repository,\" GitHub, 2026. Available: https://github.com/Pratham-stack-coder/GreenMind-AI.",
    ]
    for ref in refs:
        p_ref = doc.add_paragraph()
        p_ref.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_ref.paragraph_format.space_before = Pt(0)
        p_ref.paragraph_format.space_after = Pt(2)
        p_ref.paragraph_format.left_indent = Inches(0.20)
        p_ref.paragraph_format.first_line_indent = Inches(-0.20)
        r = p_ref.add_run(ref)
        r.font.size = Pt(7.8)

    out_file = Path("research_paper/GreenMind_AI_IEEE_Manuscript.docx")
    doc.save(out_file)
    print(f"Generated DOCX manuscript: {out_file.resolve()}")

if __name__ == "__main__":
    build_docx()
