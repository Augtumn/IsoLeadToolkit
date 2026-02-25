"""Geochemistry overlays and isochron helpers."""
import ast
import logging
import operator

import numpy as np
import pandas as pd

from core import app_state
from visualization.line_styles import resolve_line_style
from .data import _get_analysis_data, _lazy_import_geochemistry
from .core import _get_subset_dataframe, _get_pb_columns
from .isochron import resolve_isochron_errors as _resolve_isochron_errors

logger = logging.getLogger(__name__)

# Minimum absolute slope to avoid division by zero in label positioning
_SLOPE_EPSILON = 1e-10


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
            ax.plot(
                x_vals,
                y_vals,
                color=style['color'],
                linewidth=style['linewidth'],
                linestyle=style['linestyle'],
                alpha=style['alpha'],
                zorder=1,
                label='_nolegend_'
            )
        except Exception as err:
            logger.warning("Failed to draw model curve: %s", err)

def _build_isochron_label(result_dict):
    """根据 isochron_label_options 动态构建等时线标注文本。"""
    opts = getattr(app_state, 'isochron_label_options', {})
    parts = []
    age = result_dict.get('age') or result_dict.get('age_ma')
    if opts.get('show_age', True) and age is not None and age > 0:
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
    """Draw isochron reference lines and growth curves for Pb-Pb plots."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return

    try:
        if actual_algorithm == 'PB_EVOL_76':
            mode = 'ISOCHRON1'
        else:
            return

        params = geochemistry.engine.get_parameters()

        show_fits = getattr(app_state, 'show_isochrons', True)
        if not show_fits:
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
        y_col = col_207
        if x_col not in df.columns or y_col not in df.columns:
            return

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
            ax.plot(
                x_line,
                y_line,
                linestyle=isochron_style['linestyle'],
                color=isochron_style['color'] or color,
                linewidth=isochron_style['linewidth'],
                alpha=isochron_style['alpha'],
                zorder=2
            )

            if mode == 'ISOCHRON1' and geochemistry:
                age_ma = None
                try:
                    age_ma, _ = geochemistry.calculate_pbpb_age_from_ratio(slope, slope_err, params)
                    if age_ma is not None and age_ma > 0:
                        # 保存年龄到结果
                        app_state.isochron_results[grp]['age_ma'] = age_ma
                except Exception as age_err:
                    logger.warning("Failed to calculate isochron age for slope %.6f: %s", slope, age_err)

                # 动态构建标注
                label_text = _build_isochron_label(app_state.isochron_results[grp])
                if label_text:
                    xlim = ax.get_xlim()
                    ylim = ax.get_ylim()

                    txt_x = min(x_max_g, xlim[1] * 0.95)
                    txt_y = slope * txt_x + intercept

                    if txt_y < ylim[0] or txt_y > ylim[1]:
                        if txt_y > ylim[1]:
                            txt_y = ylim[1] * 0.95
                            txt_x = (txt_y - intercept) / slope if abs(slope) > _SLOPE_EPSILON else txt_x
                        else:
                            txt_y = ylim[0] + (ylim[1] - ylim[0]) * 0.05
                            txt_x = (txt_y - intercept) / slope if abs(slope) > _SLOPE_EPSILON else txt_x

                    ax.text(txt_x, txt_y, f" {label_text}", color=color, fontsize=9, va='center', ha='left', fontweight='bold')

                if getattr(app_state, 'show_growth_curves', True) and age_ma is not None and age_ma > 0:
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
                        ax.plot(
                            x_growth,
                            y_growth,
                            linestyle=growth_style['linestyle'],
                            color=growth_style['color'] or color,
                            alpha=growth_style['alpha'],
                            linewidth=growth_style['linewidth'],
                            zorder=1.5
                        )
                        ax.text(x_growth[0], y_growth[0], annot_text, fontsize=8, color=color, va='bottom', ha='right', alpha=0.8)

            

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
        line_style = resolve_line_style(app_state, 'isochron', fallback_style)
        # 选中等时线用稍粗的线
        draw_width = line_style['linewidth'] * 1.3

        ax.plot(
            x_range,
            y_range,
            color=line_style['color'] or '#ef4444',
            linewidth=draw_width,
            linestyle=line_style['linestyle'],
            alpha=line_style['alpha'],
            zorder=100,
            label='_nolegend_'
        )

        # 动态构建标注
        label_text = _build_isochron_label(data)
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
                fontsize=10,
                fontweight='bold',
                ha='center',
                va='bottom',
                bbox=dict(
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

def _position_paleo_label(ax, text_artist, slope, intercept, age=None):
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
    if age is not None:
        text_artist.set_text(f" {age:.0f} Ma")

def _draw_paleoisochrons(ax, actual_algorithm, ages, params):
    """Draw paleoisochron reference lines for given ages."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        app_state.paleoisochron_label_data = []
        xlim = ax.get_xlim()
        x_min = max(0, xlim[0])
        x_max = xlim[1]
        x_vals = np.linspace(x_min, x_max, 200)

        for age in ages:
            params_line = geochemistry.calculate_paleoisochron_line(
                age,
                params=params,
                algorithm=actual_algorithm
            )
            if not params_line:
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
            ax.plot(
                x_vals,
                y_vals,
                linestyle=paleo_style['linestyle'],
                color=paleo_style['color'],
                linewidth=paleo_style['linewidth'],
                alpha=paleo_style['alpha'],
                zorder=3,
                label='_nolegend_'
            )
            if len(x_vals) > 0:
                text_artist = ax.text(
                    x_vals[-1], y_vals[-1],
                    f" {age:.0f} Ma",
                    color=paleo_style['color'],
                    fontsize=8,
                    va='center',
                    ha='left',
                    alpha=paleo_style['alpha']
                )
                app_state.paleoisochron_label_data.append({
                    'text': text_artist,
                    'slope': slope,
                    'intercept': intercept,
                    'age': age
                })
                _position_paleo_label(ax, text_artist, slope, intercept, age=age)
    except Exception as err:
        logger.warning("Failed to draw paleoisochrons: %s", err)

