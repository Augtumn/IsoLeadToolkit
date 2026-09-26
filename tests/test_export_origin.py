"""Origin export tests: extraction, project building (with a stubbed originpro),
the Excel fallback and the failure reasons reported to the UI."""
from __future__ import annotations

from pathlib import Path

import matplotlib
import pandas as pd
import pytest

matplotlib.use("Agg")

from matplotlib.figure import Figure  # noqa: E402

from application.use_cases import export_origin  # noqa: E402
from core import app_state  # noqa: E402


# ── fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture()
def scatter_axes():
    """A 2D axes with two labelled scatter groups."""
    figure = Figure(figsize=(4.0, 3.0))
    axis = figure.add_subplot(111)
    axis.scatter([1.0, 2.0, 3.0], [1.5, 2.5, 3.5], label="GroupA", c="#ff0000")
    axis.scatter([4.0, 5.0], [1.0, 2.0], label="GroupB", c="#0000ff")
    axis.set_xlabel("206Pb/204Pb")
    axis.set_ylabel("207Pb/204Pb")
    return axis


@pytest.fixture()
def patched_axes(monkeypatch, scatter_axes):
    monkeypatch.setattr(app_state, "ax", scatter_axes, raising=False)
    monkeypatch.setattr(app_state, "render_mode", "2D", raising=False)
    monkeypatch.setattr(app_state, "group_marker_map", {"GroupA": "o", "GroupB": "s"}, raising=False)
    monkeypatch.setattr(app_state, "current_plot_title", "Test plot", raising=False)
    return scatter_axes


# ── pure helpers ──────────────────────────────────────────────────────────

def test_hex_color_converts_and_falls_back() -> None:
    assert export_origin._hex_color("#ff0000") == "#ff0000"
    assert export_origin._hex_color((0.0, 0.0, 1.0)) == "#0000ff"
    assert export_origin._hex_color("not-a-color") == "#333333"


def test_origin_marker_maps_known_symbols() -> None:
    assert export_origin._origin_marker("o") == 1
    assert export_origin._origin_marker("s") == 0
    assert export_origin._origin_marker("totally-unknown") == 1


def test_origin_sheet_name_sanitises_and_deduplicates() -> None:
    used: set[str] = set()
    first = export_origin._origin_sheet_name("Pb 206/204", "", used)
    second = export_origin._origin_sheet_name("Pb 206/204", "", used)
    assert first == "Pb_206_204"
    assert second == "Pb_206_204_1", "sheet names must stay unique"
    assert export_origin._origin_sheet_name("", "", used) == "Sheet"

    weird = export_origin._origin_sheet_name("a[b]*c?d\\e", "OV_", used)
    assert all(ch not in weird for ch in "[]*?\\"), weird

    long_name = export_origin._origin_sheet_name("x" * 60, "", used)
    assert len(long_name.replace("_1", "")) <= 28


# ── extraction ────────────────────────────────────────────────────────────

def test_collect_origin_export_data_reads_scatter_groups(scatter_axes) -> None:
    data = export_origin.collect_origin_export_data(scatter_axes, mode="2D")

    assert data["mode"] == "2D"
    assert data["is_ternary"] is False
    labels = [group["label"] for group in data["scatter_groups"]]
    assert labels == ["GroupA", "GroupB"]
    first = data["scatter_groups"][0]
    assert first["x"] == [1.0, 2.0, 3.0]
    assert first["y"] == [1.5, 2.5, 3.5]
    assert first["color"] == "#ff0000"
    assert first["marker"] == 1
    assert data["axis_labels"]["x"] == "206Pb/204Pb"
    assert data["axis_labels"]["y"] == "207Pb/204Pb"
    assert data["overlay_data"] == {}
    assert data["isochron_lines"] == []
    assert data["equation_lines"] == []


def test_collect_origin_export_data_without_collections_is_empty() -> None:
    figure = Figure()
    axis = figure.add_subplot(111)
    axis.plot([0.0, 1.0], [0.0, 1.0])
    data = export_origin.collect_origin_export_data(axis, mode="2D")
    assert data["scatter_groups"] == []


def test_pb_evolution_overlays_are_extracted_without_origin() -> None:
    curves = export_origin._extract_pb_evolution_overlay_data("PB_EVOL_76", (0.0, 45.0))
    assert curves, "PB evolution modes must provide model curves"
    for entries in curves.values():
        assert entries
        for x_arr, y_arr, _label, _style in entries:
            assert len(x_arr) == len(y_arr) > 0


# ── .opju project building with a stubbed originpro ──────────────────────

