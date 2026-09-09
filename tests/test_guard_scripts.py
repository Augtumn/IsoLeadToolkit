"""Guard scripts should report zero findings across protected scopes."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.guard_helpers import assert_guard_clean, run_guard_script

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "script_name",
    [
        "check_state_mutations.py",
        "check_gateway_generic_mutations.py",
        "check_gateway_generic_mutations_in_tests.py",
        "check_gateway_direct_state_assignments.py",
        "check_state_dict_mutations.py",
    ],
)
def test_guard_script_reports_zero_hits(script_name: str) -> None:
    result = run_guard_script(script_name)
    assert_guard_clean(result)


def test_locale_checker_reports_no_missing_keys() -> None:
    """Every translate() key used by code must exist in both locales."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "locales" / "check_untranslated.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_locale_files_have_identical_keys() -> None:
    en = json.loads((REPO_ROOT / "locales" / "en.json").read_text(encoding="utf-8"))
    zh = json.loads((REPO_ROOT / "locales" / "zh.json").read_text(encoding="utf-8"))
    assert set(en) == set(zh), sorted(set(en) ^ set(zh))
