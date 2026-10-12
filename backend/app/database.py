"""
Database layer — SQLAlchemy async ORM (SQLite / PostgreSQL) + Redis caching.
Provides automatic persistence for telemetry, recommendations, audit logs,
simulations, predictions, agent runs, and cloud resources.
Defaults to local SQLite (greenmind.db) if DATABASE_URL is not set.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    cast,
    func,
    Integer,
    String,
    Text,
    select,
    inspect,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings
from .auth import get_current_user_id
from .credential_crypto import decrypt_credentials, encrypt_credentials

settings = get_settings()
logger = logging.getLogger(__name__)

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
    owner_id = Column(String(255), nullable=True)
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


class UserProviderCredentialRecord(Base):
    __tablename__ = "user_provider_credentials"

    owner_id = Column(String(255), primary_key=True)
    provider = Column(String(32), primary_key=True)
    encrypted_credentials = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TelemetryRecord(Base):
    __tablename__ = "cloud_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(255), nullable=True)
    timestamp = Column(String(64), index=True)
    provider = Column(String(32), index=True)
    region = Column(String(32), index=True)
    account_id = Column(String(64), nullable=True)
    resource_id = Column(String(128), nullable=True, index=True)
    resource_type = Column(String(64), default="instance")
    source = Column(String(32), default="DEMO")
    cpu = Column(Float, default=0.0)
    memory = Column(Float, nullable=True)
    storage = Column(Float, nullable=True)
    network = Column(Float, nullable=True)
    network_in = Column(Float, nullable=True)
    network_out = Column(Float, nullable=True)
    cost_per_hour = Column(Float, default=0.0)
    carbon_intensity = Column(Float, default=0.0)
    status = Column(String(32), default="running")
    memory_source = Column(String(32), default="DEMO")
    memory_note = Column(Text, nullable=True)
    recorded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "provider": self.provider,
            "region": self.region,
            "account_id": self.account_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "cpu": self.cpu,
            "memory": self.memory,
            "storage": self.storage,
            "network": self.network,
            "network_in": self.network_in,
            "network_out": self.network_out,
            "cost_usd_per_hour": self.cost_per_hour,
            "carbon_gco2_per_hour": self.carbon_intensity,
            "status": self.status,
            "source": self.source,
            "memory_source": self.memory_source,
            "memory_note": self.memory_note,
        }


class PredictionRecord(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(255), nullable=True)
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
    owner_id = Column(String(255), nullable=True)
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
    owner_id = Column(String(255), nullable=True)
    run_id = Column(String(64), index=True)
    agent_name = Column(String(32), index=True)
    score = Column(Integer)
    findings_json = Column(Text, default="[]")
    recommendations_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class OptimizationResultRecord(Base):
    __tablename__ = "optimization_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(String(255), nullable=True)
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
    owner_id = Column(String(255), nullable=True)
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
    owner_id = Column(String(255), nullable=True)
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
    """Create tables and safely add per-user ownership to existing databases."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_owner_columns)


def _ensure_owner_columns(sync_conn) -> None:
    """Add ownership columns to databases created before tenant isolation."""
    tables = (
        "cloud_resources", "cloud_metrics", "predictions", "recommendations",
        "agent_results", "optimization_results", "simulation_results", "audit_log_records",
    )
    existing_tables = set(inspect(sync_conn).get_table_names())
    for table in tables:
        if table not in existing_tables:
            continue
        columns = {column["name"] for column in inspect(sync_conn).get_columns(table)}
        if "owner_id" not in columns:
            sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN owner_id VARCHAR(255)"))
        if table == "cloud_metrics" and "recorded_at" not in columns:
            sync_conn.execute(text("ALTER TABLE cloud_metrics ADD COLUMN recorded_at DATETIME"))
        sync_conn.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_owner_id ON {table} (owner_id)"))
    if "cloud_metrics" in existing_tables:
        metric_columns = {column["name"] for column in inspect(sync_conn).get_columns("cloud_metrics")}
        if "recorded_at" in metric_columns:
            sync_conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_cloud_metrics_recorded_at ON cloud_metrics (recorded_at)"
            ))


