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


class ExportPanelCommonMixin:
    """Shared helper methods consumed by export mixins."""

    def _load_scienceplots(self):
        """Load scienceplots from installed environment or local reference clone."""
        try:
            import scienceplots  # noqa: F401
            return True
        except Exception as err:
            logger.warning("_load_scienceplots failed: %s", err)

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

    @staticmethod
    def _profile_default_params(profile: dict) -> dict:
        """Compute all export parameter defaults from a journal profile dict."""
        legend_style = dict(profile.get('legend', {}) or {})
        legend_fontsize = float(legend_style.get('fontsize', 8.0))
        return {
            'point_size': int(profile.get('point_size', 60)),
            'legend_size': int(round(legend_fontsize)),
            'label_size': int(round(legend_fontsize + 2.0)),
            'title_size': int(round(legend_fontsize + 3.0)),
            'tick_size': int(round(legend_fontsize - 0.5)),
            'dpi': int(profile.get('dpi', 400)),
            'tight_bbox': True,
            'transparent': False,
            'pad_inches': 0.02,
            'image_ext': 'png',
            'embed_fonts': True,
            'white_background': True,
        }

    def _resolve_export_save_options(self, profile: dict, *, overrides: dict | None = None) -> dict:
        """Collect figure save options from export controls.

        All current callers pass *overrides* (the panel builds no export
        control widgets of its own), so only the override path is kept.
        """
        dpi_override = int(overrides.get('dpi', profile.get('dpi', 400)))
        use_tight_bbox = bool(overrides.get('tight_bbox', True))
        transparent = bool(overrides.get('transparent', False))
        pad_inches = float(overrides.get('pad_inches', 0.02))
        preset_key = str(overrides.get('preset_key', 'science_single'))
        image_ext = str(overrides.get('image_ext', 'png'))
        embed_fonts = bool(overrides.get('embed_fonts', True))
        white_background = bool(overrides.get('white_background', True))
        point_size = int(overrides.get('point_size', profile.get('point_size', 60)))
        legend_size = int(overrides.get('legend_size', 8))
        label_size = int(overrides.get('label_size', 10))
        title_size = int(overrides.get('title_size', 12))
        tick_size = int(overrides.get('tick_size', 9))

        state_gateway.set_export_image_options(
            preset_key=str(preset_key),
            image_ext=str(image_ext),
            dpi=dpi_override,
            bbox_tight=use_tight_bbox,
            pad_inches=pad_inches,
            transparent=transparent,
            point_size=point_size,
            legend_size=legend_size,
            label_size=label_size,
            title_size=title_size,
            tick_size=tick_size,
            embed_fonts=embed_fonts,
            white_background=white_background,
        )

        return resolve_image_save_options(
            profile=profile,
            dpi_override=dpi_override,
            bbox_tight=use_tight_bbox,
            transparent=transparent,
            pad_inches=pad_inches,
            default_dpi=int(CONFIG.get('savefig_dpi', 400)),
            embed_fonts=embed_fonts,
            white_background=white_background,
        )

    @staticmethod
    def _fallback_export_rc(
        profile: dict,
        *,
        label_fontsize: int | None = None,
        title_fontsize: int | None = None,
        tick_fontsize: int | None = None,
    ) -> dict:
        """Fallback rcParams when SciencePlots is unavailable."""
        return fallback_export_rc(
            profile,
            label_fontsize=label_fontsize,
            title_fontsize=title_fontsize,
            tick_fontsize=tick_fontsize,
        )

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
        embed_fonts: bool = True,
        white_background: bool = True,
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
            metadata=self._export_figure_metadata(),
            embed_fonts=bool(embed_fonts),
            white_background=bool(white_background),
        )

    @staticmethod
    def _export_figure_metadata() -> dict[str, str]:
        """PDF document metadata: the plot title plus this application."""
        title = str(getattr(app_state, 'current_plot_title', '') or '').strip()
        metadata = {'Creator': 'IsotopesAnalyse', 'Producer': 'IsotopesAnalyse'}
        if title:
            metadata['Title'] = title
            metadata['Subject'] = title
        return metadata

