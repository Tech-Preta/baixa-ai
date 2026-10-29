"""Allowlist and shape checks for public media URLs."""

import ipaddress
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit, urlunsplit

from app.errors import MSG_HOST, MSG_INVALID, MSG_UNSUPPORTED, AppError

_PROVIDERS = (
    ("youtube.com", "youtube"),
    ("youtu.be", "youtube"),
    ("instagram.com", "instagram"),
    ("tiktok.com", "tiktok"),
    ("x.com", "x"),
    ("twitter.com", "x"),
)
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_YOUTUBE_MEDIA_PATH = re.compile(r"^/(?:shorts|embed|v)/([A-Za-z0-9_-]{11})/?$", re.IGNORECASE)

_SHORT_TIKTOK_HOSTS = {"vm.tiktok.com", "vt.tiktok.com"}

_INSTAGRAM_PATH = re.compile(
    r"^/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+/?$"
    r"|^/stories/[^/]+/\d+/?$"
    r"|^/share/(?:p|reel|reels|tv)/[A-Za-z0-9_-]+/?$",
    re.IGNORECASE,
)
_TIKTOK_PATH = re.compile(
    r"^/@[^/]+/(?:video|photo)/\d+/?$"
    r"|^/t/[A-Za-z0-9]+/?$"
    r"|^/embed/v2/\d+/?$",
    re.IGNORECASE,
)
_TIKTOK_SHORT_PATH = re.compile(r"^/[A-Za-z0-9]+/?$")
_X_PATH = re.compile(
    r"^/(?:[^/]+/status(?:es)?|i/status)/\d+(?:/(?:photo|video)/\d+)?/?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedMediaUrl:
    url: str
    provider: str
    host: str


def validate_media_url(raw: str) -> ParsedMediaUrl:
    if not isinstance(raw, str):
        raise AppError("invalid_url", MSG_INVALID, 400)
    text = raw.strip().strip("\"'“”")
    if not text or any(char in text for char in ("\n", "\r", "\t", " ")):
        raise AppError("invalid_url", MSG_INVALID, 400)

    parts = urlsplit(text)
    if parts.scheme.lower() not in {"http", "https"}:
        raise AppError("invalid_url", MSG_INVALID, 400)
    if parts.username or parts.password:
        raise AppError("invalid_url", MSG_INVALID, 400)
    host = (parts.hostname or "").lower().rstrip(".")
    if not host or _is_ip(host):
        raise AppError("invalid_url", MSG_INVALID, 400)
    if parts.port not in (None, 80, 443):
        raise AppError("invalid_url", MSG_INVALID, 400)

    provider = _provider_for(host)
    if provider is None:
        raise AppError("unsupported_host", MSG_HOST, 400)
    if provider == "youtube":
        normalized = _normalize_youtube(host, parts.path or "/", parts.query)
        return ParsedMediaUrl(url=normalized, provider=provider, host=host)
    if not _path_allowed(provider, host, parts.path or "/"):
        raise AppError("unsupported_content", MSG_UNSUPPORTED, 422)

    normalized = urlunsplit((parts.scheme.lower(), host, parts.path or "/", parts.query, ""))
    return ParsedMediaUrl(url=normalized, provider=provider, host=host)


def _provider_for(host: str) -> str | None:
    for domain, provider in _PROVIDERS:
        if host == domain or host.endswith("." + domain):
            return provider
    return None


def _normalize_youtube(host: str, path: str, query: str) -> str:
    params = parse_qs(query, keep_blank_values=False)
    if "list" in params:
        raise AppError("unsupported_content", MSG_UNSUPPORTED, 422)
    lowered = path.lower()
    if lowered.startswith("/live") or lowered.startswith("/playlist"):
        raise AppError("unsupported_content", MSG_UNSUPPORTED, 422)

    if host == "youtu.be" or host.endswith(".youtu.be"):
        match = re.fullmatch(r"/([A-Za-z0-9_-]{11})/?", path)
        if match is None:
            raise AppError("unsupported_content", MSG_UNSUPPORTED, 422)
        return f"https://{host}/{match.group(1)}"

    if lowered in {"/watch", "/watch/"}:
        video_id = (params.get("v") or [""])[0]
        if _YOUTUBE_ID.fullmatch(video_id) is None:
            raise AppError("unsupported_content", MSG_UNSUPPORTED, 422)
        return f"https://{host}/watch?v={video_id}"

    match = _YOUTUBE_MEDIA_PATH.fullmatch(path)
    if match is None:
        raise AppError("unsupported_content", MSG_UNSUPPORTED, 422)
    kind = path.strip("/").split("/", 1)[0].lower()
    return f"https://{host}/{kind}/{match.group(1)}"


def _path_allowed(provider: str, host: str, path: str) -> bool:
    if provider == "instagram":
        return _INSTAGRAM_PATH.match(path) is not None
    if provider == "tiktok":
        if host in _SHORT_TIKTOK_HOSTS:
            return _TIKTOK_SHORT_PATH.match(path) is not None
        return _TIKTOK_PATH.match(path) is not None
    return _X_PATH.match(path) is not None


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True
