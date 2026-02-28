"""Geochemistry overlays and isochron helpers."""
import ast
import logging
import operator

import numpy as np
import pandas as pd

from core import app_state
from data.plumbotectonics_data import PLUMBOTECTONICS_SECTIONS
from visualization.line_styles import resolve_line_style, ensure_line_style
from .data import _get_analysis_data, _lazy_import_geochemistry
from .core import _get_subset_dataframe, _get_pb_columns
from .isochron import resolve_isochron_errors as _resolve_isochron_errors

logger = logging.getLogger(__name__)

# Minimum absolute slope to avoid division by zero in label positioning
_SLOPE_EPSILON = 1e-10


def _register_overlay_artist(style_key, artist):
    if artist is None:
        return
    if not hasattr(app_state, 'overlay_artists'):
        app_state.overlay_artists = {}
    app_state.overlay_artists.setdefault(style_key, []).append(artist)


def _resolve_label_options(style_key, fallback):
    style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
    resolved = dict(fallback)
    for key in resolved:
        if key not in style:
            continue
        value = style[key]
        if value is None:
            continue
        if isinstance(value, str) and value.strip() == '':
            continue
        resolved[key] = value
    return resolved


def _format_label_text(template, age=None, **kwargs):
    if not template:
        return None
    fmt_kwargs = dict(kwargs)
    if age is not None:
        fmt_kwargs['age'] = age
    try:
        return template.format(**fmt_kwargs)
    except Exception:
        return template


def _label_bbox(label_opts, edgecolor=None):
    if not label_opts.get('label_background', False):
        return None
    facecolor = label_opts.get('label_bg_color', '#ffffff')
    alpha = float(label_opts.get('label_bg_alpha', 0.85))
    return dict(
        boxstyle='round,pad=0.25',
        facecolor=facecolor,
        edgecolor=edgecolor or 'none',
        alpha=alpha
    )


def _register_overlay_curve_label(
    text_artist,
    x_vals,
    y_vals,
    label_text,
    position_mode,
    style_key=None
):
    if text_artist is None:
        return
    if not hasattr(app_state, 'overlay_curve_label_data'):
        app_state.overlay_curve_label_data = []
    app_state.overlay_curve_label_data.append({
        'text': text_artist,
        'x_line': list(x_vals),
        'y_line': list(y_vals),
        'label_text': label_text,
        'position': position_mode or 'auto',
        'style_key': style_key,
    })


