"""
Compatibility view classes providing layered access to AppState fields.
Each view wraps AppState with property getter/setter pairs that delegate
to the underlying AppState, dispatching through StateStore when available.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
