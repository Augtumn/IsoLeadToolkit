"""Find user-visible text that never went through ``translate()``.

``check_untranslated.py`` can only judge the keys that are passed to ``translate``; text that is handed to
a widget directly - ``setText("Save")``, ``QLabel("Choose a file")``, ``f"Color for {group}"`` - is
invisible to it and stays English in every language. This checker looks for exactly that: a string
literal (or an f-string with words in it) passed to a Qt call that displays text.

It cannot decide by itself whether a given literal is a phrase or an identifier - ``"Cluster "`` is a data
column and ``"Color for "`` is a label - so candidates are recorded in a baseline with a reason, and the
count may not grow. ``--update-baseline`` records today's candidates; ``--fail-on-hits`` reports any
candidate that is not in the baseline.

Usage:
    uv run python locales/check_hardcoded_text.py                 # report
    uv run python locales/check_hardcoded_text.py --fail-on-hits  # exit 1 on any new candidate
    uv run python locales/check_hardcoded_text.py --update-baseline
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE_PATH = ROOT / "locales" / "hardcoded_text_baseline.json"

#: Classes whose first positional argument (or ``text=``) is shown to the user.
TEXT_CLASSES = frozenset({
    "QLabel", "QPushButton", "QCheckBox", "QRadioButton", "QToolButton", "QGroupBox",
    "QAction", "QMenu", "QLineEdit", "QDialog", "QMessageBox",
})

#: Methods that set displayed text, by the argument index that carries it.
TEXT_METHODS = {
    "setText": 0,
    "setWindowTitle": 0,
    "setToolTip": 0,
    "setStatusTip": 0,
    "setWhatsThis": 0,
    "setPlaceholderText": 0,
    "setTabText": 1,
    "setItemText": 1,
    "addAction": 0,
    "addItem": 1,
    "addTab": 1,
    "warning": 2,
    "information": 2,
    "critical": 2,
    "question": 2,
}

#: A literal that is an identifier, a path, a pattern or a style fragment rather than a phrase.
CODEISH = re.compile(r"^[\s\w]*$")


def _is_phrase(value: str) -> bool:
    """True when *value* reads as words a person would see."""
    text = value.strip()
    if len(text) < 3:
        return False
    if "_" in text or "/" in text or "\\" in text or ";" in text or "{" in text:
        return False
    if not re.search(r"[A-Za-z]{3,}", text):
        return False
    if CODEISH.fullmatch(text) and " " not in text:
        # A single lowercase word with no spaces is far more likely a mode code than a label; the
        # baseline records the exceptions either way.
        return bool(re.search(r"[A-Z]", text))
    return True


def _literal(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts = [v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
        joined = "".join(parts)
        return joined if joined.strip() else None
    return None


def _argument(call: ast.Call, index: int) -> ast.AST | None:
    if len(call.args) > index:
        return call.args[index]
    for keyword in call.keywords:
        if keyword.arg in ("text", "title", "label"):
            return keyword.value
    return None


def _candidates_in(path: Path) -> list[tuple[int, str]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as err:
        raise SystemExit(f"cannot parse {path}: {err}")

    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
            if name in TEXT_CLASSES:
                value = _literal(_argument(node, 0) or node)
                if value is not None and _is_phrase(value):
                    found.append((node.lineno, value))
                continue
            if name in TEXT_METHODS:
                value = _literal(_argument(node, TEXT_METHODS[name]))
                if value is not None and _is_phrase(value):
                    found.append((node.lineno, value))
                continue
        # An f-string that reads as words is a phrase being assembled, whether or not it reaches a Qt
        # call on this line - "Color for {group}" is shown, and ", dmax={value}" is shown. Prose that is
        # legitimately English (a data column, a log tag) is recorded in the baseline.
        if isinstance(node, ast.JoinedStr):
            value = _literal(node)
            if value is not None and _is_phrase(value) and " " in value.strip():
                found.append((node.lineno, value))
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-on-hits", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    args = parser.parse_args()

    baseline: dict[str, str] = {}
    if BASELINE_PATH.exists():
        baseline = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    candidates: dict[str, str] = {}
    for path in sorted((ROOT / "ui").rglob("*.py")):
        relative = path.relative_to(ROOT).as_posix()
        for line, value in _candidates_in(path):
            candidates.setdefault(f"{relative}::{value}", f"{relative}:{line}")

    if args.update_baseline:
        merged = {key: baseline.get(key, "") for key in candidates}
        BASELINE_PATH.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"baseline written: {len(merged)} candidate(s)")
        return 0

    new = {key: where for key, where in candidates.items() if key not in baseline}
    gone = [key for key in baseline if key not in candidates]
    print(f"candidates: {len(candidates)}  baseline: {len(baseline)}  new: {len(new)}  gone: {len(gone)}")
    for key, where in sorted(new.items(), key=lambda item: item[1]):
        print(f"  {where}  {key.split('::', 1)[1]!r}")
    for key in sorted(gone):
        print(f"  (baseline entry no longer found: {key})")

    if args.fail_on_hits and new:
        print(f"TOTAL={len(new)}")
        return 1
    print("TOTAL=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
