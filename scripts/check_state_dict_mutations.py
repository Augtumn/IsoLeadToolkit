"""Check in-place dict mutations on _sync_state-managed app_state dict fields.

Detects patterns like ``app_state.umap_params[key] = value`` that modify
state-store-managed dicts in-place without syncing the snapshot.  Only flags
fields that :meth:`StateStore._sync_state` overwrites with ``dict()`` copies
— in-place mutations on those fields are silently lost on the next dispatch.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from source_scan_guard import print_scan_result, scan_pattern_hits

# Dict fields that _sync_state() overwrites with fresh dict() copies.
# In-place mutation on these is silently lost on the next dispatch.
_SYNCED_DICT_FIELDS: set[str] = {
    "umap_params",
    "tsne_params",
    "pca_params",
    "robust_pca_params",
    "ml_params",
    "v1v2_params",
    "plot_font_sizes",
    "current_palette",
    "group_marker_map",
    "overlay_artists",
    "isochron_results",
    "plumbotectonics_group_visibility",
}

# Match app_state.<dict_field>[<key>] = <value>
PATTERN = re.compile(r"app_state\.([a-z_][a-z0-9_]*)\[[^\]]+\]\s*=")
EXCLUDED_PARTS = {".venv", "reference", ".git", "__pycache__", "tests", "scripts"}

# Files whose mutations are immediately followed by state_gateway.set_*_params()
ALLOWLIST: set[str] = {
    "ui/panels/data/projection.py",
    "ui/panels/data/build.py",
    "visualization/plotting/geochem/isochron_fits.py",
}


def should_scan(path: Path, _repo_root: Path) -> bool:
    if path.suffix != ".py":
        return False
    return not any(part in EXCLUDED_PARTS for part in path.parts)


def _find_mutations(root: Path) -> dict[str, list[tuple[int, str]]]:
    """Return {relative_path: [(line_no, field_name), ...]} for unsynced hits."""
    results: dict[str, list[tuple[int, str]]] = {}
    for file_path in root.rglob("*.py"):
        if not should_scan(file_path, root):
            continue
        rel = file_path.relative_to(root).as_posix()
        if rel in ALLOWLIST:
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in PATTERN.finditer(text):
            field = m.group(1)
            if field not in _SYNCED_DICT_FIELDS:
                continue
            line_no = text[: m.start()].count("\n") + 1
            results.setdefault(rel, []).append((line_no, field))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect unsynced in-place dict mutations on _sync_state-managed fields."
    )
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    root = Path.cwd()
    mutations = _find_mutations(root)

    total = sum(len(hits) for hits in mutations.values())
    print(f"TOTAL={total}")

    if total > 0:
        print(
            "\nUnsynced in-place dict mutations "
            "(add state_gateway.set_<field>(app_state.<field>) after each):"
        )
        for rel in sorted(mutations):
            print(f"\n{rel}:")
            for line_no, field in mutations[rel]:
                print(f"  L{line_no}: app_state.{field}[...] = ...")

    if args.fail_on_hits and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
