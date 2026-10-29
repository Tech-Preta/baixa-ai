"""Environment-backed settings. Secrets stay out of the image."""

import os
from dataclasses import dataclass

_DEV_SECRET = "dev-only-change-me"
_DEFAULT_ORIGIN = "https://baixa.nataliagranato.xyz"


def _csv(name: str, default: str) -> tuple[str, ...]:
    raw = os.environ.get(name, default)
    values = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not values:
        raise RuntimeError(f"{name} must include at least one value")
    return values


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc


def _float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    cors_origins: tuple[str, ...] = (_DEFAULT_ORIGIN,)
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 600
    extract_timeout_seconds: float = 30
    download_timeout_seconds: float = 120
    max_file_bytes: int = 100 * 1024 * 1024
    token_secret: str = _DEV_SECRET
    token_ttl_seconds: int = 600
    sentry_dsn: str | None = None
    sentry_environment: str | None = None
    trust_proxy: bool = True
    cache_ttl_seconds: float = 180
    max_extract_entries: int = 20

    @classmethod
    def from_env(cls) -> "Settings":
        app_env = os.environ.get("APP_ENV", "development").strip().lower()
        secret = os.environ.get("DOWNLOAD_TOKEN_SECRET", "").strip()
        if app_env == "production" and secret in {"", _DEV_SECRET}:
            raise RuntimeError("DOWNLOAD_TOKEN_SECRET is required when APP_ENV=production")
        dsn = os.environ.get("SENTRY_DSN", "").strip()
        environment = os.environ.get("SENTRY_ENVIRONMENT", "").strip()
        return cls(
            cors_origins=_csv("CORS_ORIGINS", _DEFAULT_ORIGIN),
            rate_limit_requests=_int("RATE_LIMIT_REQUESTS", 60),
            rate_limit_window_seconds=_int("RATE_LIMIT_WINDOW_SECONDS", 600),
            extract_timeout_seconds=_float("EXTRACT_TIMEOUT_SECONDS", 30),
            download_timeout_seconds=_float("DOWNLOAD_TIMEOUT_SECONDS", 120),
            max_file_bytes=_int("MAX_FILE_BYTES", 100 * 1024 * 1024),
            token_secret=secret or _DEV_SECRET,
            token_ttl_seconds=_int("TOKEN_TTL_SECONDS", 600),
            sentry_dsn=dsn or None,
            sentry_environment=environment or None,
            trust_proxy=_bool("TRUST_PROXY", True),
            cache_ttl_seconds=_float("CACHE_TTL_SECONDS", 180),
            max_extract_entries=_int("MAX_EXTRACT_ENTRIES", 20),
        )
