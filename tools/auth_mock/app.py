from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import uuid

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, RedirectResponse

app = FastAPI()

SHARED_SECRET = os.getenv("AUTH_MOCK_SHARED_SECRET", "dev-shared-secret")
USERS_JSON = os.getenv("AUTH_MOCK_USERS_JSON", "")

DEFAULT_USERS = [
    {
        "label": "Known user",
        "external_id": "11111111-1111-1111-1111-111111111111",
        "username": "known.user",
        "email": "known.user@example.test",
        "first_name": "Known",
        "last_name": "User",
    },
    {
        "label": "Disabled user",
        "external_id": "22222222-2222-2222-2222-222222222222",
        "username": "disabled.user",
        "email": "disabled.user@example.test",
        "first_name": "Disabled",
        "last_name": "User",
    },
    {
        "label": "Unknown user",
        "external_id": "33333333-3333-3333-3333-333333333333",
        "username": "unknown.user",
        "email": "unknown.user@example.test",
        "first_name": "Unknown",
        "last_name": "User",
    },
]


def _load_users() -> list[dict[str, str]]:
    if not USERS_JSON.strip():
        return DEFAULT_USERS
    try:
        loaded = json.loads(USERS_JSON)
        if isinstance(loaded, list) and loaded:
            return loaded
    except Exception:
        pass
    return DEFAULT_USERS


def _pick_user(external_id: str | None) -> dict[str, str]:
    users = _load_users()
    if external_id:
        for user in users:
            if user.get("external_id") == external_id:
                return user
    return users[0]


@app.get("/login", response_class=HTMLResponse)
def login(return_to: str = Query(...), external_id: str | None = Query(default=None)):
    users = _load_users()
    if external_id is None and len(users) > 1:
        links = []
        for user in users:
            label = user.get("label", user.get("username", "user"))
            target = (
                f"/login?return_to={urllib.parse.quote(return_to, safe='')}"
                f"&external_id={urllib.parse.quote(user['external_id'], safe='')}"
            )
            links.append(f"<li><a href='{target}'>{label}</a></li>")
        return HTMLResponse(
            "<html><body><h2>Choisir un utilisateur mock</h2><ul>"
            + "".join(links)
            + "</ul></body></html>"
        )

    user = _pick_user(external_id)
    _ = uuid.UUID(user["external_id"])
    username = user["username"]
    email = user["email"]
    first_name = user["first_name"]
    last_name = user["last_name"]
    ts = str(int(time.time()))
    payload = "\n".join([user["external_id"], username, email, first_name, last_name, ts])
    sig = hmac.new(SHARED_SECRET.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    query = urllib.parse.urlencode(
        {
            "external_id": user["external_id"],
            "username": username,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "ts": ts,
            "sig": sig,
        }
    )
    target = f"{return_to}?{query}"
    return RedirectResponse(target, status_code=302)
