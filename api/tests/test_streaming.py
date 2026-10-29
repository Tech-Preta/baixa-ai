import asyncio
import socket

import httpx
import pytest

from app.errors import AppError
from app.streaming import ensure_public_host, open_remote


def _public_resolve(host: str, port: int, *args: object, **kwargs: object) -> list:
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", port))]


def test_rejects_private_and_link_local_targets() -> None:
    for url in (
        "http://127.0.0.1/secret",
        "http://169.254.169.254/",
        "http://10.0.0.8/a",
        "http://[::1]/a",
    ):
        with pytest.raises(AppError) as exc:
            ensure_public_host(url, resolve=_public_resolve)
        assert exc.value.code == "extraction_failed"


def test_rejects_hostname_that_resolves_to_a_private_address() -> None:
    def resolve(host: str, port: int, *args: object, **kwargs: object) -> list:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", port))]

    with pytest.raises(AppError):
        ensure_public_host("https://cdn.example/a.mp4", resolve=resolve)


def test_streams_public_file_without_forwarding_cookies() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "cookie" not in {name.lower() for name in request.headers}
        assert request.headers["user-agent"] == "Baixa"
        return httpx.Response(200, content=b"videobytes", headers={"content-type": "video/mp4"})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            opened = await open_remote(
                "https://cdn.example/720.mp4",
                headers={"User-Agent": "Baixa", "Cookie": "session=nope"},
                max_bytes=1000,
                client=client,
                resolve=_public_resolve,
            )
            data = bytearray()
            async for chunk in opened.iter_capped(1000):
                data.extend(chunk)
            assert bytes(data) == b"videobytes"
            assert opened.content_type == "video/mp4"
            assert opened.content_length == len(b"videobytes")

    asyncio.run(run())


def test_refuses_redirects_to_private_hosts() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1/secret"})

    async def run() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            with pytest.raises(AppError):
                await open_remote(
                    "https://cdn.example/720.mp4",
                    headers={"User-Agent": "Baixa", "Cookie": "nope"},
                    max_bytes=1000,
                    client=client,
                    resolve=_public_resolve,
                )

    asyncio.run(run())
    assert seen == ["https://cdn.example/720.mp4"]


def test_rejects_oversized_and_html_payloads() -> None:
    def too_big(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"12345", headers={"content-type": "video/mp4"})

    async def run_too_big() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(too_big)) as client:
            with pytest.raises(AppError) as exc:
                await open_remote(
                    "https://cdn.example/720.mp4",
                    headers={},
                    max_bytes=4,
                    client=client,
                    resolve=_public_resolve,
                )
            assert exc.value.code == "too_large"

    asyncio.run(run_too_big())

    def html(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html></html>", headers={"content-type": "text/html"})

    async def run_html() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(html)) as client:
            with pytest.raises(AppError) as exc:
                await open_remote(
                    "https://cdn.example/720.mp4",
                    headers={"Cookie": "nope"},
                    max_bytes=1000,
                    client=client,
                    resolve=_public_resolve,
                )
            assert exc.value.code == "extraction_failed"

    asyncio.run(run_html())
