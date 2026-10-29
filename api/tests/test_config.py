import pytest

from app.config import Settings


def test_defaults_and_production_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DOWNLOAD_TOKEN_SECRET", raising=False)
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    settings = Settings.from_env()
    assert settings.cors_origins == ("https://baixa.nataliagranato.xyz",)
    assert settings.sentry_dsn is None
    assert settings.max_file_bytes == 100 * 1024 * 1024

    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        Settings.from_env()

    monkeypatch.setenv("DOWNLOAD_TOKEN_SECRET", "real-secret")
    monkeypatch.setenv("CORS_ORIGINS", "https://baixa.nataliagranato.xyz, http://localhost:3000")
    monkeypatch.setenv("SENTRY_DSN", "https://public@sentry.example/1")
    settings = Settings.from_env()
    assert settings.token_secret == "real-secret"
    assert settings.cors_origins == (
        "https://baixa.nataliagranato.xyz",
        "http://localhost:3000",
    )
    assert settings.sentry_dsn == "https://public@sentry.example/1"


def test_sentry_sdk_starts_only_when_dsn_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    import sentry_sdk

    from app.main import create_app

    calls: list[dict] = []

    def init(*args: object, **kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", init)
    create_app(Settings(sentry_dsn=None))
    assert calls == []
    create_app(Settings(sentry_dsn="https://public@sentry.example/1", sentry_environment="test"))
    assert calls[0]["dsn"] == "https://public@sentry.example/1"
    assert calls[0]["send_default_pii"] is False
    assert calls[0]["traces_sample_rate"] == 0.0
    assert calls[0]["environment"] == "test"
