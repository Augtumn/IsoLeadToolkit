"""Primary rendering routines for embeddings and scatter plots."""
from __future__ import annotations

import logging
import traceback

import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from core import CONFIG, app_state, translate
from . import kde as kde_utils
from .style import (
    _apply_current_style,
    _enforce_plot_style,
    _apply_axis_text_style,
    _legend_layout_config,
    _legend_columns_for_layout,
    _style_legend,
)
from .data import _get_analysis_data, _lazy_import_geochemistry
from .core import (
    _ensure_axes,
    _build_group_palette,
    get_umap_embedding,
    get_tsne_embedding,
    get_pca_embedding,
    get_robust_pca_embedding,
    _get_subset_dataframe,
    _get_pb_columns,
    _find_age_column,
)
from .geo import (
    _draw_model_curves,
    _draw_isochron_overlays,
    _draw_selected_isochron,
    _draw_paleoisochrons,
    _draw_model_age_lines,
    _draw_model_age_lines_86,
    _draw_mu_kappa_paleoisochrons,
    _draw_plumbotectonics_curves,
    _draw_plumbotectonics_isoage_lines,
    _draw_equation_overlays,
)
from visualization.line_styles import resolve_line_style, ensure_line_style
from .legend_model import overlay_legend_items, group_legend_items
from .ternary import _apply_ternary_stretch

logger = logging.getLogger(__name__)

try:
    from ..events import refresh_selection_overlay
except ImportError:
    refresh_selection_overlay = None


def _notify_legend_panel(title, handles, labels):
    callback = getattr(app_state, 'legend_update_callback', None)
    if callable(callback):
        try:
            callback(title, handles, labels)
        except Exception:
            pass

def _build_legend_proxies(handles, labels):
    """Build proxy legend handles from group_legend_items data."""
    items = group_legend_items(all_groups=list(labels))
    use_patch = any(isinstance(h, Patch) for h in handles)
    proxies = []
    for item in items:
        color = item['color']
        if use_patch:
            proxies.append(Patch(facecolor=color, edgecolor='none'))
        else:
            proxies.append(
                Line2D(
                    [0],
                    [0],
                    marker=item['marker'],
                    linestyle='None',
                    markerfacecolor=color,
                    markeredgecolor=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                    markeredgewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                    markersize=8,
                )
            )
    return proxies

def _build_overlay_legend_entries(actual_algorithm):
    """Build legend entries for geochemistry overlay curves."""
    entries = []
    for item in overlay_legend_items(actual_algorithm=actual_algorithm):
        style = resolve_line_style(app_state, item['style_key'], item['fallback'])
        color = style.get('color') or item['default_color']
        handle = Line2D(
            [0], [0],
            color=color,
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
        )
        entries.append((handle, translate(item['label_key'])))
    return entries


def _place_inline_legend(
    ax, group_col, legend_handles, legend_labels,
    *, show_marginal_kde=False, scatters=None, is_kde_mode=False,
):
    """Place in-plot legend and notify the outside legend panel.

    Shared by plot_embedding, plot_2d_data, and plot_3d_data.
    """
    app_state.legend_last_title = group_col
    app_state.legend_last_handles = legend_handles
    app_state.legend_last_labels = legend_labels
    _notify_legend_panel(group_col, legend_handles, legend_labels)

    n_cats = len(legend_labels)
    if n_cats > 30:
        logger.info("Too many categories for standard legend. Use Control Panel legend.")
        return

    inside_location = getattr(app_state, 'legend_position', None)
    if not inside_location or str(inside_location).startswith('outside_'):
        return

    location_key = inside_location
    auto_ncol = _legend_columns_for_layout(legend_labels, ax, location_key)
    if auto_ncol is None:
        ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if n_cats > 15 else 1)
    else:
        ncol = auto_ncol

    legend_kwargs = {
        'title': group_col,
        'frameon': True,
        'fancybox': True,
        'ncol': ncol,
    }

    loc, bbox, mode, borderaxespad = _legend_layout_config(
        ax, show_marginal_kde=show_marginal_kde, location_key=location_key,
    )
    legend_kwargs['loc'] = loc
    legend_kwargs['bbox_to_anchor'] = bbox if bbox else None
    if mode:
        legend_kwargs['mode'] = mode
    if borderaxespad is not None:
        legend_kwargs['borderaxespad'] = borderaxespad

    legend = ax.legend(handles=legend_handles, labels=legend_labels, **legend_kwargs)

    if legend is not None and bbox:
        try:
            legend.set_bbox_to_anchor(bbox, transform=ax.transAxes)
        except Exception:
            pass

    _style_legend(legend, show_marginal_kde=show_marginal_kde, location_key=location_key)

    if legend is not None and scatters and not is_kde_mode:
        try:
            for leg_patch, sc in zip(legend.get_patches(), scatters):
                app_state.legend_to_scatter[leg_patch] = sc
        except Exception:
            pass


def _resolve_kde_style(target: str = 'kde') -> dict:
    legacy_key = 'kde_style' if target == 'kde' else 'marginal_kde_style'
    style_key = 'kde_curve' if target == 'kde' else 'marginal_kde_curve'
    legacy_style = getattr(app_state, legacy_key, {}) or {}
    fallback = {
        'color': None,
        'linewidth': float(legacy_style.get('linewidth', 1.0)),
        'linestyle': '-',
        'alpha': float(legacy_style.get('alpha', 0.6 if target == 'kde' else 0.25)),
        'fill': bool(legacy_style.get('fill', True)),
    }
    if target == 'kde':
        fallback['levels'] = int(legacy_style.get('levels', 10))
    return ensure_line_style(app_state, style_key, fallback)