class _StubSheet:
    def __init__(self, name: str, calls: list[tuple]) -> None:
        self.name = name
        self.calls = calls
        self.columns: dict[int, tuple[list, str]] = {}
        self.axis_designation: str | None = None

    def from_list(self, column: int, data, long_name: str = "") -> None:
        self.columns[column] = (list(data), long_name)
        self.calls.append(("from_list", self.name, column, long_name, len(list(data))))

    def cols_axis(self, designation: str) -> None:
        self.axis_designation = designation
        self.calls.append(("cols_axis", self.name, designation))


class _StubBook:
    def __init__(self, calls: list[tuple], fail: bool = False) -> None:
        self.calls = calls
        self.sheets: list[_StubSheet] = []
        self.fail = fail

    def add_sheet(self, name: str) -> _StubSheet:
        if self.fail:
            raise RuntimeError("Origin is not running")
        sheet = _StubSheet(name, self.calls)
        self.sheets.append(sheet)
        self.calls.append(("add_sheet", name))
        return sheet


class _StubPlot:
    def __init__(self, kind: str, calls: list[tuple]) -> None:
        self.color = None
        self.symbol_kind = None
        self.symbol_size = None
        self.width = None
        self.kind = kind
        self.calls = calls

    def _record(self, name: str, value) -> None:
        self.calls.append(("plot_attr", name, value))


class _StubAxis:
    def __init__(self) -> None:
        self.title = None


class _StubLegend:
    def __init__(self) -> None:
        self.text = ""
        self.ints: dict[str, int] = {}

    def set_int(self, key: str, value: int) -> None:
        self.ints[key] = value


class _StubLayer:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls
        self.axes: dict[str, _StubAxis] = {}
        self.legend = _StubLegend()
        self.title: str | None = None
        self.plots: list[_StubPlot] = []

    def add_plot(self, sheet, coly: int = 1, colx: int = 0, type: str = "s", colz=None) -> _StubPlot:
        plot = _StubPlot(type, self.calls)
        self.plots.append(plot)
        self.calls.append(("add_plot", sheet.name, type, colx, coly, colz))
        return plot

    def group(self) -> None:
        self.calls.append(("group",))

    def rescale(self) -> None:
        self.calls.append(("rescale",))

    def label(self, kind: str) -> _StubLegend:
        self.calls.append(("label", kind))
        return self.legend

    def axis(self, name: str) -> _StubAxis:
        return self.axes.setdefault(name, _StubAxis())

    def set_str(self, key: str, value: str) -> None:
        self.calls.append(("set_str", key, value))


class _StubGraphProvider:
    def __init__(self, calls: list[tuple]) -> None:
        self.calls = calls
        self.layer = _StubLayer(calls)
        self.saved: list[tuple] = []

    def __getitem__(self, index: int) -> _StubLayer:
        assert index == 0
        return self.layer

    def save_fig(self, path: str, width: int = 0) -> bool:
        self.saved.append((path, width))
        self.calls.append(("save_fig", path, width))
        return True


class _StubOrigin:
    def __init__(self, fail_book: bool = False) -> None:
        self.calls: list[tuple] = []
        self.book = _StubBook(self.calls, fail=fail_book)
        self.graph = _StubGraphProvider(self.calls)
        self.saved: list[str] = []

    def new_book(self, kind: str, title: str) -> _StubBook:
        self.calls.append(("new_book", kind, title))
        return self.book

    def new_graph(self, template: str = "scatter") -> _StubGraphProvider:
        self.calls.append(("new_graph", template))
        return self.graph

    def save(self, path: str) -> bool:
        self.saved.append(path)
        self.calls.append(("save", path))
        return True


def _patch_origin(monkeypatch, stub: _StubOrigin | None) -> None:
    monkeypatch.setattr(export_origin, "_lazy_import_originpro", lambda: stub)


def test_origin_project_exports_sheets_plots_legend_and_axis_titles(
    monkeypatch, patched_axes, tmp_path: Path
) -> None:
    stub = _StubOrigin()
    _patch_origin(monkeypatch, stub)
    target = tmp_path / "project.opju"

    ok, reason = export_origin.export_to_origin_detailed(str(target))

    assert ok is True, reason
    assert reason == ""

    sheet_names = [call[1] for call in stub.calls if call[0] == "add_sheet"]
    assert sheet_names == ["GroupA", "GroupB"]

    assert stub.book.sheets[0].columns[0][1] == "X"
    assert stub.book.sheets[0].columns[1][1] == "Y"
    assert [call[0] for call in stub.calls].count("add_plot") == 2
    assert stub.graph.layer.plots[0].color == "#ff0000"
    assert stub.graph.layer.plots[1].symbol_kind == 0  # GroupB marker "s"

    legend_text = stub.graph.layer.legend.text
    assert "GroupA" not in legend_text  # legend uses Origin's %(n,@WS) references
    assert legend_text.count("\\l(") == 2

    assert stub.graph.layer.axes["x"].title == "206Pb/204Pb"
    assert stub.graph.layer.axes["y"].title == "207Pb/204Pb"
    assert stub.saved == [str(target)]
    assert stub.graph.saved and stub.graph.saved[0][0].endswith("project.png")


