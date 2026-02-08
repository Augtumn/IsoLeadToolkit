"""
Dimensionality Reduction Visualization
Handles UMAP and t-SNE embedding computation and plot rendering
"""
import traceback
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
import itertools
from core.config import CONFIG
from core.state import app_state
# Import events module for selection overlay refresh
try:
    from .events import refresh_selection_overlay
except ImportError:
    refresh_selection_overlay = None

import pandas as pd
import numpy as np
from visualization import plotting_kde as kde_utils
from visualization.plotting_style import (
    _apply_current_style,
    _enforce_plot_style,
    _apply_axis_text_style,
    _legend_location_config,
    _style_legend,
    refresh_plot_style,
)
from visualization import plotting_data as data_utils
from visualization.plotting_data import (
    _lazy_import_ml,
    _get_analysis_data,
)
from visualization.plotting_analysis import (
    show_scree_plot,
    show_pca_loadings,
    show_embedding_correlation,
    show_shepard_diagram,
    show_correlation_heatmap,
)
from visualization.line_styles import resolve_line_style

# from data import geochemistry calculation logic
try:
    from data import geochemistry
    from data.geochemistry import calculate_all_parameters
except ImportError:
    print("[WARN] geochemistry module not found. V1V2 algorithm will not be available.", flush=True)
    geochemistry = None
    calculate_all_parameters = None


# Lazy-loaded heavy dependencies to speed first render
umap = None
Axes3D = None
Ellipse = None


def _lazy_import_umap():
    global umap
    if umap is None:
        import umap as _umap
        umap = _umap


def _lazy_import_mplot3d():
    global Axes3D
    if Axes3D is None:
        from mpl_toolkits.mplot3d import Axes3D as _Axes3D  # noqa: F401
        Axes3D = _Axes3D


def _lazy_import_ellipse():
    global Ellipse
    if Ellipse is None:
        from matplotlib.patches import Ellipse as _Ellipse
        Ellipse = _Ellipse


def _ensure_axes(dimensions=2):
    """Ensure the figure has the correct axes dimensionality."""
    if app_state.fig is None:
        return None

    if dimensions == 3:
        _lazy_import_mplot3d()
        if app_state.ax is None or getattr(app_state.ax, 'name', '') != '3d':
            try:
                app_state.fig.clf()
            except Exception:
                pass
            app_state.ax = app_state.fig.add_subplot(111, projection='3d')
    else:
        if app_state.ax is None or getattr(app_state.ax, 'name', '') == '3d':
            try:
                app_state.fig.clf()
            except Exception:
                pass
            app_state.ax = app_state.fig.add_subplot(111)

    return app_state.ax