def _draw_model_curves(ax, actual_algorithm, params_list):
    """Draw model curves for Pb evolution plots."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return

    if not params_list:
        params_list = [geochemistry.engine.get_parameters()]

    for params in params_list:
        try:
            tsec = float(params.get('Tsec', 0.0))
            if tsec > 0:
                t_max = tsec / 1e6
                t1_override = tsec
            else:
                t_max = float(params.get('T2', params.get('T1', 0.0))) / 1e6
                t1_override = params.get('T2', params.get('T1', None))
            t_vals = np.linspace(0, max(t_max, 1.0), 300)
            curve = geochemistry.calculate_modelcurve(
                t_vals,
                params=params,
                T1=t1_override / 1e6 if t1_override else None
            )
            x_vals = np.asarray(curve['Pb206_204'])
            if actual_algorithm == 'PB_EVOL_76':
                y_vals = np.asarray(curve['Pb207_204'])
            else:
                y_vals = np.asarray(curve['Pb208_204'])

            style = resolve_line_style(
                app_state,
                'model_curve',
                {
                    'color': '#94a3b8',
                    'linewidth': getattr(app_state, 'model_curve_width', 1.2),
                    'linestyle': '-',
                    'alpha': 0.8
                }
            )
            label_opts = _resolve_label_options(
                'model_curve',
                {
                    'label_text': '',
                    'label_fontsize': 9,
                    'label_background': False,
                    'label_bg_color': '#ffffff',
                    'label_bg_alpha': 0.85,
                    'label_position': 'auto',
                }
            )
            line_artists = ax.plot(
                x_vals,
                y_vals,
                color=style['color'],
                linewidth=style['linewidth'],
                linestyle=style['linestyle'],
                alpha=style['alpha'],
                zorder=1,
                label='_nolegend_'
            )
            for artist in line_artists:
                _register_overlay_artist('model_curve', artist)

            label_text = _format_label_text(
                label_opts.get('label_text'),
                index=len(getattr(app_state, 'overlay_curve_label_data', [])) + 1
            )
            if label_text:
                text_artist = ax.text(
                    x_vals[0], y_vals[0],
                    label_text,
                    color=style['color'],
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=style['color'])
                )
                _register_overlay_curve_label(
                    text_artist,
                    x_vals,
                    y_vals,
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_curve'
                )
                _position_isoage_label_on_line(
                    ax,
                    text_artist,
                    x_vals,
                    y_vals,
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto')
                )
        except Exception as err:
            logger.warning("Failed to draw model curve: %s", err)


def _load_plumbotectonics_data():
    return PLUMBOTECTONICS_SECTIONS


def _plumbotectonics_section_name(section, index):
    label = (section.get('label') or '').strip()
    if label:
        return label
    return f"Model {index + 1}"


def get_plumbotectonics_variants():
    """Return available plumbotectonics model variants."""
    sections = _load_plumbotectonics_data()
    if not sections:
        return []
    variants = []
    for idx, section in enumerate(sections):
        variants.append((str(idx), _plumbotectonics_section_name(section, idx)))
    return variants


def _select_plumbotectonics_section(sections):
    if not sections:
        return None
    variant = getattr(app_state, 'plumbotectonics_variant', None)
    try:
        idx = int(variant)
    except Exception:
        idx = None
    if idx is not None and 0 <= idx < len(sections):
        return sections[idx]
    return sections[0]


def _fit_plumbotectonics_curve(x_vals, y_vals, n_points=200):
    x_arr = np.asarray(x_vals, dtype=float)
    y_arr = np.asarray(y_vals, dtype=float)
    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[valid]
    y_arr = y_arr[valid]
    if x_arr.size < 2:
        return x_arr, y_arr

    order = np.argsort(x_arr)
    x_sorted = x_arr[order]
    y_sorted = y_arr[order]

    unique_x, inv = np.unique(x_sorted, return_inverse=True)
    if unique_x.size < 2:
        return unique_x, y_sorted[:unique_x.size]
    y_accum = np.zeros_like(unique_x, dtype=float)
    counts = np.zeros_like(unique_x, dtype=float)
    for idx, group_idx in enumerate(inv):
        y_accum[group_idx] += y_sorted[idx]
        counts[group_idx] += 1
    y_unique = np.divide(y_accum, counts, out=np.zeros_like(y_accum), where=counts > 0)

    x_min = float(unique_x.min())
    x_max = float(unique_x.max())
    if not np.isfinite(x_min) or not np.isfinite(x_max) or x_min == x_max:
        return unique_x, y_unique

    x_fit = np.linspace(x_min, x_max, int(n_points))
    try:
        from scipy.interpolate import PchipInterpolator
        y_fit = PchipInterpolator(unique_x, y_unique)(x_fit)
    except Exception:
        y_fit = np.interp(x_fit, unique_x, y_unique)
    return x_fit, y_fit


def _plumbotectonics_color(name):
    key = str(name).lower()
    if 'mantle' in key or '地幔' in key:
        return '#0ea5e9'
    if 'upper' in key or '上地壳' in key:
        return '#f97316'
    if 'lower' in key or '下地壳' in key:
        return '#22c55e'
    if 'orogene' in key or 'orogen' in key:
        return '#a855f7'
    return '#64748b'

def _plumbotectonics_marker(name):
    key = str(name).lower()
    if 'mantle' in key or '地幔' in key:
        return 'o'
    if 'lower' in key or '下地壳' in key:
        return 's'
    if 'upper' in key or '上地壳' in key:
        return '^'
    if 'orogene' in key or 'orogen' in key:
        return 'D'
    return 'o'


def _draw_plumbotectonics_curves(ax, actual_algorithm):
    """Draw Plumbotectonics model curves using fitted data points."""
    sections = _load_plumbotectonics_data()
    section = _select_plumbotectonics_section(sections)
    if not section:
        return

    y_key = 'pb207' if str(actual_algorithm).endswith('_76') else 'pb208'

    base_style = resolve_line_style(
        app_state,
        'plumbotectonics_curve',
        {
            'color': None,
            'linewidth': getattr(app_state, 'plumbotectonics_curve_width', 1.2),
            'linestyle': '-',
            'alpha': 0.85
        }
    )
    label_opts = _resolve_label_options(
        'plumbotectonics_curve',
        {
            'label_text': '',
            'label_fontsize': 9,
            'label_background': False,
            'label_bg_color': '#ffffff',
            'label_bg_alpha': 0.85,
            'label_position': 'auto',
        }
    )

    variant_label = section.get('label')
    if variant_label:
        logger.info("Plumbotectonics model variant: %s", variant_label)

    for group in section.get('groups', []):
        name = str(group.get('name', ''))
        x_vals = group.get('pb206', [])
        y_vals = group.get(y_key, [])
        x_fit, y_fit = _fit_plumbotectonics_curve(x_vals, y_vals)
        if len(x_fit) < 2:
            continue
        color = base_style['color'] or _plumbotectonics_color(name)
        marker = _plumbotectonics_marker(name)
        line_artists = ax.plot(
            x_fit,
            y_fit,
            color=color,
            linewidth=base_style['linewidth'],
            linestyle=base_style['linestyle'],
            alpha=base_style['alpha'],
            zorder=1.2,
            label='_nolegend_'
        )
        for artist in line_artists:
            _register_overlay_artist('plumbotectonics_curve', artist)
        point_artists = ax.plot(
            x_vals,
            y_vals,
            linestyle='None',
            marker=marker,
            markersize=4.5,
            color=color,
            alpha=min(base_style['alpha'] + 0.1, 1.0),
            zorder=1.3,
            label='_nolegend_'
        )
        for artist in point_artists:
            _register_overlay_artist('plumbotectonics_curve', artist)

        label_text = _format_label_text(label_opts.get('label_text'), name=name)
        if label_text:
            text_artist = ax.text(
                x_fit[0], y_fit[0],
                label_text,
                color=color,
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='center',
                alpha=base_style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=color)
            )
            _register_overlay_curve_label(
                text_artist,
                x_fit,
                y_fit,
                label_text,
                label_opts.get('label_position', 'auto'),
                style_key='plumbotectonics_curve'
            )
            _position_isoage_label_on_line(
                ax,
                text_artist,
                x_fit,
                y_fit,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto')
            )


def _draw_plumbotectonics_isoage_lines(ax, actual_algorithm):
    """Draw same-age connection lines (paleoisochrons) for Plumbotectonics."""
    sections = _load_plumbotectonics_data()
    section = _select_plumbotectonics_section(sections)
    if not section:
        return

    y_key = 'pb207' if str(actual_algorithm).endswith('_76') else 'pb208'
    groups = [g for g in section.get('groups', []) if g.get('pb206') and g.get(y_key)]
    if not groups:
        return

    lengths = []
    for g in groups:
        lengths.append(len(g.get('t', [])))
        lengths.append(len(g.get('pb206', [])))
        lengths.append(len(g.get(y_key, [])))
    n_points = min(lengths) if lengths else 0
    if n_points < 2:
        return

    paleo_style = resolve_line_style(
        app_state,
        'paleoisochron',
        {
            'color': '#94a3b8',
            'linewidth': getattr(app_state, 'paleoisochron_width', 0.9),
            'linestyle': '--',
            'alpha': 0.85
        }
    )
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

    app_state.plumbotectonics_isoage_label_data = []

    for idx in range(n_points):
        pts = []
        t_val = None
        for g in groups:
            try:
                t_val = float(g.get('t', [])[idx])
                x_val = float(g.get('pb206', [])[idx])
                y_val = float(g.get(y_key, [])[idx])
            except (TypeError, ValueError, IndexError):
                continue
            if not (np.isfinite(t_val) and np.isfinite(x_val) and np.isfinite(y_val)):
                continue
            pts.append((x_val, y_val))

        if len(pts) < 2:
            continue

        pts.sort(key=lambda p: p[0])
        x_line = [p[0] for p in pts]
        y_line = [p[1] for p in pts]
        line_artists = ax.plot(
            x_line,
            y_line,
            linestyle=paleo_style['linestyle'],
            color=paleo_style['color'],
            linewidth=paleo_style['linewidth'],
            alpha=paleo_style['alpha'],
            zorder=1.05,
            label='_nolegend_'
        )
        for artist in line_artists:
            _register_overlay_artist('paleoisochron', artist)

        if t_val is not None and len(x_line) >= 2:
            label_text = _format_label_text(label_opts.get('label_text'), t_val * 1000.0)
            if not label_text:
                label_text = f" {t_val * 1000.0:.0f} Ma"
            text_artist = ax.text(
                x_line[0], y_line[0],
                label_text,
                color=paleo_style['color'],
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='left',
                alpha=paleo_style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=paleo_style['color'])
            )
            app_state.plumbotectonics_isoage_label_data.append({
                'text': text_artist,
                'x_line': x_line,
                'y_line': y_line,
                'age': t_val * 1000.0,
                'label_text': label_text,
                'position': label_opts.get('label_position', 'auto'),
                'style_key': 'paleoisochron',
            })
            _position_isoage_label_on_line(
                ax,
                text_artist,
                x_line,
                y_line,
                age_ma=t_val * 1000.0,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto')
            )

def _draw_mu_kappa_paleoisochrons(ax, ages):
    """Draw paleoisochron ages as vertical guides for Mu/Kappa plots."""
    if not ages:
        return
    try:
        paleo_style = resolve_line_style(
            app_state,
            'paleoisochron',
            {
                'color': '#94a3b8',
                'linewidth': getattr(app_state, 'paleoisochron_width', 0.9),
                'linestyle': '--',
                'alpha': 0.85
            }
        )
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
        # Place labels in axes coordinates so zoom/pan preserves their position.
        position_mode = label_opts.get('label_position', 'auto')
        if position_mode == 'start':
            label_y = 0.02
        elif position_mode == 'center':
            label_y = 0.5
        else:
            label_y = 0.98
        label_transform = ax.get_xaxis_transform()
        for age in ages:
            try:
                age_val = float(age)
            except (TypeError, ValueError):
                continue
            if not np.isfinite(age_val):
                continue
            line_artist = ax.axvline(
                age_val,
                color=paleo_style['color'],
                linewidth=paleo_style['linewidth'],
                linestyle=paleo_style['linestyle'],
                alpha=paleo_style['alpha'],
                zorder=2,
                clip_on=True,
            )
            _register_overlay_artist('paleoisochron', line_artist)
            ax.text(
                age_val,
                label_y,
                _format_label_text(label_opts.get('label_text'), age_val) or f" {age_val:.0f} Ma",
                color=paleo_style['color'],
                fontsize=label_opts['label_fontsize'],
                rotation=90,
                va='top',
                ha='right',
                alpha=paleo_style['alpha'],
                transform=label_transform,
                clip_on=True,
                bbox=_label_bbox(label_opts, edgecolor=paleo_style['color'])
            )
    except Exception as err:
        logger.warning("Failed to draw Mu/Kappa paleoisochrons: %s", err)

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

        df = app_state.df_global
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
                app_state.isochron_results = {}
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
                    xlim = ax.get_xlim()
                    ylim = ax.get_ylim()

                    position_mode = label_opts.get('label_position', 'auto')
                    if position_mode == 'start':
                        txt_x = x_min_g
                    elif position_mode == 'end':
                        txt_x = x_max_g
                    elif position_mode == 'center':
                        txt_x = (x_min_g + x_max_g) / 2
                    else:
                        txt_x = min(x_max_g, xlim[1] * 0.95)
                    txt_y = slope * txt_x + intercept

                    if txt_y < ylim[0] or txt_y > ylim[1]:
                        if txt_y > ylim[1]:
                            txt_y = ylim[1] * 0.95
                            txt_x = (txt_y - intercept) / slope if abs(slope) > _SLOPE_EPSILON else txt_x
                        else:
                            txt_y = ylim[0] + (ylim[1] - ylim[0]) * 0.05
                            txt_x = (txt_y - intercept) / slope if abs(slope) > _SLOPE_EPSILON else txt_x

                    ax.text(
                        txt_x,
                        txt_y,
                        f" {label_text}",
                        color=color,
                        fontsize=label_opts['label_fontsize'],
                        va='center',
                        ha='left',
                        fontweight='bold',
                        bbox=_label_bbox(label_opts, edgecolor=color)
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
                            _position_isoage_label_on_line(
                                ax,
                                text_artist,
                                x_growth,
                                y_growth,
                                label_text=label_text,
                                position_mode=label_opts.get('label_position', 'auto')
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
                    xlim = ax.get_xlim()
                    ylim = ax.get_ylim()

                    position_mode = label_opts.get('label_position', 'auto')
                    if position_mode == 'start':
                        txt_x = x_min_g
                    elif position_mode == 'end':
                        txt_x = x_max_g
                    elif position_mode == 'center':
                        txt_x = (x_min_g + x_max_g) / 2
                    else:
                        txt_x = min(x_max_g, xlim[1] * 0.95)
                    txt_y = slope * txt_x + intercept

                    if txt_y < ylim[0] or txt_y > ylim[1]:
                        if txt_y > ylim[1]:
                            txt_y = ylim[1] * 0.95
                            txt_x = (txt_y - intercept) / slope if abs(slope) > _SLOPE_EPSILON else txt_x
                        else:
                            txt_y = ylim[0] + (ylim[1] - ylim[0]) * 0.05
                            txt_x = (txt_y - intercept) / slope if abs(slope) > _SLOPE_EPSILON else txt_x

                    ax.text(
                        txt_x,
                        txt_y,
                        f" {label_text}",
                        color=color,
                        fontsize=label_opts['label_fontsize'],
                        va='center',
                        ha='left',
                        fontweight='bold',
                        bbox=_label_bbox(label_opts, edgecolor=color)
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
                            _position_isoage_label_on_line(
                                ax,
                                text_artist,
                                x_growth,
                                y_growth,
                                label_text=label_text,
                                position_mode=label_opts.get('label_position', 'auto')
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

def _label_angle_for_slope(ax, x0, y0, slope, dx):
    """Compute label angle (deg) for a line in display coords."""
    try:
        x1 = x0 + dx
        y1 = y0 + slope * dx
        p0 = ax.transData.transform((x0, y0))
        p1 = ax.transData.transform((x1, y1))
        angle = np.degrees(np.arctan2(p1[1] - p0[1], p1[0] - p0[0]))
        return angle
    except Exception:
        return np.degrees(np.arctan(slope))


def _collect_avoid_points_display(ax, exclude_artist=None, max_points=1200):
    """Collect points (in display coordinates) that labels should avoid."""
    points_data = []

    sample_coords = getattr(app_state, 'sample_coordinates', {}) or {}
    if isinstance(sample_coords, dict):
        points_data.extend(sample_coords.values())

    if not points_data:
        for sc in getattr(app_state, 'scatter_collections', []) or []:
            try:
                offsets = sc.get_offsets()
            except Exception:
                continue
            if offsets is None:
                continue
            try:
                for x_val, y_val in np.asarray(offsets, dtype=float):
                    points_data.append((float(x_val), float(y_val)))
            except Exception:
                continue

    label_entries = []
    label_entries.extend(getattr(app_state, 'overlay_curve_label_data', []) or [])
    label_entries.extend(getattr(app_state, 'paleoisochron_label_data', []) or [])
    label_entries.extend(getattr(app_state, 'plumbotectonics_label_data', []) or [])
    label_entries.extend(getattr(app_state, 'plumbotectonics_isoage_label_data', []) or [])
    for entry in label_entries:
        if not isinstance(entry, dict):
            continue
        text_artist = entry.get('text')
        if text_artist is None or text_artist is exclude_artist:
            continue
        try:
            x_val, y_val = text_artist.get_position()
            points_data.append((float(x_val), float(y_val)))
        except Exception:
            continue

    if not points_data:
        return np.empty((0, 2), dtype=float)

    points_arr = np.asarray(points_data, dtype=float)
    if points_arr.ndim != 2 or points_arr.shape[1] != 2:
        return np.empty((0, 2), dtype=float)

    finite = np.isfinite(points_arr[:, 0]) & np.isfinite(points_arr[:, 1])
    points_arr = points_arr[finite]
    if points_arr.size == 0:
        return np.empty((0, 2), dtype=float)

    if points_arr.shape[0] > max_points:
        idx = np.linspace(0, points_arr.shape[0] - 1, max_points, dtype=int)
        points_arr = points_arr[idx]

    try:
        return np.asarray(ax.transData.transform(points_arr), dtype=float)
    except Exception:
        return np.empty((0, 2), dtype=float)


def _estimate_label_radius_px(text_artist, default_fontsize=9.0):
    """Estimate a label clearance radius in display pixels."""
    try:
        fontsize = float(text_artist.get_fontsize())
    except Exception:
        fontsize = float(default_fontsize)
    if not np.isfinite(fontsize) or fontsize <= 0:
        fontsize = float(default_fontsize)

    try:
        text = str(text_artist.get_text() or '')
    except Exception:
        text = ''
    text_len = max(len(text.strip()), 3)

    approx_w = max(18.0, 0.58 * fontsize * text_len)
    approx_h = max(12.0, 1.35 * fontsize)
    return max(14.0, 0.5 * np.hypot(approx_w, approx_h))


def _position_paleo_label(ax, text_artist, slope, intercept, age=None, label_text=None, position_mode='auto'):
    """Position a paleoisochron label inside axes, aligned to line."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_span = xlim[1] - xlim[0]
    y_span = ylim[1] - ylim[0]
    if x_span == 0 or y_span == 0:
        return

    pad_x = x_span * 0.02
    pad_y = y_span * 0.02

    def _in_bounds(x_val, y_val):
        return (xlim[0] + pad_x) <= x_val <= (xlim[1] - pad_x) and (ylim[0] + pad_y) <= y_val <= (ylim[1] - pad_y)

    if position_mode in ('start', 'center', 'end'):
        if position_mode == 'start':
            x_anchor = xlim[0] + pad_x
        elif position_mode == 'end':
            x_anchor = xlim[1] - pad_x
        else:
            x_anchor = (xlim[0] + xlim[1]) / 2
        y_anchor = slope * x_anchor + intercept
        if _in_bounds(x_anchor, y_anchor):
            angle = _label_angle_for_slope(ax, x_anchor, y_anchor, slope, dx=x_span * 0.02)
            text_artist.set_position((x_anchor, y_anchor))
            text_artist.set_rotation(angle)
            text_artist.set_rotation_mode('anchor')
            text_artist.set_ha('center')
            text_artist.set_va('center')
            text_artist.set_clip_on(True)
            if label_text is not None:
                text_artist.set_text(label_text)
            elif age is not None:
                text_artist.set_text(f" {age:.0f} Ma")
            return

    candidates = []

    x_right = xlim[1] - pad_x
    y_right = slope * x_right + intercept
    if _in_bounds(x_right, y_right):
        candidates.append((x_right, y_right, 'right'))

    if abs(slope) > _SLOPE_EPSILON:
        y_top = ylim[1] - pad_y
        x_top = (y_top - intercept) / slope
        if _in_bounds(x_top, y_top):
            candidates.append((x_top, y_top, 'top'))

    x_left = xlim[0] + pad_x
    y_left = slope * x_left + intercept
    if _in_bounds(x_left, y_left):
        candidates.append((x_left, y_left, 'left'))

    if abs(slope) > _SLOPE_EPSILON:
        y_bottom = ylim[0] + pad_y
        x_bottom = (y_bottom - intercept) / slope
        if _in_bounds(x_bottom, y_bottom):
            candidates.append((x_bottom, y_bottom, 'bottom'))

    if candidates:
        avoid_disp = _collect_avoid_points_display(ax, exclude_artist=text_artist)
        if avoid_disp.size:
            candidate_xy = np.asarray([(item[0], item[1]) for item in candidates], dtype=float)
            candidate_disp = np.asarray(ax.transData.transform(candidate_xy), dtype=float)
            dist2 = ((candidate_disp[:, None, :] - avoid_disp[None, :, :]) ** 2).sum(axis=2)
            min_dist2 = dist2.min(axis=1)
            clearance = _estimate_label_radius_px(text_artist) + 4.0
            overlap_count = (dist2 <= (clearance ** 2)).sum(axis=1).astype(float)
            edge_bonus = np.asarray([
                150.0 if item[2] == 'top' else (80.0 if item[2] == 'right' else 0.0)
                for item in candidates
            ], dtype=float)
            score = min_dist2 + edge_bonus - overlap_count * 12000.0
            best_idx = int(np.argmax(score))
            x_anchor, y_anchor, edge = candidates[best_idx]
        else:
            preferred = None
            for candidate in candidates:
                if candidate[2] == 'top':
                    preferred = candidate
                    break
            if preferred is None:
                for candidate in candidates:
                    if candidate[2] == 'right':
                        preferred = candidate
                        break
            if preferred is None:
                preferred = candidates[0]
            x_anchor, y_anchor, edge = preferred
    else:
        x_anchor = xlim[1] - pad_x
        y_anchor = slope * x_anchor + intercept
        y_anchor = min(max(y_anchor, ylim[0] + pad_y), ylim[1] - pad_y)
        edge = 'right'

    angle = _label_angle_for_slope(ax, x_anchor, y_anchor, slope, dx=x_span * 0.02)
    text_artist.set_position((x_anchor, y_anchor))
    text_artist.set_rotation(angle)
    text_artist.set_rotation_mode('anchor')
    if edge == 'top':
        text_artist.set_ha('center')
        text_artist.set_va('bottom')
    elif edge == 'right':
        text_artist.set_ha('right')
        text_artist.set_va('center')
    elif edge == 'left':
        text_artist.set_ha('left')
        text_artist.set_va('center')
    else:
        text_artist.set_ha('center')
        text_artist.set_va('top')
    text_artist.set_clip_on(True)
    if label_text is not None:
        text_artist.set_text(label_text)
    elif age is not None:
        text_artist.set_text(f" {age:.0f} Ma")


