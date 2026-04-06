"""Shared helper methods for export panel."""

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


class ExportPanelCommonMixin:
    """Shared helper methods consumed by export mixins."""

    def _resolve_group_col(self) -> str | None:
        """Resolve group column using current state fallback rules."""
        group_col = getattr(app_state, 'last_group_col', None)
        group_cols = list(getattr(app_state, 'group_cols', []) or [])
        if not group_col or group_col not in group_cols:
            if group_cols:
                return group_cols[0]
            return None
        return group_col

    def _default_numeric_cols(self) -> list[str]:
        """Return numeric data columns available in current dataframe."""
        df_global = getattr(app_state, 'df_global', None)
        if df_global is None:
            return []
        data_cols = list(getattr(app_state, 'data_cols', []) or [])
        return [c for c in data_cols if c in df_global.columns]

    def _resolve_2d_cols(self) -> list[str]:
        """Return valid 2D column selection with fallback defaults."""
        available = self._default_numeric_cols()
        selected = [c for c in list(getattr(app_state, 'selected_2d_cols', []) or []) if c in available]
        if len(selected) >= 2:
            return selected[:2]
        return available[:2]

    def _resolve_3d_cols(self) -> list[str]:
        """Return valid 3D column selection with fallback defaults."""
        available = self._default_numeric_cols()
        selected = [c for c in list(getattr(app_state, 'selected_3d_cols', []) or []) if c in available]
        if len(selected) >= 3:
            return selected[:3]
        return available[:3]

    def _render_current_mode_sync(self, point_size: int | None = None) -> bool:
        """Render current mode synchronously onto app_state.fig/app_state.ax."""
        from visualization.plotting import plot_2d_data, plot_3d_data, plot_embedding

        render_mode = str(getattr(app_state, 'render_mode', '') or '')
        group_col = self._resolve_group_col()
        if not group_col:
            logger.warning("No group column available for image export")
            return False

        size = int(point_size if point_size is not None else getattr(app_state, 'point_size', 60))

        if render_mode == '2D':
            cols_2d = self._resolve_2d_cols()
            if len(cols_2d) != 2:
                return False
            is_kde = bool(getattr(app_state, 'show_kde', False) or getattr(app_state, 'show_2d_kde', False))
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
            'last_pca_variance': getattr(app_state, 'last_pca_variance', None),
            'last_pca_components': getattr(app_state, 'last_pca_components', None),
            'current_feature_names': getattr(app_state, 'current_feature_names', None),
        }

        return bool(
            plot_embedding(
                group_col,
                render_mode,
                umap_params=getattr(app_state, 'umap_params', None),
                tsne_params=getattr(app_state, 'tsne_params', None),
                pca_params=getattr(app_state, 'pca_params', None),
                robust_pca_params=getattr(app_state, 'robust_pca_params', None),
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

    def _load_scienceplots(self):
        """Load scienceplots from installed environment or local reference clone."""
        try:
            import scienceplots  # noqa: F401
            return True
        except Exception:
            pass

        workspace_root = Path(__file__).resolve().parents[3]
        local_src = workspace_root / 'reference' / 'SciencePlots-master' / 'src'
        if local_src.exists():
            src_str = str(local_src)
            if src_str not in sys.path:
                sys.path.insert(0, src_str)
        try:
            import scienceplots  # noqa: F401
            return True
        except Exception as err:
            logger.warning("Failed to import scienceplots: %s", err)
            return False

    def _image_export_profile(self, preset_key: str) -> dict:
        """Return export profile for a journal preset."""
        return build_image_export_profile(preset_key)

    def _resolve_export_point_size(self, profile: dict) -> int:
        """Resolve point size from UI override or profile default."""
        point_size = int(profile.get('point_size', 60))
        if self.image_point_size_spin is not None:
            point_size = int(self.image_point_size_spin.value())
        return point_size

    def _resolve_export_legend_size(self, profile: dict) -> int:
        """Resolve legend font size from UI override or profile default."""
        point_size = int(round(float((profile.get('legend', {}) or {}).get('fontsize', 8.0))))
        if self.image_legend_size_spin is not None:
            point_size = int(self.image_legend_size_spin.value())
        return point_size

    def _resolve_export_save_options(self, profile: dict) -> dict:
        """Collect figure save options from export controls."""
        dpi_override = int(self.image_dpi_spin.value()) if self.image_dpi_spin is not None else None
        use_tight_bbox = bool(self.image_tight_bbox_check.isChecked()) if self.image_tight_bbox_check is not None else True
        transparent = bool(self.image_transparent_check.isChecked()) if self.image_transparent_check is not None else False
        preset_key = self.image_preset_combo.currentData() if self.image_preset_combo is not None else 'science_single'
        image_ext = self.image_format_combo.currentData() if self.image_format_combo is not None else 'png'
        point_size = int(self.image_point_size_spin.value()) if self.image_point_size_spin is not None else None
        legend_size = int(self.image_legend_size_spin.value()) if self.image_legend_size_spin is not None else None
        pad_inches = 0.02
        if self.image_pad_inches_spin is not None:
            pad_inches = float(self.image_pad_inches_spin.value())

        state_gateway.set_export_image_options(
            preset_key=str(preset_key),
            image_ext=str(image_ext),
            dpi=dpi_override,
            bbox_tight=use_tight_bbox,
            pad_inches=pad_inches,
            transparent=transparent,
            point_size=point_size,
            legend_size=legend_size,
        )

        return resolve_image_save_options(
            profile=profile,
            dpi_override=dpi_override,
            bbox_tight=use_tight_bbox,
            transparent=transparent,
            pad_inches=pad_inches,
            default_dpi=int(CONFIG.get('savefig_dpi', 400)),
        )

    @staticmethod
    def _fallback_export_rc(profile: dict) -> dict:
        """Fallback rcParams when SciencePlots is unavailable."""
        return fallback_export_rc(profile)

    @staticmethod
    def _normalize_export_target(file_path: str, preferred_ext: str) -> tuple[str, str]:
        """Normalize output path and extension using supported export formats."""
        return normalize_export_target(file_path, preferred_ext)

    def _save_export_figure(
        self,
        export_fig,
        file_path: str,
        image_ext: str,
        export_dpi: int,
        bbox_tight: bool,
        pad_inches: float,
        transparent: bool,
    ) -> None:
        """Save figure using unified export options."""
        save_export_figure(
            export_fig,
            file_path,
            image_ext,
            export_dpi=int(export_dpi),
            bbox_tight=bool(bbox_tight),
            pad_inches=float(pad_inches),
            transparent=bool(transparent),
        )

    @staticmethod
    def _snapshot_overlay_label_state() -> dict:
        """Capture overlay label entries currently tracked in app_state."""
        keys = (
            'paleoisochron_label_data',
            'plumbotectonics_label_data',
            'plumbotectonics_isoage_label_data',
            'overlay_curve_label_data',
        )
        snapshot = {}
        for key in keys:
            value = getattr(app_state, key, [])
            if isinstance(value, list):
                snapshot[key] = list(value)
            else:
                snapshot[key] = []
        return snapshot

    def _attach_preview_label_state(self, preview_fig) -> None:
        """Attach overlay label metadata to preview figure for interaction refresh."""
        if preview_fig is None:
            return
        try:
            preview_fig._overlay_label_state = self._snapshot_overlay_label_state()
        except Exception:
            preview_fig._overlay_label_state = {}

    def _refresh_preview_overlay_labels(self, preview_fig, preview_ax) -> None:
        """Refresh overlay labels on preview axes after pan/zoom interactions."""
        from visualization.plotting import refresh_paleoisochron_labels

        if preview_fig is None or preview_ax is None:
            return
        label_state = getattr(preview_fig, '_overlay_label_state', None)
        if not isinstance(label_state, dict) or not label_state:
            return

        keys = (
            'paleoisochron_label_data',
            'plumbotectonics_label_data',
            'plumbotectonics_isoage_label_data',
            'overlay_curve_label_data',
        )
        backup = {
            'fig': getattr(app_state, 'fig', None),
            'ax': getattr(app_state, 'ax', None),
            'overlay_label_refreshing': bool(getattr(app_state, 'overlay_label_refreshing', False)),
            'adjust_text_in_progress': bool(getattr(app_state, 'adjust_text_in_progress', False)),
        }
        for key in keys:
            backup[key] = getattr(app_state, key, [])

        try:
            state_gateway.set_figure_axes(preview_fig, preview_ax)
            state_gateway.set_overlay_label_flags(refreshing=False, adjust_in_progress=False)
            state_gateway.set_overlay_label_state({
                key: list(label_state.get(key, [])) for key in keys
            })

            refresh_paleoisochron_labels()

            # Keep updated references on the preview figure for subsequent interactions.
            for key in keys:
                label_state[key] = list(getattr(app_state, key, []) or [])
        except Exception as err:
            logger.debug("Preview overlay label refresh skipped: %s", err)
        finally:
            state_gateway.set_figure_axes(backup['fig'], backup['ax'])
            state_gateway.set_overlay_label_flags(
                refreshing=backup['overlay_label_refreshing'],
                adjust_in_progress=backup['adjust_text_in_progress'],
            )
            state_gateway.set_overlay_label_state({
                key: backup[key] for key in keys
            })

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

    def _normalize_export_legends(
        self,
        export_fig,
        profile: dict,
        legend_size_override: int | None = None,
        point_size_override: int | None = None,
    ) -> None:
        """Rebuild legends with preset-specific style so size is deterministic."""
        if export_fig is None:
            return
        legend_style = dict(profile.get('legend', {}) or {})
        legend_size = float(legend_size_override if legend_size_override is not None else legend_style.get('fontsize', 8.0))
        title_size = float(legend_style.get('title_fontsize', legend_size + 0.5))
        marker_scale = float(legend_style.get('markerscale', 0.9))
        point_size_for_legend = float(point_size_override if point_size_override is not None else profile.get('point_size', 50))
        handlelength = float(legend_style.get('handlelength', 1.2))
        handletextpad = float(legend_style.get('handletextpad', 0.5))
        labelspacing = float(legend_style.get('labelspacing', 0.3))
        borderpad = float(legend_style.get('borderpad', 0.3))
        columnspacing = float(legend_style.get('columnspacing', 0.7))

        for ax in list(getattr(export_fig, 'axes', []) or []):
            legend = None
            try:
                legend = ax.get_legend()
            except Exception:
                legend = None
            if legend is None:
                continue

            handles = getattr(legend, 'legend_handles', None)
            if handles is None:
                handles = getattr(legend, 'legendHandles', None)
            labels = [text.get_text() for text in legend.get_texts()]
            if not handles or not labels or len(handles) != len(labels):
                handles, labels = ax.get_legend_handles_labels()
            if not handles or not labels:
                continue

            frame_on = True
            try:
                frame_on = bool(legend.get_frame_on())
            except Exception:
                pass

            loc = getattr(legend, '_loc', 'best')
            ncol = int(getattr(legend, '_ncols', 1) or 1)
            bbox_anchor = None
            try:
                bbox = legend.get_bbox_to_anchor()
                if bbox is not None:
                    points = bbox.get_points()
                    if points is not None:
                        points_axes = ax.transAxes.inverted().transform(points)
                        x0, y0 = points_axes[0]
                        x1, y1 = points_axes[1]
                        if abs(x1 - x0) < _LEGEND_BBOX_POINT_EPSILON and abs(y1 - y0) < _LEGEND_BBOX_POINT_EPSILON:
                            bbox_anchor = (float(x0), float(y0))
                        else:
                            bbox_anchor = (float(x0), float(y0), float(x1 - x0), float(y1 - y0))
            except Exception:
                bbox_anchor = None

            try:
                legend.remove()
            except Exception:
                pass

            new_legend_kwargs = {
                'handles': handles,
                'labels': labels,
                'title': "",
                'loc': loc,
                'ncol': max(1, ncol),
                'frameon': frame_on,
                'fontsize': legend_size,
                'title_fontsize': title_size,
                'markerscale': marker_scale,
                'handlelength': handlelength,
                'handletextpad': handletextpad,
                'labelspacing': labelspacing,
                'borderpad': borderpad,
                'columnspacing': columnspacing,
                'borderaxespad': 0.2,
            }
            if bbox_anchor is not None:
                new_legend_kwargs['bbox_to_anchor'] = bbox_anchor

            try:
                rebuilt_legend = ax.legend(**new_legend_kwargs)
                if rebuilt_legend is not None:
                    rebuilt_legend.set_title("")
                    rebuilt_legend.get_title().set_visible(False)
                    self._apply_legend_marker_size_from_point(rebuilt_legend, point_size_for_legend)
            except Exception:
                try:
                    # Fallback for older Matplotlib versions lacking title_fontsize.
                    new_legend_kwargs.pop('title_fontsize', None)
                    rebuilt_legend = ax.legend(**new_legend_kwargs)
                    if rebuilt_legend is not None:
                        rebuilt_legend.get_title().set_fontsize(title_size)
                        rebuilt_legend.set_title("")
                        rebuilt_legend.get_title().set_visible(False)
                        self._apply_legend_marker_size_from_point(rebuilt_legend, point_size_for_legend)
                except Exception:
                    pass

    @staticmethod
    def _apply_legend_marker_size_from_point(legend, point_size: float) -> None:
        """Scale legend marker glyphs to follow plotted scatter point size."""
        import math

        if legend is None:
            return
        point_area = max(1.0, float(point_size))
        marker_size_pt = max(2.0, math.sqrt(point_area))
        scatter_area = point_area
        try:
            legend.set_markerscale(1.0)
        except Exception:
            pass

        handles = getattr(legend, 'legend_handles', None)
        if handles is None:
            handles = getattr(legend, 'legendHandles', None)
        if not handles:
            return

        for handle in handles:
            try:
                if hasattr(handle, 'set_markersize'):
                    handle.set_markersize(marker_size_pt)
                elif hasattr(handle, 'set_sizes'):
                    handle.set_sizes([scatter_area])
            except Exception:
                continue
