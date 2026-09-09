"""Check for missing or untranslated localization entries."""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


def _load_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _iter_python_files(root: Path) -> list[Path]:
    ignore_dirs = {
        ".venv",
        "__pycache__",
        "reference",
        "build",
        "dist",
        ".git",
        "assets",
        "docs",
        "locales",
    }
    paths: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignore_dirs for part in path.parts):
            continue
        paths.append(path)
    return paths


def _collect_translate_keys(py_path: Path) -> set[str]:
    try:
        source = py_path.read_text(encoding="utf-8")
    except Exception:
        return set()

    try:
        tree = ast.parse(source, filename=str(py_path))
    except SyntaxError:
        return set()

    keys: set[str] = set()
    passthrough_calls = {"make_group"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and (func.id == "translate" or func.id in passthrough_calls):
            if not node.args:
                continue
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                keys.add(first.value)
    return keys


def _write_report(path: Path, lines: list[str]) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    locales_dir = repo_root / "locales"
    en_path = locales_dir / "en.json"
    zh_path = locales_dir / "zh.json"

    en_data = _load_json(en_path)
    zh_data = _load_json(zh_path)

    code_keys: set[str] = set()
    for py_path in _iter_python_files(repo_root):
        code_keys.update(_collect_translate_keys(py_path))

    en_keys = set(en_data.keys())
    zh_keys = set(zh_data.keys())
    expected_keys = en_keys | zh_keys | code_keys

    missing_in_zh = sorted(expected_keys - zh_keys)
    missing_in_en = sorted(expected_keys - en_keys)
    code_missing_both = sorted(code_keys - en_keys - zh_keys)
    untranslated_zh = sorted(
        key for key, value in zh_data.items()
        if isinstance(value, str) and value.strip() == key.strip()
    )

    lines: list[str] = []
    lines.append("Localization Untranslated Report")
    lines.append("=" * 32)
    lines.append(f"Total code keys: {len(code_keys)}")
    lines.append(f"en.json keys: {len(en_keys)}")
    lines.append(f"zh.json keys: {len(zh_keys)}")
    lines.append("")

    def _section(title: str, items: list[str]) -> None:
        lines.append(title)
        lines.append("-" * len(title))
        if not items:
            lines.append("(none)")
        else:
            lines.extend(items)
        lines.append("")

    _section("Missing in zh.json", missing_in_zh)
    _section("Missing in en.json", missing_in_en)
    _section("Code keys missing in both", code_missing_both)
    _section("Untranslated zh values (value == key)", untranslated_zh)

    report_path = locales_dir / "reports" / "untranslated.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    _write_report(report_path, lines)
    print(f"Report written to: {report_path}")

    # Fail the check when keys used by the code have no entry in either
    # locale: silently exiting 0 let drift (e.g. "Unknown error") ship.
    if code_missing_both or missing_in_zh or missing_in_en:
        print(
            "MISSING_KEYS=%s (code missing both=%s, missing in zh=%s, "
            "missing in en=%s)"
            % (
                len(code_missing_both) + len(missing_in_zh) + len(missing_in_en),
                len(code_missing_both),
                len(missing_in_zh),
                len(missing_in_en),
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
