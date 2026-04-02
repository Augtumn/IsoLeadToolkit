"""Shared helpers for guard-script based tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_guard_script(script_name: str) -> subprocess.CompletedProcess[str]:
    """Run a guard script from scripts/ with fail-on-hits mode enabled."""
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / script_name

    return subprocess.run(
        [sys.executable, str(script_path), "--fail-on-hits"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )


def assert_guard_clean(result: subprocess.CompletedProcess[str]) -> None:
    """Assert guard run finished successfully with zero findings."""
    assert result.returncode == 0, result.stdout + result.stderr
    assert "TOTAL=0" in result.stdout
