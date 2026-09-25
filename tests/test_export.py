"""Export use cases and export-panel helper tests."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from application.use_cases.export_data import (
    _parse_linear_expression,
    _unique_sheet_name,
    append_selected_data_to_excel,
    build_export_dataframe,
    export_dataframe_to_file,
    export_selected_data_to_file,
)
from application.use_cases.export_image import (
    DEFAULT_EXPORT_HEIGHT_RATIO,
    MIN_EXPORT_DPI,
    build_image_export_profile,
    normalize_export_target,
    resolve_image_save_options,
)
from core import app_state, state_gateway
from ui.panels.export.common import ExportPanelCommonMixin
from ui.panels.export.export_legends import ExportPanelLegendMixin
from ui.panels.export.data_export import ExportPanelDataExportMixin


def test_build_export_dataframe_with_umap_dimensions() -> None:
    df_global = pd.DataFrame(
        {
            "sample": ["A", "B", "C"],
            "value": [10, 20, 30],
        }
    )
    embedding = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    export_df = build_export_dataframe(
        selected_indices=[0, 2],
        df_global=df_global,
        embedding=embedding,
        embedding_type="UMAP",
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params={"n_neighbors": 15},
        render_mode="UMAP",
    )

    assert list(export_df["sample"]) == ["A", "C"]
    assert list(export_df["UMAP 1"]) == [0.1, 0.5]
    assert list(export_df["UMAP 2"]) == [0.2, 0.6]
    assert list(export_df["param_n_neighbors"]) == [15, 15]


def test_build_export_dataframe_2d_ignores_stale_embedding() -> None:
    """2D/3D exports must not append stale embedding coordinates."""
    df_global = pd.DataFrame(
        {
            "sample": ["A", "B", "C"],
            "X": [1.0, 2.0, 3.0],
            "Y": [4.0, 5.0, 6.0],
        }
    )
    stale_embedding = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    export_df = build_export_dataframe(
        selected_indices=[0, 1, 2],
        df_global=df_global,
        embedding=stale_embedding,
        embedding_type="UMAP",
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        axis_labels={"x": "X", "y": "Y"},
        render_mode="2D",
    )

    assert list(export_df.columns) == ["sample", "X", "Y"]


def test_build_export_dataframe_geochem_appends_kappa_model() -> None:
    """PB_EVOL_86 must export kappa_model (the actual result key), not 'kappa'."""
    df_global = pd.DataFrame(
        {
            "sample": ["A", "B"],
            "206Pb/204Pb": [18.0, 19.0],
            "207Pb/204Pb": [15.6, 15.7],
            "208Pb/204Pb": [38.5, 39.0],
        }
    )

    export_df = build_export_dataframe(
        selected_indices=[0, 1],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        render_mode="PB_EVOL_86",
    )

    assert "kappa_model" in export_df.columns
    assert "kappa" not in export_df.columns
    assert "mu_model" in export_df.columns
    assert "t_Model (Ma)" in export_df.columns
    # Values are finite (engine parameters are initialized).
    assert export_df["kappa_model"].notna().all()


def test_export_selected_data_to_file_csv_has_bom(tmp_path: Path) -> None:
    """CSV exports use utf-8-sig so Excel renders CJK names correctly."""
    df_global = pd.DataFrame({"样品": ["甲", "乙"], "值": [1.0, 2.0]})

    target = export_selected_data_to_file(
        selected_indices=[0, 1],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        file_path=str(tmp_path / "out.csv"),
        preferred_format="csv",
        render_mode="UMAP",
    )

    raw = Path(target).read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "CSV must start with a UTF-8 BOM"
    assert "样品".encode("utf-8") in raw


def test_append_selected_data_to_excel_renames_duplicate_sheet(tmp_path: Path) -> None:
    df_global = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    target = str(tmp_path / "out.xlsx")

    first = append_selected_data_to_excel(
        selected_indices=[0, 1],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        file_path=target,
        sheet_name="Data",
        render_mode="UMAP",
    )
    assert Path(first).exists()

    # Second append with the same sheet name must not silently overwrite.
    second = append_selected_data_to_excel(
        selected_indices=[0],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        file_path=target,
        sheet_name="Data",
        render_mode="UMAP",
    )
    import openpyxl

    wb = openpyxl.load_workbook(second)
    try:
        assert wb.sheetnames == ["Data", "Data1"]
    finally:
        wb.close()


def test_parse_linear_expression() -> None:
    assert _parse_linear_expression("y = 1.0049*x + 20.259") == (1.0049, 20.259)
    assert _parse_linear_expression("y = -0.5 x - 3") == (-0.5, -3.0)
    assert _parse_linear_expression("y = 2e-3*x + 1.5") == (0.002, 1.5)
    assert _parse_linear_expression("not linear") == (None, None)
    assert _parse_linear_expression("") == (None, None)


def test_unique_sheet_name() -> None:
    assert _unique_sheet_name("Data", set()) == "Data"
    assert _unique_sheet_name("Data", {"Data"}) == "Data1"
    assert _unique_sheet_name("Data", {"Data", "Data1"}) == "Data2"


def test_export_dataframe_to_csv_with_preferred_suffix(tmp_path: Path) -> None:
    data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})

    target = export_dataframe_to_file(
        dataframe=data,
        file_path=str(tmp_path / "export_result"),
        preferred_format="csv",
    )

    assert target.endswith(".csv")
    assert (tmp_path / "export_result.csv").exists()


def test_normalize_export_target_appends_supported_extension() -> None:
    normalized_path, ext = normalize_export_target("figure_output", "svg")

    assert normalized_path.endswith(".svg")
    assert ext == "svg"


def test_normalize_export_target_rewrites_unsupported_extension() -> None:
    normalized_path, ext = normalize_export_target("figure.badext", "png")

    assert normalized_path.endswith(".png")
    assert ext == "png"


def test_resolve_image_save_options_applies_bounds() -> None:
    profile = build_image_export_profile("science_single")

    options = resolve_image_save_options(
        profile=profile,
        dpi_override=50,
        bbox_tight=True,
        transparent=True,
        pad_inches=-0.5,
        default_dpi=300,
    )

    assert options["dpi"] == MIN_EXPORT_DPI
    assert options["bbox_tight"] is True
    assert options["transparent"] is True
    assert options["pad_inches"] == 0.0


def test_export_profiles_use_named_default_height_ratio() -> None:
    science = build_image_export_profile("science_single")
    ieee = build_image_export_profile("ieee_single")

    assert science["height_ratio"] == DEFAULT_EXPORT_HEIGHT_RATIO
    assert ieee["height_ratio"] == DEFAULT_EXPORT_HEIGHT_RATIO


class _FakeText:
    def __init__(self, text: str) -> None:
        self._text = text

    def get_text(self) -> str:
        return self._text


class _FakeBbox:
    def __init__(self, points):
        self._points = points

    def get_points(self):
        return self._points


class _IdentityTransform:
    def inverted(self):
        return self

    def transform(self, points):
        return points


class _FakeTitle:
    def set_visible(self, _visible: bool) -> None:
        return None

    def set_fontsize(self, _size: float) -> None:
        return None


class _FakeRebuiltLegend:
    def set_title(self, _title: str) -> None:
        return None

    def get_title(self) -> _FakeTitle:
        return _FakeTitle()


class _FakeLegend:
    def __init__(self, points) -> None:
        self._bbox = _FakeBbox(points)
        self._loc = "best"
        self._ncols = 1
        self.legend_handles = [object()]

    def get_texts(self):
        return [_FakeText("Group A")]

    def get_frame_on(self) -> bool:
        return True

    def get_bbox_to_anchor(self):
        return self._bbox

    def remove(self) -> None:
        return None


class _FakeAxis:
    def __init__(self, points) -> None:
        self._legend = _FakeLegend(points)
        self.transAxes = _IdentityTransform()
        self.legend_kwargs = None

    def get_legend(self):
        return self._legend

    def get_legend_handles_labels(self):
        return [object()], ["Group A"]

    def legend(self, **kwargs):
        self.legend_kwargs = kwargs
        return _FakeRebuiltLegend()


class _FakePanel(ExportPanelLegendMixin, ExportPanelCommonMixin):
    @staticmethod
    def _apply_legend_marker_size_from_point(_legend, _point_size: float) -> None:
        return None


def test_normalize_export_legends_collapses_near_point_bbox_anchor() -> None:
    panel = _FakePanel()
    axis = _FakeAxis(points=((0.2, 0.3), (0.2 + 1e-12, 0.3 + 1e-12)))
    fig = SimpleNamespace(axes=[axis])

    panel._normalize_export_legends(fig, profile={"legend": {}}, legend_size_override=8, legend_marker_override=50)

    assert axis.legend_kwargs is not None
    assert axis.legend_kwargs["bbox_to_anchor"] == (0.2, 0.3)


def test_normalize_export_legends_keeps_bbox_extent_for_area_anchor() -> None:
    panel = _FakePanel()
    axis = _FakeAxis(points=((0.2, 0.3), (0.5, 0.6)))
    fig = SimpleNamespace(axes=[axis])

    panel._normalize_export_legends(fig, profile={"legend": {}}, legend_size_override=8, legend_marker_override=50)

    assert axis.legend_kwargs is not None
    assert axis.legend_kwargs["bbox_to_anchor"] == (0.2, 0.3, 0.3, 0.3)


class _Stub:
    pass


def test_profile_default_params() -> None:
    profile = {
        "point_size": 48,
        "dpi": 300,
        "legend": {"fontsize": 7.0},
    }
    params = ExportPanelCommonMixin._profile_default_params(profile)
    assert params["point_size"] == 48
    assert params["dpi"] == 300
    assert params["legend_size"] == 7
    assert params["label_size"] == 9  # fontsize + 2
    assert params["title_size"] == 10  # fontsize + 3
    assert params["tick_size"] == 6  # round(7.0 - 0.5) -> banker's rounding
    assert params["tight_bbox"] is True
    assert params["transparent"] is False
    assert params["image_ext"] == "png"


def test_resolve_export_save_options_with_overrides() -> None:
    stub = _Stub()
    profile = {"dpi": 300}
    options = ExportPanelCommonMixin._resolve_export_save_options(
        stub, profile, overrides={"dpi": 96, "tight_bbox": True, "transparent": True, "pad_inches": 0.1}
    )
    assert options["dpi"] == 96
    assert options["bbox_tight"] is True
    assert options["transparent"] is True
    assert options["pad_inches"] == 0.1

    # DPI floor is enforced.
    options = ExportPanelCommonMixin._resolve_export_save_options(
        stub, profile, overrides={"dpi": 10, "tight_bbox": False, "transparent": False, "pad_inches": -1}
    )
    assert options["dpi"] == 72
    assert options["pad_inches"] == 0.0


def test_resolve_export_indices_selected_or_all() -> None:
    previous = getattr(app_state, "selected_indices", None)
    previous_df = getattr(app_state, "df_global", None)
    try:
        import pandas as pd

        state_gateway.clear_selected_indices()
        state_gateway.set_dataframe_and_source(
            pd.DataFrame({"x": [1, 2, 3]}), file_path="t.csv", sheet_name=None
        )
        # No selection -> all rows, sorted.
        assert ExportPanelDataExportMixin._resolve_export_indices() == [0, 1, 2]

        state_gateway.set_selected_indices({2, 0})
        # Selected rows come back sorted (deterministic order).
        assert ExportPanelDataExportMixin._resolve_export_indices() == [0, 2]
    finally:
        if previous is not None:
            state_gateway.set_selected_indices(previous)
        if previous_df is not None:
            state_gateway.set_dataframe_and_source(
                previous_df, file_path="", sheet_name=None
            )


def test_current_export_context_carries_pca_variance_and_v1v2_params() -> None:
    previous_embedding = getattr(app_state, "last_embedding", None)
    previous_type = getattr(app_state, "last_embedding_type", None)
    previous_variance = getattr(app_state, "last_pca_variance", None)
    previous_mode = getattr(app_state, "render_mode", None)
    previous_v1v2 = getattr(app_state, "v1v2_params", None)
    try:
        state_gateway.set_last_embedding([[1.0, 2.0]], "PCA")
        state_gateway.set_pca_diagnostics(last_pca_variance=[0.85, 0.10])
        state_gateway.set_render_mode("V1V2")
        state_gateway.set_v1v2_params({"a": 0.0, "b": 2.0367, "c": -6.143, "scale": 1.0})
        state_gateway.set_pca_params({"n_components": 2})

        context = ExportPanelDataExportMixin._current_export_context()
        assert context["pca_variance"] == [0.85, 0.10]
        assert context["algorithm_params"]["b"] == 2.0367
        assert context["algorithm_params"]["scale"] == 1.0
    finally:
        state_gateway.set_embedding_task_token(0)
        if previous_embedding is not None:
            state_gateway.set_last_embedding(previous_embedding, str(previous_type or "PCA"))
        if previous_variance is not None:
            state_gateway.set_pca_diagnostics(last_pca_variance=previous_variance)
        if previous_mode is not None:
            state_gateway.set_render_mode(previous_mode)
        if previous_v1v2 is not None:
            state_gateway.set_v1v2_params(previous_v1v2)


def test_geochem_export_skips_when_208pb_missing(monkeypatch, caplog) -> None:
    """Missing 208Pb must skip the derived columns, never fabricate a constant."""
    import logging

    from application.use_cases import export_data as export_module

    df = pd.DataFrame({
        "206Pb/204Pb": [18.5, 18.6],
        "207Pb/204Pb": [15.6, 15.7],
    })

    with caplog.at_level(logging.WARNING, logger=export_module.__name__):
        result = export_module._compute_geochem_params(df, "PB_EVOL_86")

    assert result == {}
    assert "missing columns" in caplog.text
    assert "208Pb/204Pb" in caplog.text


def test_geochem_export_uses_real_208pb_when_present(monkeypatch) -> None:
    from application.use_cases import export_data as export_module

    df = pd.DataFrame({
        "206Pb/204Pb": [18.5, 18.6],
        "207Pb/204Pb": [15.6, 15.7],
        "208Pb/204Pb": [38.5, 38.6],
    })

    captured: dict = {}

    def _fake_calc(pb206, pb207, pb208, **kwargs):
        captured["pb208"] = np.asarray(pb208, dtype=float)
        captured["kwargs"] = kwargs
        return {"kappa_model": np.full_like(pb206, 1.0)}

    monkeypatch.setattr("data.geochemistry.calculate_all_parameters", _fake_calc)
    result = export_module._compute_geochem_params(df, "PB_KAPPA_AGE")

    assert "kappa_model" in result
    assert np.allclose(captured["pb208"], [38.5, 38.6])
