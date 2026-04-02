"""Tests for StateStore-backed gateway mutations."""

from __future__ import annotations

from typing import Any

from core import app_state, state_gateway


def _snapshot_state() -> dict[str, Any]:
    return {
        "render_mode": getattr(app_state, "render_mode", "UMAP"),
        "algorithm": getattr(app_state, "algorithm", "UMAP"),
        "selected_indices": set(getattr(app_state, "selected_indices", set()) or set()),
        "selection_mode": bool(getattr(app_state, "selection_mode", False)),
        "df_global": getattr(app_state, "df_global", None),
        "file_path": getattr(app_state, "file_path", None),
        "sheet_name": getattr(app_state, "sheet_name", None),
        "data_version": int(getattr(app_state, "data_version", 0)),
        "group_cols": list(getattr(app_state, "group_cols", []) or []),
        "data_cols": list(getattr(app_state, "data_cols", []) or []),
        "last_group_col": getattr(app_state, "last_group_col", None),
        "selection_tool": getattr(app_state, "selection_tool", None),
        "point_size": int(getattr(app_state, "point_size", 60)),
        "tooltip_columns": list(getattr(app_state, "tooltip_columns", []) or []),
        "ui_theme": str(getattr(app_state, "ui_theme", "Modern Light")),
        "preserve_import_render_mode": bool(getattr(app_state, "preserve_import_render_mode", False)),
        "available_groups": list(getattr(app_state, "available_groups", []) or []),
        "visible_groups": list(getattr(app_state, "visible_groups", []) or []) if getattr(app_state, "visible_groups", None) else None,
        "selected_2d_cols": list(getattr(app_state, "selected_2d_cols", []) or []),
        "selected_3d_cols": list(getattr(app_state, "selected_3d_cols", []) or []),
        "selected_ternary_cols": list(getattr(app_state, "selected_ternary_cols", []) or []),
        "selected_2d_confirmed": bool(getattr(app_state, "selected_2d_confirmed", False)),
        "selected_3d_confirmed": bool(getattr(app_state, "selected_3d_confirmed", False)),
        "selected_ternary_confirmed": bool(getattr(app_state, "selected_ternary_confirmed", False)),
        "export_image_options": dict(getattr(app_state, "export_image_options", {}) or {}),
    }


def _restore_state(snapshot: dict[str, Any]) -> None:
    state_gateway.set_attrs(
        {
            "algorithm": snapshot["algorithm"],
            "selection_mode": snapshot["selection_mode"],
        }
    )
    state_gateway.set_render_mode(str(snapshot["render_mode"]))
    state_gateway.set_algorithm(str(snapshot["algorithm"]))
    state_gateway.set_point_size(int(snapshot["point_size"]))
    state_gateway.set_tooltip_columns(snapshot["tooltip_columns"])
    state_gateway.set_ui_theme(str(snapshot["ui_theme"]))
    state_gateway.set_preserve_import_render_mode(bool(snapshot["preserve_import_render_mode"]))
    state_gateway.set_selection_mode(snapshot["selection_mode"])
    state_gateway.set_selection_tool(snapshot["selection_tool"])
    state_gateway.set_dataframe_and_source(
        snapshot["df_global"],
        file_path=snapshot["file_path"],
        sheet_name=snapshot["sheet_name"],
    )
    state_gateway.set_attr("data_version", snapshot["data_version"])
    state_gateway.set_group_data_columns(snapshot["group_cols"], snapshot["data_cols"])
    state_gateway.set_last_group_col(snapshot["last_group_col"])
    state_gateway.set_selected_indices(snapshot["selected_indices"])
    state_gateway.set_selected_2d_columns(snapshot["selected_2d_cols"], confirmed=snapshot["selected_2d_confirmed"])
    state_gateway.set_selected_3d_columns(snapshot["selected_3d_cols"], confirmed=snapshot["selected_3d_confirmed"])
    state_gateway.set_selected_ternary_columns(snapshot["selected_ternary_cols"], confirmed=snapshot["selected_ternary_confirmed"])
    state_gateway.sync_available_and_visible_groups(snapshot["available_groups"])
    state_gateway.set_visible_groups(snapshot["visible_groups"])
    state_gateway.set_export_image_options(**snapshot["export_image_options"])


def test_state_store_set_render_mode_syncs_algorithm() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_render_mode("PCA")

        assert app_state.render_mode == "PCA"
        assert app_state.algorithm == "PCA"
        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["render_mode"] == "PCA"
    finally:
        _restore_state(snapshot)


def test_state_store_session_preference_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_render_mode("2D")
        state_gateway.set_algorithm("RobustPCA")
        state_gateway.set_point_size(88)
        state_gateway.set_tooltip_columns(["Lab No.", "Period"])
        state_gateway.set_ui_theme("Modern Light")
        state_gateway.set_preserve_import_render_mode(True)

        assert app_state.algorithm == "RobustPCA"
        assert app_state.point_size == 88
        assert app_state.tooltip_columns == ["Lab No.", "Period"]
        assert app_state.ui_theme == "Modern Light"
        assert app_state.preserve_import_render_mode is True

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["algorithm"] == "RobustPCA"
        assert store_snapshot["point_size"] == 88
        assert store_snapshot["tooltip_columns"] == ["Lab No.", "Period"]
        assert store_snapshot["ui_theme"] == "Modern Light"
        assert store_snapshot["preserve_import_render_mode"] is True
    finally:
        _restore_state(snapshot)


