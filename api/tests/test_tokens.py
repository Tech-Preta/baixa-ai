import pytest

from app.errors import AppError
from app.tokens import sign_token, verify_token

SECRET = "test-secret"
NOW = 1_700_000_000


def test_roundtrip_and_rejects_tampering_or_expiry() -> None:
    token = sign_token(
        {
            "url": "https://www.instagram.com/reel/AbC123/",
            "kind": "file",
            "index": 0,
            "format_id": "hd",
            "exp": NOW + 30,
        },
        SECRET,
    )
    data = verify_token(token, SECRET, now=NOW)
    assert data["format_id"] == "hd"

    with pytest.raises(AppError) as expired:
        verify_token(token, SECRET, now=NOW + 31)
    assert expired.value.code == "invalid_token"

    with pytest.raises(AppError):
        verify_token(token, "other-secret", now=NOW)

    body, _, sig = token.partition(".")
    with pytest.raises(AppError):
        verify_token(body + "." + sig[:-1] + ("A" if sig[-1] != "A" else "B"), SECRET, now=NOW)
