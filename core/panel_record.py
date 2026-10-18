"""One panel, described once.

The health check found four representations of the same panel state, kept consistent by hand, with two panel bugs
traced to them disagreeing. This class is the contract they converge on.

It lives in core, not in visualization where the panel helpers are: the render use case builds render-state records and
an application module may not import a presentation module, which the layering guard reported as soon as the first
version had it in visualization/plotting/panels.py.
"""
from __future__ import annotations


class PanelRecord(dict):
    """One panel, described once: its window and what it draws.

    The health check found four representations of the same panel state - the mode list, the window records, the
    render states and the panel area's own records - "manually kept consistent", with two panel bugs traced to them
    disagreeing. This class is the single contract they are converging on: the keys it declares are the ones a panel
    record has.

    It stays a dict subclass while the call sites move, so a migration does not have to finish in one step: every
    existing ``record.get("mode")`` keeps working, and the properties are what new code uses. ``KEYS`` is what a test
    compares the consumers against, so a key used but not declared here fails a test instead of a panel silently
    doing nothing.

    The two kinds of record today carry different subsets: a window record has ``window``, ``figure``, ``canvas``,
    ``toolbar``, ``axes``, ``needs_fit``, ``legend`` and ``active``; a render-state record has ``ax``, ``collections``,
    ``artist_to_sample``, ``sample_to_artist`` and ``group_to_scatter``. Both carry ``mode``.
    """

    #: Every key a panel record may carry. Adding one is the first step of adding it to a panel.
    KEYS = (
        # window records
        "window",
        "mode",
        "figure",
        "canvas",
        "axes",
        "toolbar",
        "needs_fit",
        "active",
        "legend",
        # render-state records
        "ax",
        "collections",
        "artist_to_sample",
        "sample_to_artist",
        "group_to_scatter",
    )

    @property
    def mode(self) -> str:
        return str(self.get("mode") or "")

    @property
    def window(self):
        return self.get("window")

    @property
    def figure(self):
        return self.get("figure")

    @property
    def canvas(self):
        return self.get("canvas")

    @property
    def axes(self):
        return self.get("axes")

    @property
    def ax(self):
        return self.get("ax")

    @property
    def toolbar(self):
        return self.get("toolbar")

    @property
    def active(self) -> bool:
        return bool(self.get("active"))

    @property
    def needs_fit(self) -> bool:
        return bool(self.get("needs_fit"))

    @property
    def legend(self) -> dict:
        return dict(self.get("legend") or {})

    @property
    def collections(self) -> list:
        return list(self.get("collections") or [])

    @property
    def artist_to_sample(self) -> dict:
        return dict(self.get("artist_to_sample") or {})

    @property
    def sample_to_artist(self) -> dict:
        return dict(self.get("sample_to_artist") or {})

    @property
    def group_to_scatter(self) -> dict:
        return dict(self.get("group_to_scatter") or {})
