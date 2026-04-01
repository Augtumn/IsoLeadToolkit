"""Geochemistry overlays and isochron helpers."""
import ast
import logging
import operator

import numpy as np
import pandas as pd

from core import app_state, state_gateway
from visualization.line_styles import resolve_line_style, ensure_line_style
from .label_layout import position_curve_label, apply_adjust_text_to_labels
from .data import _get_analysis_data, _lazy_import_geochemistry
from .core import _get_subset_dataframe, _get_pb_columns
from .isochron import resolve_isochron_errors as _resolve_isochron_errors

logger = logging.getLogger(__name__)

from .geochem.overlay_helpers import (
    _draw_model_curves,
    _draw_mu_kappa_paleoisochrons,
    _draw_plumbotectonics_curves,
    _draw_plumbotectonics_isoage_lines,
    _format_label_text,
    _is_overlay_label_style_visible,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
    get_overlay_default_color,
    get_plumbotectonics_group_entries,
    get_plumbotectonics_group_palette,
    get_plumbotectonics_variants,
)


def _build_isochron_label(result_dict):
    """根据 isochron_label_options 动态构建等时线标注文本。"""
    opts = getattr(app_state, 'isochron_label_options', {})
    parts = []
    age = result_dict.get('age')
    if age is None:
        age = result_dict.get('age_ma')
    if opts.get('show_age', True) and age is not None and age >= 0:
        parts.append(f"{age:.0f} Ma")
    if opts.get('show_n_points', True) and result_dict.get('n_points'):
        parts.append(f"n={result_dict['n_points']}")
    if opts.get('show_mswd', False) and result_dict.get('mswd') is not None:
        parts.append(f"MSWD={result_dict['mswd']:.2f}")
    if opts.get('show_r_squared', False) and result_dict.get('r_squared') is not None:
        parts.append(f"R²={result_dict['r_squared']:.3f}")
    if opts.get('show_slope', False) and result_dict.get('slope') is not None:
        parts.append(f"m={result_dict['slope']:.4f}")
    if opts.get('show_intercept', False) and result_dict.get('intercept') is not None:
        parts.append(f"b={result_dict['intercept']:.4f}")
    return ", ".join(parts) if parts else ""

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

def _draw_selected_isochron(ax):
    """Draw isochron line for box-selected data points."""
    try:
        # Check if we have selected isochron data
        if app_state.selected_isochron_data is None:
            return

        data = app_state.selected_isochron_data
        x_range = data['x_range']
        y_range = data['y_range']

        # 统一使用 isochron 样式
        from visualization.line_styles import resolve_line_style
        fallback_style = {
            'color': '#ef4444',
            'linewidth': 2.0,
            'linestyle': '-',
            'alpha': 0.9
        }
        line_style = resolve_line_style(app_state, 'selected_isochron', fallback_style)
        # 选中等时线用稍粗的线
        draw_width = line_style['linewidth'] * 1.3

        line_artists = ax.plot(
            x_range,
            y_range,
            color=line_style['color'] or '#ef4444',
            linewidth=draw_width,
            linestyle=line_style['linestyle'],
            alpha=line_style['alpha'],
            zorder=100,
            label='_nolegend_'
        )
        for artist in line_artists:
            _register_overlay_artist('selected_isochron', artist)

        label_opts = _resolve_label_options(
            'isochron',
            {
                'label_text': '',
                'label_fontsize': 10,
                'label_background': True,
                'label_bg_color': '#ffffff',
                'label_bg_alpha': 0.9,
                'label_position': 'auto',
            }
        )
        label_text = _build_isochron_label(data)
        age_val = data.get('age')
        if age_val is None:
            age_val = data.get('age_ma')
        label_override = _format_label_text(label_opts.get('label_text'), age_val)
        if label_override:
            label_text = label_override
        if label_text:
            x_mid = (x_range[0] + x_range[1]) / 2
            y_mid = (y_range[0] + y_range[1]) / 2
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            y_offset = (ylim[1] - ylim[0]) * 0.02

            ax.text(
                x_mid,
                y_mid + y_offset,
                label_text,
                color=line_style['color'] or '#ef4444',
                fontsize=label_opts['label_fontsize'],
                fontweight='bold',
                ha='center',
                va='bottom',
                bbox=_label_bbox(label_opts, edgecolor=line_style['color'] or '#ef4444')
                or dict(
                    boxstyle='round,pad=0.4',
                    facecolor='white',
                    edgecolor=line_style['color'] or '#ef4444',
                    alpha=0.9,
                    linewidth=1.5
                ),
                zorder=101
            )

    except Exception as err:
        logger.warning("Failed to draw selected isochron: %s", err)

