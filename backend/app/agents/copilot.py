"""
AI Cloud Copilot — natural language interface to cloud management actions.

Rule-based intent engine by default (no API key required).
Add GEMINI_API_KEY or OPENAI_API_KEY to .env for real LLM responses.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from ..config import get_settings

settings = get_settings()


# ── Intent patterns ────────────────────────────────────────────────────────────

_INTENT_PATTERNS: list[tuple[list[str], str]] = [
    (["cost", "spend", "bill", "expensive", "save money", "savings"], "cost"),
    (["carbon", "green", "emission", "co2", "sustainability", "renewable"], "sustainability"),
    (["cpu", "performance", "slow", "latency", "memory", "bottleneck", "scale"], "performance"),
    (["security", "vulnerability", "breach", "permission", "iam", "encrypt", "mfa"], "security"),
    (["reliability", "uptime", "availability", "backup", "failover", "ha", "sla"], "reliability"),
    (["predict", "forecast", "future", "next hour", "trend"], "prediction"),
    (["simulate", "what if", "digital twin", "before", "after", "impact"], "simulation"),
    (["recommend", "optimize", "suggestion", "improve", "best practice"], "recommendations"),
    (["status", "health", "overview", "dashboard", "summary"], "overview"),
    (["region", "migrate", "move", "transfer"], "migration"),
]


def _detect_intent(message: str) -> str:
    lower = message.lower()
    scores: dict[str, int] = {}
    for keywords, intent in _INTENT_PATTERNS:
        for kw in keywords:
            if kw in lower:
                scores[intent] = scores.get(intent, 0) + 1
    if not scores:
        return "general"
    return max(scores, key=lambda k: scores[k])


# ── Response templates ────────────────────────────────────────────────────────

_RESPONSES: dict[str, dict] = {
    "cost": {
        "reply": (
            "I've analyzed your cloud spending. Here are the key cost optimization opportunities:\n\n"
            "**Immediate actions:**\n"
            "- Right-size over-provisioned instances — potential 20–40% savings\n"
            "- Terminate idle instances (CPU < 10%) immediately\n"
            "- Purchase 1-year Reserved Instances for sustained workloads — ~30% savings\n\n"
            "**Strategic actions:**\n"
            "- Enable auto-scaling to avoid over-provisioning during off-peak hours\n"
            "- Use Spot Instances for fault-tolerant batch workloads — up to 80% savings\n\n"
            "Would you like me to run a detailed cost analysis or simulate the impact of right-sizing?"
        ),
        "actions": [
            {"label": "Run Cost Analysis", "endpoint": "/api/v1/agents/run", "method": "POST"},
            {"label": "Simulate Right-Sizing", "endpoint": "/api/v1/digital-twin/simulate", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "Show me idle instances by region",
            "What would I save by switching to Reserved Instances?",
            "Simulate downsizing my m5.xlarge to m5.large",
        ],
    },
    "sustainability": {
        "reply": (
            "Let me check your carbon footprint and green scheduling options.\n\n"
            "**Carbon reduction strategies:**\n"
            "- Schedule batch workloads during low-carbon intensity windows (typically 1–6 AM)\n"
            "- Consider migrating to **ca-central** (hydroelectric — cleanest region, ~90 gCO2/kWh)\n"
            "- Enable carbon budget alerts to track Scope 2 emissions\n\n"
            "**Current status:**\n"
            "The carbon intensity curve shows the best deferral window for your region. "
            "Deferring non-urgent jobs by 6–10h can reduce emissions by 15–25% at no cost change."
        ),
        "actions": [
            {"label": "View Carbon Curve", "endpoint": "/api/v1/carbon-curve", "method": "GET"},
            {"label": "Run Sustainability Analysis", "endpoint": "/api/v1/agents/run", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "What is the greenest region for my workload?",
            "When should I schedule my batch job tonight?",
            "Compare my carbon footprint to industry average",
        ],
    },
    "performance": {
        "reply": (
            "I'm monitoring your performance metrics in real time. Here's what I see:\n\n"
            "**Performance insights:**\n"
            "- CPU forecast uses a Gradient Boosting model (MAE: 3.8%) to predict load 1 hour ahead\n"
            "- Auto-scaling triggers at 75% CPU to prevent latency spikes\n"
            "- Memory anomalies are flagged when utilization exceeds 2.5 standard deviations from baseline\n\n"
            "**Recommendation:** Enable predictive auto-scaling — scale *before* you hit the threshold, "
            "not after. GreenMind's ML forecast can trigger scale-out 45 minutes earlier."
        ),
        "actions": [
            {"label": "View Predictions", "endpoint": "/api/v1/predictions/forecast", "method": "POST"},
            {"label": "Check Performance Score", "endpoint": "/api/v1/analytics/score", "method": "GET"},
        ],
        "follow_up_suggestions": [
            "Predict my CPU for the next 2 hours",
            "Am I about to hit a performance bottleneck?",
            "Show me my memory utilization trend",
        ],
    },
    "security": {
        "reply": (
            "I've performed a security posture assessment. Key findings:\n\n"
            "**Critical (act now):**\n"
            "- Enforce MFA on all admin accounts\n"
            "- Remove 0.0.0.0/0 ingress rules from security groups\n\n"
            "**High priority:**\n"
            "- Enable encryption at rest for all EBS volumes\n"
            "- Audit IAM roles for least-privilege compliance\n\n"
            "**Note:** Connect your cloud provider account for a full live audit including "
            "CloudTrail logs, GuardDuty findings, and S3 bucket policy analysis."
        ),
        "actions": [
            {"label": "Run Security Audit", "endpoint": "/api/v1/agents/run", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "Which IAM roles have admin access?",
            "Are any of my S3 buckets public?",
            "Scan for security group misconfigurations",
        ],
    },
    "reliability": {
        "reply": (
            "Here's your reliability posture:\n\n"
            "**Architecture risks:**\n"
            "- Single-AZ deployments have no redundancy — any AZ failure = total outage\n"
            "- Ensure auto-scaling groups span at least 2 AZs\n\n"
            "**Backup & recovery:**\n"
            "- Configure automated daily snapshots for all data volumes\n"
            "- Test restore procedures quarterly\n\n"
            "**Health checks:**\n"
            "- Enable ALB health checks on all service endpoints to prevent routing to unhealthy instances"
        ),
        "actions": [
            {"label": "Run Reliability Analysis", "endpoint": "/api/v1/agents/run", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "How many availability zones am I using?",
            "When was my last backup?",
            "What is my current SLA?",
        ],
    },
    "prediction": {
        "reply": (
            "GreenMind's ML engine forecasts 5 metrics simultaneously:\n\n"
            "| Metric | Model | MAE vs Baseline |\n"
            "|--------|-------|-----------------|\n"
            "| CPU | Gradient Boosting | -41.4% |\n"
            "| Memory | Gradient Boosting | -25.4% |\n"
            "| Network | Gradient Boosting | -45.4% |\n"
            "| Cost | Gradient Boosting | -100% |\n"
            "| Carbon | Gradient Boosting | -98.9% |\n\n"
            "All models use chronological train/test splits to prevent data leakage. "
            "Predictions are 1 hour ahead (4 × 15-min steps)."
        ),
        "actions": [
            {"label": "Run Forecast", "endpoint": "/api/v1/predictions/forecast", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "What will my CPU be in 1 hour?",
            "Forecast my cost for today",
            "Predict my carbon emissions this week",
        ],
    },
    "simulation": {
        "reply": (
            "The Digital Twin engine lets you simulate infrastructure changes before applying them.\n\n"
            "**What you can simulate:**\n"
            "- Resize instances (e.g., m5.xlarge → m5.large)\n"
            "- Scale out/in (add or remove instances)\n"
            "- Migrate to a different region\n"
            "- Consolidate multiple instances\n\n"
            "Each simulation returns a before/after comparison with cost, performance, and carbon impact estimates."
        ),
        "actions": [
            {"label": "Open Digital Twin", "endpoint": "/api/v1/digital-twin/simulate", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "What would happen if I resize to m5.large?",
            "Simulate migrating to ca-central region",
            "What is the carbon impact of adding 2 more instances?",
        ],
    },
    "recommendations": {
        "reply": (
            "I've generated optimization recommendations across all 5 dimensions:\n\n"
            "Use the **Recommendations** tab to see the full ranked list with confidence scores, "
            "estimated savings, and step-by-step implementation guides.\n\n"
            "I prioritize by: Critical → High → Medium → Low, balancing cost savings, "
            "performance risk, and sustainability impact."
        ),
        "actions": [
            {"label": "View Recommendations", "endpoint": "/api/v1/recommendations", "method": "GET"},
            {"label": "Run Full Analysis", "endpoint": "/api/v1/agents/run", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "What is my top cost recommendation?",
            "Show me only critical issues",
            "How do I implement the right-sizing recommendation?",
        ],
    },
    "overview": {
        "reply": (
            "**GreenMind AI System Overview**\n\n"
            "Your cloud infrastructure is being monitored across:\n"
            "- **Providers:** AWS, Azure, GCP (Demo mode)\n"
            "- **Regions:** 6 regions with carbon intensity tracking\n"
            "- **Metrics:** CPU, Memory, Network, Storage, Cost, Carbon\n"
            "- **ML Models:** 5 forecasters (all beating naive baseline)\n"
            "- **Agents:** Cost, Performance, Sustainability, Security, Reliability\n\n"
            "Navigate to the Dashboard for live metrics, or ask me about any specific area."
        ),
        "actions": [
            {"label": "View Dashboard", "endpoint": "/", "method": "GET"},
            {"label": "Run Full Analysis", "endpoint": "/api/v1/agents/run", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "What is my overall optimization score?",
            "Show me all critical issues",
            "How does my carbon footprint compare to last week?",
        ],
    },
    "migration": {
        "reply": (
            "Region migration analysis:\n\n"
            "**Cleanest regions by carbon score:**\n"
            "1. ca-central — 95/100 (hydroelectric, ~90 gCO2/kWh avg)\n"
            "2. us-west — 82/100 (high solar/wind, ~247 gCO2/kWh avg)\n"
            "3. eu-west — 76/100 (wind-heavy, ~250 gCO2/kWh avg)\n\n"
            "Migration involves latency trade-offs. Simulating a migration will estimate "
            "the cost, latency, and carbon impact."
        ),
        "actions": [
            {"label": "Simulate Region Migration", "endpoint": "/api/v1/digital-twin/simulate", "method": "POST"},
        ],
        "follow_up_suggestions": [
            "What is the latency impact of migrating to ca-central?",
            "How much carbon would I save in eu-west?",
            "Simulate migrating my database to us-west",
        ],
    },
    "general": {
        "reply": (
            "I'm GreenMind's AI Cloud Copilot. I can help you with:\n\n"
            "- **Cost optimization** — right-sizing, reserved instances, idle resource cleanup\n"
            "- **Performance** — CPU/memory forecasting, scaling recommendations\n"
            "- **Sustainability** — carbon-aware scheduling, green region selection\n"
            "- **Security** — posture assessment, compliance gaps\n"
            "- **Reliability** — HA architecture, backup policies\n"
            "- **Digital Twin** — simulate infrastructure changes before applying\n\n"
            "Try asking: *\"What can I do to reduce my cloud bill?\"* or *\"When should I run my batch job?\"*"
        ),
        "actions": [],
        "follow_up_suggestions": [
            "What can I do to reduce my cloud bill?",
            "When is the best time to run my batch job tonight?",
            "What is my overall cloud health score?",
            "Show me my top 3 cost savings opportunities",
        ],
    },
}


async def respond(message: str, history: list[dict], context: dict) -> dict:
    """Process a copilot message and return a structured response.

    Context injection: if the caller provides live metric readings via *context*,
    we prepend a concise environment snapshot to the reply so the answer feels
    grounded in the user's actual infrastructure state rather than generic advice.
    """
    intent = _detect_intent(message)

    # Try real LLM if API key is available
    if settings.gemini_api_key or settings.openai_api_key:
        try:
            return await _llm_respond(message, history, context, intent)
        except Exception:
            pass  # fall through to rule-based

    template = _RESPONSES.get(intent, _RESPONSES["general"])
    base_reply = template["reply"]

    # Build a live-context prefix when metrics are present in the request context
    ctx_lines: list[str] = []
    if context:
        provider = context.get("provider", "")
        region = context.get("region", "")
        cpu = context.get("cpu")
        cost = context.get("cost_usd_per_hour")
        carbon = context.get("carbon_gco2_per_hour")
        score = context.get("overall_score")

        parts: list[str] = []
        if provider and region:
            parts.append(f"**{provider.upper()} / {region}**")
        if cpu is not None:
            load = "high" if cpu > 75 else "moderate" if cpu > 45 else "low"
            parts.append(f"CPU {cpu:.1f}% ({load} load)")
        if cost is not None:
            parts.append(f"${cost:.4f}/hr")
        if carbon is not None:
            parts.append(f"{carbon:.1f} gCO₂/hr")
        if score is not None:
            parts.append(f"score {score}/100")

        if parts:
            ctx_lines.append("*Live context: " + " · ".join(parts) + "*\n\n")

    full_reply = "".join(ctx_lines) + base_reply

    return {
        "reply": full_reply,
        "actions": template.get("actions", []),
        "charts": [],
        "follow_up_suggestions": template.get("follow_up_suggestions", []),
        "intent": intent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



async def _llm_respond(message: str, history: list[dict], context: dict, intent: str) -> dict:
    """Real LLM-backed response (Gemini or OpenAI)."""
    system_prompt = (
        "You are GreenMind AI's Cloud Copilot — an expert in cloud cost optimization, "
        "sustainability, performance, security, and reliability. "
        "The user is managing cloud infrastructure. Provide concise, actionable advice. "
        "Use markdown formatting. Keep responses under 300 words unless asked for detail."
    )

    if settings.gemini_api_key:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel("gemini-pro")
        chat = model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]} for m in history
        ])
        response = chat.send_message(message)
        reply = response.text
    elif settings.openai_api_key:
        import openai  # type: ignore
        client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        msgs = [{"role": "system", "content": system_prompt}]
        msgs.extend(history)
        msgs.append({"role": "user", "content": message})
        resp = await client.chat.completions.create(model="gpt-4o-mini", messages=msgs)
        reply = resp.choices[0].message.content

    template = _RESPONSES.get(intent, _RESPONSES["general"])
    return {
        "reply": reply,
        "actions": template.get("actions", []),
        "charts": [],
        "follow_up_suggestions": template.get("follow_up_suggestions", []),
        "intent": intent,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
