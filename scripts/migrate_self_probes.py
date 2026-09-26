"""Codemod: replace getattr(self, "widget", None) / hasattr(self, "widget") with direct
attribute access.

The probed widget names are declared as class attributes (default None) on the class
that uses them, which is equivalent - a missing attribute and an attribute that is None
behave the same - and makes the dependency visible instead of hidden behind a probe.

Usage:
    python scripts/migrate_self_probes.py ui/panels/foo.py [more files...]

It refreshes scripts/self_attribute_probes_baseline.json afterwards, so the ratchet
guard (scripts/check_self_attribute_probes.py) records the reduction.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GETATTR = re.compile(r"getattr\(self,\s*([\"'])([A-Za-z_][\w]*)\1,\s*None\)")
HASATTR = re.compile(r"hasattr\(self,\s*([\"'])([A-Za-z_][\w]*)\1\)")


def _probe_classes(path: Path) -> dict[str, set[str]]:
    """class name -> names probed with getattr/hasattr on self inside that class."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    result: dict[str, set[str]] = {}
    for cls in [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]:
        names: set[str] = set()
        for node in ast.walk(cls):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in {"getattr", "hasattr"} and len(node.args) >= 2:
                    target, attr = node.args[0], node.args[1]
                    if isinstance(target, ast.Name) and target.id == "self" and isinstance(attr, ast.Constant):
                        names.add(str(attr.value))
        if names:
            result[cls.name] = names
    return result


def migrate(rel: str) -> None:
    path = ROOT / rel
    text = path.read_text(encoding="utf-8")
    per_class = _probe_classes(path)
    if not per_class:
        print(f"{rel}: no probes")
        return

    tree = ast.parse(text)
    classes = {c.name: c for c in ast.walk(tree) if isinstance(c, ast.ClassDef)}
    lines = text.splitlines(keepends=True)
    for class_name, names in sorted(per_class.items(), key=lambda kv: classes[kv[0]].lineno, reverse=True):
        cls = classes[class_name]
        body = cls.body
        insert_at = body[0].lineno - 1
        if (
            isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            insert_at = body[0].end_lineno
        existing = {
            name for name in names
            if re.search(rf"^\s+{name}\s*=\s*None\s*$", text, flags=re.MULTILINE)
        }
        todo = sorted(names - existing)
        if not todo:
            continue
        block = "".join(f"    {name} = None\n" for name in todo)
        block += (
            "\n    # Declared by the class that uses them, so no probe is needed for widgets\n"
            "    # that build() creates later (UI review item B).\n"
        )
        lines.insert(insert_at, block)
        print(f"  {rel}: {class_name} <- {len(todo)} class attributes")

    text = "".join(lines)
    text = GETATTR.sub(lambda m: f"self.{m.group(2)}", text)
    text = HASATTR.sub(lambda m: f"self.{m.group(2)} is not None", text)
    path.write_text(text, encoding="utf-8")
    compiled = subprocess.run(
        [sys.executable, "-c", f"import py_compile; py_compile.compile(r'{rel}', doraise=True)"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    print(f"  {rel}: compile {'OK' if compiled.returncode == 0 else compiled.stderr[-200:]}")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for rel in sys.argv[1:]:
        migrate(rel)
    subprocess.run([sys.executable, "scripts/check_self_attribute_probes.py", "--update"], cwd=str(ROOT))
    check = subprocess.run(
        [sys.executable, "scripts/check_self_attribute_probes.py"],
        cwd=str(ROOT), capture_output=True, text=True,
    )
    print("guard:", " | ".join(check.stdout.strip().splitlines()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