def plot_embedding(
    group_col: str,
    algorithm: str,
    umap_params: dict | None = None,
    tsne_params: dict | None = None,
    pca_params: dict | None = None,
    robust_pca_params: dict | None = None,
    size: int = 60,
) -> bool:
    """Update plot with specified algorithm and parameters"""
    try:
        logger.debug(f"plot_embedding called: algorithm={algorithm}, group_col={group_col}, size={size}")

        if app_state.fig is None:
            logger.error("Plot axes not initialized")
            return False

        # Determine dimensions based on algorithm
        actual_algorithm = algorithm.strip().upper() if isinstance(algorithm, str) else str(algorithm)
        if actual_algorithm == 'ROBUSTPCA':
            actual_algorithm = 'RobustPCA'  # Keep case for display
        if actual_algorithm in ('PB_MODELS_76', 'PB_MODELS_86'):
            actual_algorithm = 'PB_EVOL_76' if actual_algorithm.endswith('_76') else 'PB_EVOL_86'
        if actual_algorithm in ('ISOCHRON1', 'ISOCHRON2'):
            actual_algorithm = 'PB_EVOL_76' if actual_algorithm == 'ISOCHRON1' else 'PB_EVOL_86'

        target_dims = 2
        if actual_algorithm == 'TERNARY':
            target_dims = 'ternary'

        prev_ax = app_state.ax
        prev_embedding_type = getattr(app_state, 'last_embedding_type', None)
        prev_xlim = None
        prev_ylim = None
        if prev_ax is not None and getattr(prev_ax, 'name', '') != '3d':
            try:
                prev_xlim = prev_ax.get_xlim()
                prev_ylim = prev_ax.get_ylim()
            except Exception:
                prev_xlim = None
                prev_ylim = None

        _ensure_axes(dimensions=target_dims)

        if app_state.ax is None:
            logger.error("Failed to configure axes")
            return False

        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        try:
            # Reset any prior aspect/scale settings (e.g., ternary plots) for 2D
            app_state.ax.set_aspect('auto')
            app_state.ax.set_autoscale_on(True)
        except Exception:
            pass
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        # Ensure parameters are provided
        if umap_params is None:
            umap_params = CONFIG['umap_params']
        if tsne_params is None:
            tsne_params = CONFIG['tsne_params']
        if pca_params is None:
            pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42})
        if robust_pca_params is None:
            robust_pca_params = CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42})

        logger.debug(
            "Using params - UMAP: %s, tSNE: %s, PCA: %s, RobustPCA: %s",
            umap_params, tsne_params, pca_params, robust_pca_params,
        )

        # Get embedding based on algorithm
        embedding = None
        logger.debug("Actual algorithm (normalized): %s", actual_algorithm)

        if actual_algorithm == 'UMAP':
            logger.debug("Computing UMAP embedding")
            embedding = get_umap_embedding(umap_params)
        elif actual_algorithm == 'TSNE':
            logger.debug("Computing tSNE embedding")
            embedding = get_tsne_embedding(tsne_params)
        elif actual_algorithm == 'PCA':
            logger.debug("Computing PCA embedding")
            embedding = get_pca_embedding(pca_params)
        elif actual_algorithm == 'RobustPCA':
            logger.debug("Computing Robust PCA embedding")
            embedding = get_robust_pca_embedding(robust_pca_params)
        elif actual_algorithm == 'V1V2':
            logger.debug("Computing V1V2 embedding")
            geochemistry, calculate_all_parameters = _lazy_import_geochemistry()
            if calculate_all_parameters is None:
                logger.error("V1V2 module not loaded")
                return False

            X, indices = _get_analysis_data()
            if X is None:
                return False

            cols = app_state.data_cols
            col_206 = "206Pb/204Pb" if "206Pb/204Pb" in cols else None
            col_207 = "207Pb/204Pb" if "207Pb/204Pb" in cols else None
            col_208 = "208Pb/204Pb" if "208Pb/204Pb" in cols else None

            if not (col_206 and col_207 and col_208):
                logger.error(
                    "Could not identify isotope columns in %s. "
                    "Please ensure columns '206Pb/204Pb', '207Pb/204Pb', '208Pb/204Pb' are selected.",
                    cols,
                )
                return False

            idx_206 = cols.index(col_206)
            idx_207 = cols.index(col_207)
            idx_208 = cols.index(col_208)

            pb206 = X[:, idx_206]
            pb207 = X[:, idx_207]
            pb208 = X[:, idx_208]

            try:
                v1v2_params = getattr(app_state, 'v1v2_params', {})
                scale = v1v2_params.get('scale', 1.0)
                a = v1v2_params.get('a')
                b = v1v2_params.get('b')
                c = v1v2_params.get('c')

                results = calculate_all_parameters(
                    pb206,
                    pb207,
                    pb208,
                    calculate_ages=False,
                    a=a,
                    b=b,
                    c=c,
                    scale=scale,
                )
                v1 = results['V1']
                v2 = results['V2']
                embedding = np.column_stack((v1, v2))
                app_state.last_embedding = embedding
                app_state.last_embedding_type = 'V1V2'
            except Exception as e:
                logger.error(f"V1V2 calculation failed: {e}")
                return False

        elif actual_algorithm in (
            'PB_EVOL_76', 'PB_EVOL_86', 'PB_MU_AGE', 'PB_KAPPA_AGE',
            'PLUMBOTECTONICS_76', 'PLUMBOTECTONICS_86'
        ):
            logger.debug("Computing Geochemistry embedding for %s", actual_algorithm)
            geochemistry, _ = _lazy_import_geochemistry()
            if geochemistry is None:
                logger.error("Geochemistry module not loaded")
                return False

            df_subset, indices = _get_subset_dataframe()
            if df_subset is None:
                return False

            col_206, col_207, col_208 = _get_pb_columns(df_subset.columns)
            if not (col_206 and col_207 and col_208):
                logger.error("Geochemistry plots require 206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb columns.")
                return False

            pb206 = pd.to_numeric(df_subset[col_206], errors='coerce').values
            pb207 = pd.to_numeric(df_subset[col_207], errors='coerce').values
            pb208 = pd.to_numeric(df_subset[col_208], errors='coerce').values

            if actual_algorithm in ('PB_MU_AGE', 'PB_KAPPA_AGE'):
                t_ma = None
                if getattr(app_state, 'use_real_age_for_mu_kappa', False):
                    age_col = getattr(app_state, 'mu_kappa_age_col', None)
                    if age_col and age_col in df_subset.columns:
                        t_ma = pd.to_numeric(df_subset[age_col], errors='coerce').values

                if t_ma is None:
                    try:
                        from data.geochemistry import engine, resolve_age_model
                        current_model = getattr(engine, 'current_model_name', '')
                        params = engine.get_parameters()
                        age_model = resolve_age_model(params, current_model)
                        is_geokit = "Geokit" in current_model
                        if age_model == 'two_stage':
                            t_ma = geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
                        elif is_geokit:
                            t_ma = geochemistry.calculate_single_stage_age(
                                pb206,
                                pb207,
                                params=params,
                                initial_age=params.get('T1'),
                            )
                        else:
                            t_ma = geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
                    except Exception as age_err:
                        logger.warning("Failed to compute model age: %s", age_err)
                        return False

                if actual_algorithm == 'PB_MU_AGE':
                    mu_vals = geochemistry.calculate_model_mu(pb206, pb207, t_ma)
                    embedding = np.column_stack((t_ma, mu_vals))
                else:
                    kappa_vals = geochemistry.calculate_model_kappa(pb208, pb206, t_ma)
                    embedding = np.column_stack((t_ma, kappa_vals))
            else:
                if actual_algorithm in ('PB_EVOL_76', 'PLUMBOTECTONICS_76'):
                    embedding = np.column_stack((pb206, pb207))
                else:
                    embedding = np.column_stack((pb206, pb208))

            app_state.last_embedding = embedding
            app_state.last_embedding_type = actual_algorithm

        elif actual_algorithm == 'TERNARY':
            logger.debug("Computing Ternary embedding")
            cols = getattr(app_state, 'selected_ternary_cols', [])
            if not cols or len(cols) != 3:
                logger.error("Ternary columns not selected")
                return False

            try:
                X, indices = _get_analysis_data()
                if indices is None:
                    return False

                if app_state.df_global is None:
                    return False

                df_subset = app_state.df_global.iloc[indices]

                c_top, c_left, c_right = cols

                missing = [c for c in cols if c not in df_subset.columns]
                if missing:
                    logger.error(f"Missing columns for ternary plot: {missing}")
                    return False

                top_vals = pd.to_numeric(df_subset[c_top], errors='coerce').fillna(0).values
                left_vals = pd.to_numeric(df_subset[c_left], errors='coerce').fillna(0).values
                right_vals = pd.to_numeric(df_subset[c_right], errors='coerce').fillna(0).values

                embedding = np.column_stack((top_vals, left_vals, right_vals))
                app_state.last_embedding = embedding
                app_state.last_embedding_type = 'TERNARY'

                if hasattr(app_state, 'ternary_manual_ranges'):
                    del app_state.ternary_manual_ranges
                if hasattr(app_state, 'ternary_ranges'):
                    del app_state.ternary_ranges

            except Exception as e:
                logger.error(f"Ternary calculation failed: {e}")
                traceback.print_exc()
                return False
        else:
            logger.error(f"Unknown algorithm: {algorithm}")
            return False

        if embedding is None:
            logger.error(f"Failed to compute {algorithm} embedding")
            return False

        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_source = app_state.df_global.iloc[indices_to_plot].copy()
        else:
            indices_to_plot = list(range(len(app_state.df_global)))
            df_source = app_state.df_global.copy()

        if embedding.shape[0] != len(df_source):
            logger.error(f"Embedding size {embedding.shape[0]} does not match data size {len(df_source)}")
            return False

        def _reset_plot_dataframe():
            base = df_source
            if group_col not in base.columns:
                return None
            base[group_col] = base[group_col].fillna('Unknown').astype(str)
            try:
                if actual_algorithm == 'TERNARY':
                    base['_emb_t'] = embedding[:, 0]
                    base['_emb_l'] = embedding[:, 1]
                    base['_emb_r'] = embedding[:, 2]
                elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
                    idx_x = app_state.pca_component_indices[0]
                    idx_y = app_state.pca_component_indices[1]

                    n_comps = embedding.shape[1]
                    if idx_x >= n_comps:
                        idx_x = 0
                    if idx_y >= n_comps:
                        idx_y = 1 if n_comps > 1 else 0

                    base['_emb_x'] = embedding[:, idx_x]
                    base['_emb_y'] = embedding[:, idx_y]
                    logger.debug(f"Plotting components {idx_x + 1} and {idx_y + 1}")
                else:
                    base['_emb_x'] = embedding[:, 0]
                    base['_emb_y'] = embedding[:, 1]
            except Exception as emb_error:
                logger.error(f"Unable to align embedding with data: {emb_error}")
                return None
            return base

        df_plot = _reset_plot_dataframe()
        if df_plot is None:
            logger.error(f"Unable to prepare plotting data for column: {group_col}")
            return False
        if group_col not in df_plot.columns:
            logger.error(f"Column not found: {group_col}")
            return False

        all_groups = sorted(df_plot[group_col].unique())
        app_state.available_groups = all_groups

        visible_groups = app_state.visible_groups
        if visible_groups is not None:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not allowed:
                df_plot = df_plot[mask].copy()
            elif not mask.any():
                logger.info("No data matches the selected legend filter; showing all groups instead.")
                app_state.visible_groups = None
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    logger.info("Filtered 3D data is empty; showing all groups instead.")
                    df_plot = _reset_plot_dataframe()
                    if df_plot is None:
                        return False
                    app_state.visible_groups = None
                    app_state.available_groups = sorted(df_plot[group_col].unique())

        unique_cats = sorted(df_plot[group_col].unique())
        logger.debug(f"Unique categories in {group_col}: {unique_cats}")

        new_palette = _build_group_palette(unique_cats)

        if actual_algorithm == 'TERNARY':
            t_cols = getattr(app_state, 'selected_ternary_cols', ['Top', 'Left', 'Right'])

            h = np.sqrt(3) / 2

            app_state.ax.plot([0, 1, 0.5, 0], [0, 0, h, 0], 'k-', linewidth=1.5, zorder=0)

            if getattr(app_state, 'plot_style_grid', False):
                grid_color = '#e2e8f0'
                for i in range(1, 10):
                    val = i * 0.1
                    app_state.ax.plot([val * 0.5, 1 - val * 0.5], [val * h, val * h], '-', color=grid_color, lw=0.6, zorder=0)

                    x1, y1 = (1 - val), 0
                    x2, y2 = (0.5 * (1 - val)), h * (1 - val)
                    app_state.ax.plot([x1, x2], [y1, y2], '-', color=grid_color, lw=0.6, zorder=0)

                    x3, y3 = val, 0
                    x4, y4 = (0.5 + 0.5 * val), h * (1 - val)
                    app_state.ax.plot([x3, x4], [y3, y4], '-', color=grid_color, lw=0.6, zorder=0)

            app_state.ax.text(0.5, h + 0.05, t_cols[0], ha='center', va='bottom', fontsize=10, fontweight='bold')
            app_state.ax.text(-0.05, -0.05, t_cols[1], ha='right', va='top', fontsize=10, fontweight='bold')
            app_state.ax.text(1.05, -0.05, t_cols[2], ha='left', va='top', fontsize=10, fontweight='bold')

            app_state.ax.axis('off')
            app_state.ax.set_aspect('equal')

            app_state.ax.set_xlim(-0.1, 1.1)
            app_state.ax.set_ylim(-0.1, h + 0.1)

        if getattr(app_state, 'show_kde', False):
            try:
                kde_utils.lazy_import_seaborn()
                if actual_algorithm == 'TERNARY':
                    logger.info("Generating KDE for Ternary Plot...")
                    for cat in unique_cats:
                        subset = df_plot[df_plot[group_col] == cat].copy()
                        if subset.empty:
                            continue

                        ts = subset['_emb_t'].to_numpy(dtype=float)
                        ls = subset['_emb_l'].to_numpy(dtype=float)
                        rs = subset['_emb_r'].to_numpy(dtype=float)

                        ts, ls, rs = _apply_ternary_stretch(ts, ls, rs)

                        sums = ts + ls + rs
                        with np.errstate(divide='ignore', invalid='ignore'):
                            sums[sums == 0] = 1.0
                            t_norm = ts / sums
                            r_norm = rs / sums

                        h = np.sqrt(3) / 2
                        x_cart = 0.5 * t_norm + 1.0 * r_norm
                        y_cart = h * t_norm

                        kde_style = _resolve_kde_style('kde')
                        kde_utils.sns.kdeplot(
                            x=x_cart,
                            y=y_cart,
                            color=new_palette[cat],
                            ax=app_state.ax,
                            levels=int(kde_style.get('levels', 10)),
                            fill=bool(kde_style.get('fill', True)),
                            alpha=float(kde_style.get('alpha', 0.6)),
                            linewidth=float(kde_style.get('linewidth', 1.0)),
                            warn_singular=False,
                            legend=False,
                            zorder=1,
                        )
                else:
                    logger.info(f"Generating KDE for {actual_algorithm}...")
                    kde_style = _resolve_kde_style('kde')
                    kde_utils.sns.kdeplot(
                        data=df_plot,
                        x='_emb_x',
                        y='_emb_y',
                        hue=group_col,
                        palette=new_palette,
                        ax=app_state.ax,
                        levels=int(kde_style.get('levels', 10)),
                        fill=bool(kde_style.get('fill', True)),
                        alpha=float(kde_style.get('alpha', 0.6)),
                        linewidth=float(kde_style.get('linewidth', 1.0)),
                        warn_singular=False,
                        legend=False,
                        zorder=1,
                    )
            except Exception as kde_err:
                logger.warning(f"Failed to render KDE: {kde_err}")

        scatters = []
        is_kde_mode = getattr(app_state, 'show_kde', False)
        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)

        for i, cat in enumerate(unique_cats):
            if is_kde_mode:
                continue

            try:
                subset = df_plot[df_plot[group_col] == cat]
                if subset.empty:
                    continue
                indices = subset.index.tolist()

                if actual_algorithm == 'TERNARY':
                    ts = subset['_emb_t'].to_numpy(dtype=float, copy=False)
                    ls = subset['_emb_l'].to_numpy(dtype=float, copy=False)
                    rs = subset['_emb_r'].to_numpy(dtype=float, copy=False)

                    if len(ts) == 0:
                        continue

                    t_vals = ts
                    l_vals = ls
                    r_vals = rs

                    t_vals, l_vals, r_vals = _apply_ternary_stretch(t_vals, l_vals, r_vals)

                    sums = t_vals + l_vals + r_vals
                    with np.errstate(divide='ignore', invalid='ignore'):
                        sums[sums == 0] = 1.0

                        t_norm = t_vals / sums
                        l_norm = l_vals / sums
                        r_norm = r_vals / sums

                    h = np.sqrt(3) / 2
                    x_cart = 0.5 * t_norm + 1.0 * r_norm
                    y_cart = h * t_norm

                    marker_size = getattr(app_state, 'plot_marker_size', size)
                    marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                    marker_shape = app_state.group_marker_map.get(
                        cat,
                        getattr(app_state, 'plot_marker_shape', 'o')
                    )
                    color = app_state.current_palette[cat]

                    sc = app_state.ax.scatter(
                        x_cart,
                        y_cart,
                        label=cat,
                        color=color,
                        s=marker_size,
                        marker=marker_shape,
                        alpha=marker_alpha,
                        edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                        linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                        zorder=2,
                        picker=5,
                    )

                    offsets = sc.get_offsets()
                    sc.indices = indices
                    scatters.append(sc)

                    for j, idx in enumerate(indices):
                        if j < len(offsets):
                            x_val, y_val = offsets[j]
                            key = (round(float(x_val), 2), round(float(y_val), 2))
                            app_state.sample_index_map[key] = idx
                            app_state.sample_coordinates[idx] = (x_val, y_val)
                            app_state.artist_to_sample[(id(sc), j)] = idx

                else:
                    xs = subset['_emb_x'].to_numpy(dtype=float, copy=False)
                    ys = subset['_emb_y'].to_numpy(dtype=float, copy=False)

                    if len(xs) == 0:
                        continue

                    marker_size = getattr(app_state, 'plot_marker_size', size)
                    marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                    marker_shape = app_state.group_marker_map.get(
                        cat,
                        getattr(app_state, 'plot_marker_shape', 'o')
                    )

                    color = app_state.current_palette[cat]
                    sc = app_state.ax.scatter(
                        xs,
                        ys,
                        label=cat,
                        color=color,
                        s=marker_size,
                        marker=marker_shape,
                        alpha=marker_alpha,
                        edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                        linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                        zorder=2,
                        picker=5,
                    )

                    for j, idx in enumerate(indices):
                        x_val = float(xs[j])
                        y_val = float(ys[j])
                        key = (round(x_val, 2), round(y_val, 2))
                        app_state.sample_index_map[key] = idx
                        app_state.sample_coordinates[idx] = (x_val, y_val)
                        app_state.artist_to_sample[(id(sc), j)] = idx

                scatters.append(sc)
                app_state.scatter_collections.append(sc)
                app_state.group_to_scatter[cat] = sc

            except Exception as e:
                logger.warning(f"Error plotting category {cat}: {e}")
                continue

        if not scatters and not is_kde_mode:
            logger.error("No data points plotted")
            return False

        kde_utils.clear_marginal_axes()
        if show_marginal_kde and actual_algorithm != 'TERNARY':
            try:
                if getattr(app_state.ax, 'name', '') != '3d':
                    kde_utils.draw_marginal_kde(app_state.ax, df_plot, group_col, app_state.current_palette, unique_cats)
            except Exception as kde_err:
                logger.warning(f"Failed to render marginal KDE: {kde_err}")

        try:
            handles = []
            labels = []

            if is_kde_mode:
                from matplotlib.patches import Patch
                for cat in unique_cats:
                    color = app_state.current_palette[cat]
                    patch = Patch(facecolor=color, edgecolor='none', label=cat, alpha=0.6)
                    handles.append(patch)
                    labels.append(cat)

            legend_handles = handles if handles else list(scatters)
            legend_labels = labels if labels else list(unique_cats)
            for handle, label in _build_overlay_legend_entries(actual_algorithm):
                if label in legend_labels:
                    continue
                legend_handles.append(handle)
                legend_labels.append(label)

            _place_inline_legend(
                app_state.ax, group_col, legend_handles, legend_labels,
                show_marginal_kde=show_marginal_kde,
                scatters=scatters, is_kde_mode=is_kde_mode,
            )
        except Exception as e:
            logger.warning(f"Legend creation error: {e}")

        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""

        if actual_algorithm == 'UMAP':
            title = (
                f'Embedding - UMAP{subset_info} (n_neighbors={umap_params["n_neighbors"]}, min_dist={umap_params["min_dist"]})\n'
                f'Colored by {group_col}'
            )
        elif actual_algorithm == 'TSNE':
            title = (
                f'Embedding - t-SNE{subset_info} (perplexity={tsne_params["perplexity"]}, lr={tsne_params["learning_rate"]})\n'
                f'Colored by {group_col}'
            )
        elif actual_algorithm == 'PCA':
            title = f'Embedding - PCA{subset_info} (n_components={pca_params["n_components"]})\nColored by {group_col}'
        elif actual_algorithm == 'RobustPCA':
            title = (
                f'Embedding - Robust PCA{subset_info} (n_components={robust_pca_params["n_components"]})\n'
                f'Colored by {group_col}'
            )
        elif actual_algorithm == 'V1V2':
            title = f'Geochem - V1-V2 Diagram{subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'TERNARY':
            title = f'Raw - Ternary Plot{subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PB_EVOL_76':
            title = f'Geochem - Pb Evolution / Model Curves (206-207){subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PB_EVOL_86':
            title = f'Geochem - Pb Evolution / Model Curves (206-208){subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PLUMBOTECTONICS_76':
            title = f'Geochem - Plumbotectonics (206-207){subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PLUMBOTECTONICS_86':
            title = f'Geochem - Plumbotectonics (206-208){subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PB_MU_AGE':
            title = f'Geochem - Mu vs Age{subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PB_KAPPA_AGE':
            title = f'Geochem - Kappa vs Age{subset_info}\nColored by {group_col}'
        else:
            title = f'{actual_algorithm}{subset_info}\nColored by {group_col}'

        title_font_dict = {}

        has_cjk = any('\u4e00' <= char <= '\u9fff' for char in title)
        if has_cjk:
            cjk_font = getattr(app_state, 'custom_cjk_font', '')
            if cjk_font:
                title_font_dict['fontname'] = cjk_font
            else:
                try:
                    available = {f.name for f in font_manager.fontManager.ttflist}
                    for f in CONFIG.get('preferred_plot_fonts', []):
                        if f in available:
                            title_font_dict['fontname'] = f
                            break
                except Exception:
                    pass

        if getattr(app_state, 'show_plot_title', True):
            app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0), **title_font_dict)
        else:
            app_state.ax.set_title("")

        if actual_algorithm == 'V1V2':
            app_state.ax.set_xlabel("V1")
            app_state.ax.set_ylabel("V2")
        elif actual_algorithm in ('PB_EVOL_76', 'PLUMBOTECTONICS_76'):
            app_state.ax.set_xlabel("206Pb/204Pb")
            app_state.ax.set_ylabel("207Pb/204Pb")
        elif actual_algorithm in ('PB_EVOL_86', 'PLUMBOTECTONICS_86'):
            app_state.ax.set_xlabel("206Pb/204Pb")
            app_state.ax.set_ylabel("208Pb/204Pb")
        elif actual_algorithm == 'PB_MU_AGE':
            app_state.ax.set_xlabel("Age (Ma)")
            app_state.ax.set_ylabel("Mu (238U/204Pb)")
        elif actual_algorithm == 'PB_KAPPA_AGE':
            app_state.ax.set_xlabel("Age (Ma)")
            app_state.ax.set_ylabel("Kappa (232Th/238U)")
        elif actual_algorithm == 'TERNARY':
            app_state.ax.set_aspect('equal')
        elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
            idx_x = app_state.pca_component_indices[0] + 1
            idx_y = app_state.pca_component_indices[1] + 1
            app_state.ax.set_xlabel(f"PC{idx_x}")
            app_state.ax.set_ylabel(f"PC{idx_y}")
        else:
            app_state.ax.set_xlabel(f"{actual_algorithm} Dimension 1")
            app_state.ax.set_ylabel(f"{actual_algorithm} Dimension 2")

        _apply_axis_text_style(app_state.ax)

        if actual_algorithm in ('PB_EVOL_76', 'PB_EVOL_86'):
            geochemistry, _ = _lazy_import_geochemistry()
            params = geochemistry.engine.get_parameters() if geochemistry else {}
            if getattr(app_state, 'show_model_curves', True):
                params_list = [params]
                _draw_model_curves(app_state.ax, actual_algorithm, params_list)

            if getattr(app_state, 'show_isochrons', True):
                _draw_isochron_overlays(app_state.ax, actual_algorithm)

            # Draw selected isochron if isochron tool is active
            if app_state.selection_tool == 'isochron':
                _draw_selected_isochron(app_state.ax)

            if getattr(app_state, 'show_paleoisochrons', True):
                ages = getattr(app_state, 'paleoisochron_ages', [3000, 2000, 1000, 0])
                _draw_paleoisochrons(app_state.ax, actual_algorithm, ages, params)

            if actual_algorithm in ('PB_EVOL_76', 'PB_EVOL_86') and getattr(app_state, 'show_model_age_lines', True):
                df_subset, _ = _get_subset_dataframe()
                if df_subset is not None:
                    col_206, col_207, _ = _get_pb_columns(df_subset.columns)
                    if col_206 and col_207:
                        pb206 = pd.to_numeric(df_subset[col_206], errors='coerce').values
                        pb207 = pd.to_numeric(df_subset[col_207], errors='coerce').values
                        if actual_algorithm == 'PB_EVOL_76':
                            _draw_model_age_lines(app_state.ax, pb206, pb207, params)
                        else:
                            col_208 = "208Pb/204Pb" if "208Pb/204Pb" in df_subset.columns else None
                            if col_208:
                                pb208 = pd.to_numeric(df_subset[col_208], errors='coerce').values
                                _draw_model_age_lines_86(app_state.ax, pb206, pb207, pb208, params)

        if actual_algorithm in ('PLUMBOTECTONICS_76', 'PLUMBOTECTONICS_86'):
            if getattr(app_state, 'show_paleoisochrons', True):
                _draw_plumbotectonics_isoage_lines(app_state.ax, actual_algorithm)
            if getattr(app_state, 'show_plumbotectonics_curves', True):
                _draw_plumbotectonics_curves(app_state.ax, actual_algorithm)

        if actual_algorithm in ('PB_MU_AGE', 'PB_KAPPA_AGE'):
            if getattr(app_state, 'show_paleoisochrons', True):
                ages = getattr(app_state, 'paleoisochron_ages', [3000, 2000, 1000, 0])
                _draw_mu_kappa_paleoisochrons(app_state.ax, ages)

        if app_state.ax is prev_ax and prev_xlim and prev_ylim:
            if actual_algorithm != 'TERNARY' and getattr(app_state.ax, 'name', '') != '3d':
                try:
                    if prev_embedding_type and str(prev_embedding_type).upper() == str(actual_algorithm).upper():
                        app_state.ax.set_xlim(prev_xlim)
                        app_state.ax.set_ylim(prev_ylim)
                except Exception:
                    pass

        if actual_algorithm != 'TERNARY' and getattr(app_state.ax, 'name', '') != '3d':
            _draw_equation_overlays(app_state.ax)

        app_state.ax.tick_params()

        app_state.annotation = app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15,
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass

        if refresh_selection_overlay:
            try:
                refresh_selection_overlay()
            except Exception as e:
                logger.warning(f"Failed to restore selection overlay: {e}")

        return True

    except Exception as e:
        logger.error(f"Plot update failed: {e}")
        traceback.print_exc()
        return False

