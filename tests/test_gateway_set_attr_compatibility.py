"""Compatibility checks for legacy state_gateway.set_attr routing."""

from __future__ import annotations

import pytest

from core import app_state, state_gateway


def test_group_and_data_columns_set_attr_compatibility() -> None:
    original_group_cols = list(getattr(app_state, "group_cols", []) or [])
    original_data_cols = list(getattr(app_state, "data_cols", []) or [])

    try:
        state_gateway.set_group_data_columns(["G0"], ["A", "B", "C"])

        state_gateway.set_attr("group_cols", ["G1", "G2"])
        assert app_state.group_cols == ["G1", "G2"]
        assert app_state.data_cols == ["A", "B", "C"]

        state_gateway.set_attr("data_cols", ["X", "Y"])
        assert app_state.group_cols == ["G1", "G2"]
        assert app_state.data_cols == ["X", "Y"]

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["group_cols"] == ["G1", "G2"]
        assert store_snapshot["data_cols"] == ["X", "Y"]
    finally:
        state_gateway.set_group_data_columns(original_group_cols, original_data_cols)


def test_tooltip_set_attr_compatibility() -> None:
    original_show_tooltip = bool(getattr(app_state, "show_tooltip", False))

    try:
        state_gateway.set_attr("show_tooltip", True)
        assert app_state.show_tooltip is True
        assert app_state.state_store.snapshot()["show_tooltip"] is True

        state_gateway.set_attr("show_tooltip", False)
        assert app_state.show_tooltip is False
        assert app_state.state_store.snapshot()["show_tooltip"] is False
    finally:
        state_gateway.set_show_tooltip(original_show_tooltip)


def test_export_image_options_set_attr_compatibility() -> None:
    original_options = dict(getattr(app_state, "export_image_options", {}) or {})

    try:
        state_gateway.set_attr(
            "export_image_options",
            {
                "preset_key": "ieee_single",
                "image_ext": "SVG",
                "dpi": 50,
                "bbox_tight": False,
                "pad_inches": -1.0,
                "transparent": True,
                "point_size": 13,
                "legend_size": 8,
            },
        )

        options = state_gateway.get_export_image_options()
        assert options["preset_key"] == "ieee_single"
        assert options["image_ext"] == "svg"
        assert options["dpi"] == 72
        assert options["bbox_tight"] is False
        assert options["pad_inches"] == 0.0
        assert options["transparent"] is True
        assert options["point_size"] == 13
        assert options["legend_size"] == 8
    finally:
        state_gateway.set_export_image_options(**original_options)


@pytest.mark.parametrize(
    "attr",
    [
        "show_model_curves",
        "show_plumbotectonics_curves",
        "show_paleoisochrons",
        "show_model_age_lines",
        "show_growth_curves",
        "show_isochrons",
    ],
)
def test_overlay_toggle_known_attr_compatibility(attr: str) -> None:
    original_value = bool(getattr(app_state, attr, False))

    try:
        state_gateway.set_overlay_toggle(attr, not original_value)
        assert bool(getattr(app_state, attr)) is (not original_value)
    finally:
        state_gateway.set_overlay_toggle(attr, original_value)


def test_overlay_toggle_unknown_attr_ignored() -> None:
    fallback_attr = "_test_overlay_toggle_fallback"
    existed = hasattr(app_state, fallback_attr)
    original_value = bool(getattr(app_state, fallback_attr, False)) if existed else False

    try:
        state_gateway.set_overlay_toggle(fallback_attr, True)
        state_gateway.set_overlay_toggle(fallback_attr, False)
        if existed:
            assert getattr(app_state, fallback_attr) is original_value
        else:
            assert not hasattr(app_state, fallback_attr)
    finally:
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)


def test_palette_and_marker_map_setter_syncs_snapshot() -> None:
    original_palette = dict(getattr(app_state, "current_palette", {}) or {})
    original_marker_map = dict(getattr(app_state, "group_marker_map", {}) or {})

    try:
        state_gateway.set_palette_and_marker_map({"GroupA": "#112233"}, {"GroupA": "s"})

        assert app_state.current_palette == {"GroupA": "#112233"}
        assert app_state.group_marker_map == {"GroupA": "s"}
        assert app_state.state_store.snapshot()["current_palette"] == {"GroupA": "#112233"}
        assert app_state.state_store.snapshot()["group_marker_map"] == {"GroupA": "s"}
    finally:
        state_gateway.set_palette_and_marker_map(original_palette, original_marker_map)


def test_group_marker_map_set_attr_compatibility() -> None:
    original_marker_map = dict(getattr(app_state, "group_marker_map", {}) or {})

    try:
        state_gateway.set_attr("group_marker_map", {"GroupA": "^", "GroupB": "D"})

        assert app_state.group_marker_map == {"GroupA": "^", "GroupB": "D"}
        assert app_state.state_store.snapshot()["group_marker_map"] == {
            "GroupA": "^",
            "GroupB": "D",
        }
    finally:
        state_gateway.set_group_marker_map(original_marker_map)


