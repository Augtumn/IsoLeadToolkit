"""Ensure generic gateway mutation helpers are not used in production modules."""

from __future__ import annotations

from tests.guard_helpers import assert_guard_clean, run_guard_script


def test_gateway_generic_mutation_guard_reports_zero_hits() -> None:
    result = run_guard_script("check_gateway_generic_mutations.py")
    assert_guard_clean(result)
