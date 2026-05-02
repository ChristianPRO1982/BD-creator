from __future__ import annotations

import pytest

from app.api.utils import validate_text_bounds


def test_text_bounds_ok():
    validate_text_bounds(0.0, 0.0, 1.0, 1.0)


def test_text_bounds_outside():
    with pytest.raises(ValueError):
        validate_text_bounds(0.8, 0.8, 0.3, 0.3)