def get_umap_embedding(params):
    """Get or compute UMAP embedding with caching."""
    try:
        _lazy_import_umap()

        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = (
            'umap',
            params.get('n_neighbors'),
            params.get('min_dist'),
            params.get('random_state'),
            params.get('n_components', 2),
            subset_key,
        )

        if key in app_state.embedding_cache:
            result = app_state.embedding_cache[key]
            if result is not None:
                return result

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            print("[ERROR] No data available for UMAP computation", flush=True)
            return None

        reducer = umap.UMAP(**params)
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'UMAP'
        return embedding

    except Exception as e:
        print(f"[ERROR] UMAP computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_tsne_embedding(params):
    """Get or compute t-SNE embedding with caching."""
    try:
        _lazy_import_ml()

        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = (
            'tsne',
            params.get('perplexity'),
            params.get('learning_rate'),
            params.get('random_state'),
            params.get('n_components', 2),
            subset_key,
        )

        if key in app_state.embedding_cache:
            result = app_state.embedding_cache[key]
            if result is not None:
                return result

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            print("[ERROR] No data available for t-SNE computation", flush=True)
            return None

        n_samples = X.shape[0]
        perplexity = float(params.get('perplexity', 30))
        if n_samples <= 1:
            print("[ERROR] Not enough samples for t-SNE", flush=True)
            return None
        if perplexity >= n_samples:
            perplexity = max(2, n_samples - 1)

        learning_rate = max(float(params.get('learning_rate', 200)), 10)

        reducer = data_utils.TSNE(
            n_components=params.get('n_components', 2),
            perplexity=perplexity,
            learning_rate=learning_rate,
            random_state=params.get('random_state', 42),
            verbose=0,
            n_jobs=-1
        )

        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'tSNE'
        return embedding

    except Exception as e:
        print(f"[ERROR] t-SNE computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_pca_embedding(params):
    """Get or compute PCA embedding with caching."""
    try:
        _lazy_import_ml()
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = ('pca', params.get('n_components', 2), params.get('random_state', 42), subset_key)
        if key in app_state.embedding_cache:
            result = app_state.embedding_cache[key]
            if result is not None:
                return result

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            print("[ERROR] No data available for PCA computation", flush=True)
            return None

        scaler = data_utils.StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            if np.isnan(X_scaled).any():
                X_scaled = np.nan_to_num(X_scaled)
        except Exception:
            X_scaled = X

        reducer = data_utils.PCA(
            n_components=params.get('n_components', 2),
            random_state=params.get('random_state', 42)
        )

        embedding = reducer.fit_transform(X_scaled)
        app_state.last_pca_variance = reducer.explained_variance_ratio_
        app_state.last_pca_components = reducer.components_
        app_state.current_feature_names = app_state.data_cols

        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'PCA'
        return embedding

    except Exception as e:
        print(f"[ERROR] PCA computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_robust_pca_embedding(params):
    """Get or compute Robust PCA (via MinCovDet) embedding with caching."""
    try:
        _lazy_import_ml()

        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = (
            'robust_pca',
            params.get('n_components', 2),
            params.get('random_state', 42),
            params.get('support_fraction', 0.75),
            subset_key
        )

        if key in app_state.embedding_cache:
            result = app_state.embedding_cache[key]
            if result is not None:
                return result

        X, _ = _get_analysis_data()
        if X is None or X.shape[0] == 0:
            print("[ERROR] No data available for Robust PCA computation", flush=True)
            return None

        scaler = data_utils.StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            if np.isnan(X_scaled).any():
                X_scaled = np.nan_to_num(X_scaled)
        except Exception:
            X_scaled = X

        if X_scaled.shape[0] <= X_scaled.shape[1]:
            reducer = data_utils.PCA(
                n_components=params.get('n_components', 2),
                random_state=params.get('random_state', 42)
            )
            embedding = reducer.fit_transform(X_scaled)
            app_state.last_pca_variance = reducer.explained_variance_ratio_
            app_state.last_pca_components = reducer.components_
        else:
            support_fraction = params.get('support_fraction', 0.75)
            mcd = data_utils.MinCovDet(random_state=params.get('random_state', 42), support_fraction=support_fraction)
            mcd.fit(X_scaled)
            cov = mcd.covariance_
            mean = mcd.location_
            eigvals, eigvecs = np.linalg.eigh(cov)
            order = np.argsort(eigvals)[::-1]
            eigvecs = eigvecs[:, order]
            eigvals = eigvals[order]
            n_components = params.get('n_components', 2)
            components = eigvecs[:, :n_components]
            embedding = (X_scaled - mean) @ components
            if eigvals.sum() > 0:
                app_state.last_pca_variance = eigvals[:n_components] / eigvals.sum()
            app_state.last_pca_components = components.T

        app_state.current_feature_names = app_state.data_cols
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'RobustPCA'
        return embedding

    except Exception as e:
        print(f"[ERROR] Robust PCA computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_embedding(algorithm, umap_params=None, tsne_params=None, pca_params=None, robust_pca_params=None):
    from visualization import plotting_embed
    return plotting_embed.get_embedding(
        algorithm,
        umap_params=umap_params,
        tsne_params=tsne_params,
        pca_params=pca_params,
        robust_pca_params=robust_pca_params,
    )


def plot_embedding(group_col, algorithm, umap_params=None, tsne_params=None, pca_params=None, robust_pca_params=None, size=60):
    from visualization import plotting_embed
    return plotting_embed.plot_embedding(
        group_col,
        algorithm,
        umap_params=umap_params,
        tsne_params=tsne_params,
        pca_params=pca_params,
        robust_pca_params=robust_pca_params,
        size=size,
    )


def plot_umap(group_col, params, size):
    from visualization import plotting_embed
    return plotting_embed.plot_umap(group_col, params, size)


def plot_2d_data(group_col, data_columns, size=60, show_kde=False):
    from visualization import plotting_embed
    return plotting_embed.plot_2d_data(group_col, data_columns, size=size, show_kde=show_kde)


def plot_3d_data(group_col, data_columns, size=60):
    from visualization import plotting_embed
    return plotting_embed.plot_3d_data(group_col, data_columns, size=size)


def _build_group_palette(unique_cats):
    """Build or reuse a stable group -> color mapping."""
    if not hasattr(app_state, 'current_palette'):
        app_state.current_palette = {}

    prop_cycle = plt.rcParams.get('axes.prop_cycle', None)
    cycle_colors = []
    if prop_cycle is not None:
        try:
            cycle_colors = prop_cycle.by_key().get('color', [])
        except Exception:
            cycle_colors = []

    color_cycle = itertools.cycle(cycle_colors if cycle_colors else ['#333333'])

    for cat in unique_cats:
        if cat not in app_state.current_palette or not app_state.current_palette.get(cat):
            app_state.current_palette[cat] = next(color_cycle)

    return {cat: app_state.current_palette[cat] for cat in unique_cats}


def _apply_ternary_stretch(t_vals, l_vals, r_vals):
    """Apply ternary stretch transform based on current mode."""
    if not getattr(app_state, 'ternary_stretch', False):
        return t_vals, l_vals, r_vals

    factors = getattr(app_state, 'ternary_factors', [1.0, 1.0, 1.0])
    if not factors or len(factors) != 3:
        factors = [1.0, 1.0, 1.0]

    t_vals = np.asarray(t_vals, dtype=float) * float(factors[0])
    l_vals = np.asarray(l_vals, dtype=float) * float(factors[1])
    r_vals = np.asarray(r_vals, dtype=float) * float(factors[2])

    mode = getattr(app_state, 'ternary_stretch_mode', 'power')
    power = float(getattr(app_state, 'ternary_stretch_power', 0.5))

    def _minmax(vals):
        vmin = np.nanmin(vals)
        vmax = np.nanmax(vals)
        if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax == vmin:
            return vals
        return (vals - vmin) / (vmax - vmin)

    if mode in ('minmax', 'hybrid'):
        t_vals = _minmax(t_vals)
        l_vals = _minmax(l_vals)
        r_vals = _minmax(r_vals)

    if mode in ('power', 'hybrid'):
        t_vals = np.power(np.maximum(t_vals, 0), power)
        l_vals = np.power(np.maximum(l_vals, 0), power)
        r_vals = np.power(np.maximum(r_vals, 0), power)

    return t_vals, l_vals, r_vals


def _get_subset_dataframe():
    """Return the active subset of the dataframe and its indices."""
    if app_state.df_global is None:
        return None, None

    if app_state.active_subset_indices is not None:
        indices = sorted(list(app_state.active_subset_indices))
        if not indices:
            return None, None
        return app_state.df_global.iloc[indices].copy(), indices

    return app_state.df_global.copy(), list(range(len(app_state.df_global)))


def _get_pb_columns(columns):
    """Find Pb isotope ratio columns with a best-effort heuristic."""
    col_206 = "206Pb/204Pb" if "206Pb/204Pb" in columns else None
    col_207 = "207Pb/204Pb" if "207Pb/204Pb" in columns else None
    col_208 = "208Pb/204Pb" if "208Pb/204Pb" in columns else None

    if col_206 and col_207 and col_208:
        return col_206, col_207, col_208

    for col in columns:
        low = str(col).lower()
        if col_206 is None and "206" in low and "204" in low:
            col_206 = col
        if col_207 is None and "207" in low and "204" in low:
            col_207 = col
        if col_208 is None and "208" in low and "204" in low:
            col_208 = col

    return col_206, col_207, col_208


def _find_age_column(columns):
    """Find an age column for Mu/Kappa plots."""
    candidates = [
        "Age (Ma)",
        "Age(Ma)",
        "Age_Ma",
        "Age",
        "age",
        "t_ma",
        "t"
    ]
    for name in candidates:
        if name in columns:
            return name
    for col in columns:
        low = str(col).lower()
        if "age" in low:
            return col
    return None


def _draw_model_curves(ax, actual_algorithm, params_list):
    """Draw model curves for Pb evolution plots."""
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
            print(f"[WARN] Failed to draw model curve: {err}", flush=True)


def _draw_isochron_overlays(ax, actual_algorithm):
    """Draw isochron reference lines and growth curves for Pb-Pb plots."""
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
        y_col = col_207 if mode == 'ISOCHRON1' else col_208
        if x_col not in df.columns or y_col not in df.columns:
            return

        df_subset = df.iloc[indices]

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
                calculate_isochron_age_from_slope,
                calculate_source_mu_from_isochron,
                calculate_source_kappa_from_slope,
            )
        except ImportError:
            calculate_isochron_age_from_slope = None
            calculate_source_mu_from_isochron = None
            calculate_source_kappa_from_slope = None

        for grp in unique_groups:
            if app_state.visible_groups and grp not in app_state.visible_groups and grp != 'All Data':
                continue

            mask = (group_labels == grp)
            if np.sum(mask) < 2:
                continue

            if grp == 'All Data':
                x_grp = df_subset[x_col].values.astype(float)
                y_grp = df_subset[y_col].values.astype(float)
            else:
                x_grp = df_subset.loc[df_subset.index[mask], x_col].values.astype(float)
                y_grp = df_subset.loc[df_subset.index[mask], y_col].values.astype(float)

            valid = ~np.isnan(x_grp) & ~np.isnan(y_grp)
            x_grp = x_grp[valid]
            y_grp = y_grp[valid]

            if len(x_grp) < 2:
                continue

            try:
                slope, intercept = np.polyfit(x_grp, y_grp, 1)
            except Exception:
                continue

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

            if mode == 'ISOCHRON1' and calculate_isochron_age_from_slope:
                age_ma = calculate_isochron_age_from_slope(slope)
                if age_ma is not None and age_ma > 0:
                    txt_x = x_max_g
                    txt_y = slope * txt_x + intercept
                    ax.text(txt_x, txt_y, f" {age_ma:.0f} Ma", color=color, fontsize=9, va='center', ha='left', fontweight='bold')

                    if getattr(app_state, 'show_growth_curves', True):
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

            elif mode == 'ISOCHRON2' and calculate_source_kappa_from_slope and calculate_isochron_age_from_slope:
                if getattr(app_state, 'show_growth_curves', True):
                    if col_207 and col_206 in df_subset and col_207 in df_subset:
                        if grp == 'All Data':
                            x_iso = df_subset[col_206].values.astype(float)
                            y_iso = df_subset[col_207].values.astype(float)
                        else:
                            x_iso = df_subset.loc[df_subset.index[mask], col_206].values.astype(float)
                            y_iso = df_subset.loc[df_subset.index[mask], col_207].values.astype(float)

                        valid_iso = ~np.isnan(x_iso) & ~np.isnan(y_iso)
                        x_iso = x_iso[valid_iso]
                        y_iso = y_iso[valid_iso]

                        if len(x_iso) >= 2:
                            try:
                                slope_iso, intercept_iso = np.polyfit(x_iso, y_iso, 1)
                                age_ma = calculate_isochron_age_from_slope(slope_iso)
                                if age_ma is not None and age_ma > 0:
                                    slope_208 = slope
                                    growth = geochemistry.calculate_isochron2_growth_curve(
                                        slope_208,
                                        slope_iso,
                                        intercept_iso,
                                        age_ma,
                                        params=params,
                                        steps=100
                                    )

                                    if growth:
                                        x_growth = growth['x']
                                        y_growth = growth['y']
                                        kappa_source = growth['kappa_source']

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

                                        label_text = f" κ={kappa_source:.1f}\n ({age_ma:.0f}Ma)"
                                        ax.text(x_growth[0], y_growth[0], label_text, fontsize=8, color=color, va='bottom', ha='right', alpha=0.8)
                            except Exception as iso2_err:
                                print(f"[WARN] ISOCHRON2 Curve Error: {iso2_err}", flush=True)

    except Exception as err:
        print(f"[WARN] Failed to draw isochron overlays: {err}", flush=True)


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

    if abs(slope) > 1e-12:
        y_top = ylim[1] - pad_y
        x_top = (y_top - intercept) / slope
        if _in_bounds(x_top, y_top):
            candidates.append((x_top, y_top, 'top'))

    x_left = xlim[0] + pad_x
    y_left = slope * x_left + intercept
    if _in_bounds(x_left, y_left):
        candidates.append((x_left, y_left, 'left'))

    if abs(slope) > 1e-12:
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
        print(f"[WARN] Failed to draw paleoisochrons: {err}", flush=True)


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
        print(f"[WARN] Failed to draw model age lines: {err}", flush=True)


def _draw_model_age_lines_86(ax, pb206, pb207, pb208, params):
    """Draw model age construction lines for 206/204 vs 208/204."""
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
        print(f"[WARN] Failed to draw model age lines (206-208): {err}", flush=True)


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
                y_vals = eval(expression, {'x': x_vals, 'np': np, 'math': np})
            except Exception as err:
                print(f"[WARN] Failed to evaluate equation '{expression}': {err}", flush=True)
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


def calculate_auto_ternary_factors():
    """
    Calculate optimal scaling factors for the ternary plot using geometric means.
    This effectively centers the data in the ternary diagram (compositional centering).
    """
    import numpy as np
    from scipy.stats import gmean
    
    try:
        if not hasattr(app_state, 'selected_ternary_cols') or len(app_state.selected_ternary_cols) != 3:
            print("[WARN] Factors calc: invalid col selection", flush=True)
            return False

        # Get data (using global dataset or subset?)
        # For factors, usually better to consider ALL data active rows to prevent jumping
        # But if user has filtered, maybe they want to center on filtered.
        # Let's use subset if active.
        cols = app_state.selected_ternary_cols
        
        if app_state.active_subset_indices is not None:
             df = app_state.df_global.iloc[app_state.active_subset_indices].copy()
        else:
             df = app_state.df_global.copy()
        
        # Extract numerical data
        data = df[cols].apply(pd.to_numeric, errors='coerce').fillna(0.001).values
        
        # Maximize with epsilon
        data = np.maximum(data, 1e-6)
        
        # Geometric means
        gmeans = gmean(data, axis=0)
        
        # Factors = 1 / GM
        # Normalize so min factor is 1.0
        factors = 1.0 / gmeans
        min_f = np.min(factors)
        if min_f > 0:
            factors = factors / min_f
        
        app_state.ternary_factors = factors.tolist()
        print(f"[INFO] Auto-Calculated Factors: {app_state.ternary_factors}", flush=True)
        return True
        
    except Exception as e:
        print(f"[ERROR] Auto factor calculation failed: {e}", flush=True)
        traceback.print_exc()
        return False








    



