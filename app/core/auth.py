from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_TOKEN_TTL_SECONDS = 8 * 60 * 60

_password_hasher = PasswordHasher()


def _get_secret() -> str:
    secret = os.getenv("AUTH_SECRET_KEY")
    if not secret:
        secret = "dev-secret"
        print("[WARNING] AUTH_SECRET_KEY not set. Using insecure default. Set it in production!")
    return secret


def _get_pepper() -> str:
    pepper = os.getenv("AUTH_PASSWORD_PEPPER")
    if not pepper:
        pepper = "dev-pepper"
        print("[WARNING] AUTH_PASSWORD_PEPPER not set. Using insecure default. Set it in production!")
    return pepper


def _apply_pepper(password: str) -> str:
    return f"{password}{_get_pepper()}"


def hash_password(password: str) -> str:
    return _password_hasher.hash(_apply_pepper(password))


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, _apply_pepper(password))
    except VerifyMismatchError:
        return False


def _sign(payload: bytes) -> str:
    signature = hmac.new(
        _get_secret().encode("utf-8"), payload, hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")


def _encode_payload(payload: dict) -> tuple[str, bytes]:
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    encoded = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
    return encoded, payload_bytes


def _decode_payload(encoded: str) -> dict | None:
    padding = "=" * (-len(encoded) % 4)
    try:
        payload_bytes = base64.urlsafe_b64decode(f"{encoded}{padding}")
        return json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None


@dataclass(frozen=True)
class AuthToken:
    user_id: str
    role: str


def create_token(user_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": int(time.time()) + _TOKEN_TTL_SECONDS,
    }
    encoded, payload_bytes = _encode_payload(payload)
    signature = _sign(payload_bytes)
    return f"{encoded}.{signature}"


def verify_token(token: str) -> AuthToken | None:
    try:
        encoded, signature = token.split(".", 1)
    except ValueError:
        return None
    payload = _decode_payload(encoded)
    if payload is None:
        return None
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    if not hmac.compare_digest(_sign(payload_bytes), signature):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or not role:
        return None
    return AuthToken(user_id=user_id, role=role)
