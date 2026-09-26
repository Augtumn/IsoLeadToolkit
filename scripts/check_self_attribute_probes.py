"""Guard: no new getattr(self, "widget", ...) / hasattr(self, "widget") probes.

Panels reach for their widgets defensively because the attribute may not exist yet,
which hides typos and makes dependencies invisible (see docs/ui_architecture_review.md
item B). The count is ratcheted: a file may keep its current probes or reduce them, but
adding new ones fails this guard. Migrating a file means lowering its baseline with
``--update``.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASELINE = Path(__file__).resolve().parent / "self_attribute_probes_baseline.json"
PATTERN = re.compile(r"(?:hasattr|getattr)\(self,\s*[\"']([A-Za-z_][\w]*)[\"']")


def count_probes() -> dict[str, int]:
    counts: dict[str, int] = {}
    for path in sorted((ROOT / "ui").rglob("*.py")):
        found = len(PATTERN.findall(path.read_text(encoding="utf-8")))
        if found:
            counts[path.relative_to(ROOT).as_posix()] = found
    return counts


def load_baseline() -> dict[str, int]:
    if not BASELINE.exists():
        return {}
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true", help="write the current counts as the baseline")
    parser.add_argument("--fail-on-hits", action="store_true", help="exit non-zero when the ratchet is broken")
    args = parser.parse_args()

    current = count_probes()
    if args.update:
        BASELINE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"baseline updated: {sum(current.values())} probes in {len(current)} files")
        return 0

    baseline = load_baseline()
    regressions = {
        name: (baseline.get(name, 0), count)
        for name, count in current.items()
        if count > baseline.get(name, 0)
    }
    total = sum(current.values())
    if regressions:
        print(f"TOTAL={len(regressions)}")
        for name, (was, now) in sorted(regressions.items()):
            print(f"1\t{name}: {was} -> {now} probes (migrate or lower the baseline with --update)")
        return 1

    saved = sum(baseline.values()) - total
    print("# probes: %d in %d files (baseline %d%s)" % (total, len(current), sum(baseline.values()),
                                                        f", reduced by {saved}" if saved else ""))
    print("TOTAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
