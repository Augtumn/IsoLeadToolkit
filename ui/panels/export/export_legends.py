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

_LEGEND_BBOX_POINT_EPSILON = 1e-9

class ExportPanelLegendMixin:
    """Legend normalisation and preview label state for export figures."""

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
            'fig': app_state.fig,
            'ax': app_state.ax,
            'overlay_label_refreshing': bool(app_state.overlay_label_refreshing),
            'adjust_text_in_progress': bool(app_state.adjust_text_in_progress),
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

    def _normalize_export_legends(
        self,
        export_fig,
        profile: dict,
        legend_size_override: int | None = None,
        legend_marker_override: int | None = None,
    ) -> None:
        """Rebuild legends with preset-specific style so size is deterministic."""
        if export_fig is None:
            return
        legend_style = dict(profile.get('legend', {}) or {})
        legend_size = float(legend_size_override if legend_size_override is not None else legend_style.get('fontsize', 8.0))
        title_size = float(legend_style.get('title_fontsize', legend_size + 0.5))
        marker_scale = float(legend_style.get('markerscale', 0.9))
        legend_marker_size = float(legend_marker_override if legend_marker_override is not None else profile.get('point_size', 50))
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
                    self._apply_legend_marker_size_from_point(rebuilt_legend, legend_marker_size)
            except Exception:
                try:
                    # Fallback for older Matplotlib versions lacking title_fontsize.
                    new_legend_kwargs.pop('title_fontsize', None)
                    rebuilt_legend = ax.legend(**new_legend_kwargs)
                    if rebuilt_legend is not None:
                        rebuilt_legend.get_title().set_fontsize(title_size)
                        rebuilt_legend.set_title("")
                        rebuilt_legend.get_title().set_visible(False)
                        self._apply_legend_marker_size_from_point(rebuilt_legend, legend_marker_size)
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
