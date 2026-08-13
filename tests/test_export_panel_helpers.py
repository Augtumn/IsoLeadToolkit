"""Tests for export panel helper logic (pure/static parts, offscreen-safe)."""

from __future__ import annotations

from types import SimpleNamespace

from core import app_state, state_gateway
from ui.panels.export.common import ExportPanelCommonMixin
from ui.panels.export.data_export import ExportPanelDataExportMixin


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