@pytest.mark.parametrize(
    "attr,payload",
    [
        ("overlay_curve_label_data", [{"text": "A"}]),
        ("paleoisochron_label_data", [{"text": "B"}]),
        ("plumbotectonics_label_data", [{"text": "C"}]),
        ("plumbotectonics_isoage_label_data", [{"text": "D"}]),
    ],
)
def test_overlay_label_data_set_attr_compatibility(attr: str, payload: list[dict[str, str]]) -> None:
    original = list(getattr(app_state, attr, []) or [])

    try:
        state_gateway.set_attr(attr, payload)

        assert getattr(app_state, attr) == payload
        assert app_state.state_store.snapshot()[attr] == payload
    finally:
        state_gateway.set_attr(attr, original)


def test_set_attr_unknown_key_ignored() -> None:
    fallback_attr = "_test_set_attr_unknown"
    existed = hasattr(app_state, fallback_attr)
    original_value = getattr(app_state, fallback_attr, None) if existed else None

    try:
        state_gateway.set_attr(fallback_attr, 123)

        if existed:
            assert getattr(app_state, fallback_attr) == original_value
        else:
            assert not hasattr(app_state, fallback_attr)
    finally:
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)


def test_panel_style_updates_known_key_and_unknown_key() -> None:
    original_plot_style_grid = bool(getattr(app_state, "plot_style_grid", False))
    fallback_attr = "_test_panel_style_unknown"
    existed = hasattr(app_state, fallback_attr)
    original_value = getattr(app_state, fallback_attr, None) if existed else None
    original_selection_mode = bool(getattr(app_state, "selection_mode", False))

    try:
        state_gateway.set_panel_style_updates(
            {
                "plot_style_grid": (not original_plot_style_grid),
                fallback_attr: "ignored",
                "selection_mode": (not original_selection_mode),
            }
        )

        assert bool(getattr(app_state, "plot_style_grid", False)) is (not original_plot_style_grid)
        assert bool(getattr(app_state, "selection_mode", False)) is original_selection_mode
        if existed:
            assert getattr(app_state, fallback_attr) == original_value
        else:
            assert not hasattr(app_state, fallback_attr)
    finally:
        if hasattr(app_state, "plot_style_grid"):
            setattr(app_state, "plot_style_grid", original_plot_style_grid)
        state_gateway.set_selection_mode(original_selection_mode)
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)


def test_overlay_label_state_only_updates_known_keys() -> None:
    original_overlay_curve = list(getattr(app_state, "overlay_curve_label_data", []) or [])
    original_paleo = list(getattr(app_state, "paleoisochron_label_data", []) or [])
    original_plumbo = list(getattr(app_state, "plumbotectonics_label_data", []) or [])
    original_isoage = list(getattr(app_state, "plumbotectonics_isoage_label_data", []) or [])

    try:
        state_gateway.set_overlay_label_state(
            {
                "overlay_curve_label_data": [{"text": "A"}],
                "paleoisochron_label_data": [{"text": "B"}],
                "plumbotectonics_label_data": [{"text": "C"}],
                "plumbotectonics_isoage_label_data": [{"text": "D"}],
            }
        )

        assert app_state.overlay_curve_label_data == [{"text": "A"}]
        assert app_state.paleoisochron_label_data == [{"text": "B"}]
        assert app_state.plumbotectonics_label_data == [{"text": "C"}]
        assert app_state.plumbotectonics_isoage_label_data == [{"text": "D"}]

        snapshot = app_state.state_store.snapshot()
        assert snapshot["overlay_curve_label_data"] == [{"text": "A"}]
        assert snapshot["paleoisochron_label_data"] == [{"text": "B"}]
        assert snapshot["plumbotectonics_label_data"] == [{"text": "C"}]
        assert snapshot["plumbotectonics_isoage_label_data"] == [{"text": "D"}]
    finally:
        state_gateway.set_overlay_label_state(
            {
                "overlay_curve_label_data": original_overlay_curve,
                "paleoisochron_label_data": original_paleo,
                "plumbotectonics_label_data": original_plumbo,
                "plumbotectonics_isoage_label_data": original_isoage,
            }
        )


def test_overlay_label_state_ignores_unknown_keys() -> None:
    fallback_attr = "_test_overlay_label_state_unknown"
    existed = hasattr(app_state, fallback_attr)
    original_value = getattr(app_state, fallback_attr, None) if existed else None

    try:
        state_gateway.set_overlay_label_state({fallback_attr: [{"text": "x"}]})

        if existed:
            assert getattr(app_state, fallback_attr) == original_value
        else:
            assert not hasattr(app_state, fallback_attr)
    finally:
        if existed:
            setattr(app_state, fallback_attr, original_value)
        elif hasattr(app_state, fallback_attr):
            delattr(app_state, fallback_attr)


