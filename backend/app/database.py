"""
Database layer — SQLAlchemy async ORM (SQLite / PostgreSQL) + Redis caching.
Provides automatic persistence for telemetry, recommendations, audit logs,
simulations, predictions, agent runs, and cloud resources.
Defaults to local SQLite (greenmind.db) if DATABASE_URL is not set.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    select,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

settings = get_settings()

# Default to SQLite with aiosqlite for zero-config persistence
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "greenmind.db"))
fallback_url = f"sqlite+aiosqlite:///{db_path}"

DB_URL = settings.database_url
if not DB_URL:
    DB_URL = fallback_url
else:
    # Normalize postgres url for asyncpg if plain postgresql:// is provided
    if DB_URL.startswith("postgresql://"):
        DB_URL = DB_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

try:
    _engine = create_async_engine(DB_URL, echo=False)
except Exception as e:
    import logging
    logging.getLogger(__name__).warning(
        f"Could not initialize database engine for {DB_URL}: {e}. Falling back to SQLite."
    )
    DB_URL = fallback_url
    _engine = create_async_engine(DB_URL, echo=False)

_async_session_maker = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


# ── Declarative Base & Models ──────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


class CloudResourceRecord(Base):
    __tablename__ = "cloud_resources"

    id = Column(String(128), primary_key=True)
    name = Column(String(255))
    type = Column(String(64))
    provider = Column(String(32), index=True)
    region = Column(String(32), index=True)
    status = Column(String(32))
    cpu_utilization = Column(Float, default=0.0)
    memory_utilization = Column(Float, default=0.0)
    cost_per_hour = Column(Float, default=0.0)
    carbon_intensity = Column(Float, default=0.0)
    tags_json = Column(Text, default="{}")
    right_size_candidate = Column(Boolean, default=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class TelemetryRecord(Base):
    __tablename__ = "cloud_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(String(64), index=True)
    provider = Column(String(32), index=True)
    region = Column(String(32), index=True)
    source = Column(String(32), default="SIMULATED_DEMO")
    cpu = Column(Float)
    memory = Column(Float)
    storage = Column(Float)
    network = Column(Float)
    cost_per_hour = Column(Float)
    carbon_intensity = Column(Float)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PredictionRecord(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target = Column(String(32), index=True)
    current_value = Column(Float)
    predicted_value = Column(Float)
    delta_pct = Column(Float)
    anomaly = Column(Boolean, default=False)
    confidence = Column(Float, default=0.85)
    horizon_minutes = Column(Integer, default=60)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class RecommendationRecord(Base):
    __tablename__ = "recommendations"

    id = Column(String(64), primary_key=True)
    category = Column(String(32), index=True)
    priority = Column(String(32), index=True)
    title = Column(String(255))
    description = Column(Text)
    impact_summary = Column(Text)
    estimated_monthly_savings_usd = Column(Float, default=0.0)
    estimated_carbon_reduction_pct = Column(Float, default=0.0)
    effort = Column(String(16), default="medium")
    action = Column(String(255))
    evidence_json = Column(Text, default="[]")
    confidence = Column(Float, default=0.85)
    status = Column(String(32), default="open", index=True)  # open, applied, dismissed
    applied_at = Column(String(64), nullable=True)
    steps_taken_json = Column(Text, default="[]")
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class AgentResultRecord(Base):
    __tablename__ = "agent_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), index=True)
    agent_name = Column(String(32), index=True)
    score = Column(Integer)
    findings_json = Column(Text, default="[]")
    recommendations_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class OptimizationResultRecord(Base):
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    overall_score = Column(Integer)
    cost_score = Column(Integer)
    performance_score = Column(Integer)
    sustainability_score = Column(Integer)
    security_score = Column(Integer)
    reliability_score = Column(Integer)
    trend = Column(String(32))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SimulationRecord(Base):
    __tablename__ = "simulation_results"

    id = Column(String(64), primary_key=True)
    changes_json = Column(Text)
    before_json = Column(Text)
    after_json = Column(Text)
    delta_json = Column(Text)
    risk_score = Column(Float, default=0.0)
    recommendation = Column(Text)
    confidence = Column(Float, default=0.8)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditLogRecord(Base):
    __tablename__ = "audit_log_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    recommendation_id = Column(String(64), index=True)
    title = Column(String(255))
    action = Column(String(255))
    status = Column(String(32))  # applied, rolled_back, simulated, failed
    dry_run = Column(Boolean, default=False)
    monthly_savings_usd = Column(Float, default=0.0)
    carbon_reduction_pct = Column(Float, default=0.0)
    new_score = Column(Integer, nullable=True)
    operator_notes = Column(Text, nullable=True)
    steps_taken_json = Column(Text, default="[]")
    timestamp = Column(String(64))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# ── Initialization ─────────────────────────────────────────────────────────────

async def init_db() -> None:
    """Create all tables if they do not exist."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency yielding an async DB session."""
    async with _async_session_maker() as session:
        yield session


# ── Redis (optional) ──────────────────────────────────────────────────────────

_redis = None
if settings.redis_url:
    try:
        import redis.asyncio as aioredis  # type: ignore
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        pass


async def cache_get(key: str) -> Any | None:
    if _redis is None:
        return None
    try:
        raw = await _redis.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    if _redis is None:
        return
    try:
        await _redis.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


# ── In-Memory Ring Buffer & Persistence Helpers ────────────────────────────────

_HISTORY_MAX = 2000
_telemetry_history: list[dict] = []


def record_telemetry(entry: dict) -> None:
    """Synchronous in-memory logging for high-speed loops."""
    global _telemetry_history
    if "recorded_at" not in entry:
        entry["recorded_at"] = datetime.now(timezone.utc).isoformat()
    _telemetry_history.append(entry)
    if len(_telemetry_history) > _HISTORY_MAX:
        _telemetry_history = _telemetry_history[-_HISTORY_MAX:]


def get_telemetry_history(limit: int = 100) -> list[dict]:
    return list(reversed(_telemetry_history[-limit:]))


async def persist_telemetry_entry(entry: dict) -> None:
    """Asynchronously persist telemetry reading to database."""
    record_telemetry(entry)
    try:
        async with _async_session_maker() as session:
            record = TelemetryRecord(
                timestamp=entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                provider=entry.get("provider", "aws"),
                region=entry.get("region", "us-east"),
                source=entry.get("source", "SIMULATED_DEMO"),
                cpu=float(entry.get("cpu", 0.0)),
                memory=float(entry.get("memory", 0.0)),
                storage=float(entry.get("storage", 0.0)),
                network=float(entry.get("network", 0.0)),
                cost_per_hour=float(entry.get("cost_per_hour", 0.0)),
                carbon_intensity=float(entry.get("carbon_intensity", 0.0)),
            )
            session.add(record)
            await session.commit()
    except Exception:
        pass


async def persist_audit_log(
    rec_id: str,
    title: str,
    action: str,
    status: str,
    monthly_savings: float,
    carbon_reduction: float,
    new_score: int | None,
    steps_taken: list[str],
    dry_run: bool = False,
    operator_notes: str | None = None,
) -> None:
    """Persist an applied/rollback remediation action to the audit table."""
    try:
        async with _async_session_maker() as session:
            log = AuditLogRecord(
                recommendation_id=rec_id,
                title=title,
                action=action,
                status=status,
                dry_run=dry_run,
                monthly_savings_usd=monthly_savings,
                carbon_reduction_pct=carbon_reduction,
                new_score=new_score,
                operator_notes=operator_notes,
                steps_taken_json=json.dumps(steps_taken),
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
            session.add(log)
            await session.commit()
    except Exception:
        pass
