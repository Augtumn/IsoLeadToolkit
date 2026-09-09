"""Guard scripts must actually detect violations (positive tests).

Regression context: the guards anchored to ``Path.cwd()`` and matched
excluded directories against *absolute* path parts, so a scan could print
``TOTAL=0`` while inspecting nothing at all.
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from tests.guard_helpers import run_guard_script

REPO_ROOT = Path(__file__).resolve().parents[1]


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