def test_point_size_set_attr_conversion() -> None:
    original_point_size = int(getattr(app_state, "point_size", 60))

    try:
        state_gateway.set_attr("point_size", "77")
        assert app_state.point_size == 77
        assert app_state.state_store.snapshot()["point_size"] == 77
    finally:
        state_gateway.set_point_size(original_point_size)


def test_pca_diagnostics_set_attr_compatibility() -> None:
    original_variance = getattr(app_state, "last_pca_variance", None)
    original_components = getattr(app_state, "last_pca_components", None)
    original_features = getattr(app_state, "current_feature_names", None)

    try:
        state_gateway.set_attr("last_pca_variance", [0.7, 0.3])
        state_gateway.set_attr("last_pca_components", [[1.0, 0.0], [0.0, 1.0]])
        state_gateway.set_attr("current_feature_names", ["Si", "Pb"])

        assert app_state.last_pca_variance == [0.7, 0.3]
        assert app_state.last_pca_components == [[1.0, 0.0], [0.0, 1.0]]
        assert app_state.current_feature_names == ["Si", "Pb"]

        snapshot = app_state.state_store.snapshot()
        assert snapshot["last_pca_variance"] == [0.7, 0.3]
        assert snapshot["last_pca_components"] == [[1.0, 0.0], [0.0, 1.0]]
        assert snapshot["current_feature_names"] == ["Si", "Pb"]
    finally:
        state_gateway.set_pca_diagnostics(
            last_pca_variance=original_variance,
            last_pca_components=original_components,
            current_feature_names=original_features,
        )


def test_last_embedding_and_selected_isochron_set_attr_compatibility() -> None:
    original_embedding = getattr(app_state, "last_embedding", None)
    original_embedding_type = str(getattr(app_state, "last_embedding_type", "") or "")
    original_selected_isochron_data = getattr(app_state, "selected_isochron_data", None)

    try:
        state_gateway.set_attr("last_embedding_type", "TERNARY")
        state_gateway.set_attr("last_embedding", [[0.1, 0.2], [0.3, 0.4]])
        state_gateway.set_attr("selected_isochron_data", {"group": "B", "mswd": 1.7})

        assert app_state.last_embedding_type == "TERNARY"
        assert app_state.last_embedding == [[0.1, 0.2], [0.3, 0.4]]
        assert app_state.selected_isochron_data == {"group": "B", "mswd": 1.7}

        snapshot = app_state.state_store.snapshot()
        assert snapshot["last_embedding_type"] == "TERNARY"
        assert snapshot["last_embedding"] == [[0.1, 0.2], [0.3, 0.4]]
        assert snapshot["selected_isochron_data"] == {"group": "B", "mswd": 1.7}
    finally:
        state_gateway.set_last_embedding(original_embedding, original_embedding_type)
        state_gateway.set_selected_isochron_data(original_selected_isochron_data)


def test_ui_theme_set_attr_conversion() -> None:
    original_theme = str(getattr(app_state, "ui_theme", "Modern Light"))

    try:
        state_gateway.set_attr("ui_theme", 123)
        assert app_state.ui_theme == "123"
        assert app_state.state_store.snapshot()["ui_theme"] == "123"
    finally:
        state_gateway.set_ui_theme(original_theme)


def test_language_set_attr_conversion() -> None:
    original_language = str(getattr(app_state, "language", "zh"))

    try:
        state_gateway.set_attr("language", 123)
        assert app_state.language == "123"
        assert app_state.state_store.snapshot()["language"] == "123"
    finally:
        state_gateway.set_language_code(original_language)


def test_geo_model_name_set_attr_conversion() -> None:
    original_model_name = str(getattr(app_state, "geo_model_name", "Stacey & Kramers (2nd Stage)"))

    try:
        state_gateway.set_attr("geo_model_name", 123)
        assert app_state.geo_model_name == "123"
        assert app_state.state_store.snapshot()["geo_model_name"] == "123"
    finally:
        state_gateway.set_geo_model_name(original_model_name)


def test_file_and_sheet_set_attr_compatibility() -> None:
    original_file_path = getattr(app_state, "file_path", None)
    original_sheet_name = getattr(app_state, "sheet_name", None)

    try:
        state_gateway.set_attr("file_path", "d:/tmp/demo.xlsx")
        state_gateway.set_attr("sheet_name", "SheetA")

        assert app_state.file_path == "d:/tmp/demo.xlsx"
        assert app_state.sheet_name == "SheetA"

        snapshot = app_state.state_store.snapshot()
        assert snapshot["file_path"] == "d:/tmp/demo.xlsx"
        assert snapshot["sheet_name"] == "SheetA"
    finally:
        state_gateway.set_file_path(original_file_path)
        state_gateway.set_sheet_name(original_sheet_name)