def test_state_store_selected_indices_mutations() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_selected_indices({1, 2})
        state_gateway.add_selected_indices([2, 3])
        state_gateway.remove_selected_indices([1])

        assert app_state.selected_indices == {2, 3}
        assert app_state.state_store.snapshot()["selected_indices"] == {2, 3}

        state_gateway.clear_selected_indices()
        assert app_state.selected_indices == set()
    finally:
        _restore_state(snapshot)


def test_state_store_selection_tool_and_mode_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_selection_mode(False)
        assert app_state.selection_mode is False

        state_gateway.set_selection_tool("lasso")
        assert app_state.selection_tool == "lasso"
        assert app_state.selection_mode is True

        state_gateway.clear_selection()
        assert app_state.selected_indices == set()
        assert app_state.selection_mode is False
        # Preserve existing behavior: clear_selection does not clear tool identity.
        assert app_state.selection_tool == "lasso"

        state_gateway.set_selection_tool(None)
        assert app_state.selection_tool is None
        assert app_state.selection_mode is False
    finally:
        _restore_state(snapshot)


def test_state_store_export_image_options_roundtrip() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_export_image_options(
            preset_key="ieee_single",
            image_ext="SVG",
            dpi=50,
            bbox_tight=False,
            pad_inches=-1.0,
            transparent=True,
            point_size=12,
            legend_size=7,
        )
        options = state_gateway.get_export_image_options()

        assert options["preset_key"] == "ieee_single"
        assert options["image_ext"] == "svg"
        assert options["dpi"] == 72
        assert options["bbox_tight"] is False
        assert options["pad_inches"] == 0.0
        assert options["transparent"] is True
        assert options["point_size"] == 12
        assert options["legend_size"] == 7
        assert dict(app_state.export_image_options) == options
    finally:
        _restore_state(snapshot)


def test_state_store_column_selection_domains() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.set_selected_2d_columns(["x", "y"], confirmed=True)
        state_gateway.set_selected_3d_columns(["x", "y", "z"], confirmed=True)
        state_gateway.set_selected_ternary_columns(["a", "b", "c"], confirmed=False)

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["selected_2d_cols"] == ["x", "y"]
        assert store_snapshot["selected_3d_cols"] == ["x", "y", "z"]
        assert store_snapshot["selected_ternary_cols"] == ["a", "b", "c"]
        assert store_snapshot["selected_2d_confirmed"] is True
        assert store_snapshot["selected_3d_confirmed"] is True
        assert store_snapshot["selected_ternary_confirmed"] is False

        state_gateway.reset_column_selection()
        assert app_state.selected_2d_cols == []
        assert app_state.selected_3d_cols == []
        assert app_state.selected_ternary_cols == []
        assert app_state.selected_2d_confirmed is False
        assert app_state.selected_3d_confirmed is False
        assert app_state.selected_ternary_confirmed is False
    finally:
        _restore_state(snapshot)


def test_state_store_available_visible_groups_sync() -> None:
    snapshot = _snapshot_state()
    try:
        state_gateway.sync_available_and_visible_groups(["A", "B", "C"])
        state_gateway.set_visible_groups(["A", "C"])
        assert app_state.visible_groups == ["A", "C"]

        state_gateway.sync_available_and_visible_groups(["B", "C"])
        assert app_state.available_groups == ["B", "C"]
        assert app_state.visible_groups == ["C"]

        state_gateway.set_visible_groups(None)
        assert app_state.visible_groups is None
    finally:
        _restore_state(snapshot)


def test_state_store_data_source_and_columns_domains() -> None:
    snapshot = _snapshot_state()
    try:
        mock_df = {"rows": 2}
        state_gateway.set_dataframe_and_source(mock_df, file_path="d:/tmp/a.xlsx", sheet_name="Sheet1")
        state_gateway.set_group_data_columns(["Group"], ["206Pb/204Pb", "207Pb/204Pb"])
        state_gateway.set_last_group_col("Group")

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["df_global"] is mock_df
        assert store_snapshot["file_path"] == "d:/tmp/a.xlsx"
        assert store_snapshot["sheet_name"] == "Sheet1"
        assert store_snapshot["group_cols"] == ["Group"]
        assert store_snapshot["data_cols"] == ["206Pb/204Pb", "207Pb/204Pb"]
        assert store_snapshot["last_group_col"] == "Group"
    finally:
        _restore_state(snapshot)


def test_state_store_bump_data_version_clears_cache() -> None:
    snapshot = _snapshot_state()
    try:
        app_state.embedding_cache.set(("k",), "v")
        before_version = int(app_state.data_version)
        assert len(app_state.embedding_cache) == 1

        state_gateway.bump_data_version()

        assert app_state.data_version == before_version + 1
        assert len(app_state.embedding_cache) == 0
    finally:
        _restore_state(snapshot)