def test_origin_project_returns_reason_when_building_fails(
    monkeypatch, patched_axes, tmp_path: Path
) -> None:
    stub = _StubOrigin(fail_book=True)
    _patch_origin(monkeypatch, stub)

    ok, reason = export_origin.export_to_origin_detailed(str(tmp_path / "project.opju"))

    assert ok is False
    assert "Origin" in reason


def test_origin_export_reports_missing_package(monkeypatch, patched_axes, tmp_path: Path) -> None:
    _patch_origin(monkeypatch, None)
    ok, reason = export_origin.export_to_origin_detailed(str(tmp_path / "project.opju"))
    assert ok is False and "originpro" in reason

    # the bool API stays compatible
    assert export_origin.export_to_origin(str(tmp_path / "project.opju")) is False


def test_origin_export_reports_missing_axes(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(app_state, "ax", None, raising=False)
    _patch_origin(monkeypatch, _StubOrigin())
    ok, reason = export_origin.export_to_origin_detailed(str(tmp_path / "project.opju"))
    assert ok is False and "axes" in reason


def test_origin_export_reports_missing_scatter_data(monkeypatch, tmp_path: Path) -> None:
    figure = Figure()
    axis = figure.add_subplot(111)
    axis.plot([0.0, 1.0], [0.0, 1.0])  # no labelled scatter collections
    monkeypatch.setattr(app_state, "ax", axis, raising=False)
    monkeypatch.setattr(app_state, "render_mode", "2D", raising=False)
    _patch_origin(monkeypatch, _StubOrigin())

    ok, reason = export_origin.export_to_origin_detailed(str(tmp_path / "project.opju"))
    assert ok is False and "scatter" in reason


# ── Excel fallback (no originpro) ────────────────────────────────────────

def test_origin_ready_data_writes_one_sheet_per_series(patched_axes, tmp_path: Path) -> None:
    target = tmp_path / "origin_data.xlsx"

    assert export_origin.export_origin_ready_data(str(target)) is True
    assert target.exists()

    workbook = pd.read_excel(target, sheet_name=None)
    assert set(workbook) == {"Info", "GroupA", "GroupB"}

    group_a = workbook["GroupA"]
    assert list(group_a.columns) == ["206Pb/204Pb", "207Pb/204Pb"]
    assert group_a["206Pb/204Pb"].tolist() == [1.0, 2.0, 3.0]
    assert workbook["GroupB"]["207Pb/204Pb"].tolist() == [1.0, 2.0]

    info = workbook["Info"].set_index("Item")["Value"]
    assert info["Render mode"] == "2D"
    assert info["Plot title"] == "Test plot"
    assert "Import" in info["How to import"]


def test_origin_ready_data_uses_unique_sheet_names(tmp_path: Path, monkeypatch) -> None:
    figure = Figure()
    axis = figure.add_subplot(111)
    # two groups whose labels collapse to the same sheet name
    axis.scatter([1.0, 2.0], [1.0, 2.0], label="Pb 206/204", c="#111111")
    axis.scatter([3.0, 4.0], [3.0, 4.0], label="Pb:206:204", c="#222222")
    monkeypatch.setattr(app_state, "ax", axis, raising=False)
    monkeypatch.setattr(app_state, "render_mode", "2D", raising=False)
    monkeypatch.setattr(app_state, "group_marker_map", {}, raising=False)

    target = tmp_path / "dupes.xlsx"
    assert export_origin.export_origin_ready_data(str(target)) is True
    sheets = set(pd.read_excel(target, sheet_name=None))
    assert len(sheets) == 3, sheets  # Info + two deduplicated series sheets


def test_origin_ready_data_without_axes_or_data_is_reported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_state, "ax", None, raising=False)
    assert export_origin.export_origin_ready_data(str(tmp_path / "none.xlsx")) is False

    figure = Figure()
    axis = figure.add_subplot(111)
    axis.plot([0.0, 1.0], [0.0, 1.0])
    monkeypatch.setattr(app_state, "ax", axis, raising=False)
    assert export_origin.export_origin_ready_data(str(tmp_path / "empty.xlsx")) is False