def refresh_paleoisochron_labels():
    """Refresh paleoisochron label positions after zoom/pan."""
    ax = getattr(app_state, 'ax', None)
    if ax is None:
        return

    label_data = getattr(app_state, 'paleoisochron_label_data', [])
    if not label_data:
        return

    for entry in label_data:
        text_artist = entry.get('text')
        if text_artist is None:
            continue
        _position_paleo_label(ax, text_artist, entry.get('slope', 0), entry.get('intercept', 0), age=entry.get('age'))

def _draw_model_age_lines(ax, pb206, pb207, params):
    """Draw model age construction lines for 206/204 vs 207/204."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        t_sk = geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
        t_cdt = geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
        if params.get('Tsec', 0.0) <= 0:
            t_model = t_cdt
            t1_override = params.get('T2', params.get('T1', None))
        else:
            t_model = np.where(np.isfinite(t_sk), t_sk, t_cdt)
            t1_override = params.get('Tsec', None)

        curve = geochemistry.calculate_modelcurve(t_model, params=params, T1=t1_override / 1e6 if t1_override else None)
        x_curve = np.asarray(curve['Pb206_204'])
        y_curve = np.asarray(curve['Pb207_204'])

        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            idxs = np.random.choice(idxs, size=max_lines, replace=False)

        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb207[i]) or np.isnan(x_curve[i]) or np.isnan(y_curve[i]):
                continue
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
            ax.plot(
                [x_curve[i], pb206[i]], [y_curve[i], pb207[i]],
                color=age_style['color'],
                linewidth=age_style['linewidth'],
                linestyle=age_style['linestyle'],
                alpha=age_style['alpha'],
                zorder=1,
                label='_nolegend_'
            )
            ax.scatter(x_curve[i], y_curve[i], s=10, color='#475569', alpha=0.6, zorder=2, label='_nolegend_')
    except Exception as err:
        logger.warning("Failed to draw model age lines: %s", err)

def _draw_model_age_lines_86(ax, pb206, pb207, pb208, params):
    """Draw model age construction lines for 206/204 vs 208/204."""
    geochemistry, _ = _lazy_import_geochemistry()
    if geochemistry is None:
        return
    try:
        t_sk = geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
        t_cdt = geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
        if params.get('Tsec', 0.0) <= 0:
            t_model = t_cdt
            t1_override = params.get('T2', params.get('T1', None))
        else:
            t_model = np.where(np.isfinite(t_sk), t_sk, t_cdt)
            t1_override = params.get('Tsec', None)

        curve = geochemistry.calculate_modelcurve(t_model, params=params, T1=t1_override / 1e6 if t1_override else None)
        x_curve = np.asarray(curve['Pb206_204'])
        z_curve = np.asarray(curve['Pb208_204'])

        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            idxs = np.random.choice(idxs, size=max_lines, replace=False)

        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb208[i]) or np.isnan(x_curve[i]) or np.isnan(z_curve[i]):
                continue
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
            ax.plot(
                [x_curve[i], pb206[i]], [z_curve[i], pb208[i]],
                color=age_style['color'],
                linewidth=age_style['linewidth'],
                linestyle=age_style['linestyle'],
                alpha=age_style['alpha'],
                zorder=1,
                label='_nolegend_'
            )
            ax.scatter(x_curve[i], z_curve[i], s=10, color='#475569', alpha=0.6, zorder=2, label='_nolegend_')
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

        style = {
            'color': overlay.get('color', '#ef4444'),
            'linewidth': overlay.get('linewidth', 1.0),
            'linestyle': overlay.get('linestyle', '--'),
            'alpha': overlay.get('alpha', 0.85)
        }

        ax.plot(
            x_vals,
            y_vals,
            color=style['color'],
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
            zorder=1,
            label='_nolegend_'
        )

