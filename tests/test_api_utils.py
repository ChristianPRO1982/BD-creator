from __future__ import annotations

import pytest

from app.api.utils import validate_hex_color, validate_opacity, validate_text_bounds


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
