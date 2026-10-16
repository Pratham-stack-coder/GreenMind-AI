"""
Generates an elegant, publication-quality architecture diagram for GreenMind AI.
Conforms to IEEE transaction / conference figure styling guidelines.
Flow: Telemetry -> Forecasting -> Multi-Agent Analysis -> Conflict Resolution -> Digital Twin Simulation -> Recommendations
"""

from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as patches

plt.rcParams['font.sans-serif'] = 'Arial'
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['figure.dpi'] = 300

fig, ax = plt.subplots(figsize=(12, 4.4), dpi=300)
ax.set_xlim(0, 120)
ax.set_ylim(0, 44)
ax.axis('off')

# Colors
c_border = "#1E293B"
c_telemetry = "#F1F5F9"
c_ml = "#E2E8F0"
c_agent = "#FEF3C7"
c_conflict = "#FEE2E2"
c_dt = "#DCFCE7"
c_output = "#EDE9FE"
c_arrow = "#0F172A"

def draw_box(x, y, w, h, title, subtitle, items, bg_color):
    rect = patches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.2,rounding_size=1.0",
        linewidth=1.2, edgecolor=c_border, facecolor=bg_color
    )
    ax.add_patch(rect)
    
    # Title
    ax.text(x + w/2, y + h - 2.6, title, ha='center', va='center',
            fontsize=7.8, fontweight='bold', color="#0F172A")
    # Subtitle
    if subtitle:
        ax.text(x + w/2, y + h - 4.8, subtitle, ha='center', va='center',
                fontsize=6.6, fontstyle='italic', color="#475569")
    
    # Dividing line
    ax.plot([x + 1.0, x + w - 1.0], [y + h - 6.2, y + h - 6.2], color="#94A3B8", lw=0.7)
    
    # Items
    start_y = y + h - 8.2
    for i, item in enumerate(items):
        weight = 'bold' if item.startswith("•") and not item.startswith("•  ") else 'normal'
        color = "#0F172A" if weight == 'bold' else "#334155"
        ax.text(x + 1.2, start_y - i * 2.15, item, ha='left', va='center',
                fontsize=6.2, fontweight=weight, color=color)

# 1. Telemetry Ingestion (x=2 to 18)
draw_box(
    2.0, 5, 16.0, 36,
    "1. Telemetry Ingestion",
    "Multi-Source 15-min Series",
    [
        "• Cloud Connectors:",
        "   - AWS CloudWatch",
        "   - Azure Monitor",
        "   - GCP Monitoring",
        "• Synthetic Generator:",
        "   - 60 days @ 15 min",
        "   - 5,756 records",
        "• Telemetry Signals:",
        "   - CPU utilization (%)",
        "   - Memory load (%)",
        "   - Network IO (Mbps)",
        "   - Hourly spend ($/h)",
        "   - Carbon (gCO2 proxy)"
    ],
    c_telemetry
)

# 2. Multi-Metric Forecasting (x=22 to 38)
draw_box(
    22.0, 5, 16.0, 36,
    "2. ML Forecasting",
    "5 Gradient Boosting Models",
    [
        "• Horizon: 1h ahead (4 steps)",
        "• Train / Test Split:",
        "   - Chronological 80/20",
        "   - 4,604 train / 1,152 test",
        "• Input Features:",
        "   - Target lags, 1h avg/std",
        "   - Hour, Day-of-Week",
        "• Held-out Test Error:",
        "   - CPU: MAE 3.81% (R² .86)",
        "   - Mem: MAE 2.98% (R² .64)",
        "   - Net: MAE 43.88 (R² .87)",
        "   - Cost: MAE $0.009 (R² .47)",
        "   - CO2: MAE 4.06g (R² .39)"
    ],
    c_ml
)

# 3. Multi-Agent Analysis (x=42 to 58)
draw_box(
    42.0, 5, 16.0, 36,
    "3. Multi-Agent Analysis",
    "LangGraph StateGraph",
    [
        "• Cost Agent:",
        "   - Detects idle instances",
        "   - Spot & RI opportunities",
        "• Performance Agent:",
        "   - Headroom & saturation",
        "   - Scale-out thresholds",
        "• Sustainability Agent:",
        "   - Grid carbon curves",
        "   - Green window deferral",
        "• Security & Reliability:",
        "   - IAM & TLS posture",
        "   - HA multi-zone resilience"
    ],
    c_agent
)

# 4. Conflict Resolution (x=62 to 78)
draw_box(
    62.0, 5, 16.0, 36,
    "4. Conflict Resolution",
    "Deterministic Arbitration",
    [
        "• Trade-off Engine:",
        "   - Headroom vs Cost",
        "     (Predictive scaling)",
        "   - Deferral vs Immediate",
        "     (Batch time-shift)",
        "   - Standby vs Elimination",
        "• Output Reconciliation:",
        "   - Rule-based priority",
        "   - Transparent rationale",
        "   - Unified candidate plan"
    ],
    c_conflict
)

# 5. Digital Twin Simulation (x=82 to 98)
draw_box(
    82.0, 5, 16.0, 36,
    "5. Digital Twin",
    "Non-Destructive Simulation",
    [
        "• Evaluated Scenarios:",
        "   - Right-Sizing",
        "   - Scale-Up / Scale-Down",
        "   - Node Consolidation",
        "   - Region Migration",
        "• Projected Outputs:",
        "   - Baseline & target scores",
        "   - Estimated bill savings",
        "   - Simulated Scope 2 delta",
        "• Safety Guarantee:",
        "   - Zero cloud mutations"
    ],
    c_dt
)

# 6. Copilot & Cockpit (x=102 to 118)
draw_box(
    102.0, 5, 16.0, 36,
    "6. Cockpit & Copilot",
    "Decision Support",
    [
        "• 8 Grounded Tools:",
        "   - Telemetry & history",
        "   - Forecasts & scores",
        "   - Digital Twin runner",
        "• Operator Cockpit:",
        "   - Explainable cards",
        "   - Dry-run action preview",
        "• Safety Guardrail:",
        "   - Live remediation",
        "     returns HTTP 501",
        "   - Audit logging only"
    ],
    c_output
)

# Connection Arrows
def draw_arrow(x_start, x_end, y, label):
    ax.annotate(
        "", xy=(x_end, y), xytext=(x_start, y),
        arrowprops=dict(
            arrowstyle="-|>", color=c_arrow,
            lw=1.4, mutation_scale=10,
            shrinkA=0, shrinkB=0
        )
    )
    ax.text((x_start + x_end) / 2, y + 1.2, label, ha='center', va='bottom',
            fontsize=6.0, fontweight='bold', color="#1E293B")

draw_arrow(18.0, 22.0, 23.0, "15m TS")
draw_arrow(38.0, 42.0, 23.0, "1h Pred")
draw_arrow(58.0, 62.0, 23.0, "Findings")
draw_arrow(78.0, 82.0, 23.0, "Resolved")
draw_arrow(98.0, 102.0, 23.0, "Simulated")

# Bottom caption
caption_text = (
    "Fig. 1. End-to-end GreenMind AI pipeline architecture: multi-source telemetry ingestion -> ML multi-metric forecasting -> "
    "specialized multi-agent analysis -> deterministic conflict resolution -> Digital Twin simulation -> operator decision support."
)
ax.text(60.0, 1.8, caption_text, ha='center', va='center', fontsize=7.6, fontstyle='italic', color="#0F172A")

out_path = Path("research_paper/greenmind_architecture.png")
plt.tight_layout()
plt.savefig(out_path, dpi=300, bbox_inches='tight')
print(f"Generated clean architecture diagram at: {out_path.resolve()}")
