"""守卫：静默异常处理器（except: pass / 仅 logger.debug）不得增加。

评审 D/E 项遗留：视图层把异常吞掉，问题只在用户面前表现为"没反应"。基线按文件记录，
迁移一批就下调一批；新增静默处理器立即失败。
"""
from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BASELINE = Path(__file__).resolve().parent / "silent_exceptions_baseline.json"
SCANNED = ("ui", "visualization", "application")


def silent_handlers(path: Path) -> int:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return 0
    count = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        body = [n for n in node.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        if not body:
            count += 1
            continue
        if len(body) == 1:
            only = body[0]
            if isinstance(only, ast.Pass):
                count += 1
            elif isinstance(only, ast.Expr) and isinstance(only.value, ast.Call):
                source = ast.unparse(only.value)
                if "logger.debug" in source or "logger.info" in source:
                    count += 1
    return count


def scan() -> dict[str, int]:
    counts: dict[str, int] = {}
    for base in SCANNED:
        for path in sorted((ROOT / base).rglob("*.py")):
            found = silent_handlers(path)
            if found:
                counts[path.relative_to(ROOT).as_posix()] = found
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--fail-on-hits", action="store_true")
    args = parser.parse_args()

    current = scan()
    if args.update:
        BASELINE.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"baseline updated: {sum(current.values())} handlers in {len(current)} files")
        return 0

    baseline = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    regressions = {
        name: (baseline.get(name, 0), count) for name, count in current.items() if count > baseline.get(name, 0)
    }
    if regressions:
        print(f"TOTAL={len(regressions)}")
        for name, (was, now) in sorted(regressions.items()):
            print(f"1\t{name}: {was} -> {now} silent handlers (make them visible or adjust the baseline)")
        return 1

    total = sum(current.values())
    saved = sum(baseline.values()) - total
    print(f"# silent handlers: {total} in {len(current)} files" + (f" (down {saved})" if saved else ""))
    print("TOTAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