def plot_umap(group_col: str, params: dict, size: int) -> bool:
    """Deprecated: Use plot_embedding instead"""
    return plot_embedding(group_col, 'UMAP', umap_params=params, size=size)

def plot_2d_data(group_col: str, data_columns: list[str], size: int = 60, show_kde: bool = False) -> bool:
    """Render a 2D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            logger.error("Plot figure not initialized")
            return False

        if not data_columns or len(data_columns) != 2:
            logger.error("Exactly two data columns are required for a 2D scatter plot")
            return False

        if app_state.df_global is None or len(app_state.df_global) == 0:
            logger.warning("No data available for plotting")
            return False

        missing = [col for col in data_columns if col not in app_state.df_global.columns]
        if missing:
            logger.error(f"Missing columns for 2D plot: {missing}")
            return False

        prev_ax = app_state.ax
        prev_2d_cols = getattr(app_state, 'last_2d_cols', None)
        prev_xlim = None
        prev_ylim = None
        if prev_ax is not None and getattr(prev_ax, 'name', '') != '3d':
            try:
                prev_xlim = prev_ax.get_xlim()
                prev_ylim = prev_ax.get_ylim()
            except Exception:
                prev_xlim = None
                prev_ylim = None

        _ensure_axes(dimensions=2)

        if app_state.ax is None:
            logger.error("Failed to configure 2D axes")
            return False

        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_plot = app_state.df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = app_state.df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            logger.warning("No complete rows available for the selected 2D columns")
            return False

        if group_col not in df_plot.columns:
            logger.error(f"Column not found: {group_col}")
            return False

        try:
            for col in data_columns:
                df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')

            df_plot = df_plot.dropna(subset=data_columns)

            if df_plot.empty:
                logger.warning("No valid numeric data available for 2D plot.")
                return False
        except Exception as e:
            logger.error(f"Failed to convert columns to numeric: {e}")
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        all_groups = sorted(df_plot[group_col].unique())
        app_state.available_groups = all_groups

        visible_groups = app_state.visible_groups
        if visible_groups is not None:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not allowed:
                df_plot = df_plot[mask].copy()
            elif not mask.any():
                logger.info("No 2D data matches the selected legend filter; reverting to all groups.")
                app_state.visible_groups = None
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    logger.info("Filtered 2D data is empty; reverting to all groups.")
                    df_plot = app_state.df_global.dropna(subset=data_columns).copy()
                    df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)
                    app_state.visible_groups = None
                    all_groups = sorted(df_plot[group_col].unique())
                    app_state.available_groups = all_groups

        _apply_current_style()

        app_state.ax.clear()
        try:
            app_state.ax.set_aspect('auto')
            app_state.ax.set_autoscale_on(True)
        except Exception:
            pass
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        unique_cats = sorted(df_plot[group_col].unique())

        new_palette = _build_group_palette(unique_cats)

        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)

        if show_kde:
            try:
                kde_utils.lazy_import_seaborn()
                kde_style = _resolve_kde_style('kde')
                kde_utils.sns.kdeplot(
                    data=df_plot,
                    x=data_columns[0],
                    y=data_columns[1],
                    hue=group_col,
                    palette=new_palette,
                    ax=app_state.ax,
                    levels=int(kde_style.get('levels', 10)),
                    fill=bool(kde_style.get('fill', True)),
                    alpha=float(kde_style.get('alpha', 0.6)),
                    linewidth=float(kde_style.get('linewidth', 1.0)),
                    warn_singular=False,
                    legend=False,
                    zorder=1,
                )
            except Exception as e:
                logger.warning(f"Failed to render KDE: {e}")

        scatters = []

        if not show_kde:
            for i, cat in enumerate(unique_cats):
                subset = df_plot[df_plot[group_col] == cat]
                if subset.empty:
                    continue

                xs = subset[data_columns[0]].astype(float).values
                ys = subset[data_columns[1]].astype(float).values
                indices = subset.index.tolist()

                color = app_state.current_palette[cat]

                marker_size = getattr(app_state, 'plot_marker_size', size)
                marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                marker_shape = app_state.group_marker_map.get(
                    cat,
                    getattr(app_state, 'plot_marker_shape', 'o')
                )
                sc = app_state.ax.scatter(
                    xs,
                    ys,
                    label=cat,
                    color=color,
                    s=marker_size,
                    marker=marker_shape,
                    alpha=marker_alpha,
                    edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                    linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                    zorder=2,
                )
                app_state.scatter_collections.append(sc)
                scatters.append(sc)
                app_state.group_to_scatter[cat] = sc

                for j, idx in enumerate(indices):
                    key = (round(float(xs[j]), 3), round(float(ys[j]), 3))
                    app_state.sample_index_map[key] = idx
                    app_state.sample_coordinates[idx] = (float(xs[j]), float(ys[j]))
                    app_state.artist_to_sample[(id(sc), j)] = idx

        if not scatters and not show_kde:
            logger.error("No points were plotted in 2D")
            return False

        kde_utils.clear_marginal_axes()
        if show_marginal_kde:
            try:
                kde_utils.draw_marginal_kde(
                    app_state.ax,
                    df_plot,
                    group_col,
                    app_state.current_palette,
                    unique_cats,
                    x_col=data_columns[0],
                    y_col=data_columns[1],
                )
            except Exception as kde_err:
                logger.warning(f"Failed to render marginal KDE: {kde_err}")

        try:
            handles = []
            labels = []

            if show_kde:
                from matplotlib.patches import Patch
                for cat in unique_cats:
                    if cat not in app_state.current_palette:
                        continue
                    color = app_state.current_palette[cat]
                    patch = Patch(facecolor=color, edgecolor='none', label=cat, alpha=0.6)
                    handles.append(patch)
                    labels.append(cat)

            legend_handles = handles if handles else list(scatters)
            legend_labels = labels if labels else list(unique_cats)

            _place_inline_legend(
                app_state.ax, group_col, legend_handles, legend_labels,
                show_marginal_kde=show_marginal_kde,
                scatters=scatters, is_kde_mode=show_kde,
            )

        except Exception as legend_err:
            logger.warning(f"2D legend creation error: {legend_err}")

        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        title = (
            f"2D Scatter Plot{subset_info} ({data_columns[0]} vs {data_columns[1]})\n"
            f"Colored by {group_col}"
        )
        if app_state.ax is prev_ax and prev_xlim and prev_ylim:
            try:
                if prev_2d_cols and list(prev_2d_cols) == list(data_columns):
                    app_state.ax.set_xlim(prev_xlim)
                    app_state.ax.set_ylim(prev_ylim)
            except Exception:
                pass

        app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
        app_state.last_2d_cols = list(data_columns)
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        _apply_axis_text_style(app_state.ax)
        try:
            app_state.ax.autoscale(enable=True, axis='both')
        except Exception:
            pass

        _draw_equation_overlays(app_state.ax)

        app_state.annotation = app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15,
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass

        return True

    except Exception as err:
        logger.error(f"2D plot failed: {err}")
        traceback.print_exc()
        return False

def plot_3d_data(group_col: str, data_columns: list[str], size: int = 60) -> bool:
    """Render a 3D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            logger.error("Plot figure not initialized")
            return False

        if not data_columns or len(data_columns) != 3:
            logger.error("Exactly three data columns are required for a 3D scatter plot")
            return False

        if app_state.df_global is None or len(app_state.df_global) == 0:
            logger.warning("No data available for plotting")
            return False

        missing = [col for col in data_columns if col not in app_state.df_global.columns]
        if missing:
            logger.error(f"Missing columns for 3D plot: {missing}")
            return False

        _ensure_axes(dimensions=3)

        if app_state.ax is None:
            logger.error("Failed to configure 3D axes")
            return False

        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_plot = app_state.df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = app_state.df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            logger.warning("No complete rows available for the selected 3D columns")
            return False

        if group_col not in df_plot.columns:
            logger.error(f"Column not found: {group_col}")
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        unique_cats = sorted(df_plot[group_col].unique())

        new_palette = _build_group_palette(unique_cats)

        for i, cat in enumerate(unique_cats):
            subset = df_plot[df_plot[group_col] == cat]
            if subset.empty:
                continue

            xs = subset[data_columns[0]].astype(float).values
            ys = subset[data_columns[1]].astype(float).values
            zs = subset[data_columns[2]].astype(float).values

            marker_size = getattr(app_state, 'plot_marker_size', size)
            marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.85)
            marker_shape = app_state.group_marker_map.get(
                cat,
                getattr(app_state, 'plot_marker_shape', 'o')
            )
            sc = app_state.ax.scatter(
                xs,
                ys,
                zs,
                label=cat,
                color=app_state.current_palette[cat],
                s=marker_size,
                marker=marker_shape,
                alpha=marker_alpha,
                edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                zorder=2,
            )
            app_state.scatter_collections.append(sc)

        legend_handles = list(app_state.scatter_collections)
        legend_labels = list(unique_cats)

        if not app_state.scatter_collections:
            logger.error("No points were plotted in 3D")
            return False

        try:
            _place_inline_legend(
                app_state.ax, group_col, legend_handles, legend_labels,
                show_marginal_kde=False,
            )
        except Exception as legend_err:
            logger.warning(f"3D legend creation error: {legend_err}")

        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        title = (
            f"3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n"
            f"Colored by {group_col}"
        )
        app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.set_zlabel(data_columns[2])
        _apply_axis_text_style(app_state.ax)

        app_state.annotation = None
        return True

    except Exception as err:
        logger.error(f"3D plot failed: {err}")
        traceback.print_exc()
        return False

