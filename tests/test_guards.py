"""Guard-script tests: cleanliness, positive detection and scan utilities."""

import json
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from scripts.source_scan_guard import print_scan_result, scan_pattern_hits
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
        "check_panel_self_resolution.py",
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


@pytest.fixture()
def planted_violation():
    """Create a temporary production module containing a direct mutation."""
    probe = REPO_ROOT / "ui" / f"_guard_probe_{uuid.uuid4().hex}.py"
    probe.write_text(
        "from core import app_state\n"
        "def _probe():\n"
        "    app_state.plot_marker_size = 42\n",
        encoding="utf-8",
    )
    try:
        yield probe
    finally:
        probe.unlink(missing_ok=True)


def test_state_mutation_guard_detects_planted_violation(planted_violation) -> None:
    result = run_guard_script("check_state_mutations.py")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "TOTAL=0" not in result.stdout
    assert planted_violation.name in result.stdout


def test_state_mutation_guard_scans_from_any_cwd(planted_violation) -> None:
    """Running from a subdirectory must still scan the whole repository."""
    result = run_guard_script("check_state_mutations.py", cwd=str(REPO_ROOT / "tests"))
    assert result.returncode == 1, result.stdout + result.stderr
    assert planted_violation.name in result.stdout


def test_state_dict_mutation_guard_detects_planted_violation() -> None:
    probe = REPO_ROOT / "ui" / f"_guard_probe_{uuid.uuid4().hex}.py"
    probe.write_text(
        "from core import app_state\n"
        "def _probe():\n"
        "    app_state.umap_params['n_neighbors'] = 7\n",
        encoding="utf-8",
    )
    try:
        result = run_guard_script("check_state_dict_mutations.py")
        assert result.returncode == 1, result.stdout + result.stderr
        assert probe.name in result.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_gateway_generic_guard_covers_plugins_and_utils() -> None:
    """plugins/ and utils/ were outside the scanned roots."""
    probe = REPO_ROOT / "plugins" / f"_guard_probe_{uuid.uuid4().hex}.py"
    # Build the call name at runtime so this test file itself does not
    # contain the literal pattern the tests-scope guard scans for.
    probe.write_text(
        "from core import state_gateway\n"
        "def _probe():\n"
        "    state_gateway.set_" + "attr('plot_marker_size', 42)\n",
        encoding="utf-8",
    )
    try:
        result = run_guard_script("check_gateway_generic_mutations.py")
        assert result.returncode == 1, result.stdout + result.stderr
        assert probe.name in result.stdout
    finally:
        probe.unlink(missing_ok=True)


def test_scan_pattern_hits_honors_allowlist(tmp_path: Path) -> None:
    src = tmp_path / "a.py"
    src.write_text("dummy_set('x', 1)\ndummy_set('y', 2)\n", encoding="utf-8")

    pattern = re.compile(r"\bdummy_set\s*\(")

    counts = scan_pattern_hits(
        tmp_path,
        pattern=pattern,
        include_file=lambda path, root: path.suffix == ".py",
        allowlist={"a.py"},
    )

    assert counts == {}


def test_scan_pattern_hits_collects_counts(tmp_path: Path) -> None:
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("sample_state.x = 1\nsample_state.y = 2\n", encoding="utf-8")
    file_b.write_text("sample_state.z = 3\n", encoding="utf-8")

    pattern = re.compile(r"sample_state\.[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)")

    counts = scan_pattern_hits(
        tmp_path,
        pattern=pattern,
        include_file=lambda path, root: path.suffix == ".py",
    )

    assert counts == {"a.py": 2, "b.py": 1}


def test_print_scan_result_outputs_total_and_sorted_rows(capsys) -> None:
    counts = {"b.py": 1, "a.py": 3}
    print_scan_result(counts)

    out = capsys.readouterr().out.strip().splitlines()
    assert out[0] == "TOTAL=4"
    assert out[1] == "3\ta.py"
    assert out[2] == "1\tb.py"