def test_plot_title_and_last_2d_cols_set_attr_compatibility() -> None:
    original_title = str(getattr(app_state, "current_plot_title", ""))
    original_last_2d_cols = (
        list(getattr(app_state, "last_2d_cols", []) or [])
        if getattr(app_state, "last_2d_cols", None) is not None
        else None
    )

    try:
        state_gateway.set_attr("current_plot_title", 123)
        state_gateway.set_attr("last_2d_cols", ["x", "y"])

        assert app_state.current_plot_title == "123"
        assert app_state.last_2d_cols == ["x", "y"]

        snapshot = app_state.state_store.snapshot()
        assert snapshot["current_plot_title"] == "123"
        assert snapshot["last_2d_cols"] == ["x", "y"]
    finally:
        state_gateway.set_current_plot_title(original_title)
        state_gateway.set_last_2d_cols(original_last_2d_cols)


def test_isochron_results_and_visibility_set_attr_compatibility() -> None:
    original_isochron_results = dict(getattr(app_state, "isochron_results", {}) or {})
    original_visibility = dict(getattr(app_state, "plumbotectonics_group_visibility", {}) or {})

    try:
        state_gateway.set_attr("isochron_results", {"A": {"mswd": 1.2}})
        state_gateway.set_attr("plumbotectonics_group_visibility", {"A": True, "B": False})

        assert app_state.isochron_results == {"A": {"mswd": 1.2}}
        assert app_state.plumbotectonics_group_visibility == {"A": True, "B": False}

        snapshot = app_state.state_store.snapshot()
        assert snapshot["isochron_results"] == {"A": {"mswd": 1.2}}
        assert snapshot["plumbotectonics_group_visibility"] == {"A": True, "B": False}
    finally:
        state_gateway.set_isochron_results(original_isochron_results)
        state_gateway.set_plumbotectonics_group_visibility(original_visibility)


def test_draw_selection_ellipse_set_attr_compatibility() -> None:
    original_value = bool(getattr(app_state, "draw_selection_ellipse", False))

    try:
        state_gateway.set_attr("draw_selection_ellipse", True)
        assert app_state.draw_selection_ellipse is True
        assert app_state.state_store.snapshot()["draw_selection_ellipse"] is True
    finally:
        state_gateway.set_draw_selection_ellipse(original_value)


def test_initial_render_done_set_attr_compatibility() -> None:
    original_value = bool(getattr(app_state, "initial_render_done", False))

    try:
        state_gateway.set_attr("initial_render_done", True)
        assert app_state.initial_render_done is True
        assert app_state.state_store.snapshot()["initial_render_done"] is True
    finally:
        state_gateway.set_initial_render_done(original_value)


def test_legend_preferences_set_attr_compatibility() -> None:
    original_color_scheme = str(getattr(app_state, "color_scheme", "vibrant"))
    original_position = getattr(app_state, "legend_position", None)
    original_location = getattr(app_state, "legend_location", "outside_left")
    original_columns = int(getattr(app_state, "legend_columns", 0))
    original_nudge_step = float(getattr(app_state, "legend_nudge_step", 0.02))
    original_offset = tuple(getattr(app_state, "legend_offset", (0.0, 0.0)) or (0.0, 0.0))

    try:
        state_gateway.set_attr("color_scheme", 777)
        state_gateway.set_attr("legend_position", "upper left")
        state_gateway.set_attr("legend_location", "outside_right")
        state_gateway.set_attr("legend_columns", "4")
        state_gateway.set_attr("legend_nudge_step", "0.125")
        state_gateway.set_attr("legend_offset", [0.2, -0.1])

        assert app_state.color_scheme == "777"
        assert app_state.legend_position == "upper left"
        assert app_state.legend_location == "outside_right"
        assert app_state.legend_columns == 4
        assert app_state.legend_nudge_step == 0.125
        assert app_state.legend_offset == (0.2, -0.1)

        store_snapshot = app_state.state_store.snapshot()
        assert store_snapshot["color_scheme"] == "777"
        assert store_snapshot["legend_position"] == "upper left"
        assert store_snapshot["legend_location"] == "outside_right"
        assert store_snapshot["legend_columns"] == 4
        assert store_snapshot["legend_nudge_step"] == 0.125
        assert store_snapshot["legend_offset"] == (0.2, -0.1)
    finally:
        state_gateway.set_color_scheme(original_color_scheme)
        state_gateway.set_legend_position(original_position)
        state_gateway.set_legend_location(original_location)
        state_gateway.set_legend_columns(original_columns)
        state_gateway.set_legend_nudge_step(original_nudge_step)
        state_gateway.set_legend_offset(original_offset)


def test_recent_files_set_attr_compatibility() -> None:
    original_recent_files = list(getattr(app_state, "recent_files", []) or [])

    try:
        state_gateway.set_attr("recent_files", ["d:/tmp/a.xlsx", "d:/tmp/b.csv"])
        assert app_state.recent_files == ["d:/tmp/a.xlsx", "d:/tmp/b.csv"]
        assert app_state.state_store.snapshot()["recent_files"] == ["d:/tmp/a.xlsx", "d:/tmp/b.csv"]
    finally:
        state_gateway.set_recent_files(original_recent_files)


