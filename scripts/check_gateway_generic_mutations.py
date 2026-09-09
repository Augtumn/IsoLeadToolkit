"""Check generic state gateway mutation calls in production Python files."""

from __future__ import annotations

import argparse
from pathlib import Path

from gateway_mutation_guard import print_scan_result, scan_generic_gateway_calls
from source_scan_guard import repo_root

EXCLUDED_PARTS = {".venv", "reference", ".git"}
# Production roots that must not use the generic gateway writers. plugins/
# and utils/ were previously unscanned, leaving the rule unenforced there.
TARGET_ROOTS = {"application", "core", "data", "ui", "visualization", "plugins", "utils"}
# Standalone entry-point scripts are covered by their own root check.
TARGET_FILES = {"main.py"}


def should_scan(path: Path, repo_root: Path) -> bool:
    if path.suffix != ".py":
        return False
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False

    try:
        rel = path.relative_to(repo_root)
    except ValueError:
        return False

    if not rel.parts:
        return False
    if rel.as_posix() in TARGET_FILES:
        return True
    if rel.parts[0] not in TARGET_ROOTS:
        return False
    if rel.as_posix() == "core/state/gateway.py":
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    root = repo_root()
    counts = scan_generic_gateway_calls(root, include_file=should_scan)
    total = sum(counts.values())
    print_scan_result(counts)

    if args.fail_on_hits and total > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
