"""Shared helper methods for export panel."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from matplotlib.colors import to_hex

from application import (
    build_image_export_profile,
    fallback_export_rc,
    normalize_export_target,
    resolve_image_save_options,
    save_export_figure,
)
from core import CONFIG, app_state, state_gateway

logger = logging.getLogger(__name__)
_LEGEND_BBOX_POINT_EPSILON = 1e-9

class ExportPanelPrepMixin:
    """Prepare the figure/columns to export (mode rendering, axis view, palettes)."""

    def _resolve_group_col(self) -> str | None:
        """Resolve group column using current state fallback rules."""
        group_col = app_state.last_group_col
        group_cols = list(app_state.group_cols or [])
        if not group_col or group_col not in group_cols:
            if group_cols:
                return group_cols[0]
            return None
        return group_col

    def _default_numeric_cols(self) -> list[str]:
        """Return numeric data columns available in current dataframe."""
        df_global = app_state.df_global
        if df_global is None:
            return []
        data_cols = list(app_state.data_cols or [])
        return [c for c in data_cols if c in df_global.columns]

    def _resolve_2d_cols(self) -> list[str]:
        """Return valid 2D column selection with fallback defaults."""
        available = self._default_numeric_cols()
        selected = [c for c in list(app_state.selected_2d_cols or []) if c in available]
        if len(selected) >= 2:
            return selected[:2]
        return available[:2]

    def _resolve_3d_cols(self) -> list[str]:
        """Return valid 3D column selection with fallback defaults."""
        available = self._default_numeric_cols()
        selected = [c for c in list(app_state.selected_3d_cols or []) if c in available]
        if len(selected) >= 3:
            return selected[:3]
        return available[:3]

    def _render_current_mode_sync(self, point_size: int | None = None) -> bool:
        """Render current mode synchronously onto app_state.fig/app_state.ax."""
        from visualization.plotting import plot_2d_data, plot_3d_data, plot_embedding

        render_mode = str(app_state.render_mode or '')
        group_col = self._resolve_group_col()
        if not group_col:
            logger.warning("No group column available for image export")
            return False

        size = int(point_size if point_size is not None else app_state.point_size)

        if render_mode == '2D':
            cols_2d = self._resolve_2d_cols()
            if len(cols_2d) != 2:
                return False
            is_kde = bool(app_state.show_kde or getattr(app_state, 'show_2d_kde', False))
            return bool(plot_2d_data(group_col, cols_2d, size=size, show_kde=is_kde))

        if render_mode == '3D':
            cols_3d = self._resolve_3d_cols()
            if len(cols_3d) != 3:
                return False
            return bool(plot_3d_data(group_col, cols_3d, size=size))

        mode_normalized = str(render_mode).strip().upper()
        if mode_normalized == 'TSNE':
            expected_embedding_type = 'tSNE'
        elif mode_normalized == 'ROBUSTPCA':
            expected_embedding_type = 'RobustPCA'
        else:
            expected_embedding_type = render_mode

        cached_embedding = getattr(app_state, 'last_embedding', None)
        cached_type = getattr(app_state, 'last_embedding_type', None)
        use_cached_embedding = (
            cached_embedding is not None
            and str(cached_type or '') == str(expected_embedding_type)
        )

        precomputed_meta = {
            'last_pca_variance': app_state.last_pca_variance,
            'last_pca_components': app_state.last_pca_components,
            'current_feature_names': app_state.current_feature_names,
        }

        return bool(
            plot_embedding(
                group_col,
                render_mode,
                umap_params=app_state.umap_params,
                tsne_params=app_state.tsne_params,
                pca_params=app_state.pca_params,
                robust_pca_params=app_state.robust_pca_params,
                size=size,
                precomputed_embedding=cached_embedding if use_cached_embedding else None,
                precomputed_meta=precomputed_meta if use_cached_embedding else None,
            )
        )

    @staticmethod
    def _capture_axis_view(ax) -> dict | None:
        """Capture axis limits and camera so export matches current view."""
        if ax is None:
            return None
        try:
            view = {
                'is3d': getattr(ax, 'name', '') == '3d',
                'xlim': ax.get_xlim(),
                'ylim': ax.get_ylim(),
            }
            if view['is3d']:
                view['zlim'] = ax.get_zlim()
                view['elev'] = getattr(ax, 'elev', None)
                view['azim'] = getattr(ax, 'azim', None)
            return view
        except Exception:
            return None

    @staticmethod
    def _apply_axis_view(ax, view: dict | None) -> None:
        """Apply previously captured axis view when axes are compatible."""
        if ax is None or not view:
            return
        try:
            is3d_now = getattr(ax, 'name', '') == '3d'
            if bool(view.get('is3d', False)) != is3d_now:
                return
            ax.set_xlim(view['xlim'])
            ax.set_ylim(view['ylim'])
            if is3d_now and 'zlim' in view:
                ax.set_zlim(view['zlim'])
                elev = view.get('elev')
                azim = view.get('azim')
                if elev is not None or azim is not None:
                    ax.view_init(
                        elev=elev if elev is not None else getattr(ax, 'elev', None),
                        azim=azim if azim is not None else getattr(ax, 'azim', None),
                    )
        except Exception:
            pass

    @staticmethod
    def _palette_from_axis_collections(ax, fallback_palette: dict) -> dict:
        """Extract visible scatter colors from current axis to preserve user-edited colors."""
        palette = dict(fallback_palette or {})
        if ax is None:
            return palette
        for collection in list(getattr(ax, 'collections', []) or []):
            try:
                label = str(collection.get_label() or '')
                if not label or label.startswith('_'):
                    continue
                facecolors = collection.get_facecolors()
                if facecolors is None or len(facecolors) == 0:
                    continue
                rgba = facecolors[0]
                palette[label] = to_hex(rgba, keep_alpha=False)
            except Exception:
                continue
        return palette
