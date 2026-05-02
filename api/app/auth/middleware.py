from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.auth.models import AnonymousUser
from app.auth.service import AuthService
from app.db.session import SessionLocal


class CurrentUserMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = AnonymousUser()
        session_user = AuthService.get_session_user(request)
        if session_user:
            db = SessionLocal()
            try:
                refreshed = AuthService.lookup_directory_user(db, session_user.external_id)
                AuthService.store_session_user(request, refreshed)
                request.state.user = refreshed
            except Exception:
                AuthService.clear_session_user(request)
            finally:
                db.close()

        return await call_next(request)
