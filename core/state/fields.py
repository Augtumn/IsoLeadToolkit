"""Declarative registry for the state fields.

Each declaration carries the field's default value, the coercion applied on the way into
the snapshot (``normalize``), the copy applied back onto the state (``copy``) and the
holder the field lives on: ``None`` for app_state itself, otherwise the sub-object's
attribute name (``legend``, ``overlay``). The store's initial snapshot and projection and
the write-back in ``_normalizers.sync_state_store_to_app()`` derive from this list, so a
field can no longer be registered in one place and forgotten in another.

Fields whose call sites do not follow the common shape stay explicit there, with a
comment saying why.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any, Callable

from . import coercers

Coercer = Callable[[Any], Any]


def _identity(value: Any) -> Any:
    return value


@dataclass(frozen=True)
class StateField:
    """One persisted state field."""

    name: str
    default: Any
    normalize: Coercer = _identity
    copy: Coercer = _identity
    holder: str | None = None

    def from_state(self, state: Any) -> Any:
        source = getattr(state, self.holder) if self.holder else state
        return self.normalize(getattr(source, self.name, self.default))

    def from_snapshot(self, snapshot: dict) -> Any:
        return self.copy(snapshot.get(self.name, self.default))


#: Every field whose plumbing comes from this registry.
SIMPLE_FIELDS: tuple[StateField, ...] = (
    # ── migrated first (item A) ──
    StateField(
        "ternary_auto_zoom",
        True,
        normalize=coercers._as_bool,
        copy=coercers._as_bool,
        holder=None,
    ),
    StateField(
        "ternary_boundary_percent",
        5.0,
        normalize=coercers._normalize_ternary_boundary_percent,
        copy=coercers._normalize_ternary_boundary_percent,
        holder=None,
    ),
    StateField(
        "ternary_limit_mode",
        'min',
        normalize=coercers._as_str,
        copy=coercers._as_str,
        holder=None,
    ),
    StateField(
        "ternary_limit_anchor",
        'min',
        normalize=coercers._as_str,
        copy=coercers._as_str,
        holder=None,
    ),
    StateField(
        "ternary_manual_limits_enabled",
        False,
        normalize=coercers._as_bool,
        copy=coercers._as_bool,
        holder=None,
    ),
    StateField(
        "ternary_manual_limits",
        {'tmin': 0.0, 'tmax': 1.0, 'lmin': 0.0, 'lmax': 1.0, 'rmin': 0.0, 'rmax': 1.0},
        normalize=coercers._normalize_ternary_manual_limits,
        copy=coercers._normalize_ternary_manual_limits,
        holder=None,
    ),
    StateField(
        "ternary_render_margin",
        0.002,
        normalize=coercers._normalize_ternary_render_margin,
        copy=coercers._normalize_ternary_render_margin,
        holder=None,
    ),
    StateField(
        "ternary_stretch_mode",
        'power',
        normalize=coercers._as_stretch_mode,
        copy=coercers._as_stretch_mode,
        holder=None,
    ),
    StateField(
        "ternary_stretch",
        False,
        normalize=coercers._as_bool,
        copy=coercers._as_bool,
        holder=None,
    ),
    StateField(
        "ternary_factors",
        [1.0, 1.0, 1.0],
        normalize=coercers._as_factors,
        copy=coercers._as_factors,
        holder=None,
    ),

    # ── adjust ──
    StateField(
        "adjust_text_expand",
        (1.08, 1.2),
        normalize=partial(coercers._normalize_adjust_text_pair, default=(1.08, 1.2), min_value=1.0, max_value=2.5),
        copy=tuple,
        holder=None,
    ),
    StateField(
        "adjust_text_force_static",
        (0.4, 0.6),
        normalize=partial(coercers._normalize_adjust_text_pair, default=(0.4, 0.6), min_value=0.0, max_value=3.0),
        copy=tuple,
        holder=None,
    ),
    StateField(
        "adjust_text_force_text",
        (0.8, 1.0),
        normalize=partial(coercers._normalize_adjust_text_pair, default=(0.8, 1.0), min_value=0.0, max_value=3.0),
        copy=tuple,
        holder=None,
    ),
    StateField(
        "adjust_text_iter_lim",
        120,
        normalize=coercers._normalize_adjust_text_iter_lim,
        copy=int,
        holder=None,
    ),
    StateField(
        "adjust_text_time_lim",
        0.25,
        normalize=coercers._normalize_adjust_text_time_lim,
        copy=float,
        holder=None,
    ),

    # ── axes ──
    StateField(
        "axes_facecolor",
        '#ffffff',
        normalize=partial(coercers._normalize_color, '#ffffff'),
        copy=str,
        holder=None,
    ),

    # ── axis ──
    StateField(
        "axis_line_color",
        '#1f2937',
        normalize=partial(coercers._normalize_color, '#1f2937'),
        copy=str,
        holder=None,
    ),
    StateField(
        "axis_linewidth",
        1.0,
        normalize=partial(coercers._normalize_style_linewidth, default=1.0),
        copy=float,
        holder=None,
    ),

    # ── color ──
    StateField(
        "color_scheme",
        'vibrant',
        normalize=str,
        copy=str,
        holder=None,
    ),

    # ── confidence ──
    StateField(
        "confidence_level",
        0.95,
        normalize=float,
        copy=float,
        holder=None,
    ),

    # ── custom ──
    StateField(
        "custom_cjk_font",
        '',
        normalize=coercers._normalize_font_name,
        copy=str,
        holder=None,
    ),
    StateField(
        "custom_primary_font",
        '',
        normalize=coercers._normalize_font_name,
        copy=str,
        holder=None,
    ),

    # ── draw ──
    StateField(
        "draw_selection_ellipse",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),

    # ── export ──
    StateField(
        "export_image_options",
        None,
        normalize=coercers._normalize_export_options,
        copy=dict,
        holder=None,
    ),

    # ── grid ──
    StateField(
        "grid_alpha",
        0.7,
        normalize=partial(coercers._normalize_unit_interval, default=0.7),
        copy=float,
        holder=None,
    ),
    StateField(
        "grid_color",
        '#e2e8f0',
        normalize=partial(coercers._normalize_color, '#e2e8f0'),
        copy=str,
        holder=None,
    ),
    StateField(
        "grid_linestyle",
        '--',
        normalize=coercers._normalize_grid_linestyle,
        copy=str,
        holder=None,
    ),
    StateField(
        "grid_linewidth",
        0.6,
        normalize=partial(coercers._normalize_style_linewidth, default=0.6),
        copy=float,
        holder=None,
    ),

    # ── label ──
    StateField(
        "label_color",
        '#1f2937',
        normalize=partial(coercers._normalize_color, '#1f2937'),
        copy=str,
        holder=None,
    ),
    StateField(
        "label_pad",
        6.0,
        normalize=partial(coercers._normalize_text_pad, default=6.0, max_value=60.0),
        copy=float,
        holder=None,
    ),
    StateField(
        "label_weight",
        'normal',
        normalize=partial(coercers._normalize_text_weight, default='normal'),
        copy=str,
        holder=None,
    ),

    # ── language ──
    StateField(
        "language",
        'zh',
        normalize=str,
        copy=str,
        holder=None,
    ),

    # ── legend ──
    StateField(
        "legend_columns",
        0,
        normalize=int,
        copy=int,
        holder='legend',
    ),
    StateField(
        "legend_display_mode",
        'inline',
        normalize=str,
        copy=str,
        holder='legend',
    ),
    StateField(
        "legend_frame_alpha",
        0.95,
        normalize=partial(coercers._normalize_unit_interval, default=0.95),
        copy=float,
        holder='legend',
    ),
    StateField(
        "legend_frame_edgecolor",
        '#cbd5f5',
        normalize=partial(coercers._normalize_color, '#cbd5f5'),
        copy=str,
        holder='legend',
    ),
    StateField(
        "legend_frame_facecolor",
        '#ffffff',
        normalize=partial(coercers._normalize_color, '#ffffff'),
        copy=str,
        holder='legend',
    ),
    StateField(
        "legend_frame_on",
        True,
        normalize=bool,
        copy=bool,
        holder='legend',
    ),
    StateField(
        "legend_nudge_step",
        0.02,
        normalize=float,
        copy=float,
        holder='legend',
    ),

    # ── marginal ──
    StateField(
        "marginal_kde_auto_bandwidth_method",
        'scott',
        normalize=coercers._normalize_kde_auto_bandwidth_method,
        copy=str,
        holder=None,
    ),
    StateField(
        "marginal_kde_bandwidth",
        0.0,
        normalize=coercers._normalize_kde_bandwidth,
        copy=float,
        holder=None,
    ),
    StateField(
        "marginal_kde_bw_adjust",
        1.0,
        normalize=float,
        copy=float,
        holder=None,
    ),
    StateField(
        "marginal_kde_cut",
        1.0,
        normalize=float,
        copy=float,
        holder=None,
    ),
    StateField(
        "marginal_kde_gridsize",
        256,
        normalize=int,
        copy=int,
        holder=None,
    ),
    StateField(
        "marginal_kde_kernel",
        'gaussian',
        normalize=coercers._normalize_kde_kernel,
        copy=str,
        holder=None,
    ),
    StateField(
        "marginal_kde_log_transform",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),
    StateField(
        "marginal_kde_max_points",
        5000,
        normalize=int,
        copy=int,
        holder=None,
    ),
    StateField(
        "marginal_kde_right_size",
        15.0,
        normalize=float,
        copy=float,
        holder=None,
    ),
    StateField(
        "marginal_kde_top_size",
        15.0,
        normalize=float,
        copy=float,
        holder=None,
    ),

    # ── minor ──
    StateField(
        "minor_grid",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),
    StateField(
        "minor_grid_alpha",
        0.4,
        normalize=partial(coercers._normalize_unit_interval, default=0.4),
        copy=float,
        holder=None,
    ),
    StateField(
        "minor_grid_color",
        '#e2e8f0',
        normalize=partial(coercers._normalize_color, '#e2e8f0'),
        copy=str,
        holder=None,
    ),
    StateField(
        "minor_grid_linestyle",
        ':',
        normalize=coercers._normalize_grid_linestyle,
        copy=str,
        holder=None,
    ),
    StateField(
        "minor_grid_linewidth",
        0.4,
        normalize=partial(coercers._normalize_style_linewidth, default=0.4),
        copy=float,
        holder=None,
    ),
    StateField(
        "minor_tick_length",
        2.5,
        normalize=partial(coercers._normalize_tick_length, default=2.5),
        copy=float,
        holder=None,
    ),
    StateField(
        "minor_tick_width",
        0.6,
        normalize=partial(coercers._normalize_style_linewidth, default=0.6),
        copy=float,
        holder=None,
    ),
    StateField(
        "minor_ticks",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),

    # ── ml ──
    StateField(
        "ml_params",
        None,
        normalize=coercers._normalize_algorithm_params,
        copy=dict,
        holder=None,
    ),

    # ── overlay ──
    StateField(
        "geo_model_name",
        'Stacey & Kramers (2nd Stage)',
        normalize=str,
        copy=str,
        holder='overlay',
    ),
    StateField(
        "isochron_line_width",
        1.5,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "isochron_rxy_value",
        0.0,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "isochron_sx_value",
        0.001,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "isochron_sy_value",
        0.001,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "model_age_line_width",
        0.7,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "model_curve_width",
        1.2,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "paleoisochron_max_age",
        3000,
        normalize=int,
        copy=int,
        holder='overlay',
    ),
    StateField(
        "paleoisochron_min_age",
        0,
        normalize=int,
        copy=int,
        holder='overlay',
    ),
    StateField(
        "paleoisochron_step",
        1000,
        normalize=int,
        copy=int,
        holder='overlay',
    ),
    StateField(
        "paleoisochron_width",
        0.9,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "plumbotectonics_curve_width",
        1.2,
        normalize=float,
        copy=float,
        holder='overlay',
    ),
    StateField(
        "plumbotectonics_variant",
        '0',
        normalize=str,
        copy=str,
        holder='overlay',
    ),
    StateField(
        "show_equation_overlays",
        False,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),
    StateField(
        "show_growth_curves",
        True,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),
    StateField(
        "show_isochrons",
        False,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),
    StateField(
        "show_model_age_lines",
        True,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),
    StateField(
        "show_model_curves",
        True,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),
    StateField(
        "show_paleoisochrons",
        True,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),
    StateField(
        "show_plumbotectonics_curves",
        True,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),
    StateField(
        "use_real_age_for_mu_kappa",
        False,
        normalize=bool,
        copy=bool,
        holder='overlay',
    ),

    # ── pca ──
    StateField(
        "pca_component_indices",
        None,
        normalize=coercers._normalize_pca_component_indices,
        copy=list,
        holder=None,
    ),
    StateField(
        "pca_params",
        None,
        normalize=coercers._normalize_algorithm_params,
        copy=dict,
        holder=None,
    ),

    # ── plot ──
    StateField(
        "plot_dpi",
        130,
        normalize=coercers._normalize_plot_dpi,
        copy=int,
        holder=None,
    ),
    StateField(
        "plot_facecolor",
        '#ffffff',
        normalize=partial(coercers._normalize_color, '#ffffff'),
        copy=str,
        holder=None,
    ),
    StateField(
        "plot_font_sizes",
        None,
        normalize=coercers._normalize_plot_font_sizes,
        copy=dict,
        holder=None,
    ),
    StateField(
        "plot_marker_alpha",
        0.8,
        normalize=coercers._normalize_plot_marker_alpha,
        copy=float,
        holder=None,
    ),
    StateField(
        "plot_marker_size",
        60,
        normalize=coercers._normalize_plot_marker_size,
        copy=int,
        holder=None,
    ),
    StateField(
        "plot_style_grid",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),

    # ── point ──
    StateField(
        "point_size",
        60,
        normalize=int,
        copy=int,
        holder=None,
    ),

    # ── robust ──
    StateField(
        "robust_pca_params",
        None,
        normalize=coercers._normalize_algorithm_params,
        copy=dict,
        holder=None,
    ),

    # ── scatter ──
    StateField(
        "scatter_edgecolor",
        '#1e293b',
        normalize=partial(coercers._normalize_color, '#1e293b'),
        copy=str,
        holder=None,
    ),
    StateField(
        "scatter_edgewidth",
        0.4,
        normalize=partial(coercers._normalize_style_linewidth, default=0.4),
        copy=float,
        holder=None,
    ),
    StateField(
        "scatter_show_edge",
        True,
        normalize=bool,
        copy=bool,
        holder=None,
    ),

    # ── selected ──
    StateField(
        "selected_isochron_line_width",
        2.0,
        normalize=float,
        copy=float,
        holder=None,
    ),

    # ── show ──
    StateField(
        "show_kde",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),
    StateField(
        "show_marginal_kde",
        True,
        normalize=bool,
        copy=bool,
        holder=None,
    ),
    StateField(
        "show_plot_title",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),
    StateField(
        "show_right_spine",
        True,
        normalize=bool,
        copy=bool,
        holder=None,
    ),
    StateField(
        "show_tooltip",
        False,
        normalize=bool,
        copy=bool,
        holder=None,
    ),
    StateField(
        "show_top_spine",
        True,
        normalize=bool,
        copy=bool,
        holder=None,
    ),

    # ── standardize ──
    StateField(
        "standardize_data",
        True,
        normalize=bool,
        copy=bool,
        holder=None,
    ),

    # ── tick ──
    StateField(
        "tick_color",
        '#1f2937',
        normalize=partial(coercers._normalize_color, '#1f2937'),
        copy=str,
        holder=None,
    ),
    StateField(
        "tick_direction",
        'out',
        normalize=coercers._normalize_tick_direction,
        copy=str,
        holder=None,
    ),
    StateField(
        "tick_length",
        4.0,
        normalize=partial(coercers._normalize_tick_length, default=4.0),
        copy=float,
        holder=None,
    ),
    StateField(
        "tick_width",
        0.8,
        normalize=partial(coercers._normalize_style_linewidth, default=0.8),
        copy=float,
        holder=None,
    ),

    # ── title ──
    StateField(
        "title_color",
        '#111827',
        normalize=partial(coercers._normalize_color, '#111827'),
        copy=str,
        holder=None,
    ),
    StateField(
        "title_pad",
        20.0,
        normalize=partial(coercers._normalize_text_pad, default=20.0, max_value=80.0),
        copy=float,
        holder=None,
    ),
    StateField(
        "title_weight",
        'bold',
        normalize=partial(coercers._normalize_text_weight, default='bold'),
        copy=str,
        holder=None,
    ),

    # ── tsne ──
    StateField(
        "tsne_params",
        None,
        normalize=coercers._normalize_algorithm_params,
        copy=dict,
        holder=None,
    ),

    # ── ui ──
    StateField(
        "ui_theme",
        'Modern Light',
        normalize=str,
        copy=str,
        holder=None,
    ),

    # ── umap ──
    StateField(
        "umap_params",
        None,
        normalize=coercers._normalize_algorithm_params,
        copy=dict,
        holder=None,
    ),

    # ── v1v2 ──
    StateField(
        "v1v2_params",
        None,
        normalize=coercers._normalize_algorithm_params,
        copy=dict,
        holder=None,
    ),

    # ── visible ──
    StateField(
        "visible_groups",
        None,
        normalize=coercers._normalize_visible_groups,
        copy=coercers._normalize_visible_groups,
        holder=None,
    ),
)

REGISTERED = {field.name for field in SIMPLE_FIELDS}


def snapshot_from_state(state: Any) -> dict[str, Any]:
    """Initial snapshot entries for the registered fields."""
    return {field.name: field.from_state(state) for field in SIMPLE_FIELDS}


def snapshot_from_store(snapshot: dict) -> dict[str, Any]:
    """Projection entries for the registered fields."""
    return {field.name: field.from_snapshot(snapshot) for field in SIMPLE_FIELDS}


def sync_fields(state: Any, snapshot: dict) -> None:
    """Write the registered fields from *snapshot* back onto *state*."""
    for field in SIMPLE_FIELDS:
        target = getattr(state, field.holder) if field.holder else state
        setattr(target, field.name, field.from_snapshot(snapshot))
