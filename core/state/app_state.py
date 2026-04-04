"""
Application State Management
Centralized global state to avoid variable chaos
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..config import CONFIG
from ..cache import EmbeddingCache
from ..overlay_state import OverlayState
from ..legend_state import LegendState
from .bootstrap import init_runtime_defaults, sync_overlay_kde_styles
from .store import StateStore


@dataclass
class DataState:
    """Compatibility view for data-related app state fields."""

    app_state: "AppState"

    @property
    def df_global(self) -> Any:
        return self.app_state.df_global

    @df_global.setter
    def df_global(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_DATAFRAME_SOURCE',
                    'df': value,
                    'file_path': getattr(self.app_state, 'file_path', None),
                    'sheet_name': getattr(self.app_state, 'sheet_name', None),
                }
            )
            return
        setattr(self.app_state, 'df_global', value)

    @property
    def data_cols(self) -> Any:
        return self.app_state.data_cols

    @data_cols.setter
    def data_cols(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_GROUP_DATA_COLUMNS',
                    'group_cols': list(getattr(self.app_state, 'group_cols', []) or []),
                    'data_cols': list(value or []),
                }
            )
            return
        setattr(self.app_state, 'data_cols', value)

    @property
    def group_cols(self) -> Any:
        return self.app_state.group_cols

    @group_cols.setter
    def group_cols(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_GROUP_DATA_COLUMNS',
                    'group_cols': list(value or []),
                    'data_cols': list(getattr(self.app_state, 'data_cols', []) or []),
                }
            )
            return
        setattr(self.app_state, 'group_cols', value)

    @property
    def active_subset_indices(self) -> Any:
        return self.app_state.active_subset_indices

    @active_subset_indices.setter
    def active_subset_indices(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_ACTIVE_SUBSET_INDICES', 'indices': value})
            return
        setattr(self.app_state, 'active_subset_indices', value)


@dataclass
class AlgorithmState:
    """Compatibility view for algorithm/cache-related fields."""

    app_state: "AppState"

    @property
    def algorithm(self) -> Any:
        return self.app_state.algorithm

    @algorithm.setter
    def algorithm(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_ALGORITHM', 'algorithm': value})
            return
        setattr(self.app_state, 'algorithm', value)

    @property
    def embedding_cache(self) -> Any:
        return self.app_state.embedding_cache

    @property
    def umap_params(self) -> Any:
        return self.app_state.umap_params

    @umap_params.setter
    def umap_params(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_UMAP_PARAMS', 'params': dict(value or {})})
            return
        setattr(self.app_state, 'umap_params', value)

    @property
    def tsne_params(self) -> Any:
        return self.app_state.tsne_params

    @tsne_params.setter
    def tsne_params(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_TSNE_PARAMS', 'params': dict(value or {})})
            return
        setattr(self.app_state, 'tsne_params', value)

    @property
    def pca_params(self) -> Any:
        return self.app_state.pca_params

    @pca_params.setter
    def pca_params(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PCA_PARAMS', 'params': dict(value or {})})
            return
        setattr(self.app_state, 'pca_params', value)

    @property
    def robust_pca_params(self) -> Any:
        return self.app_state.robust_pca_params

    @robust_pca_params.setter
    def robust_pca_params(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_ROBUST_PCA_PARAMS', 'params': dict(value or {})})
            return
        setattr(self.app_state, 'robust_pca_params', value)

    @property
    def ml_params(self) -> Any:
        return self.app_state.ml_params

    @ml_params.setter
    def ml_params(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_ML_PARAMS', 'params': dict(value or {})})
            return
        setattr(self.app_state, 'ml_params', value)

    @property
    def v1v2_params(self) -> Any:
        return self.app_state.v1v2_params

    @v1v2_params.setter
    def v1v2_params(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_V1V2_PARAMS', 'params': dict(value or {})})
            return
        setattr(self.app_state, 'v1v2_params', value)


@dataclass
class VisualState:
    """Compatibility view for figure/axes/rendered artist fields."""

    app_state: "AppState"

    @property
    def fig(self) -> Any:
        return self.app_state.fig

    @fig.setter
    def fig(self, value: Any) -> None:
        setattr(self.app_state, 'fig', value)

    @property
    def ax(self) -> Any:
        return self.app_state.ax

    @ax.setter
    def ax(self, value: Any) -> None:
        setattr(self.app_state, 'ax', value)

    @property
    def scatter_collections(self) -> Any:
        return self.app_state.scatter_collections


@dataclass
class GeochemState:
    """Compatibility view for geochemistry overlay related fields."""

    app_state: "AppState"

    @property
    def overlay(self) -> Any:
        return self.app_state.overlay

    @property
    def line_styles(self) -> Any:
        return self.app_state.line_styles


@dataclass
class StyleState:
    """Compatibility view for style and palette fields."""

    app_state: "AppState"

    @property
    def current_palette(self) -> Any:
        return self.app_state.current_palette

    @current_palette.setter
    def current_palette(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_CURRENT_PALETTE', 'palette': dict(value or {})})
            return
        setattr(self.app_state, 'current_palette', value)

    @property
    def color_scheme(self) -> Any:
        return self.app_state.color_scheme

    @color_scheme.setter
    def color_scheme(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_COLOR_SCHEME', 'color_scheme': value})
            return
        setattr(self.app_state, 'color_scheme', value)

    @property
    def custom_primary_font(self) -> Any:
        return self.app_state.custom_primary_font

    @custom_primary_font.setter
    def custom_primary_font(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_CUSTOM_PRIMARY_FONT', 'font_name': str(value or '')})
            return
        setattr(self.app_state, 'custom_primary_font', value)

    @property
    def custom_cjk_font(self) -> Any:
        return self.app_state.custom_cjk_font

    @custom_cjk_font.setter
    def custom_cjk_font(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_CUSTOM_CJK_FONT', 'font_name': str(value or '')})
            return
        setattr(self.app_state, 'custom_cjk_font', value)

    @property
    def plot_font_sizes(self) -> Any:
        return self.app_state.plot_font_sizes

    @plot_font_sizes.setter
    def plot_font_sizes(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PLOT_FONT_SIZES', 'sizes': dict(value or {})})
            return
        setattr(self.app_state, 'plot_font_sizes', value)


@dataclass
class InteractionState:
    """Compatibility view for selection and interaction fields."""

    app_state: "AppState"

    @property
    def selection_tool(self) -> Any:
        return self.app_state.selection_tool

    @selection_tool.setter
    def selection_tool(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SELECTION_TOOL', 'tool': value})
            return
        setattr(self.app_state, 'selection_tool', value)

    @property
    def selected_indices(self) -> Any:
        return self.app_state.selected_indices

    @selected_indices.setter
    def selected_indices(self, value: Any) -> None:
        state_store = getattr(self.app_state, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SELECTED_INDICES', 'indices': value})
            return
        setattr(self.app_state, 'selected_indices', value)

    @property
    def artist_to_sample(self) -> Any:
        return self.app_state.artist_to_sample

    @property
    def sample_coordinates(self) -> Any:
        return self.app_state.sample_coordinates


class AppState:
    """Centralized application state"""
    def __init__(self) -> None:
        self.df_global = None
        self.data_version = 0
        self.embedding_cache = EmbeddingCache(max_entries=CONFIG.get('embedding_cache_size', 8))
        self.algorithm = 'UMAP'  # Default algorithm: always start with UMAP
        self.umap_params = CONFIG['umap_params'].copy()
        self.tsne_params = CONFIG['tsne_params'].copy()
        self.pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42}).copy()
        self.robust_pca_params = CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42, 'support_fraction': 0.75}).copy()
        if 'support_fraction' not in self.robust_pca_params:
            self.robust_pca_params['support_fraction'] = 0.75

        self.ml_params = CONFIG.get('ml_params', {}).copy()
        self.ml_last_result = None
        self.ml_last_model_meta = None

        # Async embedding task state
        self.embedding_task_token = 0
        self.embedding_worker = None
        self.embedding_task_running = False
        self.embedding_task_algorithm = None

        # V1V2 Parameters
        self.v1v2_params = {
            'a': 0.0,
            'b': 2.0367,
            'c': -6.143,
            'scale': 1.0
        }

        # --- Sub-state objects ---
        self.overlay = OverlayState()
        self.legend = LegendState()

        # Compatibility stepping-stone for layered AppState refactor.
        self.data_state = DataState(self)
        self.algorithm_state = AlgorithmState(self)
        self.visual_state = VisualState(self)
        self.geochem_state = GeochemState(self)
        self.style_state = StyleState(self)
        self.interaction_state = InteractionState(self)

        # Shorthand aliases aligned with the planned layered naming.
        self.data = self.data_state
        self.algorithm_config = self.algorithm_state
        self.visual = self.visual_state
        self.geochem = self.geochem_state
        self.style = self.style_state
        self.interaction = self.interaction_state

        sync_overlay_kde_styles(self)
        init_runtime_defaults(self, CONFIG)
        self.state_store = StateStore(self)

    def clear_plot_state(self) -> None:
        """Reset plot-specific state"""
        self.scatter_collections.clear()
        self.sample_index_map.clear()
        self.legend.legend_to_scatter.clear()
        self.group_to_scatter = {}  # Map group name to scatter artist
        self.overlay.clear_artists()
        self.exported_indices.clear()
        self.annotation = None  # Clear annotation reference
        self.sample_coordinates.clear()
        self.artist_to_sample.clear()
        if self.selection_overlay is not None:
            try:
                self.selection_overlay.remove()
            except Exception:
                pass
        self.selection_overlay = None

    def register_language_listener(self, callback: Callable[[], None]) -> None:
        """Register a callback to be invoked when language changes."""
        if callback and callback not in self.language_listeners:
            self.language_listeners.append(callback)

    def notify_language_change(self) -> None:
        """Notify registered listeners about language changes."""
        for callback in list(self.language_listeners):
            try:
                callback()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Backward-compatible property delegation: OverlayState
    # ------------------------------------------------------------------ #

    @property
    def show_model_curves(self):
        return self.overlay.show_model_curves

    @show_model_curves.setter
    def show_model_curves(self, value):
        self.overlay.show_model_curves = value

    @property
    def show_paleoisochrons(self):
        return self.overlay.show_paleoisochrons

    @show_paleoisochrons.setter
    def show_paleoisochrons(self, value):
        self.overlay.show_paleoisochrons = value

    @property
    def show_plumbotectonics_curves(self):
        return self.overlay.show_plumbotectonics_curves

    @show_plumbotectonics_curves.setter
    def show_plumbotectonics_curves(self, value):
        self.overlay.show_plumbotectonics_curves = value

    @property
    def show_model_age_lines(self):
        return self.overlay.show_model_age_lines

    @show_model_age_lines.setter
    def show_model_age_lines(self, value):
        self.overlay.show_model_age_lines = value

    @property
    def show_isochrons(self):
        return self.overlay.show_isochrons

    @show_isochrons.setter
    def show_isochrons(self, value):
        self.overlay.show_isochrons = value

    @property
    def show_growth_curves(self):
        return self.overlay.show_growth_curves

    @show_growth_curves.setter
    def show_growth_curves(self, value):
        self.overlay.show_growth_curves = value

    @property
    def show_equation_overlays(self):
        return self.overlay.show_equation_overlays

    @show_equation_overlays.setter
    def show_equation_overlays(self, value):
        self.overlay.show_equation_overlays = value

    @property
    def use_real_age_for_mu_kappa(self):
        return self.overlay.use_real_age_for_mu_kappa

    @use_real_age_for_mu_kappa.setter
    def use_real_age_for_mu_kappa(self, value):
        self.overlay.use_real_age_for_mu_kappa = value

    @property
    def mu_kappa_age_col(self):
        return self.overlay.mu_kappa_age_col

    @mu_kappa_age_col.setter
    def mu_kappa_age_col(self, value):
        self.overlay.mu_kappa_age_col = value

    @property
    def isochron_label_options(self):
        return self.overlay.isochron_label_options

    @isochron_label_options.setter
    def isochron_label_options(self, value):
        self.overlay.isochron_label_options = value

    @property
    def geo_model_name(self):
        return self.overlay.geo_model_name

    @geo_model_name.setter
    def geo_model_name(self, value):
        self.overlay.geo_model_name = value

    @property
    def equation_overlays(self):
        return self.overlay.equation_overlays

    @equation_overlays.setter
    def equation_overlays(self, value):
        self.overlay.equation_overlays = value

    @property
    def line_styles(self):
        return self.overlay.line_styles

    @line_styles.setter
    def line_styles(self, value):
        self.overlay.line_styles = value

    @property
    def paleoisochron_min_age(self):
        return self.overlay.paleoisochron_min_age

    @paleoisochron_min_age.setter
    def paleoisochron_min_age(self, value):
        self.overlay.paleoisochron_min_age = value

    @property
    def paleoisochron_max_age(self):
        return self.overlay.paleoisochron_max_age

    @paleoisochron_max_age.setter
    def paleoisochron_max_age(self, value):
        self.overlay.paleoisochron_max_age = value

    @property
    def paleoisochron_step(self):
        return self.overlay.paleoisochron_step

    @paleoisochron_step.setter
    def paleoisochron_step(self, value):
        self.overlay.paleoisochron_step = value

    @property
    def paleoisochron_ages(self):
        return self.overlay.paleoisochron_ages

    @paleoisochron_ages.setter
    def paleoisochron_ages(self, value):
        self.overlay.paleoisochron_ages = value

    @property
    def plumbotectonics_variant(self):
        return self.overlay.plumbotectonics_variant

    @plumbotectonics_variant.setter
    def plumbotectonics_variant(self, value):
        self.overlay.plumbotectonics_variant = value

    @property
    def plumbotectonics_group_visibility(self):
        return self.overlay.plumbotectonics_group_visibility

    @plumbotectonics_group_visibility.setter
    def plumbotectonics_group_visibility(self, value):
        self.overlay.plumbotectonics_group_visibility = value

    @property
    def model_curve_models(self):
        return self.overlay.model_curve_models

    @model_curve_models.setter
    def model_curve_models(self, value):
        self.overlay.model_curve_models = value

    @property
    def isochron_error_mode(self):
        return self.overlay.isochron_error_mode

    @isochron_error_mode.setter
    def isochron_error_mode(self, value):
        self.overlay.isochron_error_mode = value

    @property
    def isochron_sx_col(self):
        return self.overlay.isochron_sx_col

    @isochron_sx_col.setter
    def isochron_sx_col(self, value):
        self.overlay.isochron_sx_col = value

    @property
    def isochron_sy_col(self):
        return self.overlay.isochron_sy_col

    @isochron_sy_col.setter
    def isochron_sy_col(self, value):
        self.overlay.isochron_sy_col = value

    @property
    def isochron_rxy_col(self):
        return self.overlay.isochron_rxy_col

    @isochron_rxy_col.setter
    def isochron_rxy_col(self, value):
        self.overlay.isochron_rxy_col = value

    @property
    def isochron_sx_value(self):
        return self.overlay.isochron_sx_value

    @isochron_sx_value.setter
    def isochron_sx_value(self, value):
        self.overlay.isochron_sx_value = value

    @property
    def isochron_sy_value(self):
        return self.overlay.isochron_sy_value

    @isochron_sy_value.setter
    def isochron_sy_value(self, value):
        self.overlay.isochron_sy_value = value

    @property
    def isochron_rxy_value(self):
        return self.overlay.isochron_rxy_value

    @isochron_rxy_value.setter
    def isochron_rxy_value(self, value):
        self.overlay.isochron_rxy_value = value

    @property
    def selected_isochron_data(self):
        return self.overlay.selected_isochron_data

    @selected_isochron_data.setter
    def selected_isochron_data(self, value):
        self.overlay.selected_isochron_data = value

    @property
    def isochron_results(self):
        return self.overlay.isochron_results

    @isochron_results.setter
    def isochron_results(self, value):
        self.overlay.isochron_results = value

    @property
    def model_curve_width(self):
        return self.overlay.model_curve_width

    @model_curve_width.setter
    def model_curve_width(self, value):
        self.overlay.model_curve_width = value

    @property
    def plumbotectonics_curve_width(self):
        return self.overlay.plumbotectonics_curve_width

    @plumbotectonics_curve_width.setter
    def plumbotectonics_curve_width(self, value):
        self.overlay.plumbotectonics_curve_width = value

    @property
    def paleoisochron_width(self):
        return self.overlay.paleoisochron_width

    @paleoisochron_width.setter
    def paleoisochron_width(self, value):
        self.overlay.paleoisochron_width = value

    @property
    def model_age_line_width(self):
        return self.overlay.model_age_line_width

    @model_age_line_width.setter
    def model_age_line_width(self, value):
        self.overlay.model_age_line_width = value

    @property
    def isochron_line_width(self):
        return self.overlay.isochron_line_width

    @isochron_line_width.setter
    def isochron_line_width(self, value):
        self.overlay.isochron_line_width = value

    @property
    def overlay_artists(self):
        return self.overlay.overlay_artists

    @overlay_artists.setter
    def overlay_artists(self, value):
        self.overlay.overlay_artists = value

    @property
    def overlay_curve_label_data(self):
        return self.overlay.overlay_curve_label_data

    @overlay_curve_label_data.setter
    def overlay_curve_label_data(self, value):
        self.overlay.overlay_curve_label_data = value

    @property
    def paleoisochron_label_data(self):
        return self.overlay.paleoisochron_label_data

    @paleoisochron_label_data.setter
    def paleoisochron_label_data(self, value):
        self.overlay.paleoisochron_label_data = value

    @property
    def plumbotectonics_label_data(self):
        return self.overlay.plumbotectonics_label_data

    @plumbotectonics_label_data.setter
    def plumbotectonics_label_data(self, value):
        self.overlay.plumbotectonics_label_data = value

    @property
    def plumbotectonics_isoage_label_data(self):
        return self.overlay.plumbotectonics_isoage_label_data

    @plumbotectonics_isoage_label_data.setter
    def plumbotectonics_isoage_label_data(self, value):
        self.overlay.plumbotectonics_isoage_label_data = value

    # ------------------------------------------------------------------ #
    # Backward-compatible property delegation: LegendState
    # ------------------------------------------------------------------ #

    @property
    def legend_position(self):
        return self.legend.legend_position

    @legend_position.setter
    def legend_position(self, value):
        self.legend.legend_position = value

    @property
    def legend_columns(self):
        return self.legend.legend_columns

    @legend_columns.setter
    def legend_columns(self, value):
        self.legend.legend_columns = value

    @property
    def legend_offset(self):
        return self.legend.legend_offset

    @legend_offset.setter
    def legend_offset(self, value):
        self.legend.legend_offset = value

    @property
    def legend_nudge_step(self):
        return self.legend.legend_nudge_step

    @legend_nudge_step.setter
    def legend_nudge_step(self, value):
        self.legend.legend_nudge_step = value

    @property
    def legend_location(self):
        return self.legend.legend_location

    @legend_location.setter
    def legend_location(self, value):
        self.legend.legend_location = value

    @property
    def legend_display_mode(self):
        return self.legend.legend_display_mode

    @legend_display_mode.setter
    def legend_display_mode(self, value):
        self.legend.legend_display_mode = value

    @property
    def legend_frame_on(self):
        return self.legend.legend_frame_on

    @legend_frame_on.setter
    def legend_frame_on(self, value):
        self.legend.legend_frame_on = value

    @property
    def legend_frame_alpha(self):
        return self.legend.legend_frame_alpha

    @legend_frame_alpha.setter
    def legend_frame_alpha(self, value):
        self.legend.legend_frame_alpha = value

    @property
    def legend_frame_facecolor(self):
        return self.legend.legend_frame_facecolor

    @legend_frame_facecolor.setter
    def legend_frame_facecolor(self, value):
        self.legend.legend_frame_facecolor = value

    @property
    def legend_frame_edgecolor(self):
        return self.legend.legend_frame_edgecolor

    @legend_frame_edgecolor.setter
    def legend_frame_edgecolor(self, value):
        self.legend.legend_frame_edgecolor = value

    @property
    def hidden_groups(self):
        return self.legend.hidden_groups

    @hidden_groups.setter
    def hidden_groups(self, value):
        self.legend.hidden_groups = value

    @property
    def legend_to_scatter(self):
        return self.legend.legend_to_scatter

    @legend_to_scatter.setter
    def legend_to_scatter(self, value):
        self.legend.legend_to_scatter = value

    @property
    def legend_update_callback(self):
        return self.legend.legend_update_callback

    @legend_update_callback.setter
    def legend_update_callback(self, value):
        self.legend.legend_update_callback = value

    @property
    def legend_last_title(self):
        return self.legend.legend_last_title

    @legend_last_title.setter
    def legend_last_title(self, value):
        self.legend.legend_last_title = value

    @property
    def legend_last_handles(self):
        return self.legend.legend_last_handles

    @legend_last_handles.setter
    def legend_last_handles(self, value):
        self.legend.legend_last_handles = value

    @property
    def legend_last_labels(self):
        return self.legend.legend_last_labels

    @legend_last_labels.setter
    def legend_last_labels(self, value):
        self.legend.legend_last_labels = value


# Global state instance
app_state = AppState()

# Global widget references for callbacks
# UMAP parameters
slider_n = None
slider_d = None
slider_r = None
slider_s = None

# t-SNE parameters
slider_p = None  # perplexity
slider_lr = None  # learning_rate

# Common controls
radio_g = None
radio_render_mode = None  # Render mode selector (UMAP/tSNE/2D/3D)
