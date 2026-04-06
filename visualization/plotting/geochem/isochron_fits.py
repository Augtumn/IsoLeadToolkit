"""Isochron fit overlay rendering for Pb evolution plots."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

from core import app_state, state_gateway
from visualization.line_styles import resolve_line_style

from ..data import _get_analysis_data, _lazy_import_geochemistry
from ..isochron import resolve_isochron_errors as _resolve_isochron_errors
from .isochron_fit_76 import render_isochron1_group
from .isochron_fit_86 import render_isochron2_group
from .overlay_helpers import _register_overlay_artist

logger = logging.getLogger(__name__)


def _draw_isochron_overlays(ax: Any, actual_algorithm: str) -> None:
    """Draw isochron reference lines for Pb-Pb plots."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return

    try:
        if actual_algorithm == 'PB_EVOL_76':
            mode = 'ISOCHRON1'
        elif actual_algorithm == 'PB_EVOL_86':
            mode = 'ISOCHRON2'
        else:
            return

        params = geochemistry.engine.get_parameters()

        show_fits = getattr(app_state, 'show_isochrons', True)
        # In PB_EVOL_76/86, model curves already represent growth trajectories.
        show_growth = False
        if not show_fits and not show_growth:
            return

        _, indices = _get_analysis_data()
        if indices is None or len(indices) == 0:
            return

        data_state = getattr(app_state, 'data', app_state)
        df = getattr(data_state, 'df_global', app_state.df_global)
        if df is None:
            return

        col_206 = '206Pb/204Pb'
        col_207 = '207Pb/204Pb'
        col_208 = '208Pb/204Pb'

        x_col = col_206
        y_col = col_207 if mode == 'ISOCHRON1' else col_208
        if x_col not in df.columns or y_col not in df.columns:
            return

        # ISOCHRON2 also needs 207 column for age calculation and growth curves.
        need_207_for_86 = mode == 'ISOCHRON2' and col_207 in df.columns

        df_subset = df.iloc[indices]
        sx_all, sy_all, rxy_all = _resolve_isochron_errors(df_subset, len(df_subset))

        group_col = app_state.last_group_col
        current_palette = getattr(app_state, 'current_palette', {})

        if not group_col or group_col not in df_subset.columns:
            unique_groups = ['All Data']
            group_labels = np.array(['All Data'] * len(df_subset))
        else:
            group_labels = df_subset[group_col].fillna('Unknown').astype(str).values
            unique_groups = np.unique(group_labels)

        for grp in unique_groups:
            if app_state.visible_groups is not None and grp not in app_state.visible_groups and grp != 'All Data':
                continue

            mask = group_labels == grp
            if np.sum(mask) < 2:
                continue

            if grp == 'All Data':
                x_grp = pd.to_numeric(df_subset[x_col], errors='coerce').values
                y_grp = pd.to_numeric(df_subset[y_col], errors='coerce').values
                sx_grp = sx_all
                sy_grp = sy_all
                rxy_grp = rxy_all
            else:
                x_grp = pd.to_numeric(df_subset.loc[df_subset.index[mask], x_col], errors='coerce').values
                y_grp = pd.to_numeric(df_subset.loc[df_subset.index[mask], y_col], errors='coerce').values
                sx_grp = sx_all[mask]
                sy_grp = sy_all[mask]
                rxy_grp = rxy_all[mask]

            valid = ~np.isnan(x_grp) & ~np.isnan(y_grp)
            valid = valid & np.isfinite(sx_grp) & np.isfinite(sy_grp) & np.isfinite(rxy_grp)
            valid = valid & (sx_grp > 0) & (sy_grp > 0) & (np.abs(rxy_grp) <= 1)

            x_grp = x_grp[valid]
            y_grp = y_grp[valid]
            sx_grp = sx_grp[valid]
            sy_grp = sy_grp[valid]
            rxy_grp = rxy_grp[valid]

            if len(x_grp) < 2:
                continue

            try:
                fit = geochemistry.york_regression(x_grp, sx_grp, y_grp, sy_grp, rxy_grp)
                slope = fit['b']
                intercept = fit['a']
                slope_err = fit['sb']
                intercept_err = fit.get('sa', None)
            except Exception:
                continue

            if not hasattr(app_state, 'isochron_results'):
                state_gateway.set_isochron_results({})
            app_state.isochron_results[grp] = {
                'slope': slope,
                'intercept': intercept,
                'slope_err': slope_err,
                'intercept_err': intercept_err,
                'n_points': len(x_grp),
                'mswd': fit.get('mswd', None),
            }

            x_min_g, x_max_g = np.min(x_grp), np.max(x_grp)
            if x_max_g == x_min_g:
                continue

            span = x_max_g - x_min_g
            x_line = np.array([x_min_g - span * 0.1, x_max_g + span * 0.1])
            y_line = slope * x_line + intercept

            color = current_palette.get(grp, '#333333')
            if grp == 'All Data':
                color = '#64748b'

            isochron_style = resolve_line_style(
                app_state,
                'isochron',
                {
                    'color': None,
                    'linewidth': getattr(app_state, 'isochron_line_width', 1.5),
                    'linestyle': '-',
                    'alpha': 0.8,
                },
            )
            if show_fits:
                line_artists = ax.plot(
                    x_line,
                    y_line,
                    linestyle=isochron_style['linestyle'],
                    color=isochron_style['color'] or color,
                    linewidth=isochron_style['linewidth'],
                    alpha=isochron_style['alpha'],
                    zorder=2,
                )
                for artist in line_artists:
                    _register_overlay_artist('isochron', artist)

            if mode == 'ISOCHRON1':
                render_isochron1_group(
                    ax=ax,
                    geochemistry=geochemistry,
                    params=params,
                    grp=grp,
                    slope=slope,
                    intercept=intercept,
                    slope_err=slope_err,
                    x_line=x_line,
                    y_line=y_line,
                    color=color,
                    show_fits=show_fits,
                    show_growth=show_growth,
                )
            elif mode == 'ISOCHRON2':
                render_isochron2_group(
                    ax=ax,
                    geochemistry=geochemistry,
                    params=params,
                    grp=grp,
                    df_subset=df_subset,
                    col_207=col_207,
                    mask=mask,
                    valid=valid,
                    x_grp=x_grp,
                    sx_grp=sx_grp,
                    sy_grp=sy_grp,
                    rxy_grp=rxy_grp,
                    slope=slope,
                    x_line=x_line,
                    y_line=y_line,
                    color=color,
                    show_fits=show_fits,
                    show_growth=show_growth,
                    need_207_for_86=need_207_for_86,
                )

    except Exception as err:
        logger.warning('Failed to draw isochron overlays: %s', err)