async def get_db():
    """FastAPI dependency yielding an async DB session."""
    async with _async_session_maker() as session:
        yield session


async def get_user_provider_credentials(owner_id: str) -> dict[str, dict[str, str]]:
    """Load and decrypt only this user's provider credentials."""
    async with _async_session_maker() as session:
        result = await session.execute(
            select(UserProviderCredentialRecord).where(UserProviderCredentialRecord.owner_id == owner_id)
        )
        return {
            row.provider: decrypt_credentials(row.encrypted_credentials)
            for row in result.scalars().all()
        }


async def store_user_provider_credentials(owner_id: str, provider: str, credentials: dict[str, str]) -> dict[str, str]:
    """Merge and persist credentials encrypted under the configured Fernet key."""
    await init_db()
    async with _async_session_maker() as session:
        row = await session.get(UserProviderCredentialRecord, (owner_id, provider))
        existing = decrypt_credentials(row.encrypted_credentials) if row else {}
        merged = {**existing, **credentials}
        if row:
            row.encrypted_credentials = encrypt_credentials(merged)
            row.updated_at = datetime.now(timezone.utc)
        else:
            session.add(UserProviderCredentialRecord(
                owner_id=owner_id,
                provider=provider,
                encrypted_credentials=encrypt_credentials(merged),
            ))
        await session.commit()
        return merged


async def delete_user_provider_credentials(owner_id: str, provider: str) -> None:
    """Delete only this user's encrypted provider credentials."""
    async with _async_session_maker() as session:
        row = await session.get(UserProviderCredentialRecord, (owner_id, provider))
        if row:
            await session.delete(row)
            await session.commit()


# ── Redis (optional) ──────────────────────────────────────────────────────────

_redis = None
if settings.redis_url:
    try:
        import redis.asyncio as aioredis  # type: ignore
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    except Exception:
        pass


