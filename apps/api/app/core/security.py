from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


class TokenError(Exception):
    pass


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padded = value + ("=" * (-len(value) % 4))
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def hash_password(password: str, salt: str | None = None, iterations: int = 210_000) -> str:
    password_salt = salt or secrets.token_urlsafe(18)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2_sha256${iterations}${password_salt}${_b64encode(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_value, salt, expected = password_hash.split("$", 3)
        iterations = int(iterations_value)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    actual = hash_password(password, salt=salt, iterations=iterations).split("$", 3)[3]
    return hmac.compare_digest(actual, expected)


def create_access_token(
    payload: dict[str, Any],
    *,
    secret_key: str,
    expires_in_seconds: int,
) -> str:
    token_payload = dict(payload)
    token_payload["exp"] = int(time.time()) + expires_in_seconds
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64encode(json.dumps(token_payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    signature = hmac.new(secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64encode(signature)}"


def parse_access_token(token: str, *, secret_key: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".", 2)
    except ValueError as exc:
        raise TokenError("token_malformed") from exc

    signing_input = f"{encoded_header}.{encoded_payload}".encode()
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input,
        hashlib.sha256,
    ).digest()
    actual_signature = _b64decode(encoded_signature)
    if not hmac.compare_digest(actual_signature, expected_signature):
        raise TokenError("token_signature_invalid")

    try:
        payload = json.loads(_b64decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise TokenError("token_payload_invalid") from exc

    if int(payload.get("exp", 0)) <= int(time.time()):
        raise TokenError("token_expired")

    return payload
