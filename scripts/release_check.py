#!/usr/bin/env python3
"""Pre-release quality check — validates project is ready for release.

Run: uv run python scripts/release_check.py
Exit: 0 on all-pass, 1 on any failure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_check(description: str, result: subprocess.CompletedProcess[str]) -> bool:
    """Print PASS/FAIL for a subprocess-based check."""
    if result.returncode == 0:
        print(f"  PASS  {description}")
        return True
    print(f"  FAIL  {description}")
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"         {line}")
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            print(f"         {line}")
    return False


def check_tests() -> bool:
    """Run the full pytest suite."""
    print("\n[Tests] Running pytest (this may take a while)...")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=line"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return _run_check("All tests pass", proc)


def check_guard(script_name: str) -> bool:
    """Run a source-guard script with --fail-on-hits."""
    script_path = _REPO_ROOT / "scripts" / script_name
    proc = subprocess.run(
        [sys.executable, str(script_path), "--fail-on-hits"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return _run_check(f"Guard: {script_name}", proc)


def check_import(name: str, import_stmt: str) -> bool:
    """Check that a Python import succeeds."""
    proc = subprocess.run(
        [sys.executable, "-c", f"{import_stmt}; print('OK')"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return _run_check(f"Import: {name}", proc)


def check_scienceplots() -> bool:
    """Check SciencePlots is importable."""
    proc = subprocess.run(
        [sys.executable, "-c", "import scienceplots; print('OK')"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    return _run_check("SciencePlots available", proc)


def check_fonts() -> bool:
    """Check primary and CJK fonts are registered with matplotlib."""
    code = """
from matplotlib.font_manager import fontManager
names = {f.name for f in fontManager.ttflist}
primary = any(n in names for n in ('Arial', 'Helvetica', 'DejaVu Sans'))
cjk = any(n in names for n in ('SimHei', 'Microsoft YaHei', 'KaiTi', 'STSong', 'Adobe Song Std', 'Adobe Heiti Std'))
print('primary_ok=' + str(primary))
print('cjk_ok=' + str(cjk))
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode != 0:
        print("  FAIL  Fonts available")
        print(f"         {proc.stderr.strip()}")
        return False
    output = proc.stdout.strip()
    primary_ok = "primary_ok=True" in output
    cjk_ok = "cjk_ok=True" in output
    if primary_ok and cjk_ok:
        print("  PASS  Fonts available (primary + CJK)")
        return True
    if not primary_ok:
        print("  FAIL  Fonts available — primary fonts missing")
    if not cjk_ok:
        print("  FAIL  Fonts available — CJK fonts missing")
    return False


def check_file_exists(description: str, *rel_paths: str) -> bool:
    """Check that one or more files exist under the repo root."""
    all_ok = True
    for rel in rel_paths:
        p = _REPO_ROOT / rel
        if p.exists():
            print(f"  PASS  {description}: {rel}")
        else:
            print(f"  FAIL  {description}: {rel} (not found)")
            all_ok = False
    return all_ok


# ---------------------------------------------------------------------------
# Ordered checks (name, callable)
# ---------------------------------------------------------------------------
CHECKS: list[tuple[str, callable]] = [  # type: ignore[type-arg]
    ("pytest", check_tests),
    ("check_state_mutations.py", lambda: check_guard("check_state_mutations.py")),
    (
        "check_gateway_direct_state_assignments.py",
        lambda: check_guard("check_gateway_direct_state_assignments.py"),
    ),
    (
        "check_gateway_generic_mutations.py",
        lambda: check_guard("check_gateway_generic_mutations.py"),
    ),
    (
        "check_state_dict_mutations.py",
        lambda: check_guard("check_state_dict_mutations.py"),
    ),
    (
        "core.state",
        lambda: check_import("core.state", "from core.state import app_state, state_gateway"),
    ),
    (
        "ui.main_window",
        lambda: check_import("ui.main_window", "from ui.main_window import Qt5MainWindow"),
    ),
    ("SciencePlots", check_scienceplots),
    ("fonts", check_fonts),
    (
        "build.spec",
        lambda: check_file_exists("Build spec exists", "build.spec"),
    ),
    (
        "pyproject.toml",
        lambda: check_file_exists("pyproject.toml exists", "pyproject.toml"),
    ),
    (
        "locales",
        lambda: check_file_exists("Locales exist", "locales/en.json", "locales/zh.json"),
    ),
    (
        "assets",
        lambda: check_file_exists("Assets exist", "assets/icons/logo.png"),
    ),
]


def main() -> int:
    print("=" * 60)
    print("  Pre-Release Quality Check")
    print("=" * 60)
    print(f"  Repository: {_REPO_ROOT}")
    print()

    passed = 0
    failed = 0
    for name, fn in CHECKS:
        ok = fn()
        if ok:
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"  Results: {passed} passed, {failed} failed  (of {len(CHECKS)} checks)")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
