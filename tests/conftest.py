"""Pytest bootstrap: workspace-local imports and headless test environment.

The Agg backend and the offscreen Qt platform are configured here once so no
test module needs its own ``matplotlib.use`` / ``QT_QPA_PLATFORM`` line; this
runs before any test module is imported.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    sys.path.insert(0, project_root_str)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import matplotlib  # noqa: E402  (must follow the Qt platform setup)

matplotlib.use("Agg")
