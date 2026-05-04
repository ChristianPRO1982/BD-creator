from __future__ import annotations

import pytest

from app.api.utils import validate_hex_color, validate_opacity, validate_template_payload, validate_text_bounds


def test_text_bounds_ok():
    validate_text_bounds(0.0, 0.0, 1.0, 1.0)


def test_text_bounds_outside():
    with pytest.raises(ValueError):
        validate_text_bounds(0.8, 0.8, 0.3, 0.3)


def test_validate_hex_color_ok():
    validate_hex_color("#a1B2c3")


def test_validate_hex_color_rejects_short():
    with pytest.raises(ValueError):
        validate_hex_color("#abc")


def test_validate_opacity_ok():
    validate_opacity(0.0)
    validate_opacity(1.0)


def test_validate_opacity_outside_range():
    with pytest.raises(ValueError):
        validate_opacity(-0.1)
    with pytest.raises(ValueError):
        validate_opacity(1.1)


def test_validate_template_payload_ok():
    name, columns, rows, slots = validate_template_payload(
        {
            "name": "Two Panels",
            "columns": 2,
            "rows": 1,
            "slots": [
                {"col_start": 1, "row_start": 1, "col_span": 1, "row_span": 1, "geometry_type": "rectangle"},
                {"col_start": 2, "row_start": 1, "col_span": 1, "row_span": 1, "geometry_type": "rectangle"},
            ],
        }
    )
    assert name == "Two Panels"
    assert columns == 2
    assert rows == 1
    assert len(slots) == 2


def test_validate_template_payload_rejects_slot_outside_grid():
    with pytest.raises(ValueError):
        validate_template_payload(
            {
                "name": "Bad",
                "columns": 2,
                "rows": 2,
                "slots": [{"col_start": 2, "row_start": 2, "col_span": 2, "row_span": 1, "geometry_type": "rectangle"}],
            }
        )
