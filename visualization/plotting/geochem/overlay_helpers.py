"""Overlay helpers for geochemistry plotting."""
import logging
import re

import numpy as np

from core import app_state, state_gateway
from data.plumbotectonics_data import PLUMBOTECTONICS_SECTIONS
from visualization.line_styles import ensure_line_style, resolve_line_style
from ..data import _lazy_import_geochemistry
from ..label_layout import position_curve_label

logger = logging.getLogger(__name__)


def _is_overlay_label_style_visible(style_key: str | None) -> bool:
    """Return whether labels for the style key should be visible."""
    style = str(style_key or '').strip()
    if style.startswith('plumbotectonics_curve:'):
        group_visibility = getattr(app_state, 'plumbotectonics_group_visibility', {}) or {}
        return bool(
            getattr(app_state, 'show_plumbotectonics_curves', True)
            and group_visibility.get(style, True)
        )

    toggle_map = {
        'model_curve': 'show_model_curves',
        'paleoisochron': 'show_paleoisochrons',
        'model_age_line': 'show_model_age_lines',
        'isochron': 'show_isochrons',
        'growth_curve': 'show_growth_curves',
        'plumbotectonics_curve': 'show_plumbotectonics_curves',
    }
    attr = toggle_map.get(style)
    if attr:
        return bool(getattr(app_state, attr, True))
    return True