def test_line_styles_set_attr_compatibility() -> None:
    original_line_styles = dict(getattr(app_state, "line_styles", {}) or {})

    try:
        state_gateway.set_attr("line_styles", {"model_curve": {"linewidth": 2.4}})
        assert app_state.line_styles["model_curve"]["linewidth"] == 2.4
        assert app_state.state_store.snapshot()["line_styles"]["model_curve"]["linewidth"] == 2.4
    finally:
        state_gateway.set_line_styles(original_line_styles)


def test_saved_themes_set_attr_compatibility() -> None:
    original_saved_themes = dict(getattr(app_state, "saved_themes", {}) or {})

    try:
        state_gateway.set_attr("saved_themes", {"demo": {"color_scheme": "vibrant"}})
        assert app_state.saved_themes["demo"]["color_scheme"] == "vibrant"
        assert app_state.state_store.snapshot()["saved_themes"]["demo"]["color_scheme"] == "vibrant"
    finally:
        state_gateway.set_saved_themes(original_saved_themes)


def test_custom_palettes_set_attr_compatibility() -> None:
    original_custom_palettes = dict(getattr(app_state, "custom_palettes", {}) or {})

    try:
        state_gateway.set_attr("custom_palettes", {"my_palette": ["#112233", "#445566"]})
        assert app_state.custom_palettes["my_palette"] == ["#112233", "#445566"]
        assert app_state.state_store.snapshot()["custom_palettes"]["my_palette"] == ["#112233", "#445566"]
    finally:
        state_gateway.set_custom_palettes(original_custom_palettes)


def test_custom_shape_sets_set_attr_compatibility() -> None:
    original_custom_shape_sets = dict(getattr(app_state, "custom_shape_sets", {}) or {})

    try:
        state_gateway.set_attr("custom_shape_sets", {"my_shapes": ["o", "s", "^"]})
        assert app_state.custom_shape_sets["my_shapes"] == ["o", "s", "^"]
        assert app_state.state_store.snapshot()["custom_shape_sets"]["my_shapes"] == ["o", "s", "^"]
    finally:
        state_gateway.set_custom_shape_sets(original_custom_shape_sets)


def test_legend_item_order_set_attr_compatibility() -> None:
    original_legend_item_order = list(getattr(app_state, "legend_item_order", []) or [])

    try:
        state_gateway.set_attr("legend_item_order", ["A", "B", "C"])
        assert app_state.legend_item_order == ["A", "B", "C"]
        assert app_state.state_store.snapshot()["legend_item_order"] == ["A", "B", "C"]
    finally:
        state_gateway.set_legend_item_order(original_legend_item_order)


def test_mixing_endmembers_set_attr_compatibility() -> None:
    original_mixing_endmembers = dict(getattr(app_state, "mixing_endmembers", {}) or {})

    try:
        state_gateway.set_attr("mixing_endmembers", {"EM1": [1, 2, 3]})
        assert app_state.mixing_endmembers == {"EM1": [1, 2, 3]}
        assert app_state.state_store.snapshot()["mixing_endmembers"] == {"EM1": [1, 2, 3]}
    finally:
        state_gateway.set_mixing_endmembers(original_mixing_endmembers)


def test_mixing_mixtures_set_attr_compatibility() -> None:
    original_mixing_mixtures = dict(getattr(app_state, "mixing_mixtures", {}) or {})

    try:
        state_gateway.set_attr("mixing_mixtures", {"M1": [4, 5]})
        assert app_state.mixing_mixtures == {"M1": [4, 5]}
        assert app_state.state_store.snapshot()["mixing_mixtures"] == {"M1": [4, 5]}
    finally:
        state_gateway.set_mixing_mixtures(original_mixing_mixtures)


def test_ternary_ranges_set_attr_compatibility() -> None:
    original_ternary_ranges = dict(getattr(app_state, "ternary_ranges", {}) or {})

    try:
        state_gateway.set_attr("ternary_ranges", {"tmin": 0.1, "tmax": 0.9})
        assert app_state.ternary_ranges == {"tmin": 0.1, "tmax": 0.9}
        assert app_state.state_store.snapshot()["ternary_ranges"] == {"tmin": 0.1, "tmax": 0.9}
    finally:
        state_gateway.set_ternary_ranges(original_ternary_ranges)


def test_kde_style_set_attr_compatibility() -> None:
    original_kde_style = dict(getattr(app_state, "kde_style", {}) or {})

    try:
        state_gateway.set_attr("kde_style", {"alpha": 0.55, "linewidth": 1.4, "fill": False, "levels": 9})
        assert app_state.kde_style["alpha"] == 0.55
        assert app_state.state_store.snapshot()["kde_style"]["levels"] == 9
    finally:
        state_gateway.set_kde_style(original_kde_style)


def test_marginal_kde_style_set_attr_compatibility() -> None:
    original_marginal_kde_style = dict(getattr(app_state, "marginal_kde_style", {}) or {})

    try:
        state_gateway.set_attr(
            "marginal_kde_style",
            {
                "alpha": 0.2,
                "linewidth": 1.1,
                "fill": True,
                "bw_adjust": 1.2,
                "gridsize": 300,
                "cut": 0.8,
                "log_transform": True,
            },
        )
        assert app_state.marginal_kde_style["gridsize"] == 300
        assert app_state.state_store.snapshot()["marginal_kde_style"]["log_transform"] is True
    finally:
        state_gateway.set_marginal_kde_style(original_marginal_kde_style)


