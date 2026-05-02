from __future__ import annotations

import hashlib
import hmac
import logging
import re
import secrets
import time
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.errors import DisabledUserError, InvalidCallbackError, KeycloakAuthError, UnknownUserError
from app.auth.models import DirectoryUser, SessionUser
from app.core.config import settings

logger = logging.getLogger("app.auth")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AuthService:
    @staticmethod
    def clear_session_user(request: Request) -> None:
        request.session.pop("lss_user", None)

    @staticmethod
    def store_session_user(request: Request, user: DirectoryUser) -> None:
        request.session.pop("lss_user", None)
        request.session["lss_user"] = user.to_session_dict()

    @staticmethod
    def get_session_user(request: Request) -> SessionUser | None:
        payload = request.session.get("lss_user")
        if not isinstance(payload, dict):
            return None
        try:
            return SessionUser.from_session(payload)
        except Exception:
            return None

    @staticmethod
    def build_mock_login_url(request: Request) -> str:
        callback = str(request.url_for("auth_callback"))
        return f"{settings.auth_mock_base_url.rstrip('/')}/login?" + urlencode({"return_to": callback})

    @staticmethod
    def build_keycloak_auth_url(request: Request) -> str:
        state = secrets.token_urlsafe(32)
        request.session["lss_keycloak_state"] = state
        oidc_base = (
            f"{settings.keycloak_server_url.rstrip('/')}/realms/{settings.keycloak_realm}"
            "/protocol/openid-connect"
        )
        query = {
            "client_id": settings.keycloak_client_id,
            "response_type": "code",
            "scope": settings.keycloak_scopes,
            "redirect_uri": settings.keycloak_redirect_uri,
            "state": state,
        }
        return f"{oidc_base}/auth?{urlencode(query)}"

    @staticmethod
    def _parse_uuid(value: str) -> str:
        try:
            return str(uuid.UUID(value))
        except ValueError as exc:
            raise InvalidCallbackError("invalid external_id UUID") from exc

    @staticmethod
    def validate_mock_callback(params: dict[str, str]) -> dict[str, str]:
        required = ["external_id", "username", "email", "first_name", "last_name", "ts", "sig"]
        missing = [name for name in required if not params.get(name)]
        if missing:
            raise InvalidCallbackError(f"missing params: {','.join(missing)}")

        for field in ["username", "email", "first_name", "last_name"]:
            if len(params[field]) > 255:
                raise InvalidCallbackError(f"{field} too long")

        try:
            ts = int(params["ts"])
        except ValueError as exc:
            raise InvalidCallbackError("ts must be integer") from exc
        if abs(int(time.time()) - ts) > settings.auth_mock_max_age_seconds:
            raise InvalidCallbackError("signature expired")

        payload = "\n".join(
            [
                params["external_id"],
                params["username"],
                params["email"],
                params["first_name"],
                params["last_name"],
                params["ts"],
            ]
        )
        expected = hmac.new(
            settings.auth_mock_shared_secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, params["sig"]):
            raise InvalidCallbackError("invalid signature")

        normalized_external = AuthService._parse_uuid(params["external_id"])
        return {
            "external_id": normalized_external,
            "username": params["username"],
            "email": params["email"],
            "first_name": params["first_name"],
            "last_name": params["last_name"],
        }

    @staticmethod
    async def validate_keycloak_callback(request: Request) -> dict[str, str]:
        params = request.query_params
        if params.get("error"):
            raise KeycloakAuthError(str(params.get("error")))
        code = params.get("code")
        state = params.get("state")
        if not code or not state:
            raise InvalidCallbackError("missing code/state")

        expected_state = request.session.pop("lss_keycloak_state", None)
        if not expected_state or not secrets.compare_digest(expected_state, state):
            raise InvalidCallbackError("invalid state")

        oidc_base = (
            f"{settings.keycloak_server_url.rstrip('/')}/realms/{settings.keycloak_realm}"
            "/protocol/openid-connect"
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(
                f"{oidc_base}/token",
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.keycloak_redirect_uri,
                    "client_id": settings.keycloak_client_id,
                    "client_secret": settings.keycloak_client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if token_resp.status_code >= 400:
                logger.error("keycloak token exchange failed status=%s body=%s", token_resp.status_code, token_resp.text[:300])
                raise KeycloakAuthError("token exchange failed")
            access_token = token_resp.json().get("access_token")
            if not access_token:
                raise KeycloakAuthError("missing access_token")

            userinfo_resp = await client.get(
                f"{oidc_base}/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code >= 400:
                logger.error("keycloak userinfo failed status=%s body=%s", userinfo_resp.status_code, userinfo_resp.text[:300])
                raise KeycloakAuthError("userinfo failed")
            userinfo = userinfo_resp.json()

        external_id = AuthService._parse_uuid(str(userinfo.get("sub", "")))
        return {
            "external_id": external_id,
            "username": str(userinfo.get("preferred_username") or ""),
            "email": str(userinfo.get("email") or ""),
            "first_name": str(userinfo.get("given_name") or ""),
            "last_name": str(userinfo.get("family_name") or ""),
        }

    @staticmethod
    def _validated_identifier(name: str, label: str) -> str:
        if not _IDENTIFIER_RE.match(name):
            raise RuntimeError(f"invalid SQL identifier for {label}")
        return name

    @staticmethod
    def lookup_directory_user(db: Session, external_id: str) -> DirectoryUser:
        schema = AuthService._validated_identifier(settings.user_schema, "USER_SCHEMA")
        table = AuthService._validated_identifier(settings.user_table, "USER_TABLE")

        base_query = text(
            f'SELECT id::text, username, email, first_name, last_name FROM "{schema}"."{table}" WHERE id = :id'
        )
        row = db.execute(base_query, {"id": external_id}).mappings().first()
        if row is None:
            logger.info("login_refused reason=unknown_user")
            raise UnknownUserError("unknown user")

        try:
            enabled_q = text(
                f'SELECT enabled FROM "{schema}"."{table}" WHERE id = :id'
            )
            enabled_row = db.execute(enabled_q, {"id": external_id}).first()
            enabled = True if enabled_row is None else bool(enabled_row[0])
        except Exception:
            enabled = True

        if not enabled:
            logger.info("login_refused reason=disabled_user")
            raise DisabledUserError("disabled user")

        return DirectoryUser(
            external_id=str(row["id"]),
            username=str(row.get("username") or ""),
            email=str(row.get("email") or ""),
            first_name=str(row.get("first_name") or ""),
            last_name=str(row.get("last_name") or ""),
        )

    @staticmethod
    def keycloak_logout_url() -> str | None:
        if settings.auth_mode != "keycloak":
            return None
        if not settings.keycloak_server_url or not settings.keycloak_realm or not settings.keycloak_client_id:
            return None
        if not settings.keycloak_logout_redirect_uri:
            return None
        oidc_base = (
            f"{settings.keycloak_server_url.rstrip('/')}/realms/{settings.keycloak_realm}"
            "/protocol/openid-connect"
        )
        return f"{oidc_base}/logout?" + urlencode(
            {
                "client_id": settings.keycloak_client_id,
                "post_logout_redirect_uri": settings.keycloak_logout_redirect_uri,
            }
        )
