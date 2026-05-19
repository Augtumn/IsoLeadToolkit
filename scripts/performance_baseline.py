#!/usr/bin/env python3
"""Performance baseline — measures import and first-render times.

Run: uv run python scripts/performance_baseline.py
Exit: 0 on success, 1 if any measurement fails.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _timed_subprocess(name: str, code: str) -> float | None:
    """Run inline Python code and return wall-clock seconds (or None on failure)."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        print(f"  FAIL  {name}: {proc.stderr.strip()[:200]}")
        return None
    return elapsed


def measure_core_import() -> float | None:
    """Time how long it takes to import core modules (cold import)."""
    code = "from core.state import app_state, state_gateway; print('ok')"
    return _timed_subprocess("core.state import", code)


def measure_full_import_chain() -> float | None:
    """Time import of core + ui.main_window (biggest import path)."""
    code = (
        "from core.state import app_state, state_gateway; "
        "from core import translate, CONFIG; "
        "from ui.main_window import Qt5MainWindow; "
        "print('ok')"
    )
    return _timed_subprocess("full import chain", code)


def measure_matplotlib_figure() -> float | None:
    """Time creation of first matplotlib Figure + basic scatter render."""
    code = """
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
t0 = __import__('time').perf_counter()
fig, ax = plt.subplots(figsize=(6, 4))
x = np.random.randn(100)
y = np.random.randn(100)
ax.scatter(x, y)
ax.set_title('Performance Baseline Test')
fig.tight_layout()
fig.canvas.draw()
elapsed = __import__('time').perf_counter() - t0
plt.close(fig)
print(f'{elapsed:.3f}')
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode != 0:
        print(f"  FAIL  matplotlib figure: {proc.stderr.strip()[:200]}")
        return None
    try:
        return float(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print(f"  FAIL  matplotlib figure: could not parse timing ({proc.stdout.strip()[:100]})")
        return None


def measure_test_discovery() -> float | None:
    """Time pytest test collection (proxy for project test overhead)."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-qq"],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        print(f"  FAIL  test discovery: {proc.stderr.strip()[:200]}")
        return None
    return elapsed


def measure_seaborn_kde() -> float | None:
    """Time seaborn KDE computation (heavyweight dependency)."""
    code = """
import matplotlib
matplotlib.use('Agg')
import numpy as np
t0 = __import__('time').perf_counter()
import seaborn as sns
data = np.random.randn(1000)
sns.kdeplot(data=data)
import matplotlib.pyplot as plt
plt.close('all')
elapsed = __import__('time').perf_counter() - t0
print(f'{elapsed:.3f}')
"""
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode != 0:
        print(f"  FAIL  seaborn KDE: {proc.stderr.strip()[:200]}")
        return None
    try:
        return float(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print(f"  FAIL  seaborn KDE: could not parse timing")
        return None


def measure_embedding_import() -> float | None:
    """Time import of ML/embedding heavy dependencies (umap, sklearn, xgboost)."""
    code = (
        "t0 = __import__('time').perf_counter(); "
        "import umap; "
        "from sklearn.decomposition import PCA; "
        "from sklearn.manifold import TSNE; "
        "import xgboost; "
        "elapsed = __import__('time').perf_counter() - t0; "
        "print(f'{elapsed:.3f}')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )
    if proc.returncode != 0:
        print(f"  FAIL  embedding imports: {proc.stderr.strip()[:200]}")
        return None
    try:
        return float(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print(f"  FAIL  embedding imports: could not parse timing")
        return None


# ---------------------------------------------------------------------------
# Ordered measurements
# ---------------------------------------------------------------------------
MEASUREMENTS: list[tuple[str, callable]] = [  # type: ignore[type-arg]
    ("Core import (app_state + gateway)", measure_core_import),
    ("Full import chain (core + ui.main_window)", measure_full_import_chain),
    ("Matplotlib figure + scatter", measure_matplotlib_figure),
    ("Seaborn KDE", measure_seaborn_kde),
    ("ML embedding imports (umap, sklearn, xgboost)", measure_embedding_import),
    ("Test discovery (pytest --collect-only)", measure_test_discovery),
]


def main() -> int:
    print("Performance Baseline")
    print("=" * 60)
    print(f"  Repository: {_REPO_ROOT}")
    print(f"  Python:     {sys.version.split()[0]}")
    print()

    results: list[tuple[str, float | None]] = []
    all_ok = True

    for name, fn in MEASUREMENTS:
        elapsed = fn()
        results.append((name, elapsed))
        if elapsed is None:
            all_ok = False
        else:
            print(f"  {name}: {elapsed:.2f}s")

    print()
    print("=" * 60)
    if all_ok:
        print("  All measurements completed successfully.")
    else:
        print("  Some measurements FAILED (see above).")

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