def test_ml_last_result_set_attr_compatibility() -> None:
    original_ml_last_result = getattr(app_state, "ml_last_result", None)

    try:
        state_gateway.set_attr("ml_last_result", {"status": "ok", "score": 0.91})
        assert app_state.ml_last_result == {"status": "ok", "score": 0.91}
        assert app_state.state_store.snapshot()["ml_last_result"] == {"status": "ok", "score": 0.91}
    finally:
        state_gateway.set_ml_last_result(original_ml_last_result)


def test_ml_last_model_meta_set_attr_compatibility() -> None:
    original_ml_last_model_meta = getattr(app_state, "ml_last_model_meta", None)

    try:
        state_gateway.set_attr("ml_last_model_meta", {"model": "xgb", "classes": 4})
        assert app_state.ml_last_model_meta == {"model": "xgb", "classes": 4}
        assert app_state.state_store.snapshot()["ml_last_model_meta"] == {"model": "xgb", "classes": 4}
    finally:
        state_gateway.set_ml_last_model_meta(original_ml_last_model_meta)


def test_projection_and_ternary_config_set_attr_compatibility() -> None:
    original_standardize_data = bool(getattr(app_state, "standardize_data", True))
    original_pca_component_indices = list(getattr(app_state, "pca_component_indices", [0, 1]) or [0, 1])
    original_ternary_auto_zoom = bool(getattr(app_state, "ternary_auto_zoom", True))
    original_ternary_limit_mode = str(getattr(app_state, "ternary_limit_mode", "min"))
    original_ternary_limit_anchor = str(getattr(app_state, "ternary_limit_anchor", "min"))
    original_ternary_boundary_percent = float(getattr(app_state, "ternary_boundary_percent", 5.0))
    original_ternary_manual_limits_enabled = bool(getattr(app_state, "ternary_manual_limits_enabled", False))
    original_ternary_manual_limits = dict(getattr(app_state, "ternary_manual_limits", {}) or {})
    original_ternary_stretch_mode = str(getattr(app_state, "ternary_stretch_mode", "power"))
    original_ternary_stretch = bool(getattr(app_state, "ternary_stretch", False))
    original_ternary_factors = list(getattr(app_state, "ternary_factors", [1.0, 1.0, 1.0]) or [1.0, 1.0, 1.0])

    try:
        state_gateway.set_attr("standardize_data", False)
        state_gateway.set_attr("pca_component_indices", [3, 5])
        state_gateway.set_attr("ternary_auto_zoom", False)
        state_gateway.set_attr("ternary_limit_mode", "both")
        state_gateway.set_attr("ternary_limit_anchor", "max")
        state_gateway.set_attr("ternary_boundary_percent", "12.5")
        state_gateway.set_attr("ternary_manual_limits_enabled", True)
        state_gateway.set_attr("ternary_manual_limits", {"tmin": 0.2, "tmax": 0.8, "lmin": 0.1, "lmax": 0.9})
        state_gateway.set_attr("ternary_stretch_mode", "hybrid")
        state_gateway.set_attr("ternary_stretch", True)
        state_gateway.set_attr("ternary_factors", [1.1, 1.2, 0.9])

        assert app_state.standardize_data is False
        assert app_state.pca_component_indices == [3, 5]
        assert app_state.ternary_auto_zoom is False
        assert app_state.ternary_limit_mode == "both"
        assert app_state.ternary_limit_anchor == "max"
        assert app_state.ternary_boundary_percent == 12.5
        assert app_state.ternary_manual_limits_enabled is True
        assert app_state.ternary_manual_limits["tmin"] == 0.2
        assert app_state.ternary_stretch_mode == "hybrid"
        assert app_state.ternary_stretch is True
        assert app_state.ternary_factors == [1.1, 1.2, 0.9]

        snapshot = app_state.state_store.snapshot()
        assert snapshot["standardize_data"] is False
        assert snapshot["pca_component_indices"] == [3, 5]
        assert snapshot["ternary_auto_zoom"] is False
        assert snapshot["ternary_limit_mode"] == "both"
        assert snapshot["ternary_limit_anchor"] == "max"
        assert snapshot["ternary_boundary_percent"] == 12.5
        assert snapshot["ternary_manual_limits_enabled"] is True
        assert snapshot["ternary_manual_limits"]["tmin"] == 0.2
        assert snapshot["ternary_stretch_mode"] == "hybrid"
        assert snapshot["ternary_stretch"] is True
        assert snapshot["ternary_factors"] == [1.1, 1.2, 0.9]
    finally:
        state_gateway.set_standardize_data(original_standardize_data)
        state_gateway.set_pca_component_indices(original_pca_component_indices)
        state_gateway.set_ternary_auto_zoom(original_ternary_auto_zoom)
        state_gateway.set_ternary_limit_mode(original_ternary_limit_mode)
        state_gateway.set_ternary_limit_anchor(original_ternary_limit_anchor)
        state_gateway.set_ternary_boundary_percent(original_ternary_boundary_percent)
        state_gateway.set_ternary_manual_limits_enabled(original_ternary_manual_limits_enabled)
        state_gateway.set_ternary_manual_limits(original_ternary_manual_limits)
        state_gateway.set_ternary_stretch_mode(original_ternary_stretch_mode)
        state_gateway.set_ternary_stretch(original_ternary_stretch)
        state_gateway.set_ternary_factors(original_ternary_factors)


