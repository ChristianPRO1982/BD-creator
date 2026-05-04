from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Any

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


def validate_template_payload(payload: dict[str, Any]) -> tuple[str, int, int, list[dict[str, int | str]]]:
    name = str(payload.get("name", "")).strip()
    columns = payload.get("columns")
    rows = payload.get("rows")
    slots = payload.get("slots")

    if not name:
        raise ValueError("Template name is required")
    if not isinstance(columns, int) or columns < 1:
        raise ValueError("columns must be an integer >= 1")
    if not isinstance(rows, int) or rows < 1:
        raise ValueError("rows must be an integer >= 1")
    if not isinstance(slots, list) or not slots:
        raise ValueError("slots must contain at least one slot")

    normalized_slots: list[dict[str, int | str]] = []
    for slot in slots:
        if not isinstance(slot, dict):
            raise ValueError("Each slot must be an object")
        col_start = slot.get("col_start")
        row_start = slot.get("row_start")
        col_span = slot.get("col_span", 1)
        row_span = slot.get("row_span", 1)
        geometry_type = slot.get("geometry_type", "rectangle")
        if not all(isinstance(v, int) for v in [col_start, row_start, col_span, row_span]):
            raise ValueError("Slot coordinates and spans must be integers")
        if col_start < 1 or row_start < 1 or col_span < 1 or row_span < 1:
            raise ValueError("Slot coordinates and spans must be >= 1")
        if geometry_type != "rectangle":
            raise ValueError("Only geometry_type=rectangle is supported")
        if col_start + col_span - 1 > columns or row_start + row_span - 1 > rows:
            raise ValueError("A slot is outside the template grid")
        normalized_slots.append(
            {
                "col_start": col_start,
                "row_start": row_start,
                "col_span": col_span,
                "row_span": row_span,
                "geometry_type": geometry_type,
            }
        )
    return name, columns, rows, normalized_slots
