from __future__ import annotations

import datetime as dt
import re
import uuid

from sqlalchemy.orm import Session

from app.db.models import Page


def validate_text_bounds(x: float, y: float, width: float, height: float) -> None:
    if x < 0 or y < 0 or width <= 0 or height <= 0:
        raise ValueError("invalid relative coordinates")
    if x + width > 1.0 or y + height > 1.0:
        raise ValueError("text block must stay inside panel")


def validate_hex_color(color: str) -> None:
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        raise ValueError("invalid color format, expected #RRGGBB")


def validate_opacity(opacity: float) -> None:
    if opacity < 0.0 or opacity > 1.0:
        raise ValueError("background_opacity must be between 0 and 1")


def invalidate_page_artifact(db: Session, page_id: uuid.UUID) -> None:
    page = db.get(Page, page_id)
    if not page:
        return
    page.rendered_image_url = None
    page.artifact_generated_at = None
    db.add(page)
    db.flush()