def test_isochron_style_set_attr_compatibility() -> None:
    original_model_curve_width = float(getattr(app_state, "model_curve_width", 1.2))
    original_plumbotectonics_curve_width = float(getattr(app_state, "plumbotectonics_curve_width", 1.2))
    original_paleoisochron_width = float(getattr(app_state, "paleoisochron_width", 0.9))
    original_model_age_line_width = float(getattr(app_state, "model_age_line_width", 0.7))
    original_isochron_line_width = float(getattr(app_state, "isochron_line_width", 1.5))
    original_selected_isochron_line_width = float(getattr(app_state, "selected_isochron_line_width", 2.0))
    original_isochron_label_options = dict(getattr(app_state, "isochron_label_options", {}) or {})

    try:
        state_gateway.set_attr("model_curve_width", "2.4")
        state_gateway.set_attr("plumbotectonics_curve_width", "2.2")
        state_gateway.set_attr("paleoisochron_width", "1.1")
        state_gateway.set_attr("model_age_line_width", "0.95")
        state_gateway.set_attr("isochron_line_width", "2.0")
        state_gateway.set_attr("selected_isochron_line_width", "2.8")
        state_gateway.set_attr("isochron_label_options", {"show_age": True, "show_mswd": True})

        assert app_state.model_curve_width == 2.4
        assert app_state.plumbotectonics_curve_width == 2.2
        assert app_state.paleoisochron_width == 1.1
        assert app_state.model_age_line_width == 0.95
        assert app_state.isochron_line_width == 2.0
        assert app_state.selected_isochron_line_width == 2.8
        assert app_state.isochron_label_options["show_mswd"] is True

        snapshot = app_state.state_store.snapshot()
        assert snapshot["model_curve_width"] == 2.4
        assert snapshot["plumbotectonics_curve_width"] == 2.2
        assert snapshot["paleoisochron_width"] == 1.1
        assert snapshot["model_age_line_width"] == 0.95
        assert snapshot["isochron_line_width"] == 2.0
        assert snapshot["selected_isochron_line_width"] == 2.8
        assert snapshot["isochron_label_options"]["show_mswd"] is True
    finally:
        state_gateway.set_model_curve_width(original_model_curve_width)
        state_gateway.set_plumbotectonics_curve_width(original_plumbotectonics_curve_width)
        state_gateway.set_paleoisochron_width(original_paleoisochron_width)
        state_gateway.set_model_age_line_width(original_model_age_line_width)
        state_gateway.set_isochron_line_width(original_isochron_line_width)
        state_gateway.set_selected_isochron_line_width(original_selected_isochron_line_width)
        state_gateway.set_isochron_label_options(original_isochron_label_options)


def test_equation_overlays_set_attr_compatibility() -> None:
    original_equation_overlays = list(getattr(app_state, "equation_overlays", []) or [])

    try:
        state_gateway.set_attr(
            "equation_overlays",
            [
                {
                    "id": "eq_custom_1",
                    "label": "y=x",
                    "latex": "y=x",
                    "expression": "x",
                    "enabled": True,
                }
            ],
        )
        assert app_state.equation_overlays and app_state.equation_overlays[0]["id"] == "eq_custom_1"
        assert app_state.state_store.snapshot()["equation_overlays"][0]["id"] == "eq_custom_1"
    finally:
        state_gateway.set_equation_overlays(original_equation_overlays)


@pytest.mark.parametrize(
    "attr",
    [
        "show_model_curves",
        "show_plumbotectonics_curves",
        "show_paleoisochrons",
        "show_model_age_lines",
        "show_growth_curves",
        "show_isochrons",
    ],
)
def test_geochem_overlay_visibility_set_attr_compatibility(attr: str) -> None:
    original_value = bool(getattr(app_state, attr, False))

    try:
        state_gateway.set_attr(attr, not original_value)
        assert bool(getattr(app_state, attr)) is (not original_value)
        assert app_state.state_store.snapshot()[attr] is (not original_value)
    finally:
        state_gateway.set_attr(attr, original_value)


