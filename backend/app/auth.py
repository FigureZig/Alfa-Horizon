"""Вход пользователем симулятора (docs/06 §10): JWT HS256 на стандартной библиотеке. В токене — только id персоны;
права не зашиты, а вычисляются из снапшотов на каждый запрос (app/domain/rights.py)."""

import base64
import hashlib
import hmac
import json
import time

from .config import settings

TTL_S = 12 * 3600


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(message: str) -> str:
    return _b64(hmac.new(settings.token_secret.encode(), message.encode(), hashlib.sha256).digest())


def issue(persona_id: str, kind: str) -> str:
    now = int(time.time())
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps({"sub": persona_id, "kind": kind, "iat": now, "exp": now + TTL_S}).encode())
    return f"{head}.{body}.{_sign(f'{head}.{body}')}"


def verify(token: str) -> dict | None:
    """Claims или None: подпись не сошлась, токен битый или истёк."""
    try:
        head, body, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(f"{head}.{body}")):
            return None
        claims = json.loads(_unb64(body))
    except (ValueError, json.JSONDecodeError):
        return None
    return claims if claims.get("exp", 0) > time.time() else None
