"""
Application State Management
Centralized global state to avoid variable chaos
"""
from __future__ import annotations

from typing import Any, Callable

from ..config import CONFIG
from ..cache import EmbeddingCache
from ..overlay_state import OverlayState
from ..legend_state import LegendState
from .bootstrap import init_runtime_defaults, sync_overlay_kde_styles
from .store import StateStore
from ._views import DataState, AlgorithmState, VisualState, GeochemState, StyleState, InteractionState


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
    def show_model_curves(self) -> bool:
        return self.overlay.show_model_curves

    @show_model_curves.setter
    def show_model_curves(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SHOW_MODEL_CURVES', 'show': bool(value)})
            return
        self.overlay.show_model_curves = value

    @property
    def show_paleoisochrons(self) -> bool:
        return self.overlay.show_paleoisochrons

    @show_paleoisochrons.setter
    def show_paleoisochrons(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SHOW_PALEOISOCHRONS', 'show': bool(value)})
            return
        self.overlay.show_paleoisochrons = value

    @property
    def show_plumbotectonics_curves(self) -> bool:
        return self.overlay.show_plumbotectonics_curves

    @show_plumbotectonics_curves.setter
    def show_plumbotectonics_curves(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SHOW_PLUMBOTECTONICS_CURVES', 'show': bool(value)})
            return
        self.overlay.show_plumbotectonics_curves = value

    @property
    def show_model_age_lines(self) -> bool:
        return self.overlay.show_model_age_lines

    @show_model_age_lines.setter
    def show_model_age_lines(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SHOW_MODEL_AGE_LINES', 'show': bool(value)})
            return
        self.overlay.show_model_age_lines = value

    @property
    def show_isochrons(self) -> bool:
        return self.overlay.show_isochrons

    @show_isochrons.setter
    def show_isochrons(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SHOW_ISOCHRONS', 'show': bool(value)})
            return
        self.overlay.show_isochrons = value

    @property
    def show_growth_curves(self) -> bool:
        return self.overlay.show_growth_curves

    @show_growth_curves.setter
    def show_growth_curves(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SHOW_GROWTH_CURVES', 'show': bool(value)})
            return
        self.overlay.show_growth_curves = value

    @property
    def show_equation_overlays(self) -> bool:
        return self.overlay.show_equation_overlays

    @show_equation_overlays.setter
    def show_equation_overlays(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SHOW_EQUATION_OVERLAYS', 'show': bool(value)})
            return
        self.overlay.show_equation_overlays = value

    @property
    def use_real_age_for_mu_kappa(self) -> bool:
        return self.overlay.use_real_age_for_mu_kappa

    @use_real_age_for_mu_kappa.setter
    def use_real_age_for_mu_kappa(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_USE_REAL_AGE_FOR_MU_KAPPA', 'enabled': bool(value)})
            return
        self.overlay.use_real_age_for_mu_kappa = value

    @property
    def mu_kappa_age_col(self) -> str | None:
        return self.overlay.mu_kappa_age_col

    @mu_kappa_age_col.setter
    def mu_kappa_age_col(self, value: str | None) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_MU_KAPPA_AGE_COL', 'column': value})
            return
        self.overlay.mu_kappa_age_col = value

    @property
    def isochron_label_options(self) -> dict[str, Any]:
        return self.overlay.isochron_label_options

    @isochron_label_options.setter
    def isochron_label_options(self, value: dict[str, Any]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_ISOCHRON_LABEL_OPTIONS', 'options': dict(value or {})})
            return
        self.overlay.isochron_label_options = value

    @property
    def geo_model_name(self) -> str:
        return self.overlay.geo_model_name

    @geo_model_name.setter
    def geo_model_name(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_GEO_MODEL_NAME', 'model_name': value})
            return
        self.overlay.geo_model_name = value

    @property
    def equation_overlays(self) -> list[dict[str, Any]]:
        return self.overlay.equation_overlays

    @equation_overlays.setter
    def equation_overlays(self, value: list[dict[str, Any]]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_EQUATION_OVERLAYS', 'overlays': list(value or [])})
            return
        self.overlay.equation_overlays = value

    @property
    def line_styles(self) -> dict[str, dict[str, Any]]:
        return self.overlay.line_styles

    @line_styles.setter
    def line_styles(self, value: dict[str, dict[str, Any]]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LINE_STYLES', 'line_styles': dict(value or {})})
            return
        self.overlay.line_styles = value

    @property
    def paleoisochron_min_age(self) -> int:
        return self.overlay.paleoisochron_min_age

    @paleoisochron_min_age.setter
    def paleoisochron_min_age(self, value: int) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PALEOISOCHRON_MIN_AGE', 'age': int(value)})
            return
        self.overlay.paleoisochron_min_age = value

    @property
    def paleoisochron_max_age(self) -> int:
        return self.overlay.paleoisochron_max_age

    @paleoisochron_max_age.setter
    def paleoisochron_max_age(self, value: int) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PALEOISOCHRON_MAX_AGE', 'age': int(value)})
            return
        self.overlay.paleoisochron_max_age = value

    @property
    def paleoisochron_step(self) -> int:
        return self.overlay.paleoisochron_step

    @paleoisochron_step.setter
    def paleoisochron_step(self, value: int) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PALEOISOCHRON_STEP', 'step': int(value)})
            return
        self.overlay.paleoisochron_step = value

    @property
    def paleoisochron_ages(self) -> list[int]:
        return self.overlay.paleoisochron_ages

    @paleoisochron_ages.setter
    def paleoisochron_ages(self, value: list[int]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PALEOISOCHRON_AGES', 'ages': list(value or [])})
            return
        self.overlay.paleoisochron_ages = value

    @property
    def plumbotectonics_variant(self) -> str:
        return self.overlay.plumbotectonics_variant

    @plumbotectonics_variant.setter
    def plumbotectonics_variant(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PLUMBOTECTONICS_VARIANT', 'variant': value})
            return
        self.overlay.plumbotectonics_variant = value

    @property
    def plumbotectonics_group_visibility(self) -> dict[str, bool]:
        return self.overlay.plumbotectonics_group_visibility

    @plumbotectonics_group_visibility.setter
    def plumbotectonics_group_visibility(self, value: dict[str, bool]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {'type': 'SET_PLUMBOTECTONICS_GROUP_VISIBILITY', 'visibility': dict(value or {})}
            )
            return
        self.overlay.plumbotectonics_group_visibility = value

    @property
    def model_curve_models(self) -> list[str] | None:
        return self.overlay.model_curve_models

    @model_curve_models.setter
    def model_curve_models(self, value: list[str] | None) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            normalized = list(value or []) if value is not None else None
            state_store.dispatch({'type': 'SET_MODEL_CURVE_MODELS', 'models': normalized})
            return
        self.overlay.model_curve_models = value

    @property
    def isochron_error_mode(self) -> str:
        return self.overlay.isochron_error_mode

    @isochron_error_mode.setter
    def isochron_error_mode(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            mode = str(value or 'fixed').strip().lower()
            if mode == 'columns':
                state_store.dispatch(
                    {
                        'type': 'SET_ISOCHRON_ERROR_COLUMNS',
                        'sx_col': str(getattr(self.overlay, 'isochron_sx_col', '') or ''),
                        'sy_col': str(getattr(self.overlay, 'isochron_sy_col', '') or ''),
                        'rxy_col': str(getattr(self.overlay, 'isochron_rxy_col', '') or ''),
                    }
                )
            else:
                state_store.dispatch(
                    {
                        'type': 'SET_ISOCHRON_ERROR_FIXED',
                        'sx_value': float(getattr(self.overlay, 'isochron_sx_value', 0.001) or 0.001),
                        'sy_value': float(getattr(self.overlay, 'isochron_sy_value', 0.001) or 0.001),
                        'rxy_value': float(getattr(self.overlay, 'isochron_rxy_value', 0.0) or 0.0),
                    }
                )
            return
        self.overlay.isochron_error_mode = value

    @property
    def isochron_sx_col(self) -> str:
        return self.overlay.isochron_sx_col

    @isochron_sx_col.setter
    def isochron_sx_col(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_ISOCHRON_ERROR_COLUMNS',
                    'sx_col': str(value or ''),
                    'sy_col': str(getattr(self.overlay, 'isochron_sy_col', '') or ''),
                    'rxy_col': str(getattr(self.overlay, 'isochron_rxy_col', '') or ''),
                }
            )
            return
        self.overlay.isochron_sx_col = value

    @property
    def isochron_sy_col(self) -> str:
        return self.overlay.isochron_sy_col

    @isochron_sy_col.setter
    def isochron_sy_col(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_ISOCHRON_ERROR_COLUMNS',
                    'sx_col': str(getattr(self.overlay, 'isochron_sx_col', '') or ''),
                    'sy_col': str(value or ''),
                    'rxy_col': str(getattr(self.overlay, 'isochron_rxy_col', '') or ''),
                }
            )
            return
        self.overlay.isochron_sy_col = value

    @property
    def isochron_rxy_col(self) -> str:
        return self.overlay.isochron_rxy_col

    @isochron_rxy_col.setter
    def isochron_rxy_col(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_ISOCHRON_ERROR_COLUMNS',
                    'sx_col': str(getattr(self.overlay, 'isochron_sx_col', '') or ''),
                    'sy_col': str(getattr(self.overlay, 'isochron_sy_col', '') or ''),
                    'rxy_col': str(value or ''),
                }
            )
            return
        self.overlay.isochron_rxy_col = value

    @property
    def isochron_sx_value(self) -> float:
        return self.overlay.isochron_sx_value

    @isochron_sx_value.setter
    def isochron_sx_value(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_ISOCHRON_ERROR_FIXED',
                    'sx_value': float(value),
                    'sy_value': float(getattr(self.overlay, 'isochron_sy_value', 0.001) or 0.001),
                    'rxy_value': float(getattr(self.overlay, 'isochron_rxy_value', 0.0) or 0.0),
                }
            )
            return
        self.overlay.isochron_sx_value = value

    @property
    def isochron_sy_value(self) -> float:
        return self.overlay.isochron_sy_value

    @isochron_sy_value.setter
    def isochron_sy_value(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_ISOCHRON_ERROR_FIXED',
                    'sx_value': float(getattr(self.overlay, 'isochron_sx_value', 0.001) or 0.001),
                    'sy_value': float(value),
                    'rxy_value': float(getattr(self.overlay, 'isochron_rxy_value', 0.0) or 0.0),
                }
            )
            return
        self.overlay.isochron_sy_value = value

    @property
    def isochron_rxy_value(self) -> float:
        return self.overlay.isochron_rxy_value

    @isochron_rxy_value.setter
    def isochron_rxy_value(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_ISOCHRON_ERROR_FIXED',
                    'sx_value': float(getattr(self.overlay, 'isochron_sx_value', 0.001) or 0.001),
                    'sy_value': float(getattr(self.overlay, 'isochron_sy_value', 0.001) or 0.001),
                    'rxy_value': float(value),
                }
            )
            return
        self.overlay.isochron_rxy_value = value

    @property
    def selected_isochron_data(self) -> Any | None:
        return self.overlay.selected_isochron_data

    @selected_isochron_data.setter
    def selected_isochron_data(self, value: Any) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_SELECTED_ISOCHRON_DATA', 'data': value})
            return
        self.overlay.selected_isochron_data = value

    @property
    def isochron_results(self) -> dict[str, Any]:
        return self.overlay.isochron_results

    @isochron_results.setter
    def isochron_results(self, value: dict[str, Any]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_ISOCHRON_RESULTS', 'results': dict(value or {})})
            return
        self.overlay.isochron_results = value

    @property
    def model_curve_width(self) -> float:
        return self.overlay.model_curve_width

    @model_curve_width.setter
    def model_curve_width(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_MODEL_CURVE_WIDTH', 'width': float(value)})
            return
        self.overlay.model_curve_width = value

    @property
    def plumbotectonics_curve_width(self) -> float:
        return self.overlay.plumbotectonics_curve_width

    @plumbotectonics_curve_width.setter
    def plumbotectonics_curve_width(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PLUMBOTECTONICS_CURVE_WIDTH', 'width': float(value)})
            return
        self.overlay.plumbotectonics_curve_width = value

    @property
    def paleoisochron_width(self) -> float:
        return self.overlay.paleoisochron_width

    @paleoisochron_width.setter
    def paleoisochron_width(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PALEOISOCHRON_WIDTH', 'width': float(value)})
            return
        self.overlay.paleoisochron_width = value

    @property
    def model_age_line_width(self) -> float:
        return self.overlay.model_age_line_width

    @model_age_line_width.setter
    def model_age_line_width(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_MODEL_AGE_LINE_WIDTH', 'width': float(value)})
            return
        self.overlay.model_age_line_width = value

    @property
    def isochron_line_width(self) -> float:
        return self.overlay.isochron_line_width

    @isochron_line_width.setter
    def isochron_line_width(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_ISOCHRON_LINE_WIDTH', 'width': float(value)})
            return
        self.overlay.isochron_line_width = value

    @property
    def overlay_artists(self) -> dict[str, list[Any]]:
        return self.overlay.overlay_artists

    @overlay_artists.setter
    def overlay_artists(self, value: dict[str, list[Any]]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_OVERLAY_ARTISTS', 'artists': dict(value or {})})
            return
        self.overlay.overlay_artists = value

    @property
    def overlay_curve_label_data(self) -> list[dict[str, Any]]:
        return self.overlay.overlay_curve_label_data

    @overlay_curve_label_data.setter
    def overlay_curve_label_data(self, value: list[dict[str, Any]]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_OVERLAY_CURVE_LABEL_DATA', 'data': list(value or [])})
            return
        self.overlay.overlay_curve_label_data = value

    @property
    def paleoisochron_label_data(self) -> list[dict[str, Any]]:
        return self.overlay.paleoisochron_label_data

    @paleoisochron_label_data.setter
    def paleoisochron_label_data(self, value: list[dict[str, Any]]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PALEOISOCHRON_LABEL_DATA', 'data': list(value or [])})
            return
        self.overlay.paleoisochron_label_data = value

    @property
    def plumbotectonics_label_data(self) -> list[dict[str, Any]]:
        return self.overlay.plumbotectonics_label_data

    @plumbotectonics_label_data.setter
    def plumbotectonics_label_data(self, value: list[dict[str, Any]]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_PLUMBOTECTONICS_LABEL_DATA', 'data': list(value or [])})
            return
        self.overlay.plumbotectonics_label_data = value

    @property
    def plumbotectonics_isoage_label_data(self) -> list[dict[str, Any]]:
        return self.overlay.plumbotectonics_isoage_label_data

    @plumbotectonics_isoage_label_data.setter
    def plumbotectonics_isoage_label_data(self, value: list[dict[str, Any]]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {'type': 'SET_PLUMBOTECTONICS_ISOAGE_LABEL_DATA', 'data': list(value or [])}
            )
            return
        self.overlay.plumbotectonics_isoage_label_data = value

    # ------------------------------------------------------------------ #
    # Backward-compatible property delegation: LegendState
    # ------------------------------------------------------------------ #

    @property
    def legend_position(self) -> str | None:
        return self.legend.legend_position

    @legend_position.setter
    def legend_position(self, value: str | None) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_POSITION', 'position': value})
            return
        self.legend.legend_position = value

    @property
    def legend_columns(self) -> int:
        return self.legend.legend_columns

    @legend_columns.setter
    def legend_columns(self, value: int) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_COLUMNS', 'columns': int(value)})
            return
        self.legend.legend_columns = value

    @property
    def legend_offset(self) -> tuple[float, float]:
        return self.legend.legend_offset

    @legend_offset.setter
    def legend_offset(self, value: tuple[float, float]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_OFFSET', 'offset': value})
            return
        self.legend.legend_offset = value

    @property
    def legend_nudge_step(self) -> float:
        return self.legend.legend_nudge_step

    @legend_nudge_step.setter
    def legend_nudge_step(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_NUDGE_STEP', 'step': float(value)})
            return
        self.legend.legend_nudge_step = value

    @property
    def legend_location(self) -> str:
        return self.legend.legend_location

    @legend_location.setter
    def legend_location(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_LOCATION', 'location': value})
            return
        self.legend.legend_location = value

    @property
    def legend_display_mode(self) -> str:
        return self.legend.legend_display_mode

    @legend_display_mode.setter
    def legend_display_mode(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_DISPLAY_MODE', 'mode': str(value)})
            return
        self.legend.legend_display_mode = value

    @property
    def legend_frame_on(self) -> bool:
        return self.legend.legend_frame_on

    @legend_frame_on.setter
    def legend_frame_on(self, value: bool) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_FRAME_ON', 'enabled': bool(value)})
            return
        self.legend.legend_frame_on = value

    @property
    def legend_frame_alpha(self) -> float:
        return self.legend.legend_frame_alpha

    @legend_frame_alpha.setter
    def legend_frame_alpha(self, value: float) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_FRAME_ALPHA', 'alpha': float(value)})
            return
        self.legend.legend_frame_alpha = value

    @property
    def legend_frame_facecolor(self) -> str:
        return self.legend.legend_frame_facecolor

    @legend_frame_facecolor.setter
    def legend_frame_facecolor(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_FRAME_FACECOLOR', 'color': str(value)})
            return
        self.legend.legend_frame_facecolor = value

    @property
    def legend_frame_edgecolor(self) -> str:
        return self.legend.legend_frame_edgecolor

    @legend_frame_edgecolor.setter
    def legend_frame_edgecolor(self, value: str) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_LEGEND_FRAME_EDGECOLOR', 'color': str(value)})
            return
        self.legend.legend_frame_edgecolor = value

    @property
    def hidden_groups(self) -> set[str]:
        return self.legend.hidden_groups

    @hidden_groups.setter
    def hidden_groups(self, value: set[str]) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch({'type': 'SET_HIDDEN_GROUPS', 'groups': set(value or set())})
            return
        self.legend.hidden_groups = value

    @property
    def legend_to_scatter(self) -> dict[Any, Any]:
        return self.legend.legend_to_scatter

    @legend_to_scatter.setter
    def legend_to_scatter(self, value: dict[Any, Any]) -> None:
        self.legend.legend_to_scatter = value

    @property
    def legend_update_callback(self) -> Callable[[], None] | None:
        return self.legend.legend_update_callback

    @legend_update_callback.setter
    def legend_update_callback(self, value: Callable[[], None] | None) -> None:
        self.legend.legend_update_callback = value

    @property
    def legend_last_title(self) -> Any | None:
        return self.legend.legend_last_title

    @legend_last_title.setter
    def legend_last_title(self, value: Any) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_LEGEND_SNAPSHOT',
                    'title': value,
                    'handles': getattr(self.legend, 'legend_last_handles', None),
                    'labels': getattr(self.legend, 'legend_last_labels', None),
                }
            )
            return
        self.legend.legend_last_title = value

    @property
    def legend_last_handles(self) -> Any | None:
        return self.legend.legend_last_handles

    @legend_last_handles.setter
    def legend_last_handles(self, value: Any) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_LEGEND_SNAPSHOT',
                    'title': getattr(self.legend, 'legend_last_title', None),
                    'handles': value,
                    'labels': getattr(self.legend, 'legend_last_labels', None),
                }
            )
            return
        self.legend.legend_last_handles = value

    @property
    def legend_last_labels(self) -> Any | None:
        return self.legend.legend_last_labels

    @legend_last_labels.setter
    def legend_last_labels(self, value: Any) -> None:
        state_store = getattr(self, 'state_store', None)
        if state_store is not None:
            state_store.dispatch(
                {
                    'type': 'SET_LEGEND_SNAPSHOT',
                    'title': getattr(self.legend, 'legend_last_title', None),
                    'handles': getattr(self.legend, 'legend_last_handles', None),
                    'labels': value,
                }
            )
            return
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
