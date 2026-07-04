from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator


class Settings(BaseModel):
    supabase_url: HttpUrl
    supabase_secret_key: str = Field(min_length=20)
    redis_url: str = Field(pattern=r"^rediss?://")
    model_root: Path
    allowed_origins: tuple[str, ...]
    environment: str = Field(pattern=r"^(development|test|production)$")
    log_level: str = Field(pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    rq_job_timeout: int = Field(ge=60, le=7200)

    @field_validator("allowed_origins")
    @classmethod
    def validate_origins(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("at least one allowed origin is required")
        if "*" in value:
            raise ValueError("wildcard CORS origins are forbidden")
        for origin in value:
            if not origin.startswith(("http://localhost:", "http://127.0.0.1:", "https://")):
                raise ValueError(f"invalid CORS origin: {origin}")
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @classmethod
    def from_environment(cls) -> "Settings":
        environment = os.getenv("ENVIRONMENT", "").lower()
        supabase_secret_key = os.getenv("SUPABASE_SECRET_KEY")
        if not supabase_secret_key and environment != "production":
            # Temporary local compatibility for the existing developer .env.
            # Production always requires the new SUPABASE_SECRET_KEY name.
            supabase_secret_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        required = {
            "SUPABASE_URL": os.getenv("SUPABASE_URL"),
            "SUPABASE_SECRET_KEY": supabase_secret_key,
            "REDIS_URL": os.getenv("REDIS_URL"),
            "MODEL_ROOT": os.getenv("MODEL_ROOT"),
            "ALLOWED_ORIGINS": os.getenv("ALLOWED_ORIGINS"),
            "ENVIRONMENT": environment,
            "LOG_LEVEL": os.getenv("LOG_LEVEL"),
            "RQ_JOB_TIMEOUT": os.getenv("RQ_JOB_TIMEOUT"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing required environment variables: " + ", ".join(missing)
            )

        origins = tuple(
            origin.strip()
            for origin in os.environ["ALLOWED_ORIGINS"].split(",")
            if origin.strip()
        )
        try:
            settings = cls(
                supabase_url=os.environ["SUPABASE_URL"],
                supabase_secret_key=supabase_secret_key,
                redis_url=os.environ["REDIS_URL"],
                model_root=Path(os.environ["MODEL_ROOT"]).expanduser().resolve(),
                allowed_origins=origins,
                environment=environment,
                log_level=os.environ["LOG_LEVEL"].upper(),
                rq_job_timeout=int(os.environ["RQ_JOB_TIMEOUT"]),
            )
        except (ValueError, ValidationError) as exc:
            raise RuntimeError(f"Invalid application configuration: {exc}") from exc

        if settings.is_production and settings.allowed_origins != (
            "https://emathtoco.vercel.app",
        ):
            raise RuntimeError(
                "Production ALLOWED_ORIGINS must be exactly "
                "https://emathtoco.vercel.app"
            )
        return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()
