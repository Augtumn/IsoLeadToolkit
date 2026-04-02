"""Guard scripts should report zero findings across protected scopes."""

from __future__ import annotations

import pytest

from tests.guard_helpers import assert_guard_clean, run_guard_script


@pytest.mark.parametrize(
    "script_name",
    [
        "check_state_mutations.py",
        "check_gateway_generic_mutations.py",
        "check_gateway_generic_mutations_in_tests.py",
    ],
)
def test_guard_script_reports_zero_hits(script_name: str) -> None:
    result = run_guard_script(script_name)
    assert_guard_clean(result)
