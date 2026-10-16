"""The render modes, their capabilities, and the renderer's own lists must agree.

Every place that kept its own tuple of modes could fall out of step with the modes the application
offers, and they did: the Plumbotectonics panel listed its own controls and left two modes out, the
"does editing a model redraw?" checks left them out as well, and the asynchronous algorithm set was
written twice. This checks the ones that are still stored separately and fails when they drift.

Run with --fail-on-hits for a non-zero exit, as the other checks in this directory do.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Imported at module level, not inside the check: a check that re-imports its own inputs cannot be
# shown to fail, and a guard nobody can prove fails is not a guard.
from application.use_cases.render_plot import _ASYNC_EMBEDDING_ALGORITHMS  # noqa: E402
from core.render_modes import (  # noqa: E402
    MODE_CAPABILITIES,
    RENDER_MODE_VALUES,
    asynchronous_modes,
)
from visualization.plotting.rendering.adapters import register_adapters  # noqa: E402
from visualization.plotting.rendering.registry import (  # noqa: E402
    registered_modes,
    unregistered_modes,
)


def _problems() -> list[str]:
    problems: list[str] = []

    listed = set(RENDER_MODE_VALUES)
    described = set(MODE_CAPABILITIES)
    for mode in sorted(listed - described):
        problems.append(f"core/render_modes.py: mode {mode!r} has no capabilities recorded")
    for mode in sorted(described - listed):
        problems.append(f"core/render_modes.py: capabilities for {mode!r}, which is not a listed mode")
    if len(RENDER_MODE_VALUES) != len(listed):
        problems.append("core/render_modes.py: the mode list repeats a value")

    if problems:
        # The two tables already disagree; asking more of them would raise rather than report, and a
        # check reports.
        return problems

    # Every mode the application offers is drawn by an adapter. This is what the migration was for: the
    # dispatch used to end in an else that handed anything unrecognised to the embedding renderer.
    try:
        register_adapters()
    except Exception as err:  # a broken adapter is a broken build, and it is reported as one
        problems.append(f"could not register the adapters: {err}")
        return problems
    missing = unregistered_modes()
    if missing:
        problems.append(
            "no adapter draws " + ", ".join(missing) + f"; registered: {registered_modes()}"
        )

    # The renderer decides asynchronously by its own set; it must be exactly the recorded one.
    recorded = set(asynchronous_modes())
    if set(_ASYNC_EMBEDDING_ALGORITHMS) != recorded:
        problems.append(
            "application/use_cases/render_plot.py: _ASYNC_EMBEDDING_ALGORITHMS "
            f"{sorted(_ASYNC_EMBEDDING_ALGORITHMS)} != the recorded {sorted(recorded)}"
        )

    # ...and so does the worker's caller, which keeps a second copy of the same set.
    events_source = (ROOT / "visualization" / "events.py").read_text(encoding="utf-8")
    marker = "_ASYNC_EMBEDDING_ALGORITHMS"
    if marker in events_source:
        start = events_source.index(marker)
        line = events_source[start : events_source.index("\n", start)]
        missing = [mode for mode in recorded if f'"{mode}"' not in line and f"'{mode}'" not in line]
        if missing:
            problems.append(
                "visualization/events.py: _ASYNC_EMBEDDING_ALGORITHMS does not name "
                f"{sorted(missing)}"
            )

    return problems


def main() -> int:
    problems = _problems()
    if problems:
        print(json.dumps(problems, indent=2, ensure_ascii=False))
    else:
        print("  every mode has its capabilities, and the asynchronous set is the recorded one")
    print(f"TOTAL={len(problems)}")
    if problems and "--fail-on-hits" in sys.argv:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
