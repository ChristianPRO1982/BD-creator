from __future__ import annotations

import uuid

from fastapi import HTTPException, Request


class AuthenticatedUser:
    def __init__(self, external_id: str):
        self.external_id = external_id

    @property
    def user_uuid(self) -> uuid.UUID:
        return uuid.UUID(self.external_id)


def require_user(request: Request) -> AuthenticatedUser:
    user = getattr(request.state, "user", None)
    if user is None or getattr(user, "is_anonymous", False):
        raise HTTPException(status_code=401, detail="Authentication required")
    return AuthenticatedUser(external_id=user.external_id)
