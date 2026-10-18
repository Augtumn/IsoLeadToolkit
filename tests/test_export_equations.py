"""The exported Equations sheet carries the slope and intercept it says it does.

Overlays store the right-hand side of their expression - "1.0049*x+20.259", "x" - and the parser used to demand a
leading "y=", a form this application never writes. Every exported row had blank Slope and Intercept columns.
"""
from __future__ import annotations

import pytest

from application.use_cases.export_data import _parse_linear_expression


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("1.0049*x+20.259", (1.0049, 20.259)),
        ("x", (1.0, 0.0)),
        ("0.5*x", (0.5, 0.0)),
        ("y=2*x-3", (2.0, -3.0)),
        ("1.5x + 0.2", (1.5, 0.2)),
        ("2*x - 3/2", (2.0, -1.5)),
        ("-0.25*x-1", (-0.25, -1.0)),
    ],
)
def test_a_linear_expression_gives_its_two_numbers(expression, expected) -> None:
    assert _parse_linear_expression(expression) == pytest.approx(expected)


@pytest.mark.parametrize("expression", ["x**2 + 1", "", "sin(x)", "x*x"])
def test_a_non_linear_expression_stays_blank(expression) -> None:
    """Blank is honest; a plausible wrong slope is not."""
    assert _parse_linear_expression(expression) == (None, None)
