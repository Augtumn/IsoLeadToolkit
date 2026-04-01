"""Primary rendering routines for embeddings and scatter plots."""
from __future__ import annotations

import logging
import traceback
from typing import Any

import numpy as np
import pandas as pd

from core import CONFIG, app_state, state_gateway, translate
from . import kde as kde_utils
from .event_bridge import refresh_selection_overlay_safe
from .style import (
    _apply_current_style,
    _enforce_plot_style,
    _apply_axis_text_style,
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
from .geo import _draw_equation_overlays

logger = logging.getLogger(__name__)


from .rendering.helpers import (
    _active_subset_indices,
    _build_legend_proxies,
    _data_cols,
    _df_global,
    _place_inline_legend,
    _resolve_kde_style,
    _render_geo_overlays,
    _render_kde_overlay,
    _render_legend,
    _render_scatter_groups,
    _render_title_labels,
)


def plot_embedding(
    group_col: str,
    algorithm: str,
    umap_params: dict | None = None,
    tsne_params: dict | None = None,
    pca_params: dict | None = None,
    robust_pca_params: dict | None = None,
    size: int = 60,
    precomputed_embedding: np.ndarray | None = None,
    precomputed_meta: dict | None = None,
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

        if precomputed_embedding is not None and actual_algorithm in ('UMAP', 'TSNE', 'PCA', 'RobustPCA'):
            embedding = np.asarray(precomputed_embedding)
            last_type = 'tSNE' if actual_algorithm == 'TSNE' else actual_algorithm
            state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': last_type})

            if isinstance(precomputed_meta, dict):
                if precomputed_meta.get('last_pca_variance') is not None:
                    state_gateway.set_attr('last_pca_variance', precomputed_meta.get('last_pca_variance'))
                if precomputed_meta.get('last_pca_components') is not None:
                    state_gateway.set_attr('last_pca_components', precomputed_meta.get('last_pca_components'))
                if precomputed_meta.get('current_feature_names') is not None:
                    state_gateway.set_attr('current_feature_names', precomputed_meta.get('current_feature_names'))

            logger.debug("Using precomputed embedding for %s", actual_algorithm)

        elif actual_algorithm == 'UMAP':
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

            cols = _data_cols()
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
                state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'V1V2'})
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

            state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': actual_algorithm})

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

                df_global = _df_global()
                if df_global is None:
                    return False

                df_subset = df_global.iloc[indices]

                c_top, c_left, c_right = cols

                missing = [c for c in cols if c not in df_subset.columns]
                if missing:
                    logger.error(f"Missing columns for ternary plot: {missing}")
                    return False

                top_vals = pd.to_numeric(df_subset[c_top], errors='coerce').fillna(0).values
                left_vals = pd.to_numeric(df_subset[c_left], errors='coerce').fillna(0).values
                right_vals = pd.to_numeric(df_subset[c_right], errors='coerce').fillna(0).values

                embedding = np.column_stack((top_vals, left_vals, right_vals))
                state_gateway.set_attrs({'last_embedding': embedding, 'last_embedding_type': 'TERNARY'})

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

        df_global = _df_global()
        if df_global is None:
            logger.error("No data available for plotting")
            return False

        subset_indices = _active_subset_indices()
        if subset_indices is not None:
            indices_to_plot = sorted(list(subset_indices))
            df_source = df_global.iloc[indices_to_plot].copy()
        else:
            indices_to_plot = list(range(len(df_global)))
            df_source = df_global.copy()

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
        state_gateway.sync_available_and_visible_groups(all_groups)

        visible_groups = app_state.visible_groups
        if visible_groups is not None:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not allowed:
                df_plot = df_plot[mask].copy()
            elif not mask.any():
                logger.info("No data matches the selected legend filter; showing all groups instead.")
                state_gateway.set_visible_groups(None)
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    logger.info("Filtered 3D data is empty; showing all groups instead.")
                    df_plot = _reset_plot_dataframe()
                    if df_plot is None:
                        return False
                    state_gateway.set_visible_groups(None)
                    state_gateway.sync_available_and_visible_groups(sorted(df_plot[group_col].unique()))

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

        _render_kde_overlay(actual_algorithm, df_plot, group_col, unique_cats, new_palette)

        scatters = _render_scatter_groups(actual_algorithm, df_plot, group_col, unique_cats, size)
        is_kde_mode = getattr(app_state, 'show_kde', False)
        show_marginal_kde = getattr(app_state, 'show_marginal_kde', False)
        if scatters is None:
            return False

        kde_utils.clear_marginal_axes()
        if show_marginal_kde and actual_algorithm != 'TERNARY':
            try:
                if getattr(app_state.ax, 'name', '') != '3d':
                    kde_utils.draw_marginal_kde(app_state.ax, df_plot, group_col, app_state.current_palette, unique_cats)
            except Exception as kde_err:
                logger.warning(f"Failed to render marginal KDE: {kde_err}")

        _render_legend(actual_algorithm, group_col, unique_cats, scatters)
        _render_title_labels(actual_algorithm, group_col, umap_params, tsne_params, pca_params, robust_pca_params)
        _render_geo_overlays(actual_algorithm, prev_ax, prev_embedding_type, prev_xlim, prev_ylim)

        app_state.ax.tick_params()

        state_gateway.set_attr(
            'annotation',
            app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15,
            ),
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass

        try:
            refresh_selection_overlay_safe()
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

        df_global = _df_global()
        if df_global is None or len(df_global) == 0:
            logger.warning("No data available for plotting")
            return False

        missing = [col for col in data_columns if col not in df_global.columns]
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

        subset_indices = _active_subset_indices()
        if subset_indices is not None:
            indices_to_plot = sorted(list(subset_indices))
            df_plot = df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = df_global.dropna(subset=data_columns).copy()

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
        state_gateway.sync_available_and_visible_groups(all_groups)

        visible_groups = app_state.visible_groups
        if visible_groups is not None:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not allowed:
                df_plot = df_plot[mask].copy()
            elif not mask.any():
                logger.info("No 2D data matches the selected legend filter; reverting to all groups.")
                state_gateway.set_visible_groups(None)
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    logger.info("Filtered 2D data is empty; reverting to all groups.")
                    df_plot = df_global.dropna(subset=data_columns).copy()
                    df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)
                    state_gateway.set_visible_groups(None)
                    all_groups = sorted(df_plot[group_col].unique())
                    state_gateway.sync_available_and_visible_groups(all_groups)

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
            show_edge = bool(getattr(app_state, 'scatter_show_edge', True))
            edge_color = getattr(app_state, 'scatter_edgecolor', '#1e293b') if show_edge else 'none'
            edge_width = getattr(app_state, 'scatter_edgewidth', 0.4) if show_edge else 0.0
            for i, cat in enumerate(unique_cats):
                subset = df_plot[df_plot[group_col] == cat]
                if subset.empty:
                    continue

                xs = pd.to_numeric(subset[data_columns[0]], errors='coerce').values
                ys = pd.to_numeric(subset[data_columns[1]], errors='coerce').values
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
                    edgecolors=edge_color,
                    linewidth=edge_width,
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

        subset_info = " (Subset)" if _active_subset_indices() is not None else ""
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

        state_gateway.set_attr('current_plot_title', title)
        if getattr(app_state, 'show_plot_title', True):
            app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
        else:
            app_state.ax.set_title("")
        state_gateway.set_attr('last_2d_cols', list(data_columns))
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        _apply_axis_text_style(app_state.ax)
        try:
            app_state.ax.autoscale(enable=True, axis='both')
        except Exception:
            pass

        _draw_equation_overlays(app_state.ax)

        state_gateway.set_attr(
            'annotation',
            app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15,
            ),
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

        df_global = _df_global()
        if df_global is None or len(df_global) == 0:
            logger.warning("No data available for plotting")
            return False

        missing = [col for col in data_columns if col not in df_global.columns]
        if missing:
            logger.error(f"Missing columns for 3D plot: {missing}")
            return False

        _ensure_axes(dimensions=3)

        if app_state.ax is None:
            logger.error("Failed to configure 3D axes")
            return False

        subset_indices = _active_subset_indices()
        if subset_indices is not None:
            indices_to_plot = sorted(list(subset_indices))
            df_plot = df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = df_global.dropna(subset=data_columns).copy()

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

            xs = pd.to_numeric(subset[data_columns[0]], errors='coerce').values
            ys = pd.to_numeric(subset[data_columns[1]], errors='coerce').values
            zs = pd.to_numeric(subset[data_columns[2]], errors='coerce').values

            marker_size = getattr(app_state, 'plot_marker_size', size)
            marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.85)
            marker_shape = app_state.group_marker_map.get(
                cat,
                getattr(app_state, 'plot_marker_shape', 'o')
            )
            show_edge = bool(getattr(app_state, 'scatter_show_edge', True))
            edge_color = getattr(app_state, 'scatter_edgecolor', '#1e293b') if show_edge else 'none'
            edge_width = getattr(app_state, 'scatter_edgewidth', 0.4) if show_edge else 0.0
            sc = app_state.ax.scatter(
                xs,
                ys,
                zs,
                label=cat,
                color=app_state.current_palette[cat],
                s=marker_size,
                marker=marker_shape,
                alpha=marker_alpha,
                edgecolors=edge_color,
                linewidth=edge_width,
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

        subset_info = " (Subset)" if _active_subset_indices() is not None else ""
        title = (
            f"3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n"
            f"Colored by {group_col}"
        )
        state_gateway.set_attr('current_plot_title', title)
        if getattr(app_state, 'show_plot_title', True):
            app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0))
        else:
            app_state.ax.set_title("")
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.set_zlabel(data_columns[2])
        _apply_axis_text_style(app_state.ax)

        state_gateway.set_attr('annotation', None)
        return True

    except Exception as err:
        logger.error(f"3D plot failed: {err}")
        traceback.print_exc()
        return False