def test_geochem_parameter_set_attr_compatibility() -> None:
    original_use_real_age = bool(getattr(app_state, "use_real_age_for_mu_kappa", False))
    original_mu_kappa_age_col = getattr(app_state, "mu_kappa_age_col", None)
    original_variant = str(getattr(app_state, "plumbotectonics_variant", "0"))
    original_step = int(getattr(app_state, "paleoisochron_step", 1000))
    original_ages = list(getattr(app_state, "paleoisochron_ages", []) or [])

    try:
        state_gateway.set_attr("use_real_age_for_mu_kappa", True)
        state_gateway.set_attr("mu_kappa_age_col", "Age_Ma")
        state_gateway.set_attr("plumbotectonics_variant", 2)
        state_gateway.set_attr("paleoisochron_step", "250")
        state_gateway.set_attr("paleoisochron_ages", [1000, 750, 500, 250])

        assert app_state.use_real_age_for_mu_kappa is True
        assert app_state.mu_kappa_age_col == "Age_Ma"
        assert app_state.plumbotectonics_variant == "2"
        assert app_state.paleoisochron_step == 250
        assert app_state.paleoisochron_ages == [1000, 750, 500, 250]

        snapshot = app_state.state_store.snapshot()
        assert snapshot["use_real_age_for_mu_kappa"] is True
        assert snapshot["mu_kappa_age_col"] == "Age_Ma"
        assert snapshot["plumbotectonics_variant"] == "2"
        assert snapshot["paleoisochron_step"] == 250
        assert snapshot["paleoisochron_ages"] == [1000, 750, 500, 250]
    finally:
        state_gateway.set_use_real_age_for_mu_kappa(original_use_real_age)
        state_gateway.set_mu_kappa_age_col(original_mu_kappa_age_col)
        state_gateway.set_plumbotectonics_variant(original_variant)
        state_gateway.set_paleoisochron_step(original_step)
        state_gateway.set_paleoisochron_ages(original_ages)


def test_isochron_error_config_set_attr_compatibility() -> None:
    original_mode = str(getattr(app_state, "isochron_error_mode", "fixed"))
    original_sx_col = str(getattr(app_state, "isochron_sx_col", "") or "")
    original_sy_col = str(getattr(app_state, "isochron_sy_col", "") or "")
    original_rxy_col = str(getattr(app_state, "isochron_rxy_col", "") or "")
    original_sx_value = float(getattr(app_state, "isochron_sx_value", 0.001))
    original_sy_value = float(getattr(app_state, "isochron_sy_value", 0.001))
    original_rxy_value = float(getattr(app_state, "isochron_rxy_value", 0.0))

    try:
        state_gateway.set_attr("isochron_error_mode", "columns")
        state_gateway.set_attr("isochron_sx_col", "sx")
        state_gateway.set_attr("isochron_sy_col", "sy")
        state_gateway.set_attr("isochron_rxy_col", "rxy")

        assert app_state.isochron_error_mode == "columns"
        assert app_state.isochron_sx_col == "sx"
        assert app_state.isochron_sy_col == "sy"
        assert app_state.isochron_rxy_col == "rxy"

        columns_snapshot = app_state.state_store.snapshot()
        assert columns_snapshot["isochron_error_mode"] == "columns"
        assert columns_snapshot["isochron_sx_col"] == "sx"
        assert columns_snapshot["isochron_sy_col"] == "sy"
        assert columns_snapshot["isochron_rxy_col"] == "rxy"

        state_gateway.set_attr("isochron_error_mode", "fixed")
        state_gateway.set_attr("isochron_sx_value", "0.01")
        state_gateway.set_attr("isochron_sy_value", "0.02")
        state_gateway.set_attr("isochron_rxy_value", "0.3")

        assert app_state.isochron_error_mode == "fixed"
        assert app_state.isochron_sx_value == 0.01
        assert app_state.isochron_sy_value == 0.02
        assert app_state.isochron_rxy_value == 0.3

        fixed_snapshot = app_state.state_store.snapshot()
        assert fixed_snapshot["isochron_error_mode"] == "fixed"
        assert fixed_snapshot["isochron_sx_value"] == 0.01
        assert fixed_snapshot["isochron_sy_value"] == 0.02
        assert fixed_snapshot["isochron_rxy_value"] == 0.3
    finally:
        if original_mode == "columns":
            state_gateway.set_isochron_error_columns(original_sx_col, original_sy_col, original_rxy_col)
            state_gateway.set_isochron_error_fixed(original_sx_value, original_sy_value, original_rxy_value)
            state_gateway.set_isochron_error_columns(original_sx_col, original_sy_col, original_rxy_col)
        else:
            state_gateway.set_isochron_error_columns(original_sx_col, original_sy_col, original_rxy_col)
            state_gateway.set_isochron_error_fixed(original_sx_value, original_sy_value, original_rxy_value)


def test_confidence_level_set_attr_conversion() -> None:
    original_level = float(getattr(app_state, "confidence_level", 0.95))

    try:
        state_gateway.set_attr("confidence_level", "0.91")
        assert app_state.confidence_level == 0.91
        assert app_state.state_store.snapshot()["confidence_level"] == 0.91
    finally:
        state_gateway.set_confidence_level(original_level)
