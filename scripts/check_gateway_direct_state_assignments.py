"""Check direct app_state assignments in gateway against runtime-only allowlist."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

_PATTERN = re.compile(r"self\._state\.(\w+)\s*=")

# These fields are runtime object references or transient diagnostics and are
# intentionally kept as direct assignments (not StateStore-managed domains).
ALLOWED_DIRECT_FIELDS = {
    "fig",
    "ax",
    "canvas",
    "legend_ax",
    "last_embedding",
    "last_embedding_type",
    "last_pca_variance",
    "last_pca_components",
    "current_feature_names",
    "control_panel_ref",
    "legend_update_callback",
    "group_marker_map",
    "annotation",
    "legend_last_title",
    "legend_last_handles",
    "legend_last_labels",
    "overlay_artists",
    "marginal_axes",
    "embedding_task_token",
    "embedding_worker",
    "embedding_task_running",
    "rectangle_selector",
    "lasso_selector",
    "selection_overlay",
    "selection_ellipse",
    "selected_isochron_data",
}


def scan_disallowed_fields(gateway_file: Path) -> dict[str, int]:
    try:
        text = gateway_file.read_text(encoding="utf-8")
    except Exception:
        return {}

    counts: dict[str, int] = {}
    for field in _PATTERN.findall(text):
        if field in ALLOWED_DIRECT_FIELDS:
            continue
        counts[field] = counts.get(field, 0) + 1
    return counts


def print_scan_result(counts: dict[str, int]) -> None:
    total = sum(counts.values())
    print(f"TOTAL={total}")

    if total <= 0:
        return

    for field, count in sorted(counts.items(), key=lambda item: item[1], reverse=True):
        print(f"{count}\t{field}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    gateway_file = root / "core" / "state" / "gateway.py"
    counts = scan_disallowed_fields(gateway_file)
    total = sum(counts.values())
    print_scan_result(counts)

    if args.fail_on_hits and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