def _position_curve_label_left(ax, text_artist, x_vals, y_vals):
    """Position a curve label near the left edge, aligned with local slope."""
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_span = xlim[1] - xlim[0]
    y_span = ylim[1] - ylim[0]
    if x_span == 0 or y_span == 0:
        return

    pad_x = x_span * 0.02
    pad_y = y_span * 0.02
    x_anchor = xlim[0] + pad_x

    x_arr = np.asarray(x_vals, dtype=float)
    y_arr = np.asarray(y_vals, dtype=float)
    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[valid]
    y_arr = y_arr[valid]
    if x_arr.size < 2:
        return

    order = np.argsort(x_arr)
    x_sorted = x_arr[order]
    y_sorted = y_arr[order]

    x_min = float(x_sorted.min())
    x_max = float(x_sorted.max())
    if x_anchor < x_min:
        x_anchor = x_min
    elif x_anchor > x_max:
        x_anchor = x_max

    y_anchor = np.interp(x_anchor, x_sorted, y_sorted)
    if not np.isfinite(y_anchor):
        return

    idx = np.searchsorted(x_sorted, x_anchor)
    if idx <= 0:
        i0, i1 = 0, 1
    elif idx >= len(x_sorted):
        i0, i1 = len(x_sorted) - 2, len(x_sorted) - 1
    else:
        i0, i1 = max(idx - 1, 0), min(idx, len(x_sorted) - 1)

    dx = x_sorted[i1] - x_sorted[i0]
    if abs(dx) < _SLOPE_EPSILON:
        slope = 0.0
    else:
        slope = (y_sorted[i1] - y_sorted[i0]) / dx

    base_disp = np.asarray(ax.transData.transform((x_anchor, y_anchor)), dtype=float)
    avoid_disp = _collect_avoid_points_display(ax, exclude_artist=text_artist)
    candidate_offsets = [0.0, 14.0, -14.0, 24.0, -24.0, 34.0, -34.0]
    best_y = y_anchor
    if avoid_disp.size:
        candidates_data = []
        candidates_disp = []
        candidates_offset = []
        inv = ax.transData.inverted()
        for offset in candidate_offsets:
            trial_disp = np.asarray((base_disp[0], base_disp[1] + offset), dtype=float)
            try:
                x_trial, y_trial = inv.transform(trial_disp)
            except Exception:
                continue
            if not np.isfinite(x_trial) or not np.isfinite(y_trial):
                continue
            if y_trial < (ylim[0] + pad_y) or y_trial > (ylim[1] - pad_y):
                continue
            candidates_data.append((x_trial, y_trial))
            candidates_disp.append(trial_disp)
            candidates_offset.append(float(offset))

        if candidates_data:
            disp_arr = np.asarray(candidates_disp, dtype=float)
            dist2 = ((disp_arr[:, None, :] - avoid_disp[None, :, :]) ** 2).sum(axis=2)
            min_dist2 = dist2.min(axis=1)
            clearance = _estimate_label_radius_px(text_artist) + 4.0
            overlap_count = (dist2 <= (clearance ** 2)).sum(axis=1).astype(float)
            # Keep labels close to original anchor unless clearance gain is meaningful.
            penalty = (np.asarray(candidates_offset, dtype=float) ** 2) * 0.25
            score = min_dist2 - penalty - overlap_count * 12000.0
            best_idx = int(np.argmax(score))
            best_y = float(candidates_data[best_idx][1])

    angle = _label_angle_for_slope(ax, x_anchor, best_y, slope, dx=x_span * 0.02)
    y_anchor = min(max(best_y, ylim[0] + pad_y), ylim[1] - pad_y)
    text_artist.set_position((x_anchor, y_anchor))
    text_artist.set_rotation(angle)
    text_artist.set_rotation_mode('anchor')
    text_artist.set_ha('left')
    text_artist.set_va('center')
    text_artist.set_clip_on(True)