def _register_overlay_artist(style_key, artist):
    if artist is None:
        return
    if not hasattr(app_state, 'overlay_artists'):
        state_gateway.set_attr('overlay_artists', {})
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
        state_gateway.set_attr('overlay_curve_label_data', [])
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
                    'color': None,
                    'linewidth': getattr(app_state, 'model_curve_width', 1.2),
                    'linestyle': '-',
                    'alpha': 0.8
                }
            )
            line_color = style.get('color') or get_overlay_default_color('model_curve')
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
            line_kwargs = {
                'linewidth': style['linewidth'],
                'linestyle': style['linestyle'],
                'alpha': style['alpha'],
                'zorder': 1,
                'label': '_nolegend_'
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artists = ax.plot(x_vals, y_vals, **line_kwargs)
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
                    color=line_color or style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
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
                    style_key='model_curve'
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


def _normalize_plumbotectonics_group_key(name: str) -> str:
    value = str(name or '').strip().lower()
    value = re.sub(r'[^a-z0-9]+', '_', value)
    return value.strip('_')


def _plumbotectonics_group_visible(style_key: str) -> bool:
    visibility = getattr(app_state, 'plumbotectonics_group_visibility', {}) or {}
    return bool(visibility.get(style_key, True))


def get_plumbotectonics_group_entries(section=None):
    """Return plumbotectonics group metadata for the active model."""
    sections = _load_plumbotectonics_data()
    if section is None:
        section = _select_plumbotectonics_section(sections)
    if not section:
        return []

    used = set()
    entries = []
    for idx, group in enumerate(section.get('groups', [])):
        name = str(group.get('name') or '').strip() or f"Group {idx + 1}"
        base_key = _normalize_plumbotectonics_group_key(name) or f"group_{idx + 1}"
        key = base_key
        if key in used:
            key = f"{base_key}_{idx + 1}"
        used.add(key)
        entries.append({
            'name': name,
            'key': key,
            'style_key': f"plumbotectonics_curve:{key}",
        })
    return entries


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


def _overlay_palette():
    palette = []
    try:
        from visualization.style_manager import style_manager_instance
        scheme = getattr(app_state, 'color_scheme', None)
        if scheme and scheme in style_manager_instance.palettes:
            palette = list(style_manager_instance.palettes.get(scheme, []))
    except Exception:
        palette = []
    if not palette:
        try:
            import matplotlib.pyplot as plt
            prop_cycle = plt.rcParams.get('axes.prop_cycle', None)
            if prop_cycle is not None:
                palette = list(prop_cycle.by_key().get('color', []))
        except Exception:
            palette = []
    return palette


def get_plumbotectonics_group_palette(section=None):
    entries = get_plumbotectonics_group_entries(section=section)
    colors = _overlay_palette()
    if not colors:
        return {}
    palette = {}
    for idx, entry in enumerate(entries):
        palette[entry['style_key']] = colors[idx % len(colors)]
    return palette


def get_overlay_default_color(style_key: str) -> str | None:
    colors = _overlay_palette()
    if not colors:
        return None
    index_map = {
        'model_curve': 0,
        'paleoisochron': 1,
        'model_age_line': 2,
    }
    idx = index_map.get(style_key, 0)
    return colors[idx % len(colors)]

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
    base_label_opts = _resolve_label_options(
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

    group_entries = get_plumbotectonics_group_entries(section=section)
    group_palette = get_plumbotectonics_group_palette(section=section)
    for group, meta in zip(section.get('groups', []), group_entries):
        name = meta['name']
        x_vals = group.get('pb206', [])
        y_vals = group.get(y_key, [])
        x_fit, y_fit = _fit_plumbotectonics_curve(x_vals, y_vals)
        if len(x_fit) < 2:
            continue
        style_key = meta['style_key']
        style = ensure_line_style(app_state, style_key, dict(base_style))
        color = style.get('color') or base_style.get('color') or group_palette.get(style_key)
        marker = _plumbotectonics_marker(name)
        label_opts = _resolve_label_options(style_key, dict(base_label_opts))
        line_kwargs = {
            'linewidth': style['linewidth'],
            'linestyle': style['linestyle'],
            'alpha': style['alpha'],
            'zorder': 1.2,
            'label': '_nolegend_',
        }
        if color is not None:
            line_kwargs['color'] = color
        line_artists = ax.plot(x_fit, y_fit, **line_kwargs)
        line_color = color
        if line_color is None and line_artists:
            try:
                line_color = line_artists[0].get_color()
            except Exception:
                line_color = None
        is_visible = _plumbotectonics_group_visible(style_key)
        for artist in line_artists:
            _register_overlay_artist(style_key, artist)
            if not is_visible:
                try:
                    artist.set_visible(False)
                except Exception:
                    pass
        point_kwargs = {
            'linestyle': 'None',
            'marker': marker,
            'markersize': 4.5,
            'alpha': min(style['alpha'] + 0.1, 1.0),
            'zorder': 1.3,
            'label': '_nolegend_',
        }
        if line_color is not None:
            point_kwargs['color'] = line_color
        point_artists = ax.plot(x_vals, y_vals, **point_kwargs)
        for artist in point_artists:
            _register_overlay_artist(style_key, artist)
            if not is_visible:
                try:
                    artist.set_visible(False)
                except Exception:
                    pass

        label_text = _format_label_text(label_opts.get('label_text'), name=name)
        if label_text:
            text_artist = ax.text(
                x_fit[0], y_fit[0],
                label_text,
                color=line_color or color or getattr(app_state, 'label_color', '#1f2937'),
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='center',
                alpha=style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=line_color or color)
            )
            _register_overlay_curve_label(
                text_artist,
                x_fit,
                y_fit,
                label_text,
                label_opts.get('label_position', 'auto'),
                style_key=style_key
            )
            if not is_visible:
                try:
                    text_artist.set_visible(False)
                except Exception:
                    pass
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=x_fit,
                y_line=y_fit,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto'),
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

    state_gateway.set_attr('plumbotectonics_isoage_label_data', [])

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
        line_kwargs = {
            'linestyle': paleo_style['linestyle'],
            'linewidth': paleo_style['linewidth'],
            'alpha': paleo_style['alpha'],
            'zorder': 1.05,
            'label': '_nolegend_'
        }
        if line_color is not None:
            line_kwargs['color'] = line_color
        line_artists = ax.plot(x_line, y_line, **line_kwargs)
        for artist in line_artists:
            _register_overlay_artist('paleoisochron', artist)

        if t_val is not None and len(x_line) >= 2:
            label_text = _format_label_text(label_opts.get('label_text'), t_val * 1000.0)
            if not label_text:
                label_text = f" {t_val * 1000.0:.0f} Ma"
            text_artist = ax.text(
                x_line[0], y_line[0],
                label_text,
                color=line_color or paleo_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='left',
                alpha=paleo_style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=line_color)
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
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=x_line,
                y_line=y_line,
                age_ma=t_val * 1000.0,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto'),
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
            line_kwargs = {
                'linewidth': paleo_style['linewidth'],
                'linestyle': paleo_style['linestyle'],
                'alpha': paleo_style['alpha'],
                'zorder': 2,
                'clip_on': True,
            }
            if line_color is not None:
                line_kwargs['color'] = line_color
            line_artist = ax.axvline(age_val, **line_kwargs)
            _register_overlay_artist('paleoisochron', line_artist)
            ax.text(
                age_val,
                label_y,
                _format_label_text(label_opts.get('label_text'), age_val) or f" {age_val:.0f} Ma",
                color=line_color or paleo_style.get('color') or getattr(app_state, 'label_color', '#1f2937'),
                fontsize=label_opts['label_fontsize'],
                rotation=90,
                va='top',
                ha='right',
                alpha=paleo_style['alpha'],
                transform=label_transform,
                clip_on=True,
                bbox=_label_bbox(label_opts, edgecolor=line_color)
            )
    except Exception as err:
        logger.warning("Failed to draw Mu/Kappa paleoisochrons: %s", err)

