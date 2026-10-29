import httpx
import pytest
import yt_dlp
from fastapi.testclient import TestClient

from app.config import Settings
from app.errors import MSG_GENERIC, MSG_PRIVATE, MSG_RATE, MSG_UNSUPPORTED
from app.main import create_app

IG = "https://www.instagram.com/reel/AbC123/"
ORIGIN = "https://baixa.nataliagranato.xyz"


def _info() -> dict:
    return {
        "title": "Um reel",
        "uploader": "maria",
        "thumbnail": "https://cdn.example/thumb.jpg",
        "formats": [
            {
                "format_id": "hd",
                "ext": "mp4",
                "protocol": "https",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "height": 720,
                "filesize": 4000,
                "url": "https://cdn.example/720.mp4",
                "http_headers": {"User-Agent": "Baixa", "Cookie": "session=nope"},
            }
        ],
    }


def _settings(**overrides: object) -> Settings:
    data: dict[str, object] = {
        "cors_origins": (ORIGIN,),
        "rate_limit_requests": 10,
        "rate_limit_window_seconds": 60,
        "extract_timeout_seconds": 5,
        "download_timeout_seconds": 5,
        "max_file_bytes": 100_000,
        "token_secret": "test-secret",
        "token_ttl_seconds": 600,
        "trust_proxy": True,
        "cache_ttl_seconds": 60,
    }
    data.update(overrides)
    return Settings(**data)  # type: ignore[arg-type]


def _public_resolve(host: str, port: int, *args: object, **kwargs: object) -> list:
    return [(2, 1, 6, "", ("1.1.1.1", port))]


@pytest.fixture
def calls() -> dict:
    return {"n": 0}


def _app(runner, calls: dict, **setting_overrides: object):
    def wrapped(url: str, timeout: float) -> dict:
        calls["n"] += 1
        result = runner(url, timeout)
        if isinstance(result, Exception):
            raise result
        return result

    def factory(timeout: float) -> httpx.AsyncClient:
        def handler(request: httpx.Request) -> httpx.Response:
            assert "cookie" not in {name.lower() for name in request.headers}
            if request.url.path.endswith(".jpg"):
                return httpx.Response(200, content=b"img", headers={"content-type": "image/jpeg"})
            assert request.headers["user-agent"] == "Baixa"
            return httpx.Response(200, content=b"videobytes", headers={"content-type": "video/mp4"})

        return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=timeout)

    return create_app(
        _settings(**setting_overrides),
        runner=wrapped,
        client_factory=factory,
        resolve=_public_resolve,
        time_fn=lambda: 1_700_000_000,
    )


def test_healthz_is_open_and_does_not_spend_rate_limit(calls: dict) -> None:
    app = _app(lambda url, timeout: _info(), calls, rate_limit_requests=1)
    client = TestClient(app)
    for _ in range(3):
        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
    extracted = client.post("/api/extract", json={"url": IG})
    assert extracted.status_code == 200
    blocked = client.post("/api/extract", json={"url": IG})
    assert blocked.status_code == 429


def test_rejects_foreign_hosts_without_calling_the_extractor(calls: dict) -> None:
    client = TestClient(_app(lambda url, timeout: _info(), calls))
    response = client.post("/api/extract", json={"url": "https://youtube.com/watch?v=abc"})
    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_host"
    assert calls["n"] == 0


def test_private_unsupported_timeout_and_hidden_internal_errors(calls: dict) -> None:
    private = TestClient(
        _app(lambda url, timeout: yt_dlp.utils.DownloadError("ERROR: Private video"), calls)
    )
    response = private.post("/api/extract", json={"url": IG})
    assert response.status_code == 422
    assert response.json() == {"error": "private_content", "message": MSG_PRIVATE}
    assert "Private video" not in response.text

    unsupported = TestClient(
        _app(lambda url, timeout: yt_dlp.utils.UnsupportedError("Unsupported URL"), calls)
    )
    response = unsupported.post("/api/extract", json={"url": IG})
    assert response.status_code == 422
    assert response.json()["message"] == MSG_UNSUPPORTED

    timeout = TestClient(_app(lambda url, timeout: TimeoutError(), calls))
    response = timeout.post("/api/extract", json={"url": IG})
    assert response.status_code == 504
    assert response.json()["error"] == "timeout"

    generic = TestClient(_app(lambda url, timeout: RuntimeError("secret internal boom"), calls))
    response = generic.post("/api/extract", json={"url": IG})
    assert response.status_code == 502
    assert response.json()["message"] == MSG_GENERIC
    assert "boom" not in response.text


def test_extract_returns_download_options_without_leaking_cdn_urls(calls: dict) -> None:
    client = TestClient(_app(lambda url, timeout: _info(), calls))
    response = client.post(
        "/api/extract",
        json={"url": IG},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ORIGIN
    body = response.json()
    assert body["provider"] == "instagram"
    assert body["title"] == "Um reel"
    assert body["author"] == "maria"
    assert body["thumbnail_path"].startswith("/api/thumbnail?token=")
    assert body["items"][0]["label"] == "Vídeo · 720p"
    assert body["items"][0]["download_path"].startswith("/api/download?token=")
    assert "cdn.example" not in response.text

    downloaded = client.get(body["items"][0]["download_path"])
    assert downloaded.status_code == 200
    assert downloaded.content == b"videobytes"
    assert downloaded.headers["content-type"].startswith("video/mp4")
    disposition = downloaded.headers["content-disposition"]
    assert disposition.startswith("attachment;")
    assert "baixa-instagram-1.mp4" in disposition

    thumb = client.get(body["thumbnail_path"])
    assert thumb.status_code == 200
    assert thumb.content == b"img"
    assert calls["n"] == 1


def test_rate_limit_uses_the_proxy_client_ip(calls: dict) -> None:
    now = {"t": 0.0}
    app = _app(
        lambda url, timeout: _info(),
        calls,
        rate_limit_requests=2,
        rate_limit_window_seconds=10,
    )
    app.state.limiter.clock = lambda: now["t"]
    client = TestClient(app)
    headers_a = {"X-Forwarded-For": "198.51.100.1, 203.0.113.5"}
    headers_b = {"X-Forwarded-For": "203.0.113.9"}

    assert client.post("/api/extract", json={"url": IG}, headers=headers_a).status_code == 200
    assert client.post("/api/extract", json={"url": IG}, headers=headers_a).status_code == 200
    blocked = client.post("/api/extract", json={"url": IG}, headers=headers_a)
    assert blocked.status_code == 429
    assert blocked.json()["message"] == MSG_RATE
    assert int(blocked.headers["retry-after"]) >= 1
    assert client.post("/api/extract", json={"url": IG}, headers=headers_b).status_code == 200

    now["t"] = 10.0
    assert client.post("/api/extract", json={"url": IG}, headers=headers_a).status_code == 200


def test_cors_is_limited_to_configured_origins(calls: dict) -> None:
    client = TestClient(_app(lambda url, timeout: _info(), calls))
    allowed = client.options(
        "/api/extract",
        headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    assert allowed.headers["access-control-allow-origin"] == ORIGIN
    denied = client.post(
        "/api/extract",
        json={"url": "https://example.com/a"},
        headers={"Origin": "https://evil.test"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_invalid_download_token(calls: dict) -> None:
    client = TestClient(_app(lambda url, timeout: _info(), calls))
    response = client.get("/api/download?token=not-a-token")
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_token"
    assert calls["n"] == 0