async def cache_get(key: str) -> Any | None:
    owner_id = get_current_user_id()
    if _redis is None or not owner_id:
        return None
    scoped_key = f"user:{owner_id}:{key}"
    try:
        raw = await _redis.get(scoped_key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    owner_id = get_current_user_id()
    if _redis is None or not owner_id:
        return
    scoped_key = f"user:{owner_id}:{key}"
    try:
        await _redis.setex(scoped_key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


# ── In-Memory Ring Buffer & Persistence Helpers ────────────────────────────────

_HISTORY_MAX = 2000
_telemetry_history: dict[str, list[dict]] = {}


def record_telemetry(entry: dict) -> None:
    """Store telemetry in the authenticated user's in-memory ring buffer."""
    owner_id = get_current_user_id()
    if not owner_id:
        return
    if "recorded_at" not in entry:
        entry["recorded_at"] = datetime.now(timezone.utc).isoformat()
    history = _telemetry_history.setdefault(owner_id, [])
    history.append(dict(entry))
    if len(history) > _HISTORY_MAX:
        del history[:-_HISTORY_MAX]


def get_telemetry_history(limit: int = 100) -> list[dict]:
    """Retrieve telemetry only from the authenticated user's ring buffer."""
    owner_id = get_current_user_id()
    if not owner_id:
        return []
    return list(reversed(_telemetry_history.get(owner_id, [])[-limit:]))


async def persist_telemetry_entry(entry: dict) -> None:
    """Persist telemetry reading to database, updating in-memory cache as well."""
    record_telemetry(entry)
    owner_id = get_current_user_id()
    if not owner_id:
        return
    try:
        async with _async_session_maker() as session:
            record = TelemetryRecord(
                owner_id=owner_id,
                timestamp=entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                provider=entry.get("provider", "aws"),
                region=entry.get("region", "us-east"),
                account_id=entry.get("account_id"),
                resource_id=entry.get("resource_id"),
                resource_type=entry.get("resource_type", "instance"),
                source=entry.get("source", "DEMO"),
                cpu=float(entry.get("cpu", 0.0)),
                memory=float(entry["memory"]) if entry.get("memory") is not None else None,
                storage=float(entry["storage"]) if entry.get("storage") is not None else None,
                network=float(entry["network"]) if entry.get("network") is not None else None,
                network_in=float(entry["network_in"]) if entry.get("network_in") is not None else None,
                network_out=float(entry["network_out"]) if entry.get("network_out") is not None else None,
                cost_per_hour=float(entry.get("cost_usd_per_hour", 0.0)),
                carbon_intensity=float(entry.get("carbon_gco2_per_hour", 0.0)),
                status=entry.get("status", "running"),
                memory_source=entry.get("memory_source", "DEMO"),
                memory_note=entry.get("memory_note"),
            )
            session.add(record)
            await session.commit()
    except Exception as exc:
        logger.warning("Unable to persist telemetry entry (%s)", type(exc).__name__)


async def query_telemetry_history(
    limit: int = 100,
    provider: str | None = None,
    region: str | None = None,
    bucket_seconds: int | None = None,
) -> list[dict]:
    """Query owner-scoped history, optionally returning the newest row per time bucket."""
    owner_id = get_current_user_id()
    if not owner_id:
        return []

    filters = [TelemetryRecord.owner_id == owner_id]
    if provider:
        filters.append(TelemetryRecord.provider == provider.lower())
    if region:
        filters.append(TelemetryRecord.region == region.lower())

    if bucket_seconds and bucket_seconds > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=bucket_seconds * limit)
        filters.append(TelemetryRecord.recorded_at >= cutoff)

    try:
        async with _async_session_maker() as session:
            if bucket_seconds and bucket_seconds > 0 and _engine.dialect.name in {"sqlite", "postgresql"}:
                if _engine.dialect.name == "sqlite":
                    epoch_seconds = cast(func.strftime("%s", TelemetryRecord.recorded_at), Float)
                else:
                    epoch_seconds = func.extract("epoch", TelemetryRecord.recorded_at)
                bucket = func.floor(epoch_seconds / bucket_seconds)
                ranked = (
                    select(
                        TelemetryRecord.id.label("record_id"),
                        bucket.label("bucket"),
                        func.row_number().over(
                            partition_by=bucket,
                            order_by=TelemetryRecord.id.desc(),
                        ).label("row_number"),
                    )
                    .where(*filters)
                    .subquery()
                )
                stmt = (
                    select(TelemetryRecord)
                    .join(ranked, TelemetryRecord.id == ranked.c.record_id)
                    .where(ranked.c.row_number == 1)
                    .order_by(ranked.c.bucket.desc())
                    .limit(limit)
                )
            else:
                stmt = (
                    select(TelemetryRecord)
                    .where(*filters)
                    .order_by(TelemetryRecord.id.desc())
                    .limit(limit)
                )

            result = await session.execute(stmt)
            records = result.scalars().all()
            if records:
                return [record.to_dict() for record in records]
    except Exception as exc:
        logger.warning("Unable to query telemetry history (%s)", type(exc).__name__)

    entries = get_telemetry_history(_HISTORY_MAX)
    if provider:
        entries = [entry for entry in entries if entry.get("provider", "").lower() == provider.lower()]
    if region:
        entries = [entry for entry in entries if entry.get("region", "").lower() == region.lower()]

    if bucket_seconds and bucket_seconds > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=bucket_seconds * limit)
        sampled: list[dict] = []
        seen_buckets: set[int] = set()
        for entry in entries:
            raw_timestamp = entry.get("recorded_at") or entry.get("timestamp")
            try:
                timestamp = raw_timestamp if isinstance(raw_timestamp, datetime) else datetime.fromisoformat(
                    str(raw_timestamp).replace("Z", "+00:00")
                )
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                continue
            if timestamp < cutoff:
                continue
            bucket_id = int(timestamp.timestamp() // bucket_seconds)
            if bucket_id in seen_buckets:
                continue
            seen_buckets.add(bucket_id)
            sampled.append(entry)
            if len(sampled) >= limit:
                break
        return sampled

    return entries[:limit]


async def persist_prediction_entry(
    target: str,
    current_value: float,
    predicted_value: float,
    delta_pct: float,
    anomaly: bool = False,
    confidence: float = 0.85,
    horizon_minutes: int = 60,
) -> None:
    """Persist ML model prediction record to database."""
    owner_id = get_current_user_id()
    if not owner_id:
        return
    try:
        async with _async_session_maker() as session:
            rec = PredictionRecord(
                owner_id=owner_id,
                target=target,
                current_value=current_value,
                predicted_value=predicted_value,
                delta_pct=delta_pct,
                anomaly=anomaly,
                confidence=confidence,
                horizon_minutes=horizon_minutes,
            )
            session.add(rec)
            await session.commit()
    except Exception:
        pass


async def persist_recommendation_entry(rec_data: dict) -> None:
    """Persist recommendation to database."""
    owner_id = get_current_user_id()
    if not owner_id:
        return
    try:
        async with _async_session_maker() as session:
            rec = RecommendationRecord(
                owner_id=owner_id,
                id=rec_data["id"],
                category=rec_data.get("category", "cost"),
                priority=rec_data.get("priority", "medium"),
                title=rec_data.get("title", ""),
                description=rec_data.get("description", ""),
                impact_summary=rec_data.get("impact_summary", ""),
                estimated_monthly_savings_usd=float(rec_data.get("estimated_monthly_savings_usd", 0.0)),
                estimated_carbon_reduction_pct=float(rec_data.get("estimated_carbon_reduction_pct", 0.0)),
                effort=rec_data.get("effort", "medium"),
                action=rec_data.get("action", ""),
                evidence_json=json.dumps(rec_data.get("evidence", [])),
                confidence=float(rec_data.get("confidence", 0.85)),
                status=rec_data.get("status", "open"),
            )
            session.add(rec)
            await session.commit()
    except Exception:
        pass


async def persist_agent_result_entry(
    run_id: str,
    agent_name: str,
    score: int,
    findings: list,
    recommendations_count: int = 0,
) -> None:
    """Persist agent run outcome to database."""
    owner_id = get_current_user_id()
    if not owner_id:
        return
    try:
        async with _async_session_maker() as session:
            rec = AgentResultRecord(
                owner_id=owner_id,
                run_id=run_id,
                agent_name=agent_name,
                score=score,
                findings_json=json.dumps(findings),
                recommendations_count=recommendations_count,
            )
            session.add(rec)
            await session.commit()
    except Exception:
        pass


async def persist_simulation_entry(
    sim_id: str,
    changes: dict,
    before: dict,
    after: dict,
    delta: dict,
    risk_score: float,
    recommendation: str,
    confidence: float = 0.8,
) -> None:
    """Persist Digital Twin simulation result to database."""
    owner_id = get_current_user_id()
    if not owner_id:
        return
    try:
        async with _async_session_maker() as session:
            rec = SimulationRecord(
                owner_id=owner_id,
                id=sim_id,
                changes_json=json.dumps(changes),
                before_json=json.dumps(before),
                after_json=json.dumps(after),
                delta_json=json.dumps(delta),
                risk_score=risk_score,
                recommendation=recommendation,
                confidence=confidence,
            )
            session.add(rec)
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
    owner_id = get_current_user_id()
    if not owner_id:
        raise RuntimeError("Audit log persistence requires an authenticated user.")
    try:
        async with _async_session_maker() as session:
            log = AuditLogRecord(
                owner_id=owner_id,
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
        logger.exception("Unable to persist audit log entry")
        raise
