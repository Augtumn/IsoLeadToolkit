"""The hardcoded-text checker: it must catch text that skips translate, and only that.

A checker nobody has seen fail is not a checker, so the detector is exercised directly on source written
for the test: one file whose labels go through ``translate`` and one whose labels do not.
"""
from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "locales" / "check_hardcoded_text.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("check_hardcoded_text_under_test", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "sample.py"
    path.write_text("from core import translate\n" + body, encoding="utf-8")
    return path


def test_reports_a_label_that_never_reaches_translate(tmp_path) -> None:
    module = _load_module()
    path = _write(
        tmp_path,
        "def build(button, label, dialog):\n"
        "    button.setText('Save the project')\n"
        "    label.setText('Choose a grouping column')\n"
        "    dialog.setWindowTitle(f'Color for {label}')\n",
    )

    found = {value for _line, value in module._candidates_in(path)}
    assert "Save the project" in found
    assert "Choose a grouping column" in found
    assert "Color for " in found


def test_accepts_text_that_goes_through_translate(tmp_path) -> None:
    module = _load_module()
    path = _write(
        tmp_path,
        "def build(button, label):\n"
        "    button.setText(translate('Save the project'))\n"
        "    label.setText(translate('Color for {group}').format(group='Tarim'))\n",
    )

    assert module._candidates_in(path) == []


def test_accepts_identifiers_and_codes(tmp_path) -> None:
    """A mode code, a state key and a CSS fragment are not prose."""
    module = _load_module()
    path = _write(
        tmp_path,
        "def build(combo, style, state):\n"
        "    combo.addItem('RobustPCA')\n"
        "    style.setText('color: #111827; border: 1px solid')\n"
        "    state.setObjectName('currentIndex')\n",
    )

    assert module._candidates_in(path) == []


def test_the_repository_has_no_new_candidates() -> None:
    """The ratchet: today's candidates are recorded in the baseline with a reason each."""
    result = runpy.run_path(str(SCRIPT), run_name="__not_main__")
    assert callable(result["main"])
    sys.argv = [str(SCRIPT), "--fail-on-hits"]
    assert result["main"]() == 0
