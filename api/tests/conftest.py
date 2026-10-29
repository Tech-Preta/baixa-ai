import socket

import pytest


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must not reach Instagram, TikTok, X, or any other host."""

    def blocked(*args: object, **kwargs: object) -> None:
        raise RuntimeError("network disabled in tests")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
