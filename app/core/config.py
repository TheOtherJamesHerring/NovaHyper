"""
app/core/config.py
------------------
All configuration is read from environment variables (12-factor).
In development, values come from a .env file at the project root.
In production, inject via K3s secrets / ConfigMap.
"""
from functools import lru_cache
from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ────────────────────────────────────────────────────────────────
    APP_NAME: str = "NovaHyper API"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"      # development | staging | production
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Security ───────────────────────────────────────────────────────────
    SECRET_KEY: str                        # Must be set in env — no default
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: PostgresDsn              # postgresql+asyncpg://user:pass@host/db
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_ECHO: bool = False                  # Set True to log all SQL (dev only)

    # ── NATS ───────────────────────────────────────────────────────────────
    NATS_URL: str = "nats://localhost:4222"
    NATS_STREAM_BACKUP: str = "backup-jobs"
    NATS_STREAM_ALERTS: str  = "alerts"

    # ── libvirt ────────────────────────────────────────────────────────────
    LIBVIRT_URI: str = "qemu:///system"    # Override with test:///default in dev

    # ── Dedup store ────────────────────────────────────────────────────────
    DEDUP_STORE_PATH: str = "/var/lib/novahyper/chunks"
    DEDUP_TARGET_CHUNK_SIZE: int = 4096    # bytes — Rabin fingerprint target
    DEDUP_MIN_CHUNK_SIZE: int = 1024
    DEDUP_MAX_CHUNK_SIZE: int = 65536

    # ── Prometheus ─────────────────────────────────────────────────────────
    METRICS_ENABLED: bool = True

    # ── First-run MSP admin bootstrap ─────────────────────────────────────
    BOOTSTRAP_ADMIN_EMAIL: str = ""
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg_scheme(cls, v: str) -> str:
        """Ensure the URL uses the asyncpg driver."""
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
