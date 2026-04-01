"""Isochron fit overlay rendering for Pb evolution plots."""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from core import app_state, state_gateway
from visualization.line_styles import resolve_line_style
from ..label_layout import position_curve_label
from ..data import _get_analysis_data, _lazy_import_geochemistry
from ..isochron import resolve_isochron_errors as _resolve_isochron_errors
from .isochron_labels import _build_isochron_label
from .overlay_helpers import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
)

logger = logging.getLogger(__name__)

def _draw_isochron_overlays(ax, actual_algorithm):
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

        col_206 = "206Pb/204Pb"
        col_207 = "207Pb/204Pb"
        col_208 = "208Pb/204Pb"

        x_col = col_206
        if mode == 'ISOCHRON1':
            y_col = col_207
        else:
            y_col = col_208
        if x_col not in df.columns or y_col not in df.columns:
            return
        # ISOCHRON2 also needs 207 column for age calculation and growth curves
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

        try:
            from data.geochemistry import (
                calculate_source_mu_from_isochron,
                calculate_source_kappa_from_slope,
            )
        except ImportError:
            calculate_source_mu_from_isochron = None
            calculate_source_kappa_from_slope = None

        for grp in unique_groups:
            if app_state.visible_groups is not None and grp not in app_state.visible_groups and grp != 'All Data':
                continue

            mask = (group_labels == grp)
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

            # 保存等时线回归结果到 app_state
            if not hasattr(app_state, 'isochron_results'):
                state_gateway.set_attr('isochron_results', {})
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
                    'alpha': 0.8
                }
            )
            if show_fits:
                line_artists = ax.plot(
                    x_line,
                    y_line,
                    linestyle=isochron_style['linestyle'],
                    color=isochron_style['color'] or color,
                    linewidth=isochron_style['linewidth'],
                    alpha=isochron_style['alpha'],
                    zorder=2
                )
                for artist in line_artists:
                    _register_overlay_artist('isochron', artist)

            if mode == 'ISOCHRON1' and geochemistry:
                age_ma = None
                try:
                    age_ma, _ = geochemistry.calculate_pbpb_age_from_ratio(slope, slope_err, params)
                    if age_ma is not None and age_ma >= 0:
                        app_state.isochron_results[grp]['age_ma'] = age_ma
                except Exception as age_err:
                    logger.warning("Failed to calculate isochron age for slope %.6f: %s", slope, age_err)

                label_opts = _resolve_label_options(
                    'isochron',
                    {
                        'label_text': '',
                        'label_fontsize': 9,
                        'label_background': False,
                        'label_bg_color': '#ffffff',
                        'label_bg_alpha': 0.85,
                        'label_position': 'auto',
                    }
                )
                label_text = _build_isochron_label(app_state.isochron_results[grp])
                age_val = app_state.isochron_results[grp].get('age')
                if age_val is None:
                    age_val = app_state.isochron_results[grp].get('age_ma')
                label_override = _format_label_text(label_opts.get('label_text'), age_val)
                if label_override:
                    label_text = label_override

                if show_fits and label_text:
                    text_artist = ax.text(
                        x_line[0],
                        y_line[0],
                        f" {label_text}",
                        color=color,
                        fontsize=label_opts['label_fontsize'],
                        va='center',
                        ha='center',
                        fontweight='bold',
                        bbox=_label_bbox(label_opts, edgecolor=color)
                    )
                    _register_overlay_curve_label(
                        text_artist,
                        x_line,
                        y_line,
                        f" {label_text}",
                        label_opts.get('label_position', 'auto'),
                        style_key='isochron'
                    )
                    position_curve_label(
                        ax,
                        text_artist,
                        mode='isoage',
                        x_line=x_line,
                        y_line=y_line,
                        label_text=f" {label_text}",
                        position_mode=label_opts.get('label_position', 'auto'),
                    )

                if show_growth and age_ma is not None and age_ma > 0:
                    growth = geochemistry.calculate_isochron1_growth_curve(
                        slope,
                        intercept,
                        age_ma,
                        params=params,
                        steps=100
                    )
                    if growth:
                        x_growth = growth['x']
                        y_growth = growth['y']
                        mu_source = growth['mu_source']
                        annot_text = f" μ={mu_source:.1f}"

                        growth_style = resolve_line_style(
                            app_state,
                            'growth_curve',
                            {
                                'color': None,
                                'linewidth': getattr(app_state, 'model_curve_width', 1.2),
                                'linestyle': ':',
                                'alpha': 0.6
                            }
                        )
                        line_artists = ax.plot(
                            x_growth,
                            y_growth,
                            linestyle=growth_style['linestyle'],
                            color=growth_style['color'] or color,
                            alpha=growth_style['alpha'],
                            linewidth=growth_style['linewidth'],
                            zorder=1.5
                        )
                        for artist in line_artists:
                            _register_overlay_artist('growth_curve', artist)

                        label_opts = _resolve_label_options(
                            'growth_curve',
                            {
                                'label_text': '',
                                'label_fontsize': 8,
                                'label_background': False,
                                'label_bg_color': '#ffffff',
                                'label_bg_alpha': 0.85,
                                'label_position': 'auto',
                            }
                        )
                        label_text = _format_label_text(label_opts.get('label_text'))
                        if not label_text:
                            label_text = annot_text
                        if label_text:
                            text_artist = ax.text(
                                x_growth[0], y_growth[0],
                                label_text,
                                fontsize=label_opts['label_fontsize'],
                                color=color,
                                va='bottom',
                                ha='right',
                                alpha=0.8,
                                bbox=_label_bbox(label_opts, edgecolor=color)
                            )
                            _register_overlay_curve_label(
                                text_artist,
                                x_growth,
                                y_growth,
                                label_text,
                                label_opts.get('label_position', 'auto'),
                                style_key='growth_curve'
                            )
                            position_curve_label(
                                ax,
                                text_artist,
                                mode='isoage',
                                x_line=x_growth,
                                y_line=y_growth,
                                label_text=label_text,
                                position_mode=label_opts.get('label_position', 'auto'),
                            )

            elif mode == 'ISOCHRON2' and geochemistry:
                # PB_EVOL_86: 208/204 vs 206/204 等时线
                # 年龄需要 207/206 斜率，尝试从同组 207 数据获取
                age_ma = None
                slope_207 = None
                intercept_207 = None

                if need_207_for_86:
                    try:
                        # 用同组数据拟合 207/206 等时线以获取年龄
                        if grp == 'All Data':
                            y207_grp = pd.to_numeric(df_subset[col_207], errors='coerce').values
                        else:
                         y207_grp = pd.to_numeric(df_subset.loc[df_subset.index[mask], col_207], errors='coerce').values
                        y207_grp = y207_grp[valid]
                        if len(y207_grp) >= 2:
                            fit_207 = geochemistry.york_regression(x_grp, sx_grp, y207_grp, sy_grp, rxy_grp)
                            slope_207 = fit_207['b']
                            intercept_207 = fit_207['a']
                            age_ma, _ = geochemistry.calculate_pbpb_age_from_ratio(slope_207, fit_207['sb'], params)
                            if age_ma is not None and age_ma >= 0:
                                app_state.isochron_results[grp]['age_ma'] = age_ma
                    except Exception as age_err:
                        logger.warning("Failed to calculate 86 isochron age for group %s: %s", grp, age_err)

                label_opts = _resolve_label_options(
                    'isochron',
                    {
                        'label_text': '',
                        'label_fontsize': 9,
                        'label_background': False,
                        'label_bg_color': '#ffffff',
                        'label_bg_alpha': 0.85,
                        'label_position': 'auto',
                    }
                )
                label_text = _build_isochron_label(app_state.isochron_results[grp])
                age_val = app_state.isochron_results[grp].get('age')
                if age_val is None:
                    age_val = app_state.isochron_results[grp].get('age_ma')
                label_override = _format_label_text(label_opts.get('label_text'), age_val)
                if label_override:
                    label_text = label_override

                if show_fits and label_text:
                    text_artist = ax.text(
                        x_line[0],
                        y_line[0],
                        f" {label_text}",
                        color=color,
                        fontsize=label_opts['label_fontsize'],
                        va='center',
                        ha='center',
                        fontweight='bold',
                        bbox=_label_bbox(label_opts, edgecolor=color)
                    )
                    _register_overlay_curve_label(
                        text_artist,
                        x_line,
                        y_line,
                        f" {label_text}",
                        label_opts.get('label_position', 'auto'),
                        style_key='isochron'
                    )
                    position_curve_label(
                        ax,
                        text_artist,
                        mode='isoage',
                        x_line=x_line,
                        y_line=y_line,
                        label_text=f" {label_text}",
                        position_mode=label_opts.get('label_position', 'auto'),
                    )

                # 生长曲线 (需要 207/206 斜率 + 208/206 斜率)
                if show_growth and age_ma is not None and age_ma > 0 and slope_207 is not None:
                    growth = geochemistry.calculate_isochron2_growth_curve(
                        slope,
                        slope_207,
                        intercept_207,
                        age_ma,
                        params=params,
                        steps=100
                    )
                    if growth:
                        x_growth = growth['x']
                        y_growth = growth['y']
                        kappa_source = growth.get('kappa_source')
                        annot_text = f" κ={kappa_source:.2f}" if kappa_source else ""

                        growth_style = resolve_line_style(
                            app_state,
                            'growth_curve',
                            {
                                'color': None,
                                'linewidth': getattr(app_state, 'model_curve_width', 1.2),
                                'linestyle': ':',
                                'alpha': 0.6
                            }
                        )
                        line_artists = ax.plot(
                            x_growth,
                            y_growth,
                            linestyle=growth_style['linestyle'],
                            color=growth_style['color'] or color,
                            alpha=growth_style['alpha'],
                            linewidth=growth_style['linewidth'],
                            zorder=1.5
                        )
                        for artist in line_artists:
                            _register_overlay_artist('growth_curve', artist)

                        label_opts = _resolve_label_options(
                            'growth_curve',
                            {
                                'label_text': '',
                                'label_fontsize': 8,
                                'label_background': False,
                                'label_bg_color': '#ffffff',
                                'label_bg_alpha': 0.85,
                                'label_position': 'auto',
                            }
                        )
                        label_text = _format_label_text(label_opts.get('label_text'))
                        if not label_text:
                            label_text = annot_text
                        if label_text:
                            text_artist = ax.text(
                                x_growth[0], y_growth[0],
                                label_text,
                                fontsize=label_opts['label_fontsize'],
                                color=color,
                                va='bottom',
                                ha='right',
                                alpha=0.8,
                                bbox=_label_bbox(label_opts, edgecolor=color)
                            )
                            _register_overlay_curve_label(
                                text_artist,
                                x_growth,
                                y_growth,
                                label_text,
                                label_opts.get('label_position', 'auto'),
                                style_key='growth_curve'
                            )
                            position_curve_label(
                                ax,
                                text_artist,
                                mode='isoage',
                                x_line=x_growth,
                                y_line=y_growth,
                                label_text=label_text,
                                position_mode=label_opts.get('label_position', 'auto'),
                            )

    except Exception as err:
        logger.warning("Failed to draw isochron overlays: %s", err)


