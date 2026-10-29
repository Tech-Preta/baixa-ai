"""HTTP API: validate a public link, list files, stream them through."""

import asyncio
import socket
import time
from collections.abc import AsyncIterator, Callable
from urllib.parse import quote, urlsplit

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.cache import ResultCache
from app.config import Settings
from app.errors import MSG_INVALID, MSG_OPTION, MSG_RATE, MSG_TIMEOUT, MSG_TOKEN, AppError
from app.media import EXT_CONTENT_TYPES, ExtractedMedia, MediaItem, extract_media
from app.ratelimit import RateLimiter
from app.streaming import open_remote
from app.tokens import sign_token, verify_token
from app.urls import validate_media_url
from app.ytdlp_runner import run_ytdlp


class ExtractRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)


def create_app(
    settings: Settings | None = None,
    *,
    clock: Callable[[], float] = time.monotonic,
    time_fn: Callable[[], float] = time.time,
    runner: Callable[[str, float], dict] | None = None,
    client_factory: Callable[[float], httpx.AsyncClient] | None = None,
    resolve: Callable | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    _init_sentry(settings)
    app = FastAPI(title="Baixa.ai", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    app.state.limiter = RateLimiter(
        limit=settings.rate_limit_requests,
        window_seconds=settings.rate_limit_window_seconds,
        clock=clock,
    )
    app.state.cache = ResultCache(ttl_seconds=settings.cache_ttl_seconds, clock=clock)
    app.state.time_fn = time_fn
    app.state.runner = runner or run_ytdlp
    app.state.client_factory = client_factory or _default_client_factory
    app.state.resolve = resolve

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
        allow_credentials=False,
        max_age=600,
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "message": exc.message},
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, _exc: RequestValidationError) -> JSONResponse:
        if request.url.path in {"/api/download", "/api/thumbnail"}:
            return JSONResponse(
                status_code=400,
                content={"error": "invalid_token", "message": MSG_TOKEN},
            )
        return JSONResponse(
            status_code=400,
            content={"error": "invalid_url", "message": MSG_INVALID},
        )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/extract")
    async def extract(body: ExtractRequest, request: Request) -> dict:
        _enforce_rate_limit(request)
        parsed = validate_media_url(body.url)
        media = await _get_or_extract(request, parsed.url, parsed.provider)
        return _present(media, request)

    @app.get("/api/download")
    async def download(token: str, request: Request) -> StreamingResponse:
        _enforce_rate_limit(request)
        payload = verify_token(
            token,
            request.app.state.settings.token_secret,
            request.app.state.time_fn(),
        )
        if payload.get("kind") != "file":
            raise AppError("invalid_token", MSG_TOKEN, 400)
        media = await _get_or_extract(request, str(payload.get("url", "")))
        item = _find_item(media, payload.get("index"), str(payload.get("format_id", "")))
        if item is None:
            raise AppError("not_found", MSG_OPTION, 404)
        filename = _filename(media.provider, item.index, item.ext)
        return await _proxy(
            request,
            item.url,
            item.headers,
            content_type=_content_type(item.ext),
            disposition=f'attachment; filename="{filename}"',
        )

    @app.get("/api/thumbnail")
    async def thumbnail(token: str, request: Request) -> StreamingResponse:
        _enforce_rate_limit(request)
        payload = verify_token(
            token,
            request.app.state.settings.token_secret,
            request.app.state.time_fn(),
        )
        if payload.get("kind") != "thumb":
            raise AppError("invalid_token", MSG_TOKEN, 400)
        media = await _get_or_extract(request, str(payload.get("url", "")))
        if not media.thumbnail_url:
            raise AppError("not_found", MSG_OPTION, 404)
        ext = _ext_from_url(media.thumbnail_url)
        return await _proxy(
            request,
            media.thumbnail_url,
            {},
            content_type=_content_type(ext),
            disposition="inline",
        )

    return app


def _init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    import sentry_sdk

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.0,
        send_default_pii=False,
        environment=settings.sentry_environment,
    )


def _default_client_factory(timeout: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout, connect=min(10.0, timeout)),
        follow_redirects=False,
        trust_env=False,
    )


def _enforce_rate_limit(request: Request) -> None:
    decision = request.app.state.limiter.check(_client_ip(request))
    if not decision.allowed:
        raise AppError(
            "rate_limited",
            MSG_RATE,
            429,
            headers={"Retry-After": str(decision.retry_after)},
        )


