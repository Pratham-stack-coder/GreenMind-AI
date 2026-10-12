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
            snapshot["recommendations"] = [rec.model_dump() for rec in recs]

        if any(w in msg for w in ["carbon", "green", "emission", "co2", "renewable", "clean"]):
            sources.append("carbon_analysis")
            carbon_data = tools.get_carbon_analysis(days=7, region=req.region)
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
            if not cost:
                parts.append("Cost analytics are unavailable for the selected provider and region.")
            else:
                days = cost.get("period_days", "selected")
                cost_source = cost.get("source", "UNKNOWN")
                parts.append(
                    f"Cost analytics for {provider} ({region}) cover {days} days and report "
                    f"total {self._format_value(cost.get('total_usd'), ' USD')} from source {cost_source}. "
                    "The hourly chart is an estimated allocation of that period total, not an observed hourly bill."
                )
                if metrics:
                    hourly = metrics.get("cost_usd_per_hour")
                    cpu = metrics.get("cpu")
                    parts.append(
                        f"Current telemetry source: {source}. "
                        f"Hourly cost metric: {self._format_value(hourly, ' USD/hr')}; "
                        f"CPU: {self._format_value(cpu, '%')}."
                    )
                drivers = cost.get("top_cost_drivers") or []
                if drivers:
                    parts.append("Top reported cost drivers: " + ", ".join(str(item) for item in drivers) + ".")
                recommendations = data.get("recommendations") or []
                if recommendations:
                    titles = [str(item.get("title")) for item in recommendations if isinstance(item, dict) and item.get("title")]
                    if titles:
                        parts.append("Available recommendations: " + "; ".join(titles[:3]) + ". Review their evidence and estimates before acting.")

        elif any(word in msg for word in ("carbon", "green", "emission", "co2", "renewable", "clean")):
            if not carbon:
                parts.append("Carbon analysis is unavailable for the selected region.")
            else:
                parts.append(
                    f"Estimated carbon analysis for {region} reports {self._format_value(carbon.get('green_hours_pct'), '%')} green hours "
                    f"over {carbon.get('period_days', 'the selected')} days, with source {carbon.get('source', 'UNKNOWN')} "
                    f"and methodology {carbon.get('methodology', 'not reported')}. "
                    "This is a regional model, not a direct measurement of workload emissions unless the source says otherwise."
                )

        elif any(word in msg for word in ("history", "trend", "over time", "recent telemetry")):
            entries = data.get("history") or []
            if not entries:
                parts.append("No recent telemetry for this provider and region is available in the process-local history buffer.")
            else:
                cpu_values = [entry.get("cpu") for entry in entries if isinstance(entry.get("cpu"), (int, float))]
                sources = sorted({str(entry.get("source", "UNKNOWN")) for entry in entries})
                time_range = f"from {entries[-1].get('timestamp', 'unknown')} through {entries[0].get('timestamp', 'unknown')}"
                summary = f"Found {len(entries)} in-process telemetry samples {time_range}; sources: {', '.join(sources)}."
                if cpu_values:
                    summary += f" CPU ranged from {min(cpu_values):.1f}% to {max(cpu_values):.1f}% across those samples."
                summary += " This history may not include readings collected before the service restarted."
                parts.append(summary)
        elif any(word in msg for word in ("scale", "cpu", "memory", "predict", "workload", "forecast", "instance")):
            if not pred or pred.get("status") == "unavailable":
                missing = (pred or {}).get("missing_inputs", [])
                suffix = f" Missing inputs: {', '.join(missing)}." if missing else ""
                parts.append("A forecast is unavailable from the current telemetry." + suffix)
            else:
                cpu_forecast = pred.get("cpu", {})
                parts.append(
                    f"Current CPU is {self._format_value(metrics.get('cpu'), '%')} from source {source}; "
                    f"the model forecasts {self._format_value(cpu_forecast.get('predicted'), '%')} for its 60-minute horizon. "
                    f"Forecast inputs use telemetry source {pred.get('input_source', 'UNKNOWN')} and regional carbon intensity source {pred.get('carbon_input_source', 'UNKNOWN')}. "
                    "Treat this as an estimate and check service-level metrics before changing capacity."
                )

        elif "health" in msg or "status" in msg or "alarm" in msg or "risk" in msg:
            if not health:
                parts.append("Cloud health data is unavailable for the selected provider and region.")
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
