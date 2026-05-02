from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DirectoryUser:
    external_id: str
    username: str
    email: str
    first_name: str
    last_name: str
    is_moderator: bool = False
    is_admin: bool = False

    def to_session_dict(self) -> dict[str, object]:
        return {
            "external_id": self.external_id,
            "username": self.username,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "is_moderator": self.is_moderator,
            "is_admin": self.is_admin,
        }


@dataclass
class SessionUser(DirectoryUser):
    @classmethod
    def from_session(cls, payload: dict[str, object]) -> "SessionUser":
        return cls(
            external_id=str(payload["external_id"]),
            username=str(payload.get("username", "")),
            email=str(payload.get("email", "")),
            first_name=str(payload.get("first_name", "")),
            last_name=str(payload.get("last_name", "")),
            is_moderator=bool(payload.get("is_moderator", False)),
            is_admin=bool(payload.get("is_admin", False)),
        )


@dataclass
class AnonymousUser:
    is_anonymous: bool = True
