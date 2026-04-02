"""Unit tests for generic source scan guard utilities."""

from __future__ import annotations

import re
from pathlib import Path

from scripts.source_scan_guard import print_scan_result, scan_pattern_hits


def test_scan_pattern_hits_honors_allowlist(tmp_path: Path) -> None:
    src = tmp_path / "a.py"
    src.write_text("dummy_set('x', 1)\ndummy_set('y', 2)\n", encoding="utf-8")

    pattern = re.compile(r"\bdummy_set\s*\(")

    counts = scan_pattern_hits(
        tmp_path,
        pattern=pattern,
        include_file=lambda path, root: path.suffix == ".py",
        allowlist={"a.py"},
    )

    assert counts == {}


def test_scan_pattern_hits_collects_counts(tmp_path: Path) -> None:
    file_a = tmp_path / "a.py"
    file_b = tmp_path / "b.py"
    file_a.write_text("sample_state.x = 1\nsample_state.y = 2\n", encoding="utf-8")
    file_b.write_text("sample_state.z = 3\n", encoding="utf-8")

    pattern = re.compile(r"sample_state\.[A-Za-z_][A-Za-z0-9_]*\s*=(?!=)")

    counts = scan_pattern_hits(
        tmp_path,
        pattern=pattern,
        include_file=lambda path, root: path.suffix == ".py",
    )

    assert counts == {"a.py": 2, "b.py": 1}


def test_print_scan_result_outputs_total_and_sorted_rows(capsys) -> None:
    counts = {"b.py": 1, "a.py": 3}
    print_scan_result(counts)

    out = capsys.readouterr().out.strip().splitlines()
    assert out[0] == "TOTAL=4"
    assert out[1] == "3\ta.py"
    assert out[2] == "1\tb.py"