def _position_isoage_label_on_line(ax, text_artist, x_line, y_line, age_ma=None, label_text=None, position_mode='auto'):
    """Position an isoage label along its line (not at the axes edge)."""
    if not x_line or not y_line:
        return
    if len(x_line) != len(y_line):
        return

    x_arr = np.asarray(x_line, dtype=float)
    y_arr = np.asarray(y_line, dtype=float)
    valid = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[valid]
    y_arr = y_arr[valid]
    if x_arr.size < 2:
        return

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_span = xlim[1] - xlim[0]
    y_span = ylim[1] - ylim[0]
    if x_span == 0 or y_span == 0:
        return

    line_xmin = float(np.min(x_arr))
    line_xmax = float(np.max(x_arr))
    line_ymin = float(np.min(y_arr))
    line_ymax = float(np.max(y_arr))
    if line_xmax < xlim[0] or line_xmin > xlim[1] or line_ymax < ylim[0] or line_ymin > ylim[1]:
        text_artist.set_visible(False)
        return
    text_artist.set_visible(True)

    pad_x = x_span * 0.08
    pad_y = y_span * 0.08
    x_min = xlim[0] + pad_x
    x_max = xlim[1] - pad_x
    y_min = ylim[0] + pad_y
    y_max = ylim[1] - pad_y

    cx = (xlim[0] + xlim[1]) / 2
    cy = (ylim[0] + ylim[1]) / 2
    cx_disp, cy_disp = ax.transData.transform((cx, cy))

    candidates = []
    inv = ax.transData.inverted()
    for i in range(len(x_arr) - 1):
        x0, y0 = float(x_arr[i]), float(y_arr[i])
        x1, y1 = float(x_arr[i + 1]), float(y_arr[i + 1])
        if not (np.isfinite(x0) and np.isfinite(y0) and np.isfinite(x1) and np.isfinite(y1)):
            continue
        p0_disp = np.asarray(ax.transData.transform((x0, y0)), dtype=float)
        p1_disp = np.asarray(ax.transData.transform((x1, y1)), dtype=float)
        v_disp = p1_disp - p0_disp
        seg_norm = np.hypot(v_disp[0], v_disp[1])
        if seg_norm < _SLOPE_EPSILON:
            continue
        normal_disp = np.asarray([-v_disp[1], v_disp[0]], dtype=float) / seg_norm
        for t in (0.25, 0.5, 0.75):
            base_disp = p0_disp + v_disp * t
            progress = (i + t) / max(len(x_arr) - 1, 1)
            for px_offset in (0.0, 12.0, -12.0, 20.0, -20.0):
                cand_disp = base_disp + normal_disp * px_offset
                try:
                    x_t, y_t = inv.transform(cand_disp)
                except Exception:
                    continue
                if not np.isfinite(x_t) or not np.isfinite(y_t):
                    continue
                if x_t < x_min or x_t > x_max or y_t < y_min or y_t > y_max:
                    continue
                center_dist2 = (cand_disp[0] - cx_disp) ** 2 + (cand_disp[1] - cy_disp) ** 2
                candidates.append((x_t, y_t, x0, y0, x1, y1, progress, abs(px_offset), center_dist2, cand_disp))

    if not candidates:
        text_artist.set_visible(False)
        return

    if position_mode == 'start':
        sorted_candidates = sorted(candidates, key=lambda item: item[6])
        keep = max(1, len(sorted_candidates) // 4)
        pool = sorted_candidates[:keep]
    elif position_mode == 'end':
        sorted_candidates = sorted(candidates, key=lambda item: item[6])
        keep = max(1, len(sorted_candidates) // 4)
        pool = sorted_candidates[-keep:]
    elif position_mode == 'center':
        pool = sorted(candidates, key=lambda item: abs(item[6] - 0.5))[:max(1, len(candidates) // 3)]
    else:
        pool = candidates

    avoid_disp = _collect_avoid_points_display(ax, exclude_artist=text_artist)
    if avoid_disp.size:
        pool_disp = np.asarray([item[9] for item in pool], dtype=float)
        dist2 = ((pool_disp[:, None, :] - avoid_disp[None, :, :]) ** 2).sum(axis=2)
        min_dist2 = dist2.min(axis=1)
        clearance = _estimate_label_radius_px(text_artist) + 4.0
        overlap_count = (dist2 <= (clearance ** 2)).sum(axis=1).astype(float)
    else:
        min_dist2 = np.full((len(pool),), 1e9, dtype=float)
        overlap_count = np.zeros((len(pool),), dtype=float)

    center_penalty = np.asarray([item[8] for item in pool], dtype=float) * 0.08
    offset_penalty = np.asarray([item[7] for item in pool], dtype=float) * 1.8
    score = min_dist2 - center_penalty - offset_penalty - overlap_count * 12000.0
    best_idx = int(np.argmax(score))
    selected = pool[best_idx]

    x_mid, y_mid, x0, y0, x1, y1, _progress, _offset, _center_dist2, _disp = selected
    dx = x1 - x0
    slope = 0.0 if abs(dx) < _SLOPE_EPSILON else (y1 - y0) / dx
    angle = _label_angle_for_slope(ax, x_mid, y_mid, slope, dx=x_span * 0.02)
    text_artist.set_position((x_mid, y_mid))
    text_artist.set_rotation(angle)

    text_artist.set_rotation_mode('anchor')
    text_artist.set_ha('center')
    text_artist.set_va('center')
    text_artist.set_clip_on(True)
    if label_text is not None:
        text_artist.set_text(label_text)
    elif age_ma is not None:
        text_artist.set_text(f" {age_ma:.0f} Ma")

def _draw_paleoisochrons(ax, actual_algorithm, ages, params):
    """Draw paleoisochron reference lines for given ages."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        app_state.paleoisochron_label_data = []
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
                    'color': '#94a3b8',
                    'linewidth': getattr(app_state, 'paleoisochron_width', 0.9),
                    'linestyle': '--',
                    'alpha': 0.85
                }
            )
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
            line_artists = ax.plot(
                x_vals,
                y_vals,
                linestyle=paleo_style['linestyle'],
                color=paleo_style['color'],
                linewidth=paleo_style['linewidth'],
                alpha=paleo_style['alpha'],
                zorder=3,
                label='_nolegend_'
            )
            for artist in line_artists:
                _register_overlay_artist('paleoisochron', artist)
            if len(x_vals) > 0:
                label_text = _format_label_text(label_opts.get('label_text'), age)
                if not label_text:
                    label_text = f" {age:.0f} Ma"
                text_artist = ax.text(
                    x_vals[-1], y_vals[-1],
                    label_text,
                    color=paleo_style['color'],
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='left',
                    alpha=paleo_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=paleo_style['color'])
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
                _position_paleo_label(
                    ax,
                    text_artist,
                    slope,
                    intercept,
                    age=age,
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto')
                )
    except Exception as err:
        logger.warning("Failed to draw paleoisochrons: %s", err)

def refresh_paleoisochron_labels():
    """Refresh paleoisochron label positions after zoom/pan."""
    ax = getattr(app_state, 'ax', None)
    if ax is None:
        return

    label_data = getattr(app_state, 'paleoisochron_label_data', [])
    if not label_data:
        label_data = []

    for entry in label_data:
        text_artist = entry.get('text')
        if text_artist is None:
            continue
        _position_paleo_label(
            ax,
            text_artist,
            entry.get('slope', 0),
            entry.get('intercept', 0),
            age=entry.get('age'),
            label_text=entry.get('label_text'),
            position_mode=entry.get('position', 'auto'),
        )

    curve_labels = getattr(app_state, 'plumbotectonics_label_data', [])
    for entry in curve_labels:
        text_artist = entry.get('text')
        if text_artist is None:
            continue
        _position_curve_label_left(ax, text_artist, entry.get('x_vals', []), entry.get('y_vals', []))

    isoage_labels = getattr(app_state, 'plumbotectonics_isoage_label_data', [])
    for entry in isoage_labels:
        text_artist = entry.get('text')
        if text_artist is None:
            continue
        _position_isoage_label_on_line(
            ax,
            text_artist,
            entry.get('x_line', []),
            entry.get('y_line', []),
            age_ma=entry.get('age'),
            label_text=entry.get('label_text'),
            position_mode=entry.get('position', 'auto'),
        )

    curve_labels = getattr(app_state, 'overlay_curve_label_data', [])
    for entry in curve_labels:
        text_artist = entry.get('text')
        if text_artist is None:
            continue
        _position_isoage_label_on_line(
            ax,
            text_artist,
            entry.get('x_line', []),
            entry.get('y_line', []),
            label_text=entry.get('label_text'),
            position_mode=entry.get('position', 'auto'),
        )

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
                'color': '#cbd5f5',
                'linewidth': getattr(app_state, 'model_age_line_width', 0.7),
                'linestyle': '-',
                'alpha': 0.7
            }
        )
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
            line_artists = ax.plot(
                [x_curve[i], pb206[i]], [y_curve[i], pb207[i]],
                color=age_style['color'],
                linewidth=age_style['linewidth'],
                linestyle=age_style['linestyle'],
                alpha=age_style['alpha'],
                zorder=1,
                label='_nolegend_'
            )
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
                    color=age_style['color'],
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=age_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=age_style['color'])
                )
                _register_overlay_curve_label(
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [y_curve[i], pb207[i]],
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_age_line'
                )
                _position_isoage_label_on_line(
                    ax,
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [y_curve[i], pb207[i]],
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto')
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
                'color': '#cbd5f5',
                'linewidth': getattr(app_state, 'model_age_line_width', 0.7),
                'linestyle': '-',
                'alpha': 0.7
            }
        )
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
            line_artists = ax.plot(
                [x_curve[i], pb206[i]], [z_curve[i], pb208[i]],
                color=age_style['color'],
                linewidth=age_style['linewidth'],
                linestyle=age_style['linestyle'],
                alpha=age_style['alpha'],
                zorder=1,
                label='_nolegend_'
            )
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
                    color=age_style['color'],
                    fontsize=label_opts['label_fontsize'],
                    va='center',
                    ha='center',
                    alpha=age_style['alpha'],
                    bbox=_label_bbox(label_opts, edgecolor=age_style['color'])
                )
                _register_overlay_curve_label(
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [z_curve[i], pb208[i]],
                    label_text,
                    label_opts.get('label_position', 'auto'),
                    style_key='model_age_line'
                )
                _position_isoage_label_on_line(
                    ax,
                    text_artist,
                    [x_curve[i], pb206[i]],
                    [z_curve[i], pb208[i]],
                    label_text=label_text,
                    position_mode=label_opts.get('label_position', 'auto')
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
            _position_isoage_label_on_line(
                ax,
                text_artist,
                x_vals,
                y_vals,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto')
            )