def _draw_paleoisochrons(ax, actual_algorithm, ages, params):
    """Draw paleoisochron reference lines for given ages."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        state_gateway.set_attr('paleoisochron_label_data', [])
        xlim = ax.get_xlim()
        x_min = xlim[0]
        x_max = xlim[1]
        x_vals = np.linspace(x_min, x_max, 200)

        for age in ages:
            params_line = geochemistry.calculate_paleoisochron_line(
                age,
                params=params,
                algorithm=actual_algorithm
            )
            if not params_line:
                logger.debug("Paleoisochron returned None for age=%s Ma, algorithm=%s", age, actual_algorithm)
                continue
            slope, intercept = params_line

            y_vals = slope * x_vals + intercept
            paleo_style = resolve_line_style(
                app_state,
                'paleoisochron',
                {
                    'color': None,
                    'linewidth': getattr(app_state, 'paleoisochron_width', 0.9),
                    'linestyle': '--',
                    'alpha': 0.85
                }
            )
            line_color = paleo_style.get('color') or get_overlay_default_color('paleoisochron')
            label_opts = _resolve_label_options(
                'paleoisochron',
                {
                    'label_text': '',
                    'label_fontsize': 8,
                    'label_background': False,
                    'label_bg_color': '#ffffff',
                    'label_bg_alpha': 0.85,
                    'label_position': 'auto',
                }
            )
            line_kwargs = {
                'linestyle': paleo_style['linestyle'],
                'linewidth': paleo_style['linewidth'],
                'alpha': paleo_style['alpha'],
                'zorder': 3,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot(x_vals, y_vals, **line_kwargs)
            for artist in line_artists:
                _register_overlay_artist('paleoisochron', artist)
            if len(x_vals) > 0:
                label_text = _format_label_text(label_opts.get('label_text'), age)
                if not label_text:
                    label_text = f" {age:.0f} Ma"
                text_artist = ax.text(
                    x_vals[-1], y_vals[-1],
                    label_text,
                    color=line_color or paleo_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='left',
                    alpha=paleo_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=line_color)
                )
                app_state.paleoisochron_label_data.append({
                    'text': text_artist,
                    'slope': slope,
                    'intercept': intercept,
                    'age': age,
                    'label_text': label_text,
                    'position': label_opts.get('label_position', 'auto'),
                    'style_key': 'paleoisochron',
                })
                position_curve_label(
                    ax,
                    text_artist,
                    mode='paleo',
                    slope=slope,
                    intercept=intercept,
                    age=age,
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto'),
                )
    except Exception as err:
        logger.warning("Failed to draw paleoisochrons: %s", err)

def refresh_paleoisochron_labels():
    """Refresh paleoisochron label positions after zoom/pan."""
    ax = getattr(app_state, 'ax', None)
    if ax is None:
        return
    if bool(getattr(app_state, 'overlay_label_refreshing', False)):
        return

    state_gateway.set_attr('overlay_label_refreshing', True)
    try:
        adjusted_labels = []

        label_data = getattr(app_state, 'paleoisochron_label_data', [])
        if not label_data:
            label_data = []

        for entry in label_data:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            style_key = entry.get('style_key') or 'paleoisochron'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception:
                    pass
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='paleo',
                slope=entry.get('slope', 0),
                intercept=entry.get('intercept', 0),
                age=entry.get('age'),
                label_text=entry.get('label_text'),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception:
                pass

        curve_labels = getattr(app_state, 'plumbotectonics_label_data', [])
        for entry in curve_labels:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            style_key = entry.get('style_key') or 'plumbotectonics_curve'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception:
                    pass
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='curve_left',
                x_vals=entry.get('x_vals', entry.get('x_line', [])),
                y_vals=entry.get('y_vals', entry.get('y_line', [])),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception:
                pass

        isoage_labels = getattr(app_state, 'plumbotectonics_isoage_label_data', [])
        for entry in isoage_labels:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            style_key = entry.get('style_key') or 'paleoisochron'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception:
                    pass
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=entry.get('x_line', []),
                y_line=entry.get('y_line', []),
                age_ma=entry.get('age'),
                label_text=entry.get('label_text'),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception:
                pass

        curve_labels = getattr(app_state, 'overlay_curve_label_data', [])
        for entry in curve_labels:
            text_artist = entry.get('text')
            if text_artist is None:
                continue
            style_key = entry.get('style_key') or 'model_curve'
            if not _is_overlay_label_style_visible(style_key):
                try:
                    text_artist.set_visible(False)
                except Exception:
                    pass
                continue
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=entry.get('x_line', []),
                y_line=entry.get('y_line', []),
                label_text=entry.get('label_text'),
                position_mode=entry.get('position', 'auto'),
            )
            try:
                if text_artist.get_visible():
                    adjusted_labels.append(text_artist)
            except Exception:
                pass

        apply_adjust_text_to_labels(ax, adjusted_labels)
    finally:
        state_gateway.set_attr('overlay_label_refreshing', False)

def _resolve_model_age(pb206, pb207, params):
    """Resolve model age and T1 override from Pb data and model params.

    Returns:
        tuple: (t_model, t1_override) where t_model is age array (Ma)
               and t1_override is T1 in years for calculate_modelcurve.
    """
    geochemistry, _ = _lazy_import_geochemistry()
    t_sk = geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
    t_cdt = geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
    if params.get('Tsec', 0.0) <= 0:
        t_model = t_cdt
        t1_override = params.get('T2', params.get('T1', None))
    else:
        t_model = np.where(np.isfinite(t_sk), t_sk, t_cdt)
        t1_override = params.get('Tsec', None)
    return t_model, t1_override


def _draw_model_age_lines(ax, pb206, pb207, params):
    """Draw model age construction lines for 206/204 vs 207/204."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        t_model, t1_override = _resolve_model_age(pb206, pb207, params)

        curve = geochemistry.calculate_modelcurve(t_model, params=params, T1=t1_override / 1e6 if t1_override else None)
        x_curve = np.asarray(curve['Pb206_204'])
        y_curve = np.asarray(curve['Pb207_204'])

        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            rng = np.random.RandomState(42)
            idxs = rng.choice(idxs, size=max_lines, replace=False)

        age_style = resolve_line_style(
            app_state,
            'model_age_line',
            {
                'color': None,
                'linewidth': getattr(app_state, 'model_age_line_width', 0.7),
                'linestyle': '-',
                'alpha': 0.7
            }
        )
        line_color = age_style.get('color') or get_overlay_default_color('model_age_line')
        label_opts = _resolve_label_options(
            'model_age_line',
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
        label_done = False
        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb207[i]) or np.isnan(x_curve[i]) or np.isnan(y_curve[i]):
                continue
            line_kwargs = {
                'linewidth': age_style['linewidth'],
                'linestyle': age_style['linestyle'],
                'alpha': age_style['alpha'],
                'zorder': 1,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot([x_curve[i], pb206[i]], [y_curve[i], pb207[i]], **line_kwargs)
            for artist in line_artists:
                _register_overlay_artist('model_age_line', artist)
            point_artist = ax.scatter(
                x_curve[i],
                y_curve[i],
                s=10,
                color='#475569',
                alpha=0.6,
                zorder=2,
                label='_nolegend_'
            )
            _register_overlay_artist('model_age_line', point_artist)
            if label_text and not label_done:
                text_artist = ax.text(
                    x_curve[i], y_curve[i],
                    label_text,
                    color=line_color or age_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=age_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=line_color)
                )
                _register_overlay_curve_label(
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [y_curve[i], pb207[i]],
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_age_line'
                )
                position_curve_label(
                    ax,
                    text_artist,
                    mode='isoage',
                    x_line=[x_curve[i], pb206[i]],
                    y_line=[y_curve[i], pb207[i]],
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto'),
                )
                label_done = True
    except Exception as err:
        logger.warning("Failed to draw model age lines: %s", err)

