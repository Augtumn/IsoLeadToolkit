"""The algorithm modes come from one definition, not from six copies of the same four names.

Reported by the health check: the set {"UMAP", "tSNE", "PCA", "RobustPCA"} was written out by hand in the render use
case, the event bridge, two dispatch handlers, the normaliser and the data panel, and the same four modes were also
derived from the capability table. A mode added to one copy would have been forgotten in the others.
"""
from __future__ import annotations

import pathlib
import re

from core.render_modes import algorithm_modes


def test_the_algorithm_modes_are_the_four_embedding_modes() -> None:
    assert set(algorithm_modes()) == {"UMAP", "tSNE", "PCA", "RobustPCA"}


def test_every_algorithm_mode_has_an_algorithm() -> None:
    from core.render_modes import MODE_CAPABILITIES

    for mode in algorithm_modes():
        assert MODE_CAPABILITIES[mode].has_algorithm, mode


def test_no_module_writes_the_four_names_out_again() -> None:
    """Two files legitimately hold a longer list beginning with these four - the default option list, which also
    offers V1V2, and the embedding adapter mode tuple, which is a different set - and the capability table names
    them one per line. Everywhere else the names come from algorithm_modes().
    """
    root = pathlib.Path(__file__).resolve().parents[1]
    allowed = {
        "core/config.py",
        "core/render_modes.py",
        "visualization/plotting/rendering/adapters/embedding_modes.py",
    }
    pattern = re.compile(r"""["\x27]UMAP["\x27]\s*,\s*["\x27]tSNE["\x27]\s*,\s*["\x27]PCA["\x27]\s*,\s*["\x27]RobustPCA["\x27]""")
    offenders = []
    for folder in ("application", "core", "ui", "visualization"):
        for path in (root / folder).rglob("*.py"):
            relative = path.relative_to(root).as_posix()
            if relative in allowed:
                continue
            if pattern.search(path.read_text(encoding="utf-8")):
                offenders.append(relative)
    assert not offenders, "these write the four algorithm names out by hand: " + repr(offenders)
