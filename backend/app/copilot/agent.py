"""
AI Cloud Copilot Agent for GreenMind AI.
Combines tool invocation, knowledge search, and LLM (OpenAI / Gemini) or deterministic engine.
Always grounds answers in live application telemetry and tools.
"""

from __future__ import annotations

import logging
from typing import Any

from ..config import get_settings
from .knowledge import search_knowledge
from .schemas import CopilotAction, CopilotChatRequest, CopilotChatResponse
from . import tools

logger = logging.getLogger(__name__)
settings = get_settings()


class CopilotAgent:
    """Agent orchestrator for conversational cloud optimization questions."""

    def __init__(self):
        self.openai_key = settings.openai_api_key
        self.gemini_key = settings.gemini_api_key

    def process_message(
        self,
        req: CopilotChatRequest,
        llm_credentials: dict[str, str] | None = None,
    ) -> CopilotChatResponse:
        msg = req.message.lower().strip()
        sources: list[str] = []
        actions: list[CopilotAction] = []
        follow_ups: list[str] = []
        snapshot: dict[str, Any] = {}

        # ── Tool Dispatches based on user intent ──────────────────────────────
        metrics = None
        cost_data = None
        carbon_data = None
        predictions = None
        recs = None
        health = None
        sim_result = None
        history = None

        if any(w in msg for w in ["history", "trend", "over time", "recent telemetry"]):
            sources.append("telemetry_history")
            history = tools.get_history(limit=50, provider=req.provider, region=req.region)
            snapshot["history"] = history

        if any(w in msg for w in ["cost", "bill", "expensive", "spend", "saving", "underutilized"]):
            sources.append("cost_analysis")
            sources.append("cloud_metrics")
            cost_data = tools.get_cost_analysis(days=7, provider=req.provider, region=req.region)
            metrics = tools.get_cloud_metrics(req.provider, req.region)
            recs = tools.get_recommendations(req.provider, req.region)
            snapshot["metrics"] = metrics
            snapshot["cost_analysis"] = cost_data
            snapshot["recommendations"] = recs

        if any(w in msg for w in ["carbon", "green", "emission", "co2", "renewable", "clean"]):
            sources.append("carbon_analysis")
            carbon_data = tools.get_carbon_analysis(days=7, region=req.region, provider=req.provider)
            snapshot["carbon_analysis"] = carbon_data

        if any(w in msg for w in ["scale", "cpu", "memory", "predict", "workload", "forecast", "instance"]):
            sources.append("predictions")
            sources.append("cloud_metrics")
            metrics = metrics or tools.get_cloud_metrics(req.provider, req.region)
            predictions = tools.get_predictions(metrics=metrics, provider=req.provider, region=req.region)
            snapshot["predictions"] = predictions

        if any(w in msg for w in ["health", "status", "risk", "alarm", "score"]):
            sources.append("cloud_health")
            health = tools.get_cloud_health(req.provider, req.region)
            snapshot["health"] = health

        if any(w in msg for w in ["what if", "simulate", "simulation", "digital twin", "right-size this", "right size"]):
            sources.append("digital_twin_simulation")
            metrics = metrics or tools.get_cloud_metrics(req.provider, req.region)
            sim_result = tools.run_digital_twin_simulation("RIGHT_SIZE", metrics=metrics)
            snapshot["simulation"] = sim_result

        if not sources:
            # General overview
            sources.append("cloud_metrics")
            metrics = tools.get_cloud_metrics(req.provider, req.region)
            snapshot["metrics"] = metrics

        # Knowledge search
        kb_docs = search_knowledge(msg, top_k=1)

        # ── LLM or Deterministic Generation ───────────────────────────────────
        if llm_credentials is None:
            gemini_key, openai_key = self.gemini_key, self.openai_key
        else:
            gemini_key = llm_credentials.get("gemini_api_key", "")
            openai_key = llm_credentials.get("openai_api_key", "")
        if gemini_key or openai_key:
            answer = self._generate_with_llm(req.message, snapshot, kb_docs, llm_credentials)
        else:
            answer = self._generate_deterministic(msg, snapshot, kb_docs)

        # Build contextual quick actions
        if "cost_analysis" in sources or "digital_twin_simulation" in sources:
            actions.append(
                CopilotAction(
                    label="Simulate Right-Sizing",
                    endpoint="/api/v1/digital-twin/scenario",
                    method="POST",
                    payload={"scenario": "RIGHT_SIZE"},
                )
            )
            actions.append(
                CopilotAction(
                    label="View Cost Recommendations",
                    endpoint="/api/v1/recommendations",
                    method="GET",
                )
            )
            follow_ups.extend([
                "What resources are underutilized right now?",
                "What happens if I right-size this instance?",
                "What is my current cloud health?",
            ])

        if "carbon_analysis" in sources:
            actions.append(
                CopilotAction(
                    label="View Carbon Curve",
                    endpoint="/api/v1/carbon-curve",
                    method="GET",
                    payload={"region": req.region},
                )
            )
            follow_ups.append("How can I reduce carbon emissions?")

        if "predictions" in sources:
            actions.append(
                CopilotAction(
                    label="View 60m Forecasts",
                    endpoint="/api/v1/predictions/forecast",
                    method="POST",
                )
            )
            follow_ups.append("Should I scale my EC2 instance?")

        return CopilotChatResponse(
            answer=answer,
            sources=list(set(sources)),
            actions=actions,
            follow_up_suggestions=list(dict.fromkeys(follow_ups))[:3],
            data_snapshot=snapshot,
        )

    def _generate_deterministic(self, msg: str, data: dict[str, Any], kb: list[dict[str, Any]]) -> str:
        """Build answers from returned values and state clearly when an analysis is unavailable."""
        metrics = data.get("metrics") or {}
        cost = data.get("cost_analysis")
        carbon = data.get("carbon_analysis")
        pred = data.get("predictions")
        health = data.get("health")
        sim = data.get("simulation")
        source = metrics.get("source", "UNKNOWN")
        provider = str(metrics.get("provider", "cloud provider")).upper()
        region = metrics.get("region", "unknown region")
        parts: list[str] = []

        if any(word in msg for word in ("cost", "bill", "spend", "expensive", "saving")):
            if not cost or cost.get("source") == "UNAVAILABLE" or cost.get("total_usd") is None:
                parts.append("Billing-period cost analytics are unavailable for the selected provider and region. No period total is being estimated.")
            else:
                days = cost.get("period_days", "selected")
                cost_source = cost.get("source", "UNKNOWN")
                parts.append(
                    f"Selected {days}-day cost total for {provider} ({region}) is "
                    f"${cost['total_usd']:.2f} (source: {cost_source}). "
                    f"Hourly run-rate from telemetry is {self._format_value(metrics.get('cost_usd_per_hour'), ' USD/hr')} (source: {source}). "
                    "Hourly cost charts show an estimated distribution because cloud providers return period totals."
                )
                drivers = cost.get("top_cost_drivers") or []
                if drivers:
                    parts.append(f"Top reported cost driver: {drivers[0]}.")

        elif "should i scale" in msg or "scale" in msg:
            if not pred or pred.get("status") == "unavailable":
                missing = (pred or {}).get("missing_inputs", [])
                suffix = f" Missing inputs: {', '.join(missing)}." if missing else ""
                parts.append("Forecast-driven scaling advice is unavailable because the baseline input telemetry is incomplete." + suffix)
            else:
                cpu_pred = pred.get("cpu", {}).get("predicted")
                curr_cpu = pred.get("cpu", {}).get("current")
                parts.append(
                    f"Current CPU is {self._format_value(curr_cpu, '%')} (source {pred.get('input_source', 'UNKNOWN')}); "
                    f"60-minute forecast is {self._format_value(cpu_pred, '%')} ({pred.get('source', 'ESTIMATED')}). "
                    "Treat this as an estimate and check service-level metrics before changing capacity."
                )

        elif "reduce carbon" in msg or "carbon" in msg or "green" in msg or "emission" in msg:
            if not carbon:
                parts.append("Regional carbon intensity estimates are unavailable.")
            else:
                green_pct = carbon.get("green_hours_pct")
                assumptions = carbon.get("assumptions")
                parts.append(
                    f"Estimated green window share for {region} is {self._format_value(green_pct, '%')}. "
                    + (f"{assumptions} " if assumptions else "")
                    + "Shift flexible jobs toward the lowest-intensity hours when feasible."
                )

        elif "health" in msg or "status" in msg or "alarm" in msg or "risk" in msg:
            if not health or health.get("source") == "UNAVAILABLE" or health.get("status") == "UNAVAILABLE":
                note = (health or {}).get("note")
                parts.append("Live cloud health checks are unavailable for the selected provider and region." + (f" {note}" if note else ""))
            else:
                details = []
                if health.get("status") is not None:
                    details.append(f"reported status {health['status']}")
                if health.get("health_score") is not None:
                    details.append(f"heuristic health score {health['health_score']}/100")
                if health.get("active_alarms") is not None and health.get("active_alarms_source"):
                    details.append(f"{health['active_alarms']} active alarms (source {health['active_alarms_source']})")
                parts.append("Cloud health response: " + (", ".join(details) if details else "no status fields were returned") + ".")
                if health.get("source"):
                    parts.append(f"Health data source: {health['source']}.")
                if health.get("note"):
                    parts.append(str(health["note"]))

        elif "underutilized" in msg:
            if not metrics:
                parts.append("Utilization telemetry is unavailable.")
            else:
                parts.append(
                    f"Current CPU: {self._format_value(metrics.get('cpu'), '%')}; "
                    f"memory: {self._format_value(metrics.get('memory'), '%')}; source: {source}. "
                    "A single reading does not establish sustained underutilization; review history before resizing."
                )

        elif any(word in msg for word in ("what if", "simulate", "simulation", "digital twin", "right-size", "right size")) or sim:
            if not sim or sim.get("status") == "unavailable":
                missing = (sim or {}).get("missing_inputs", [])
                suffix = f" Missing inputs: {', '.join(missing)}." if missing else ""
                parts.append("The simulation is unavailable because a complete baseline is missing." + suffix)
            else:
                parts.append(
                    f"The digital-twin simulation used {sim.get('input_source', 'UNKNOWN')} inputs. "
                    "Review its modeled before and after values as estimates; no cloud resources were changed."
                )

        else:
            if metrics:
                parts.append(
                    f"GreenMind returned telemetry for {provider} ({region}) from source {source}: "
                    f"CPU {self._format_value(metrics.get('cpu'), '%')}, "
                    f"memory {self._format_value(metrics.get('memory'), '%')}, "
                    f"network {self._format_value(metrics.get('network'), ' Mbps')}, "
                    f"hourly cost {self._format_value(metrics.get('cost_usd_per_hour'), ' USD/hr')}, "
                    f"carbon {self._format_value(metrics.get('carbon_gco2_per_hour'), ' gCO₂/hr')}."
                )
            else:
                parts.append("No telemetry values were returned for the selected scope.")

        if kb:
            parts.append(f"\n\nReference ({kb[0].get('title', 'knowledge base')}): {kb[0].get('content', '')[:180]}")

        return "\n".join(parts)

    @staticmethod
    def _format_value(value: Any, suffix: str = "") -> str:
        if value is None or isinstance(value, bool):
            return "unavailable"
        if isinstance(value, (int, float)):
            return f"{value:.2f}{suffix}"
        return f"{value}{suffix}"

    def _generate_with_llm(
        self,
        query: str,
        data: dict[str, Any],
        kb: list[dict[str, Any]],
        llm_credentials: dict[str, str] | None = None,
    ) -> str:
        """Call Gemini or OpenAI if API key is present."""
        from datetime import datetime, timezone
        from ..cloud import get_provider
        metrics = data.get("metrics") or {}
        prov_name = metrics.get("provider", "aws")
        p = get_provider(prov_name)
        status_mode = p.status.get("mode", "DEMO")
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        system_instruction = (
            f"You are GreenMind AI Cloud Copilot.\n"
            f"Current Provider: {prov_name.upper()} (Connection Status: {status_mode})\n"
            f"Current Region: {metrics.get('region', 'us-east')}\n"
            f"Current Time: {now_utc}\n"
            f"Telemetry Summary (source={metrics.get('source', 'UNKNOWN')}): CPU={metrics.get('cpu')}%, Cost=${metrics.get('cost_usd_per_hour')}/hr, "
            f"Carbon={metrics.get('carbon_gco2_per_hour')} gCO2/hr, Memory={metrics.get('memory')}\n"
            f"DATA TRUTH RULES:\n"
            f"1. Never state an estimated or demo value is a live measurement.\n"
            f"2. When a value is unavailable, say that it is unavailable; do not assume why.\n"
            f"3. Mark DEMO and ESTIMATED values clearly and never fill missing fields with defaults.\n"
            f"4. Ground all answers strictly in the provided data. Do not hallucinate."
        )
        context_str = f"Cloud Telemetry & Analysis Data:\n{data}\n\nRelevant Rules & Knowledge:\n{kb}"

        gemini_key = self.gemini_key if llm_credentials is None else llm_credentials.get("gemini_api_key", "")
        openai_key = self.openai_key if llm_credentials is None else llm_credentials.get("openai_api_key", "")

        if gemini_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=gemini_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                resp = model.generate_content(f"{system_instruction}\n\n{context_str}\n\nUser Question: {query}")
                if resp.text:
                    return resp.text
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}")

        if openai_key:
            try:
                import openai
                client = openai.OpenAI(api_key=openai_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": f"{context_str}\n\nUser Question: {query}"},
                    ],
                    max_tokens=600,
                )
                content = resp.choices[0].message.content
                if content:
                    return content
            except Exception as e:
                logger.warning(f"OpenAI API call failed: {e}")

        # Fallback to deterministic
        return self._generate_deterministic(query.lower(), data, kb)


copilot_agent = CopilotAgent()