def _draw_model_age_lines_86(ax, pb206, pb207, pb208, params):
    """Draw model age construion lines for 206/204 vs 208/204."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        t_model, t1_override = _resolve_model_age(pb206, pb207, params)

        curve = geochemistry.calculate_modelcurve(t_model, params=params, T1=t1_override / 1e6 if t1_override else None)
        x_curve = np.asarray(curve['Pb206_204'])
        z_curve = np.asarray(curve['Pb208_204'])

        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            rng = np.random.RandomState(42)
            idxs = rng.choice(idxs, size=max_lines, replace=False)

        age_style = resolve_line_style(
            app_state,
            'model_age_line',
            {
                'color': None,
                'linewidth': getattr(app_state, 'model_age_line_width', 0.7),
                'linestyle': '-',
                'alpha': 0.7
            }
        )
        line_color = age_style.get('color') or get_overlay_default_color('model_age_line')
        label_opts = _resolve_label_options(
            'model_age_line',
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
        label_done = False
        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb208[i]) or np.isnan(x_curve[i]) or np.isnan(z_curve[i]):
                continue
            line_kwargs = {
                'linewidth': age_style['linewidth'],
                'linestyle': age_style['linestyle'],
                'alpha': age_style['alpha'],
                'zorder': 1,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot([x_curve[i], pb206[i]], [z_curve[i], pb208[i]], **line_kwargs)
            for artist in line_artists:
                _register_overlay_artist('model_age_line', artist)
            point_artist = ax.scatter(
                x_curve[i],
                z_curve[i],
                s=10,
                color='#475569',
                alpha=0.6,
                zorder=2,
                label='_nolegend_'
            )
            _register_overlay_artist('model_age_line', point_artist)
            if label_text and not label_done:
                text_artist = ax.text(
                    x_curve[i], z_curve[i],
                    label_text,
                    color=line_color or age_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=age_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=line_color)
                )
                _register_overlay_curve_label(
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [z_curve[i], pb208[i]],
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_age_line'
                )
                position_curve_label(
                    ax,
                    text_artist,
                    mode='isoage',
                    x_line=[x_curve[i], pb206[i]],
                    y_line=[z_curve[i], pb208[i]],
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto'),
                )
                label_done = True
    except Exception as err:
        logger.warning("Failed to draw model age lines (206-208): %s", err)

def _safe_eval_expression(expression, x_vals):
    """Safely evaluate a mathematical expression over *x_vals*.

    Uses AST parsing to restrict allowed operations to arithmetic,
    comparisons, and a whitelist of numpy functions. No arbitrary
    code execution is possible.
    """
    _ALLOWED_NUMPY = {
        'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'arctan2',
        'exp', 'log', 'log2', 'log10', 'sqrt', 'abs', 'power', 'pi', 'e',
        'maximum', 'minimum', 'clip', 'where', 'sign', 'floor', 'ceil',
    }

    _BINOP_MAP = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    _UNARYOP_MAP = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")
            return node.value
        if isinstance(node, ast.Name):
            if node.id == 'x':
                return x_vals
            if node.id == 'pi':
                return np.pi
            if node.id == 'e':
                return np.e
            raise ValueError(f"Unknown variable: {node.id}")
        if isinstance(node, ast.BinOp):
            op_fn = _BINOP_MAP.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_fn(_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp):
            op_fn = _UNARYOP_MAP.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op_fn(_eval_node(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                raise ValueError("Only direct function calls are allowed")
            if isinstance(node.func, ast.Attribute):
                if not (isinstance(node.func.value, ast.Name) and node.func.value.id == 'np'):
                    raise ValueError(f"Only np.* calls are allowed")
                func_name = node.func.attr
            else:
                func_name = node.func.id
            if func_name not in _ALLOWED_NUMPY:
                raise ValueError(f"Function not allowed: {func_name}")
            np_func = getattr(np, func_name)
            args = [_eval_node(a) for a in node.args]
            return np_func(*args)
        if isinstance(node, ast.IfExp):
            test = _eval_node(node.test)
            body = _eval_node(node.body)
            orelse = _eval_node(node.orelse)
            return np.where(test, body, orelse)
        if isinstance(node, ast.Compare):
            left = _eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval_node(comparator)
                if isinstance(op, ast.Lt):
                    left = left < right
                elif isinstance(op, ast.LtE):
                    left = left <= right
                elif isinstance(op, ast.Gt):
                    left = left > right
                elif isinstance(op, ast.GtE):
                    left = left >= right
                else:
                    raise ValueError(f"Unsupported comparison: {type(op).__name__}")
            return left
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    tree = ast.parse(expression, mode='eval')
    return _eval_node(tree)


def _draw_equation_overlays(ax):
    """Draw configured equation overlays on the current axes."""
    if not getattr(app_state, 'show_equation_overlays', False):
        return

    overlays = getattr(app_state, 'equation_overlays', []) or []
    if not overlays:
        return

    x_min, x_max = ax.get_xlim()
    x_vals = np.linspace(x_min, x_max, 200)

    for overlay in overlays:
        if not overlay.get('enabled', True):
            continue

        expression = overlay.get('expression')
        slope = overlay.get('slope')
        intercept = overlay.get('intercept', 0.0)
        y_vals = None

        if expression:
            try:
                y_vals = _safe_eval_expression(expression, x_vals)
            except Exception as err:
                logger.warning("Failed to evaluate equation '%s': %s", expression, err)
                continue
        elif slope is not None:
            y_vals = slope * x_vals + intercept

        if y_vals is None:
            continue

        style_key = overlay.get('style_key')
        if not style_key:
            overlay_id = overlay.get('id') or overlay.get('expression') or overlay.get('label') or 'equation'
            style_key = f"equation:{overlay_id}"
            overlay['style_key'] = style_key

        existing_style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
        fallback_color = None if existing_style.get('color', '__missing__') in (None, '') else overlay.get('color', '#ef4444')
        style = ensure_line_style(
            app_state,
            style_key,
            {
                'color': fallback_color,
                'linewidth': overlay.get('linewidth', 1.0),
                'linestyle': overlay.get('linestyle', '--'),
                'alpha': overlay.get('alpha', 0.85),
            }
        )

        line_color = style.get('color') or overlay.get('color', '#ef4444')
        line_artists = ax.plot(
            x_vals,
            y_vals,
            color=line_color,
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
            zorder=1,
            label='_nolegend_'
        )
        for artist in line_artists:
            _register_overlay_artist(style_key, artist)

        label_opts = _resolve_label_options(
            style_key,
            {
                'label_text': '',
                'label_fontsize': 8,
                'label_background': False,
                'label_bg_color': '#ffffff',
                'label_bg_alpha': 0.85,
                'label_position': 'auto',
            }
        )
        label_text = _format_label_text(label_opts.get('label_text'), label=overlay.get('label'))
        if label_text:
            text_artist = ax.text(
                x_vals[0],
                y_vals[0],
                label_text,
                color=line_color,
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='center',
                alpha=style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=line_color)
            )
            _register_overlay_curve_label(
                text_artist,
                x_vals,
                y_vals,
                label_text,
                label_opts.get('label_position', 'auto'),
                style_key=style_key
            )
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=x_vals,
                y_line=y_vals,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto'),
            )


