"""Ensure app_state direct assignment guard remains green."""

from __future__ import annotations

from tests.guard_helpers import assert_guard_clean, run_guard_script



def test_state_mutation_guard_script_reports_zero_hits() -> None:
    result = run_guard_script("check_state_mutations.py")
    assert_guard_clean(result)
