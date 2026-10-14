"""守卫：多面板路径不得依赖"单图时代的全局单例"。

一个窗口显示多张图之后，`app_state` 里那批"唯一引用"（fig/ax/sample_coordinates/
scatter_collections/paleoisochron_label_data …）**只属于其中一张图**（实际是最后渲染/
最后激活的那张）。任何读它们去"画所有图"的代码，都会把 A 图的东西画到 B 图上去，
并且表现为"只有一个面板正常 / 某面板空白 / 最后一个面板崩"这类**随面板数线性增长**的问题。

本守卫把这些读取点**列成可数清单**（基线机制：不禁止既有数量，只禁止**增加**），
于是"要改哪些"一目了然，从机制上终止"补丁叠补丁"。

用法：
    python scripts/check_panel_singletons.py              # 检查（超出基线则 exit 1）
    python scripts/check_panel_singletons.py --list       # 打印完整清单
    python scripts/check_panel_singletons.py --update-baseline
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = Path(__file__).resolve().parent / "panel_singletons_baseline.json"

#: The single-figure references. Reading any of these in these layers is a multi-panel hazard.
SINGLETON_FIELDS = (
    "app_state.fig",
    "app_state.ax",
    "app_state.sample_coordinates",
    "app_state.scatter_collections",
    "app_state.artist_to_sample",
    "app_state.group_to_scatter",
    "app_state.paleoisochron_label_data",
    "app_state.annotation",
)

#: The layers that must work per panel. `core` owns the state and the ui window keeps the registry,
#: so neither is scanned: they are allowed to name these fields.
SCANNED_DIRS = ("ui", "application", "visualization")

#: Files whose whole job is the single-figure window.
EXEMPT = (
    "ui/app.py",
    "ui/app_parts/plotting.py",
)


def scanned_files() -> list[Path]:
    found: list[Path] = []
    for directory in SCANNED_DIRS:
        for path in (ROOT / directory).rglob("*.py"):
            relative = path.relative_to(ROOT).as_posix()
            if relative in EXEMPT:
                continue
            found.append(path)
    return sorted(found)


def hits_in(path: Path) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return found
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        for field in SINGLETON_FIELDS:
            if re.search(rf"\b{re.escape(field)}\b", line):
                found.append((number, stripped))
                break
    return found


def collect() -> dict[str, list[tuple[int, str]]]:
    per_file: dict[str, list[tuple[int, str]]] = {}
    for path in scanned_files():
        found = hits_in(path)
        if found:
            per_file[path.relative_to(ROOT).as_posix()] = found
    return per_file


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="print every hit")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    current = {name: len(found) for name, found in collect().items()}

    if args.update_baseline:
        BASELINE.write_text(
            json.dumps(current, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"baseline updated: {sum(current.values())} read(s) in {len(current)} file(s)")
        return 0

    if args.list:
        for name, found in sorted(collect().items()):
            print(f"\n{name}  ({len(found)})")
            for number, line in found:
                print(f"  {number:5d}  {line[:110]}")
        print(f"\nTOTAL={sum(current.values())} in {len(current)} file(s)")
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    grown = {
        name: (baseline.get(name, 0), count)
        for name, count in current.items()
        if count > baseline.get(name, 0)
    }
    if not grown:
        print(f"# singleton reads: {sum(current.values())} in {len(current)} file(s) (no growth)")
        print("TOTAL=0")
        return 0

    print("# the multi-panel layers gained reads of the single-figure references:")
    for name, (was, now) in sorted(grown.items()):
        print(f"1\t{name}: {was} -> {now} reads")
    print(f"TOTAL={len(grown)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
