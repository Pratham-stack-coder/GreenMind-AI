"""
Database layer — async SQLAlchemy + optional Redis.
Gracefully degrades to in-memory storage when no DATABASE_URL / REDIS_URL is configured.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from .config import get_settings

settings = get_settings()

# ── SQLAlchemy (optional) ─────────────────────────────────────────────────────
_async_session_maker = None
_engine = None

if settings.database_url:
    try:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

        _engine = create_async_engine(settings.database_url, echo=settings.debug)
        _async_session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    except Exception:
        pass  # DB optional


async def get_db():
    """FastAPI dependency — yields an async DB session or None in demo mode."""
    if _async_session_maker is None:
        yield None
        return
    async with _async_session_maker() as session:
        yield session


# ── Redis (optional) ─────────────────────────────────────────────────────────
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
    raw = await _redis.get(key)
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, ttl: int = 30) -> None:
    if _redis is None:
        return
    await _redis.setex(key, ttl, json.dumps(value, default=str))


# ── In-memory telemetry ring buffer (demo mode) ───────────────────────────────
_HISTORY_MAX = 2000  # keep last ~500h of 15-min readings
_telemetry_history: list[dict] = []


def record_telemetry(entry: dict) -> None:
    global _telemetry_history
    entry["recorded_at"] = datetime.utcnow().isoformat()
    _telemetry_history.append(entry)
    if len(_telemetry_history) > _HISTORY_MAX:
        _telemetry_history = _telemetry_history[-_HISTORY_MAX:]


def get_telemetry_history(limit: int = 100) -> list[dict]:
    return list(reversed(_telemetry_history[-limit:]))