def _client_ip(request: Request) -> str:
    if request.app.state.settings.trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "")
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if parts:
            return parts[-1]
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


async def _get_or_extract(
    request: Request,
    url: str,
    provider: str | None = None,
) -> ExtractedMedia:
    parsed = validate_media_url(url)
    if provider is not None and parsed.provider != provider:
        raise AppError("invalid_url", MSG_INVALID, 400)
    cached = request.app.state.cache.get(parsed.url)
    if cached is not None:
        return cached
    settings: Settings = request.app.state.settings
    try:
        media = await asyncio.wait_for(
            asyncio.to_thread(
                extract_media,
                parsed.url,
                provider=parsed.provider,
                timeout=settings.extract_timeout_seconds,
                max_file_bytes=settings.max_file_bytes,
                max_items=settings.max_extract_entries,
                runner=request.app.state.runner,
            ),
            timeout=settings.extract_timeout_seconds + 1,
        )
    except TimeoutError as exc:
        raise AppError("timeout", MSG_TIMEOUT, 504) from exc
    request.app.state.cache.set(parsed.url, media)
    return media


def _present(media: ExtractedMedia, request: Request) -> dict:
    settings: Settings = request.app.state.settings
    expires = int(request.app.state.time_fn()) + settings.token_ttl_seconds
    items = []
    for item in media.items:
        token = sign_token(
            _token_payload(media.page_url, "file", item.index, item.format_id, expires),
            settings.token_secret,
        )
        items.append(
            {
                "index": item.index,
                "type": item.type,
                "ext": item.ext,
                "label": item.label,
                "filesize": item.filesize,
                "download_path": f"/api/download?token={quote(token, safe='')}",
            }
        )
    thumbnail_path = None
    if media.thumbnail_url:
        token = sign_token(
            _token_payload(media.page_url, "thumb", 0, "", expires),
            settings.token_secret,
        )
        thumbnail_path = f"/api/thumbnail?token={quote(token, safe='')}"
    return {
        "provider": media.provider,
        "title": media.title,
        "author": media.author,
        "thumbnail_path": thumbnail_path,
        "items": items,
    }


def _token_payload(url: str, kind: str, index: int, format_id: str, expires: int) -> dict:
    return {"url": url, "kind": kind, "index": index, "format_id": format_id, "exp": expires}


def _find_item(media: ExtractedMedia, index: object, format_id: str) -> MediaItem | None:
    if not isinstance(index, int):
        return None
    for item in media.items:
        if item.index == index and item.format_id == format_id:
            return item
    return None


async def _proxy(
    request: Request,
    url: str,
    headers: dict[str, str],
    *,
    content_type: str,
    disposition: str,
) -> StreamingResponse:
    settings: Settings = request.app.state.settings
    client = request.app.state.client_factory(settings.download_timeout_seconds)
    try:
        opened = await open_remote(
            url,
            headers=headers,
            max_bytes=settings.max_file_bytes,
            client=client,
            resolve=request.app.state.resolve or socket.getaddrinfo,
        )
    except Exception:
        await client.aclose()
        raise

    async def body() -> AsyncIterator[bytes]:
        try:
            async for chunk in opened.iter_capped(settings.max_file_bytes):
                yield chunk
        finally:
            await client.aclose()

    response_headers = {"Content-Disposition": disposition}
    if opened.content_length is not None:
        response_headers["Content-Length"] = str(opened.content_length)
    return StreamingResponse(body(), media_type=content_type, headers=response_headers)


def _content_type(ext: str) -> str:
    return EXT_CONTENT_TYPES.get(ext.lower(), "application/octet-stream")


def _filename(provider: str, index: int, ext: str) -> str:
    safe_ext = "jpg" if ext.lower() == "jpeg" else ext.lower()
    if safe_ext not in EXT_CONTENT_TYPES and safe_ext != "jpg":
        safe_ext = "bin"
    safe_provider = provider if provider in {"instagram", "tiktok", "x"} else "media"
    return f"baixa-{safe_provider}-{index + 1}.{safe_ext}"


def _ext_from_url(url: str) -> str:
    path = urlsplit(url).path.lower()
    for ext in ("jpeg", "jpg", "png", "webp", "gif", "mp4", "webm", "mov"):
        if path.endswith("." + ext):
            return "jpg" if ext == "jpeg" else ext
    return "jpg"


app = create_app()
