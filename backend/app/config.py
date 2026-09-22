"""
Application configuration — all settings sourced from environment variables
with sensible defaults for demo/dev mode. Override via .env file or shell env.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "GreenMind AI"
    app_version: str = "2.0.0"
    debug: bool = False
    demo_mode: bool = True  # False → try real cloud provider APIs

    # ── Database (optional — falls back to in-memory if not set) ─────────────
    database_url: str = ""         # e.g. postgresql+asyncpg://user:pass@localhost/greenmind
    redis_url: str = ""            # e.g. redis://localhost:6379/0

    # ── ML ───────────────────────────────────────────────────────────────────
    model_retrain_on_startup: bool = False

    # ── Cloud Providers (leave blank for DEMO mode) ───────────────────────────
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_default_region: str = "us-east-1"

    azure_subscription_id: str = ""
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    gcp_project_id: str = ""
    gcp_service_account_json: str = ""

    # ── LLM (optional — Copilot uses rule-based engine if not set) ───────────
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # ── Carbon API (optional) ─────────────────────────────────────────────────
    electricity_maps_api_key: str = ""
    watttime_username: str = ""
    watttime_password: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
