from pathlib import Path

import pytest

from config import Settings


def test_missing_environment_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "SUPABASE_URL",
        "SUPABASE_SECRET_KEY",
        "REDIS_URL",
        "MODEL_ROOT",
        "ALLOWED_ORIGINS",
        "ENVIRONMENT",
        "LOG_LEVEL",
        "RQ_JOB_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)

    with pytest.raises(RuntimeError, match="Missing required environment"):
        Settings.from_environment()


def test_production_origin_is_exact(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "s" * 32)
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("MODEL_ROOT", str(Path.cwd() / "Models"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://preview.vercel.app")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("RQ_JOB_TIMEOUT", "1800")

    with pytest.raises(RuntimeError, match="must be exactly"):
        Settings.from_environment()


def test_development_accepts_legacy_service_role_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "s" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("MODEL_ROOT", str(Path.cwd() / "Models"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://emathtoco.vercel.app")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("RQ_JOB_TIMEOUT", "1800")

    settings = Settings.from_environment()

    assert settings.supabase_secret_key == "s" * 32


def test_production_rejects_legacy_service_role_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SUPABASE_SECRET_KEY", raising=False)
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "s" * 32)
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")
    monkeypatch.setenv("MODEL_ROOT", str(Path.cwd() / "Models"))
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://emathtoco.vercel.app")
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    monkeypatch.setenv("RQ_JOB_TIMEOUT", "1800")

    with pytest.raises(RuntimeError, match="SUPABASE_SECRET_KEY"):
        Settings.from_environment()
