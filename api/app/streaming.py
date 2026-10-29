"""Proxy a remote file to the client without writing it to disk."""

import ipaddress
import socket
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit

import httpx

from app.errors import MSG_GENERIC, MSG_TOO_LARGE, AppError

_REDIRECTS = {301, 302, 303, 307, 308}
_HEADER_ALLOW = {"user-agent", "referer", "accept", "accept-language", "origin"}
_MAX_REDIRECTS = 3


@dataclass
class OpenedRemote:
    content_type: str
    content_length: int | None
    _response: httpx.Response

    async def iter_capped(self, max_bytes: int) -> AsyncIterator[bytes]:
        total = 0
        try:
            async for chunk in self._response.aiter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise AppError("too_large", MSG_TOO_LARGE, 413)
                yield chunk
        finally:
            await self._response.aclose()


def ensure_public_host(url: str, resolve: Callable = socket.getaddrinfo) -> None:
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise AppError("extraction_failed", MSG_GENERIC, 502)
    host = parts.hostname
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None:
        if not _is_public(literal):
            raise AppError("extraction_failed", MSG_GENERIC, 502)
        return
    try:
        infos = resolve(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise AppError("extraction_failed", MSG_GENERIC, 502) from exc
    if not infos:
        raise AppError("extraction_failed", MSG_GENERIC, 502)
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not _is_public(address):
            raise AppError("extraction_failed", MSG_GENERIC, 502)


async def open_remote(
    url: str,
    *,
    headers: dict[str, str],
    max_bytes: int,
    client: httpx.AsyncClient,
    resolve: Callable = socket.getaddrinfo,
) -> OpenedRemote:
    current = url
    forwarded = _filter_headers(headers)
    for _ in range(_MAX_REDIRECTS + 1):
        ensure_public_host(current, resolve=resolve)
        request = client.build_request("GET", current, headers=forwarded)
        response = await client.send(request, stream=True)
        if response.status_code in _REDIRECTS:
            location = response.headers.get("location")
            await response.aclose()
            if not location:
                raise AppError("extraction_failed", MSG_GENERIC, 502)
            current = urljoin(current, location)
            continue
        if response.status_code >= 400:
            await response.aclose()
            raise AppError("extraction_failed", MSG_GENERIC, 502)
        content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if not _acceptable(content_type):
            await response.aclose()
            raise AppError("extraction_failed", MSG_GENERIC, 502)
        length = _length(response.headers.get("content-length"))
        if length is not None and length > max_bytes:
            await response.aclose()
            raise AppError("too_large", MSG_TOO_LARGE, 413)
        return OpenedRemote(
            content_type=content_type or "application/octet-stream",
            content_length=length,
            _response=response,
        )
    raise AppError("extraction_failed", MSG_GENERIC, 502)


def _is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _filter_headers(headers: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in headers.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if key.lower() in _HEADER_ALLOW and value.strip():
            cleaned[key] = value
    return cleaned


def _acceptable(content_type: str) -> bool:
    if not content_type:
        return True
    if content_type.startswith(("video/", "image/", "application/octet-stream")):
        return True
    return content_type in {"application/mp4", "binary/octet-stream"}


def _length(value: str | None) -> int | None:
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None
