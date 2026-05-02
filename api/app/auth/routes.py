from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.auth.errors import AuthError
from app.auth.service import AuthService
from app.core.config import settings
from app.db.session import get_db

router = APIRouter(tags=["auth"])
logger = logging.getLogger("app.auth")


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request, start: int = Query(default=0)):
    if start == 1:
        if settings.auth_mode == "mock":
            return RedirectResponse(AuthService.build_mock_login_url(request), status_code=302)
        if settings.auth_mode == "keycloak":
            return RedirectResponse(AuthService.build_keycloak_auth_url(request), status_code=302)
    html = (
        "<html><body><h1>BD Creator Login</h1>"
        "<a href='/login?start=1'>Se connecter</a></body></html>"
    )
    return HTMLResponse(html)


@router.get("/auth/callback", name="auth_callback")
async def auth_callback(request: Request, db: Session = Depends(get_db)):
    try:
        if settings.auth_mode == "mock":
            payload = AuthService.validate_mock_callback(dict(request.query_params))
        else:
            payload = await AuthService.validate_keycloak_callback(request)

        user = AuthService.lookup_directory_user(db, payload["external_id"])
        AuthService.store_session_user(request, user)
        logger.info("login_success external_id=%s username=%s", user.external_id, user.username)
        return RedirectResponse("/", status_code=302)
    except AuthError as exc:
        AuthService.clear_session_user(request)
        logger.info("login_refused reason=%s", exc.__class__.__name__)
        return RedirectResponse("/?auth_error=1", status_code=302)


@router.get("/logout")
async def logout(request: Request):
    snapshot = AuthService.get_session_user(request)
    AuthService.clear_session_user(request)
    if snapshot:
        logger.info("logout external_id=%s username=%s", snapshot.external_id, snapshot.username)

    keycloak_url = AuthService.keycloak_logout_url()
    if keycloak_url:
        return RedirectResponse(keycloak_url, status_code=302)
    return RedirectResponse("/", status_code=302)
