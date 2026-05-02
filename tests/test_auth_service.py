from __future__ import annotations

import hashlib
import hmac
import time
import uuid

import pytest

from app.auth.errors import InvalidCallbackError
from app.auth.service import AuthService
from app.core.config import settings


def signed_payload(external_id: str, ts: int | None = None, secret: str | None = None):
    now = int(time.time()) if ts is None else ts
    params = {
        "external_id": external_id,
        "username": "demo",
        "email": "demo@example.com",
        "first_name": "Demo",
        "last_name": "User",
        "ts": str(now),
    }
    payload = "\n".join([
        params["external_id"],
        params["username"],
        params["email"],
        params["first_name"],
        params["last_name"],
        params["ts"],
    ])
    sig = hmac.new((secret or settings.auth_mock_shared_secret).encode(), payload.encode(), hashlib.sha256).hexdigest()
    params["sig"] = sig
    return params


def test_validate_mock_callback_success():
    params = signed_payload(str(uuid.uuid4()))
    out = AuthService.validate_mock_callback(params)
    assert out["external_id"] == params["external_id"]


def test_validate_mock_callback_invalid_signature():
    params = signed_payload(str(uuid.uuid4()))
    params["sig"] = "bad"
    with pytest.raises(InvalidCallbackError):
        AuthService.validate_mock_callback(params)


def test_validate_mock_callback_expired():
    params = signed_payload(str(uuid.uuid4()), ts=int(time.time()) - settings.auth_mock_max_age_seconds - 10)
    with pytest.raises(InvalidCallbackError):
        AuthService.validate_mock_callback(params)


def test_validate_mock_callback_invalid_uuid():
    params = signed_payload("not-a-uuid")
    with pytest.raises(InvalidCallbackError):
        AuthService.validate_mock_callback(params)
