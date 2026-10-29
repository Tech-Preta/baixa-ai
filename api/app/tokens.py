"""Short-lived HMAC tokens. The CDN URL never goes to the browser."""

import base64
import hashlib
import hmac
import json

from app.errors import MSG_TOKEN, AppError


def sign_token(payload: dict, secret: str) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return f"{_encode(body)}.{_encode(signature)}"


def verify_token(token: str, secret: str, now: float) -> dict:
    try:
        body_b64, signature_b64 = token.split(".", 1)
        body = _decode(body_b64)
        signature = _decode(signature_b64)
        expected = hmac.new(secret.encode(), body, hashlib.sha256).digest()
        if not hmac.compare_digest(signature, expected):
            raise AppError("invalid_token", MSG_TOKEN, 400)
        data = json.loads(body)
        if not isinstance(data, dict) or float(data.get("exp", 0)) < now:
            raise AppError("invalid_token", MSG_TOKEN, 400)
        return data
    except AppError:
        raise
    except Exception as exc:
        raise AppError("invalid_token", MSG_TOKEN, 400) from exc


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(raw + padding)
