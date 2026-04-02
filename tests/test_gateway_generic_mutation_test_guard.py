"""Ensure generic gateway mutation helpers are constrained in test modules."""

from __future__ import annotations

from tests.guard_helpers import assert_guard_clean, run_guard_script


def test_gateway_generic_mutation_test_guard_reports_zero_hits() -> None:
    result = run_guard_script("check_gateway_generic_mutations_in_tests.py")
    assert_guard_clean(result)
