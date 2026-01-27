"""
Dimensionality Reduction Visualization
Handles UMAP and t-SNE embedding computation and plot rendering
"""
import traceback
import matplotlib
# Import python-ternary for Ternary plotting
import ternary
from core.config import CONFIG
from core.state import app_state
# Import events module for selection overlay refresh
try:
    from .events import refresh_selection_overlay
except ImportError:
    refresh_selection_overlay = None

import umap
from sklearn.manifold import TSNE
from sklearn.decomposition import PCA
from sklearn.covariance import MinCovDet
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
import seaborn as sns
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
from matplotlib.patches import Ellipse
import pandas as pd
import numpy as np

# from data import geochemistry calculation logic
try:
    from data import geochemistry
    from data.geochemistry import calculate_all_parameters
except ImportError:
    print("[WARN] geochemistry module not found. V1V2 algorithm will not be available.", flush=True)
    geochemistry = None
    calculate_all_parameters = None


def _build_group_palette(unique_cats):
    """Build or reuse a stable group -> color mapping."""
    if not hasattr(app_state, 'current_palette'):
        app_state.current_palette = {}

    prop_cycle = plt.rcParams['axes.prop_cycle']
    cycle_colors = prop_cycle.by_key().get('color', [])
    color_cycle = itertools.cycle(cycle_colors if cycle_colors else ['#333333'])
    default_palette = [next(color_cycle) for _ in range(len(unique_cats))]

    new_palette = {}
    for i, cat in enumerate(unique_cats):
        if cat in app_state.current_palette:
            new_palette[cat] = app_state.current_palette[cat]
        else:
            new_palette[cat] = matplotlib.colors.to_hex(default_palette[i])

    app_state.current_palette = new_palette
    app_state.current_groups = unique_cats
    return new_palette


def _apply_ternary_stretch(t_vals, l_vals, r_vals):
    """Apply ternary stretch transform based on current mode."""
    if not getattr(app_state, 'ternary_stretch', False):
        return t_vals, l_vals, r_vals

    if not getattr(app_state, 'ternary_factors', None) or len(app_state.ternary_factors) != 3:
        calculate_auto_ternary_factors()
    f_top, f_left, f_right = getattr(app_state, 'ternary_factors', [1.0, 1.0, 1.0])
    t_vals = t_vals * f_top
    l_vals = l_vals * f_left
    r_vals = r_vals * f_right

    mode = getattr(app_state, 'ternary_stretch_mode', 'power')
    if mode in ('minmax', 'hybrid'):
        def _minmax(arr):
            if len(arr) == 0:
                return arr
            mn, mx = np.min(arr), np.max(arr)
            if mx - mn < 1e-9:
                return np.zeros_like(arr) + 0.5
            return (arr - mn) / (mx - mn)
        t_vals = _minmax(t_vals)
        l_vals = _minmax(l_vals)
        r_vals = _minmax(r_vals)

    if mode in ('power', 'hybrid'):
        stretch_pow = getattr(app_state, 'ternary_stretch_power', 0.5)
        t_vals = np.power(np.clip(t_vals, 1e-12, None), stretch_pow)
        l_vals = np.power(np.clip(l_vals, 1e-12, None), stretch_pow)
        r_vals = np.power(np.clip(r_vals, 1e-12, None), stretch_pow)

    return t_vals, l_vals, r_vals

def _draw_isochron_overlays(ax, mode):
    """Draw isochron reference lines for Pb-Pb plots."""
    if geochemistry is None: return
    try:
        # Map Pb evolution modes to isochron overlay types
        if mode == 'PB_EVOL_76':
            mode = 'ISOCHRON1'
        elif mode == 'PB_EVOL_86':
            mode = 'ISOCHRON2'
        params = geochemistry.engine.get_parameters()
        
        # Unpack constants
        l238 = params['lambda_238']
        l235 = params['lambda_235']
        l232 = params['lambda_232']
        
        # Origin (Primordial)
        T_start = params['T2'] 
        a0 = params['a0']
        b0 = params['b0']
        c0 = params['c0']
        u_ratio = params['U_ratio']

        # Get current view limits to determine range
        xlim = ax.get_xlim()
        # Clamp x_min to 0 avoiding negative ratios
        x_min = max(0, xlim[0])
        x_max = xlim[1]
        


        try:
            from data.geochemistry import calculate_isochron_age_from_slope, calculate_source_mu_from_isochron, calculate_source_kappa_from_slope
        except ImportError:
            calculate_isochron_age_from_slope = None
            calculate_source_mu_from_isochron = None
            calculate_source_kappa_from_slope = None

        # Determine fitting mode
        # If "Show Age Isochrons" is checked, we fit lines to groups.
        # We rely on app_state for data
        
        show_fits = getattr(app_state, 'show_isochrons', True)
        if show_fits:
            # Fetch indices of active points
            _, indices = _get_analysis_data()
            if indices is None or len(indices) == 0: return

            # Access raw data from global dataframe (independent of selected analysis columns)
            df = app_state.df_global
            if df is None: return

            col_206 = "206Pb/204Pb"
            col_207 = "207Pb/204Pb"
            col_208 = "208Pb/204Pb"

            x_col = col_206
            y_col = None

            if x_col not in df.columns: return

            if mode == 'ISOCHRON1':
                y_col = col_207
            elif mode == 'ISOCHRON2':
                y_col = col_208
            
            if not y_col or y_col not in df.columns: return

            # Work with the subset
            df_subset = df.iloc[indices]
            
            # Identify groups
            group_col = app_state.last_group_col
            current_palette = getattr(app_state, 'current_palette', {})

            if not group_col or group_col not in df_subset.columns:
                unique_groups = ['All Data']
                group_labels = np.array(['All Data'] * len(df_subset))
            else:
                group_labels = df_subset[group_col].fillna('Unknown').astype(str).values
                unique_groups = np.unique(group_labels)

            
            for grp in unique_groups:
                # Check Visibility
                if app_state.visible_groups and grp not in app_state.visible_groups and grp != 'All Data':
                    continue

                mask = (group_labels == grp)
                if np.sum(mask) < 2: continue # Need points for line

                # Extract X and Y for this group
                # Use .values to get numpy array
                if grp == 'All Data':
                    x_grp = df_subset[x_col].values.astype(float)
                    y_grp = df_subset[y_col].values.astype(float)
                else:
                    x_grp = df_subset.loc[df_subset.index[mask], x_col].values.astype(float)
                    y_grp = df_subset.loc[df_subset.index[mask], y_col].values.astype(float)

                # Clean NaNs
                valid = ~np.isnan(x_grp) & ~np.isnan(y_grp)
                x_grp = x_grp[valid]
                y_grp = y_grp[valid]

                if len(x_grp) < 2: continue

                # Fit Line (Linear Regression)
                # Note: This is simple Y|X regression. 
                # For high precision geochron, York regression is preferred, but this is for visualization
                try:
                    slope, intercept = np.polyfit(x_grp, y_grp, 1)
                    print(f"[DEBUG] Group {grp} fit slope: {slope}", flush=True) 
                except:
                    continue
                
                # Determine Line Range
                x_min_g, x_max_g = np.min(x_grp), np.max(x_grp)
                if x_max_g == x_min_g: continue # Vertical line?

                span = x_max_g - x_min_g
                x_line = np.array([x_min_g - span*0.1, x_max_g + span*0.1])
                y_line = slope * x_line + intercept

                # Color
                color = current_palette.get(grp, '#333333')
                if grp == 'All Data': color = '#64748b'

                # Plot Line
                ax.plot(
                    x_line, y_line,
                    linestyle='-',
                    color=color,
                    linewidth=getattr(app_state, 'isochron_line_width', 1.5),
                    alpha=0.8,
                    zorder=2
                )

                # Annotate Age (Only Isochron1)
                if mode == 'ISOCHRON1' and calculate_isochron_age_from_slope:
                        age_ma = calculate_isochron_age_from_slope(slope)
                        if age_ma is not None and age_ma > 0:
                            txt_x = x_max_g
                            txt_y = slope * txt_x + intercept
                            # Offset annotation slightly
                            ax.text(txt_x, txt_y, f" {age_ma:.0f} Ma", 
                                    color=color, fontsize=9, va='center', ha='left', fontweight='bold')
                            
                            # Draw Growth Curve for this Group (Source Mu/Kappa)
                            if getattr(app_state, 'show_growth_curves', True):
                                print(f"[DEBUG] Drawing ISOCHRON1 growth curve for {grp}", flush=True)
                                # Determine Model Type (Single vs Two Stage)
                                is_two_stage = 'a1' in params
                                
                                if is_two_stage:
                                    T_start_curve = params.get('Tsec', 3.7e9)
                                    a_start = params.get('a1', 0.0)
                                    b_start = params.get('b1', 0.0)
                                    c_start = params.get('c1', 0.0)
                                else:
                                    T_start_curve = params['T2']
                                    a_start = params['a0']
                                    b_start = params['b0']
                                    c_start = params['c0']

                                t_years = age_ma * 1e6
                                t_steps = np.linspace(0, T_start_curve, 100)

                                x_growth = None
                                y_growth = None
                                annot_text = ""

                                E1_val = params.get('E1', 0.0)
                                E2_val = params.get('E2', 0.0)

                                if mode == 'ISOCHRON1': # 207Pb/204Pb vs 206Pb/204Pb
                                    # Solve for Mu
                                    C_alpha = geochemistry._exp_evolution_term(l238, T_start_curve, E1_val) - geochemistry._exp_evolution_term(l238, t_years, E1_val)
                                    C_beta = u_ratio * (geochemistry._exp_evolution_term(l235, T_start_curve, E1_val) - geochemistry._exp_evolution_term(l235, t_years, E1_val))
                                    
                                    denom = C_beta - slope * C_alpha
                                    print(f"[DEBUG] Group {grp} ISOCHRON1: Age={age_ma}Ma, Slope={slope:.4f}, Denom={denom:.4e}", flush=True)

                                    if abs(denom) > 1e-15:
                                        mu_source = (slope * a_start + intercept - b_start) / denom
                                        print(f"[DEBUG] Group {grp} ISOCHRON1: Calculated Mu={mu_source:.2f}", flush=True)

                                        x_growth = a_start + mu_source * (geochemistry._exp_evolution_term(l238, T_start_curve, E1_val) - geochemistry._exp_evolution_term(l238, t_steps, E1_val))
                                        y_growth = b_start + mu_source * u_ratio * (geochemistry._exp_evolution_term(l235, T_start_curve, E1_val) - geochemistry._exp_evolution_term(l235, t_steps, E1_val))
                                        annot_text = f" μ={mu_source:.1f}"

                                if x_growth is not None:
                                     ax.plot(
                                         x_growth, y_growth,
                                         linestyle=':',
                                         color=color,
                                         alpha=0.6,
                                         linewidth=getattr(app_state, 'model_curve_width', 1.2),
                                         zorder=1.5
                                     )
                                     ax.text(x_growth[0], y_growth[0], annot_text, 
                                             fontsize=8, color=color, va='bottom', ha='right', alpha=0.8)

                # Annotate Kappa (Only Isochron2)
                elif mode == 'ISOCHRON2' and calculate_source_kappa_from_slope and calculate_isochron_age_from_slope:
                    print(f"[DEBUG] Processing ISOCHRON2 for group: {grp}", flush=True)
                    if not getattr(app_state, 'show_growth_curves', True):
                        print("[DEBUG] Growth curves disabled in settings", flush=True)
                    else:
                        # To calculate kappa, we need the AGE.
                        # This implies we must also fit the 207/206 isochron for this SAME group.
                        
                        if col_207 and col_206 in df_subset and col_207 in df_subset:
                            # Fetch 207/206 data for this group
                            if grp == 'All Data':
                                x_iso = df_subset[col_206].values.astype(float)
                                y_iso = df_subset[col_207].values.astype(float)
                            else:
                                x_iso = df_subset.loc[df_subset.index[mask], col_206].values.astype(float)
                                y_iso = df_subset.loc[df_subset.index[mask], col_207].values.astype(float)
                            
                            valid_iso = ~np.isnan(x_iso) & ~np.isnan(y_iso)
                            x_iso = x_iso[valid_iso]
                            y_iso = y_iso[valid_iso]
                            
                            print(f"[DEBUG] Group {grp}: Found {len(x_iso)} valid points for age calc", flush=True)

                            if len(x_iso) >= 2:
                                try:
                                    slope_iso, intercept_iso = np.polyfit(x_iso, y_iso, 1)
                                    age_ma = calculate_isochron_age_from_slope(slope_iso)
                                    print(f"[DEBUG] Group {grp}: Calculated Age = {age_ma} Ma", flush=True)
                                    
                                    if age_ma is not None and age_ma > 0:
                                        # Now calculate Kappa using the 208/206 slope (which is 'slope' var from outer scope) AND this Age
                                        slope_208 = slope
                                        kappa_source = calculate_source_kappa_from_slope(slope_208, age_ma)
                                        
                                        # Also need Mu for Growth Curve?
                                        # Use the Mu from 207/206 intercept
                                        mu_source = calculate_source_mu_from_isochron(slope_iso, intercept_iso, age_ma)
                                        
                                        if kappa_source > 0 and mu_source > 0:
                                            E1_val = params.get('E1', 0.0)
                                            E2_val = params.get('E2', 0.0)
                                            # Draw Growth Curve for 208/204 vs 206/204
                                            # y_growth (208) = c0 + omega * (e(L2T) - e(L2t))
                                            # omega = mu * kappa
                                            omega_source = mu_source * kappa_source
                                            
                                            t_steps = np.linspace(0, T_start, 100)
                                            # x (206)
                                            x_growth = a0 + mu_source * (geochemistry._exp_evolution_term(l238, T_start, E1_val) - geochemistry._exp_evolution_term(l238, t_steps, E1_val))
                                            # y (208)
                                            y_growth = c0 + omega_source * (geochemistry._exp_evolution_term(l232, T_start, E2_val) - geochemistry._exp_evolution_term(l232, t_steps, E2_val))
                                            
                                            ax.plot(x_growth, y_growth, linestyle=':', color=color, alpha=0.6, linewidth=1.0, zorder=1.5)
                                            
                                            # Label
                                            label_text = f" κ={kappa_source:.1f}\n ({age_ma:.0f}Ma)"
                                            ax.text(x_growth[0], y_growth[0], label_text, 
                                                fontsize=8, color=color, va='bottom', ha='right', alpha=0.8)
                                except Exception as iso2_err:
                                    print(f"[WARN] ISOCHRON2 Curve Error: {iso2_err}", flush=True)

    except Exception as err:
        print(f"[WARN] Failed to draw isochron overlays: {err}", flush=True)

def _get_subset_dataframe():
    """Get dataframe subset respecting active selection."""
    if app_state.df_global is None:
        return None, None
    if app_state.active_subset_indices is not None:
        indices = sorted(list(app_state.active_subset_indices))
        if not indices:
            return None, None
        return app_state.df_global.iloc[indices].copy(), indices
    return app_state.df_global.copy(), list(range(len(app_state.df_global)))


def _find_age_column(columns):
    """Find a likely age column name."""
    candidates = [
        'age', 'Age', 'AGE',
        'Age (Ma)', 'Age(Ma)', 'Age_Ma', 'AgeMa',
        't', 't_Ma', 't(Ma)'
    ]
    for name in candidates:
        if name in columns:
            return name
    # Fallback: case-insensitive contains 'age'
    for col in columns:
        if 'age' in str(col).lower():
            return col
    return None


def _get_pb_columns(columns):
    """Return Pb isotope column names if present."""
    col_206 = "206Pb/204Pb" if "206Pb/204Pb" in columns else None
    col_207 = "207Pb/204Pb" if "207Pb/204Pb" in columns else None
    col_208 = "208Pb/204Pb" if "208Pb/204Pb" in columns else None
    return col_206, col_207, col_208


def _draw_model_curves(ax, mode, params_list):
    """Draw Pb evolution model curves."""
    if geochemistry is None:
        return
    prop_cycle = plt.rcParams['axes.prop_cycle']
    cycle_colors = prop_cycle.by_key().get('color', [])
    color_cycle = itertools.cycle(cycle_colors if cycle_colors else ['#64748b'])

    for params in params_list:
        try:
            tsec = params.get('Tsec', geochemistry.engine.params['Tsec'])
            if tsec and tsec > 0:
                t_max = tsec / 1e6
                t1_override = tsec
            else:
                t_max = params.get('T2', params.get('T1', geochemistry.engine.params['T2'])) / 1e6
                t1_override = params.get('T2', params.get('T1', geochemistry.engine.params['T2']))
            t_vals = np.linspace(0, t_max, 200)
            curve = geochemistry.calculate_modelcurve(t_vals, params=params, T1=t1_override / 1e6)
            x_vals = curve['Pb206_204']
            if mode == 'PB_EVOL_76':
                y_vals = curve['Pb207_204']
            else:
                y_vals = curve['Pb208_204']
            ax.plot(
                x_vals, y_vals,
                color=next(color_cycle),
                linewidth=getattr(app_state, 'model_curve_width', 1.2),
                alpha=0.8,
                zorder=1,
                label='_nolegend_'
            )
        except Exception as err:
            print(f"[WARN] Failed to draw model curve: {err}", flush=True)


def _draw_paleoisochrons(ax, mode, ages_ma, params):
    """Draw paleoisochron reference lines for given ages."""
    if geochemistry is None:
        return
    try:
        l238 = params['lambda_238']
        l235 = params['lambda_235']
        l232 = params['lambda_232']
        T1 = params.get('Tsec', 0.0)
        if T1 <= 0:
            T1 = params.get('T2', params.get('T1', T1))
        X1 = params['a1']
        Y1 = params['b1']
        Z1 = params['c1']
        u_ratio = params['U_ratio']
        U8U5 = 1.0 / u_ratio if u_ratio else 137.88
        kappa = params.get('omega_M', 36.84) / params.get('mu_M', 9.74)

        xlim = ax.get_xlim()
        x_min = max(0, xlim[0])
        x_max = xlim[1]
        x_vals = np.linspace(x_min, x_max, 200)

        for age in ages_ma:
            t = float(age) * 1e6
            e8T = np.exp(l238 * T1)
            e8t = np.exp(l238 * t)

            if mode == 'PB_EVOL_76':
                e5T = np.exp(l235 * T1)
                e5t = np.exp(l235 * t)
                slope = (e5T - e5t) / (U8U5 * (e8T - e8t))
                intercept = Y1 - slope * X1
            else:
                e2T = np.exp(l232 * T1)
                e2t = np.exp(l232 * t)
                slope = kappa * (e2T - e2t) / (e8T - e8t)
                intercept = Z1 - slope * X1

            y_vals = slope * x_vals + intercept
            ax.plot(
                x_vals, y_vals,
                linestyle='--',
                color='#94a3b8',
                linewidth=getattr(app_state, 'paleoisochron_width', 0.9),
                alpha=0.85,
                zorder=3,
                label='_nolegend_'
            )
            # Label paleoisochron (age)
            if len(x_vals) > 0:
                label_x = x_vals[-1]
                label_y = y_vals[-1]
                ax.text(
                    label_x, label_y,
                    f" {age:.0f} Ma",
                    color='#94a3b8',
                    fontsize=8,
                    va='center',
                    ha='left',
                    alpha=0.85
                )
    except Exception as err:
        print(f"[WARN] Failed to draw paleoisochrons: {err}", flush=True)


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

        # Limit number of lines for readability
        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            idxs = np.random.choice(idxs, size=max_lines, replace=False)

        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb207[i]) or np.isnan(x_curve[i]) or np.isnan(y_curve[i]):
                continue
            ax.plot(
                [x_curve[i], pb206[i]], [y_curve[i], pb207[i]],
                color='#cbd5f5',
                linewidth=getattr(app_state, 'model_age_line_width', 0.7),
                alpha=0.7,
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

        # Limit number of lines for readability
        max_lines = 200
        idxs = np.arange(len(pb206))
        if len(idxs) > max_lines:
            idxs = np.random.choice(idxs, size=max_lines, replace=False)

        for i in idxs:
            if np.isnan(pb206[i]) or np.isnan(pb208[i]) or np.isnan(x_curve[i]) or np.isnan(z_curve[i]):
                continue
            ax.plot(
                [x_curve[i], pb206[i]], [z_curve[i], pb208[i]],
                color='#cbd5f5',
                linewidth=getattr(app_state, 'model_age_line_width', 0.7),
                alpha=0.7,
                zorder=1,
                label='_nolegend_'
            )
            ax.scatter(x_curve[i], z_curve[i], s=10, color='#475569', alpha=0.6, zorder=2, label='_nolegend_')
    except Exception as err:
        print(f"[WARN] Failed to draw model age lines (206-208): {err}", flush=True)

                    
    except Exception as e:
        print(f"[WARN] Failed to draw isochron overlays: {e}")

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from tkinter import ttk
import itertools
from .style_manager import apply_custom_style

# sns.set_theme()
# Use custom style manager to avoid dependency issues and ensure CJK support

def _apply_current_style():
    """Apply the current plot style and color scheme from app_state."""
    
    # Grid
    show_grid = getattr(app_state, 'plot_style_grid', False)
        
    # Color scheme
    color_scheme = getattr(app_state, 'color_scheme', 'vibrant')
    
    # Custom Fonts
    primary_font = getattr(app_state, 'custom_primary_font', '')
    cjk_font = getattr(app_state, 'custom_cjk_font', '')
    
    # Font Sizes
    font_sizes = getattr(app_state, 'plot_font_sizes', None)
    
    # Apply styles using our custom manager
    try:
        apply_custom_style(show_grid, color_scheme, primary_font, cjk_font, font_sizes)
    except Exception as e:
        print(f"[WARN] Failed to apply styles: {e}", flush=True)
        # Fallback
        apply_custom_style(False, 'vibrant')
    
    # Apply common rcParams for sizing and grid
    try:
        fig_w, fig_h = getattr(app_state, 'plot_figsize', (13, 9))
        plt.rcParams['figure.figsize'] = (float(fig_w), float(fig_h))
        plt.rcParams['figure.dpi'] = float(getattr(app_state, 'plot_dpi', 130))
        plt.rcParams['figure.facecolor'] = getattr(app_state, 'plot_facecolor', '#ffffff')
        plt.rcParams['axes.facecolor'] = getattr(app_state, 'axes_facecolor', '#ffffff')
        plt.rcParams['grid.color'] = getattr(app_state, 'grid_color', '#e2e8f0')
        plt.rcParams['grid.linewidth'] = float(getattr(app_state, 'grid_linewidth', 0.6))
        plt.rcParams['grid.alpha'] = float(getattr(app_state, 'grid_alpha', 0.7))
        plt.rcParams['grid.linestyle'] = getattr(app_state, 'grid_linestyle', '--')
        plt.rcParams['xtick.direction'] = getattr(app_state, 'tick_direction', 'out')
        plt.rcParams['ytick.direction'] = getattr(app_state, 'tick_direction', 'out')
        plt.rcParams['axes.linewidth'] = float(getattr(app_state, 'axis_linewidth', 1.0))
    except Exception as err:
        print(f"[WARN] Failed to apply rcParams style: {err}", flush=True)

def _enforce_plot_style(ax):
    """Enforce style settings on the specific axes instance."""
    if ax is None:
        return

    # Enforce grid
    show_grid = getattr(app_state, 'plot_style_grid', False)
    ax.grid(
        show_grid,
        color=getattr(app_state, 'grid_color', '#e2e8f0'),
        linewidth=getattr(app_state, 'grid_linewidth', 0.6),
        alpha=getattr(app_state, 'grid_alpha', 0.7),
        linestyle=getattr(app_state, 'grid_linestyle', '--')
    )
    
    # Enforce facecolors from current rcParams
    if app_state.fig is not None:
        app_state.fig.patch.set_facecolor(plt.rcParams.get('figure.facecolor', 'white'))
    
    ax.set_facecolor(plt.rcParams.get('axes.facecolor', 'white'))
    ax.tick_params(direction=getattr(app_state, 'tick_direction', 'out'))
    for spine in ax.spines.values():
        spine.set_linewidth(getattr(app_state, 'axis_linewidth', 1.0))
    ax.spines['top'].set_visible(getattr(app_state, 'show_top_spine', True))
    ax.spines['right'].set_visible(getattr(app_state, 'show_right_spine', True))

def show_scree_plot(parent_window=None):
    """Display a scree plot of the explained variance for the last PCA run."""
    if not hasattr(app_state, 'last_pca_variance') or app_state.last_pca_variance is None:
        print("[WARN] No PCA variance data available. Run PCA first.", flush=True)
        return

    variance_ratio = app_state.last_pca_variance
    n_components = len(variance_ratio)
    components = range(1, n_components + 1)
    cumulative_variance = np.cumsum(variance_ratio)

    # Create a new Toplevel window
    window = tk.Toplevel(parent_window)
    window.title("Scree Plot - Explained Variance")
    window.geometry("600x450")
    
    # Create figure using Figure object directly to avoid global pyplot state
    fig = Figure(figsize=(6, 4), dpi=100)
    ax1 = fig.add_subplot(111)
    
    # Bar plot for individual variance
    ax1.bar(components, variance_ratio, alpha=0.6, color='b', label='Individual Variance')
    ax1.set_xlabel('Principal Component')
    ax1.set_ylabel('Explained Variance Ratio', color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.set_xticks(components)
    ax1.set_ylim(0, 1.05)

    # Line plot for cumulative variance
    ax2 = ax1.twinx()
    ax2.plot(components, cumulative_variance, marker='o', color='r', label='Cumulative Variance')
    ax2.set_ylabel('Cumulative Variance Ratio', color='r')
    ax2.tick_params(axis='y', labelcolor='r')
    ax2.set_ylim(0, 1.05)
    
    # Add grid
    ax1.grid(True, axis='x', alpha=0.3)
    ax2.grid(True, axis='y', alpha=0.3)
    
    ax1.set_title('Scree Plot')
    fig.tight_layout()

    # Embed in Tkinter
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _on_close():
        # No need to call plt.close(fig) since we didn't use plt interface
        window.destroy()
        
    window.protocol("WM_DELETE_WINDOW", _on_close)


def show_pca_loadings(parent_window=None):
    """Display a heatmap of PCA loadings (components)."""
    if not hasattr(app_state, 'last_pca_components') or app_state.last_pca_components is None:
        print("[WARN] No PCA components data available. Run PCA first.", flush=True)
        return

    components = app_state.last_pca_components
    feature_names = app_state.current_feature_names
    
    if not feature_names or len(feature_names) != components.shape[1]:
        print("[WARN] Feature names mismatch or missing.", flush=True)
        feature_names = [f"Feature {i+1}" for i in range(components.shape[1])]

    n_comps = components.shape[0]
    comp_names = [f"PC{i+1}" for i in range(n_comps)]

    # Create a new Toplevel window
    window = tk.Toplevel(parent_window)
    window.title("PCA Loadings")
    window.geometry("800x600")
    
    fig = Figure(figsize=(8, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    # Create heatmap
    # We transpose so features are rows (easier to read if many features) or keep as is?
    # Usually Features x PCs is better for reading if many features.
    # Let's do PCs on Y axis, Features on X axis as standard loadings matrix
    
    im = ax.imshow(components, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    
    # Add colorbar
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Loading Value')
    
    # Set ticks
    ax.set_xticks(np.arange(len(feature_names)))
    ax.set_yticks(np.arange(len(comp_names)))
    
    ax.set_xticklabels(feature_names, rotation=45, ha="right")
    ax.set_yticklabels(comp_names)
    
    # Loop over data dimensions and create text annotations.
    for i in range(len(comp_names)):
        for j in range(len(feature_names)):
            text = ax.text(j, i, f"{components[i, j]:.2f}",
                           ha="center", va="center", color="k" if abs(components[i, j]) < 0.5 else "w")

    ax.set_title("PCA Loadings (Feature Contribution to Components)")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def show_embedding_correlation(parent_window=None):
    """Display correlation between original features and embedding dimensions."""
    if not hasattr(app_state, 'last_embedding') or app_state.last_embedding is None:
        print("[WARN] No embedding data available. Run an analysis first.", flush=True)
        return

    embedding = app_state.last_embedding
    # Get original data (scaled or raw? usually raw is better for interpretation)
    X, _ = _get_analysis_data()
    
    if X is None:
        return
        
    cols = app_state.data_cols
    if not cols:
        return

    # Calculate correlation between each feature and the embedding dimensions
    # embedding is N x 2 (usually)
    # X is N x D
    
    n_dims = embedding.shape[1]
    dim_names = [f"Dim {i+1}" for i in range(n_dims)]
    
    correlations = []
    for i in range(n_dims):
        dim_corrs = []
        dim_data = embedding[:, i]
        for j in range(X.shape[1]):
            feat_data = X[:, j]
            # Use Spearman correlation as relationships might be non-linear
            # But Pearson is faster and standard for "linear" correlation heatmaps
            # Let's use Pearson for consistency with the other heatmap, or Spearman?
            # UMAP/t-SNE are non-linear, so Spearman is probably better.
            # However, numpy corrcoef is Pearson.
            # Let's stick to Pearson for simplicity and speed, or use pandas if available.
            
            # Manual Pearson calculation to avoid pandas dependency if possible, 
            # but we used pandas in show_correlation_heatmap.
            # Let's use numpy corrcoef.
            corr = np.corrcoef(dim_data, feat_data)[0, 1]
            if np.isnan(corr): corr = 0
            dim_corrs.append(corr)
        correlations.append(dim_corrs)
    
    correlations = np.array(correlations) # Shape (n_dims, n_features)
    
    # Create window
    window = tk.Toplevel(parent_window)
    window.title(f"Feature Correlation with {getattr(app_state, 'last_embedding_type', 'Embedding')} Axes")
    window.geometry("800x400")
    
    fig = Figure(figsize=(8, 4), dpi=100)
    ax = fig.add_subplot(111)
    
    # Plot heatmap
    # Rows: Dimensions, Cols: Features
    im = ax.imshow(correlations, cmap='RdBu_r', vmin=-1, vmax=1, aspect='auto')
    
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Correlation Coefficient')
    
    ax.set_yticks(np.arange(n_dims))
    ax.set_yticklabels(dim_names)
    
    ax.set_xticks(np.arange(len(cols)))
    ax.set_xticklabels(cols, rotation=45, ha="right")
    
    # Annotate
    for i in range(n_dims):
        for j in range(len(cols)):
            text = ax.text(j, i, f"{correlations[i, j]:.2f}",
                           ha="center", va="center", color="k" if abs(correlations[i, j]) < 0.5 else "w")
                           
    ax.set_title(f"Correlation: Features vs {getattr(app_state, 'last_embedding_type', 'Embedding')} Dimensions")
    fig.tight_layout()
    
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def show_shepard_diagram(parent_window=None):
    """Display a Shepard diagram (Distance Plot) to evaluate embedding quality."""
    if not hasattr(app_state, 'last_embedding') or app_state.last_embedding is None:
        print("[WARN] No embedding data available.", flush=True)
        return

    embedding = app_state.last_embedding
    X, _ = _get_analysis_data()
    
    if X is None:
        return

    # Sampling for performance if N is large
    n_samples = X.shape[0]
    max_samples = 1000 # Limit to 1000 points (approx 500k pairs)
    
    if n_samples > max_samples:
        indices = np.random.choice(n_samples, max_samples, replace=False)
        X_sub = X[indices]
        emb_sub = embedding[indices]
    else:
        X_sub = X
        emb_sub = embedding
        
    from scipy.spatial.distance import pdist
    
    # Calculate pairwise distances
    # Original space (Euclidean)
    # Note: If using UMAP/t-SNE, they might use different metrics, but Euclidean is standard for input
    d_original = pdist(X_sub)
    
    # Embedding space
    d_embedding = pdist(emb_sub)
    
    # Calculate correlation (Spearman is better for rank preservation)
    from scipy.stats import spearmanr
    corr, _ = spearmanr(d_original, d_embedding)
    
    # Create window
    window = tk.Toplevel(parent_window)
    window.title(f"Shepard Diagram ({getattr(app_state, 'last_embedding_type', 'Embedding')})")
    window.geometry("600x600")
    
    fig = Figure(figsize=(6, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    # Scatter plot
    # Downsample pairs for plotting if too many
    if len(d_original) > 5000:
        plot_indices = np.random.choice(len(d_original), 5000, replace=False)
        ax.scatter(d_original[plot_indices], d_embedding[plot_indices], alpha=0.1, s=5, c='k')
    else:
        ax.scatter(d_original, d_embedding, alpha=0.2, s=10, c='k')
        
    # Add diagonal line for reference
    # Since scales might differ, we plot y=x but also set aspect to equal to make units consistent
    # However, if scales are vastly different (e.g. 100 vs 1), equal aspect will hide data.
    # Let's just plot the diagonal across the visible range if we want to show correlation trend,
    # OR if the user specifically asked for "consistent units", we should try to normalize or use equal aspect.
    # Given "Shepard 图的横纵坐标单位不一致，建议把对角线显示出来", the user likely wants to see
    # how far points deviate from the identity line y=x.
    
    # Find the common range to draw the diagonal
    # Use the actual data limits to avoid forcing the axes to expand to a square
    xlims = (0, np.max(d_original))
    ylims = (0, np.max(d_embedding))
    
    # Plot diagonal line y=x
    # We plot it long enough to cover the potential intersection, but we won't let it dictate the view
    diag_max = max(xlims[1], ylims[1])
    ax.plot([0, diag_max], [0, diag_max], 'r--', alpha=0.5, label='x=y')
    
    # Explicitly set the limits to the data range so the plot doesn't zoom out to show the full diagonal line
    ax.set_xlim(left=0, right=xlims[1] * 1.05)
    ax.set_ylim(bottom=0, top=ylims[1] * 1.05)
    
    ax.legend()
        
    ax.set_xlabel("Original Distance")
    ax.set_ylabel("Embedding Distance")
    ax.set_title(f"Shepard Diagram\nSpearman Correlation: {corr:.3f}")
    
    fig.tight_layout()
    
    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def show_correlation_heatmap(parent_window=None):
    """Display a correlation heatmap of the current dataset."""
    X, _ = _get_analysis_data()
    if X is None:
        print("[WARN] No data available for correlation analysis.", flush=True)
        return
        
    cols = app_state.data_cols
    if not cols:
        return

    # Calculate correlation matrix
    # X is numpy array, need to convert to DataFrame for easy corr
    import pandas as pd
    df_corr = pd.DataFrame(X, columns=cols).corr()

    # Create a new Toplevel window
    window = tk.Toplevel(parent_window)
    window.title("Correlation Heatmap")
    window.geometry("700x600")
    
    fig = Figure(figsize=(7, 6), dpi=100)
    ax = fig.add_subplot(111)
    
    # Create heatmap
    im = ax.imshow(df_corr, cmap='coolwarm', vmin=-1, vmax=1)
    
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Correlation Coefficient')
    
    ax.set_xticks(np.arange(len(cols)))
    ax.set_yticks(np.arange(len(cols)))
    
    ax.set_xticklabels(cols, rotation=45, ha="right")
    ax.set_yticklabels(cols)
    
    # Annotate
    for i in range(len(cols)):
        for j in range(len(cols)):
            text = ax.text(j, i, f"{df_corr.iloc[i, j]:.2f}",
                           ha="center", va="center", color="k")

    ax.set_title("Feature Correlation Matrix")
    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=window)
    canvas.draw()
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


def _ensure_axes(dimensions=2):
    """Ensure the Matplotlib axis matches the requested dimensionality."""
    try:
        current_name = getattr(app_state.ax, 'name', '') if app_state.ax is not None else ''
        
        # Determine target projection
        target_proj = None
        if dimensions == 3:
            target_proj = '3d'
        elif dimensions == 'ternary':
            target_proj = 'ternary'
        else:
            target_proj = 'rectilinear' # Standard 2D

        # Check if we need to replace axes
        needs_replacement = False
        if app_state.ax is None:
            needs_replacement = True
        elif current_name != target_proj:
            needs_replacement = True

        if needs_replacement:
            if app_state.ax is not None:
                try:
                    app_state.ax.remove()
                except Exception:
                    pass
            
            if target_proj == '3d':
                app_state.ax = app_state.fig.add_subplot(111, projection='3d')
            elif target_proj == 'ternary':
                # python-ternary writes onto a standard 2D axes
                app_state.ax = app_state.fig.add_subplot(111)
                # We turn off standard axes as ternary draws its own
                app_state.ax.axis("off")
            else:
                app_state.ax = app_state.fig.add_subplot(111)

        # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.98, top=0.88)
        pass
    except Exception as axis_err:
        print(f"[WARN] Unable to configure axes: {axis_err}", flush=True)


def draw_confidence_ellipse(x, y, ax, n_std=2.4477, facecolor='none', **kwargs):
    """
    Create a plot of the covariance confidence ellipse of *x* and *y*.
    n_std=2.4477 corresponds to a 95% confidence interval for a 2D distribution.
    """
    if x.size < 2 or y.size < 2:
        return

    cov = np.cov(x, y)
    pearson = cov[0, 1]/np.sqrt(cov[0, 0] * cov[1, 1])
    
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                      facecolor=facecolor, **kwargs)

    scale_x = np.sqrt(cov[0, 0]) * n_std
    mean_x = np.mean(x)
    scale_y = np.sqrt(cov[1, 1]) * n_std
    mean_y = np.mean(y)

    transf = (
        matplotlib.transforms.Affine2D()
        .rotate_deg(45)
        .scale(scale_x, scale_y)
        .translate(mean_x, mean_y)
    )

    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


def _get_analysis_data():
    """Helper to get the data subset for analysis (all or selected)."""
    if app_state.active_subset_indices is not None:
        # Filter by active subset
        indices = sorted(list(app_state.active_subset_indices))
        if not indices:
            return None, None
        X = app_state.df_global.iloc[indices][app_state.data_cols].values
    else:
        # Use full dataset
        X = app_state.df_global[app_state.data_cols].values
        indices = list(range(len(app_state.df_global)))

    # Ensure data is numeric (float)
    try:
        X = X.astype(float)
    except ValueError as e:
        print(f"[ERROR] Data contains non-numeric values: {e}", flush=True)
        return None, None

    # Handle NaNs: Impute missing values instead of dropping rows
    if np.isnan(X).any():
        print("[WARN] Missing values detected in data. Imputing with 0.", flush=True)
        try:
            imputer = SimpleImputer(strategy='constant', fill_value=0)
            X = imputer.fit_transform(X)
        except Exception as e:
            print(f"[ERROR] Imputation failed: {e}. Dropping incomplete rows as fallback.", flush=True)
            mask = ~np.isnan(X).any(axis=1)
            X = X[mask]
            indices = [indices[i] for i in range(len(indices)) if mask[i]]

    return X, indices


def get_robust_pca_embedding(params):
    """Get or compute Robust PCA (via MinCovDet) embedding with caching"""
    try:
        # Note: Robust PCA depends on the data subset, so we include a hash of indices in the key if subset is active
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))
            
        key = ('robust_pca', params['n_components'], params['random_state'], params.get('support_fraction', 0.75), subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for Robust PCA. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for Robust PCA. Computing with params: {params}", flush=True)
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for Robust PCA computation", flush=True)
            return None
            
        print(f"[DEBUG] Robust PCA Input Data Shape: {X.shape}", flush=True)
            
        # Standardize features
        scaler = StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            if np.isnan(X_scaled).any():
                print("[WARN] NaNs detected in scaled data (likely constant columns). Replacing with 0.", flush=True)
                X_scaled = np.nan_to_num(X_scaled)
        except Exception:
            X_scaled = X

        # MinCovDet requires n_samples > n_features. 
        # If not met, fallback to standard PCA with a warning.
        if X_scaled.shape[0] <= X_scaled.shape[1]:
            print(f"[WARN] Not enough samples ({X_scaled.shape[0]}) for Robust PCA (needs > {X_scaled.shape[1]} features). Falling back to standard PCA.", flush=True)
            reducer = PCA(
                n_components=params['n_components'],
                random_state=params['random_state']
            )
            embedding = reducer.fit_transform(X_scaled)
        else:
            try:
                # 1. Estimate robust covariance
                # support_fraction=0.75 ensures we use enough data points to be stable but robust
                # Remove n_jobs=-1 to avoid potential multiprocess overhead/errors on small data
                support_fraction = params.get('support_fraction', 0.75)
                mcd = MinCovDet(random_state=params['random_state'], support_fraction=support_fraction)
                try:
                    mcd.fit(X_scaled)
                except Exception:
                    # If fit fails (e.g. singular covariance), try adding minute noise
                    print("[INFO] MinCovDet failed, retrying with regularization...", flush=True)
                    noise = np.random.RandomState(params['random_state']).normal(0, 1e-5, X_scaled.shape)
                    mcd.fit(X_scaled + noise)
                
                # 2. Get robust covariance and location
                robust_cov = mcd.covariance_
                robust_location = mcd.location_
                
                # 3. Center data using robust location
                X_centered = X_scaled - robust_location
                
                # 4. Eigendecomposition of robust covariance
                eigvals, eigvecs = np.linalg.eigh(robust_cov)
                
                # 5. Sort eigenvectors by eigenvalues in descending order
                idx = eigvals.argsort()[::-1]
                eigvecs = eigvecs[:, idx]
                
                # 6. Project data onto top components
                # Note: We project the centered data
                embedding = np.dot(X_centered, eigvecs[:, :params['n_components']])
                
                # Calculate explained variance ratio for Robust PCA
                # Total variance is sum of all eigenvalues
                total_variance = np.sum(eigvals)
                if total_variance > 0:
                    explained_variance_ratio = eigvals[idx][:params['n_components']] / total_variance
                    app_state.last_pca_variance = explained_variance_ratio
                else:
                    app_state.last_pca_variance = None
                
                # Store components (loadings)
                # eigvecs columns are eigenvectors, so we transpose to match sklearn PCA.components_ shape (n_components, n_features)
                app_state.last_pca_components = eigvecs[:, :params['n_components']].T
                app_state.current_feature_names = app_state.data_cols
                    
                print("[INFO] Robust PCA computed successfully (MCD method).", flush=True)
            
            except Exception as mcd_err:
                print(f"[WARN] Robust PCA (MCD) failed: {mcd_err}. Falling back to standard PCA.", flush=True)
                reducer = PCA(
                    n_components=params['n_components'],
                    random_state=params['random_state']
                )
                embedding = reducer.fit_transform(X_scaled)
                app_state.last_pca_variance = reducer.explained_variance_ratio_
                app_state.last_pca_components = reducer.components_
                app_state.current_feature_names = app_state.data_cols

        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'RobustPCA'
        print(f"[DEBUG] Robust PCA embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] Robust PCA computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_pca_embedding(params):
    """Get or compute PCA embedding with caching"""
    try:
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = ('pca', params['n_components'], params['random_state'], subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for PCA. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for PCA. Computing with params: {params}", flush=True)
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for PCA computation", flush=True)
            return None
            
        print(f"[DEBUG] PCA Input Data Shape: {X.shape}", flush=True)
        
        # Standardize features by removing the mean and scaling to unit variance
        # This is critical for PCA to work correctly on data with different scales
        # Handle constant columns to avoid NaNs
        scaler = StandardScaler()
        try:
            X_scaled = scaler.fit_transform(X)
            # Replace NaNs (from constant columns) with 0
            if np.isnan(X_scaled).any():
                print("[WARN] NaNs detected in scaled data (likely constant columns). Replacing with 0.", flush=True)
                X_scaled = np.nan_to_num(X_scaled)
        except Exception as scale_err:
            print(f"[WARN] Scaling failed: {scale_err}. Using raw data.", flush=True)
            X_scaled = X

        reducer = PCA(
            n_components=params['n_components'],
            random_state=params['random_state']
        )
        
        embedding = reducer.fit_transform(X_scaled)
        
        # Store explained variance for scree plot
        app_state.last_pca_variance = reducer.explained_variance_ratio_
        # Store components (loadings)
        app_state.last_pca_components = reducer.components_
        app_state.current_feature_names = app_state.data_cols
        
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'PCA'
        print(f"[DEBUG] PCA embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] PCA computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_umap_embedding(params):
    """Get or compute UMAP embedding with caching"""
    try:
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        key = ('umap', params['n_neighbors'], params['min_dist'], params['random_state'], subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for UMAP. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for UMAP. Computing with params: {params}", flush=True)
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for UMAP computation", flush=True)
            return None
        
        print(f"[DEBUG] UMAP Input Data Shape: {X.shape}", flush=True)
        
        # Validate parameters
        n_neighbors = min(params['n_neighbors'], X.shape[0] - 1)
        n_neighbors = max(n_neighbors, 2)
        
        reducer = umap.UMAP(
            n_neighbors=n_neighbors,
            min_dist=max(params['min_dist'], 0.0),
            random_state=params['random_state'],
            n_components=params['n_components'],
            transform_seed=params['random_state']
        )
        
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'UMAP'
        print(f"[DEBUG] UMAP embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] UMAP computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_tsne_embedding(params):
    """Get or compute t-SNE embedding with caching"""
    try:
        X, _ = _get_analysis_data()
        
        if X is None or X.shape[0] == 0:
            print(f"[ERROR] No data available for t-SNE computation", flush=True)
            return None
        
        # Adjust perplexity based on sample size (must be < n_samples)
        n_samples = X.shape[0]
        perplexity = min(params['perplexity'], (n_samples - 1) // 3)
        perplexity = max(perplexity, 5)  # Minimum perplexity of 5
        
        subset_key = 'full'
        if app_state.active_subset_indices is not None:
            subset_key = hash(tuple(sorted(list(app_state.active_subset_indices))))

        # Use adjusted perplexity in cache key
        key = ('tsne', perplexity, params['learning_rate'], params['random_state'], subset_key)
        
        if key in app_state.embedding_cache:
            print(f"[DEBUG] Cache HIT for t-SNE. Key: {key}", flush=True)
            result = app_state.embedding_cache[key]
            if result is not None:
                return result
        
        print(f"[DEBUG] Cache MISS for t-SNE. Computing with params: {params}, adjusted_perplexity={perplexity}", flush=True)
        
        # Validate learning_rate
        learning_rate = max(params['learning_rate'], 10)
        
        reducer = TSNE(
            n_components=params['n_components'],
            perplexity=perplexity,
            learning_rate=learning_rate,
            random_state=params['random_state'],
            verbose=0,
            n_jobs=-1
        )
        
        embedding = reducer.fit_transform(X)
        app_state.embedding_cache[key] = embedding
        app_state.last_embedding = embedding
        app_state.last_embedding_type = 'tSNE'
        print(f"[DEBUG] t-SNE embedding computed: shape {embedding.shape}", flush=True)
        return embedding
        
    except Exception as e:
        print(f"[ERROR] t-SNE computation failed: {e}", flush=True)
        traceback.print_exc()
        return None


def get_embedding(algorithm, umap_params=None, tsne_params=None, pca_params=None, robust_pca_params=None):
    """Get embedding based on selected algorithm"""
    if algorithm == 'UMAP':
        return get_umap_embedding(umap_params or CONFIG['umap_params'])
    elif algorithm == 'tSNE':
        return get_tsne_embedding(tsne_params or CONFIG['tsne_params'])
    elif algorithm == 'PCA':
        return get_pca_embedding(pca_params or CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42}))
    elif algorithm == 'RobustPCA':
        return get_robust_pca_embedding(robust_pca_params or CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42}))
    else:
        print(f"[ERROR] Unknown algorithm: {algorithm}")
        return None


def plot_embedding(group_col, algorithm, umap_params=None, tsne_params=None, pca_params=None, robust_pca_params=None, size=60):
    """Update plot with specified algorithm and parameters"""
    try:
        print(f"[DEBUG] plot_embedding called: algorithm={algorithm}, group_col={group_col}, size={size}", flush=True)
        
        if app_state.fig is None:
            print("[ERROR] Plot axes not initialized", flush=True)
            return False

        # Determine dimensions based on algorithm
        actual_algorithm = algorithm.strip().upper() if isinstance(algorithm, str) else str(algorithm)
        if actual_algorithm == 'ROBUSTPCA':
            actual_algorithm = 'RobustPCA' # Keep case for display
        if actual_algorithm in ('PB_MODELS_76', 'PB_MODELS_86'):
            actual_algorithm = 'PB_EVOL_76' if actual_algorithm.endswith('_76') else 'PB_EVOL_86'
        if actual_algorithm in ('ISOCHRON1', 'ISOCHRON2'):
            actual_algorithm = 'PB_EVOL_76' if actual_algorithm == 'ISOCHRON1' else 'PB_EVOL_86'

        target_dims = 2
        if actual_algorithm == 'TERNARY':
            target_dims = 'ternary'
            
        _ensure_axes(dimensions=target_dims)

        if app_state.ax is None:
            print("[ERROR] Failed to configure axes", flush=True)
            return False


        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        # Reserve space around the axes so the legend and titles are never clipped
        # try:
        #     app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
        # except Exception:
        #     pass

        # Manual styling removed in favor of scienceplots
        # app_state.fig.patch.set_facecolor("#f8fafc")
        # app_state.ax.set_facecolor("#ffffff")
        # app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.8)
        # app_state.ax.set_axisbelow(True)
        # for spine in app_state.ax.spines.values():
        #     spine.set_color("#cbd5f5")
        #     spine.set_linewidth(1.0)
        
        # Ensure parameters are provided
        if umap_params is None:
            umap_params = CONFIG['umap_params']
        if tsne_params is None:
            tsne_params = CONFIG['tsne_params']
        if pca_params is None:
            pca_params = CONFIG.get('pca_params', {'n_components': 2, 'random_state': 42})
        if robust_pca_params is None:
            robust_pca_params = CONFIG.get('robust_pca_params', {'n_components': 2, 'random_state': 42})
        
        print(f"[DEBUG] Using params - UMAP: {umap_params}, tSNE: {tsne_params}, PCA: {pca_params}, RobustPCA: {robust_pca_params}", flush=True)
        
        # Get embedding based on algorithm - normalize algorithm name
        embedding = None
        actual_algorithm = algorithm.strip().upper() if isinstance(algorithm, str) else str(algorithm)
        if actual_algorithm == 'ROBUSTPCA':
            actual_algorithm = 'RobustPCA' # Keep case for display
        if actual_algorithm in ('PB_MODELS_76', 'PB_MODELS_86'):
            actual_algorithm = 'PB_EVOL_76' if actual_algorithm.endswith('_76') else 'PB_EVOL_86'
        
        print(f"[DEBUG] Actual algorithm (normalized): {actual_algorithm}", flush=True)
        
        if actual_algorithm == 'UMAP':
            print(f"[DEBUG] Computing UMAP embedding", flush=True)
            embedding = get_umap_embedding(umap_params)
        elif actual_algorithm == 'TSNE':
            print(f"[DEBUG] Computing tSNE embedding", flush=True)
            embedding = get_tsne_embedding(tsne_params)
        elif actual_algorithm == 'PCA':
            print(f"[DEBUG] Computing PCA embedding", flush=True)
            embedding = get_pca_embedding(pca_params)
        elif actual_algorithm == 'RobustPCA':
            print(f"[DEBUG] Computing Robust PCA embedding", flush=True)
            embedding = get_robust_pca_embedding(robust_pca_params)
        elif actual_algorithm == 'V1V2':
            print(f"[DEBUG] Computing V1V2 embedding", flush=True)
            # V1V2 requires specific columns: 206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb
            # We need to find these columns in the dataset
            # Heuristic: Look for columns containing "206", "207", "208"
            
            if calculate_all_parameters is None:
                print("[ERROR] V1V2 module not loaded", flush=True)
                return False
                
            # Get data subset
            X, indices = _get_analysis_data()
            if X is None:
                return False
                
            # We need to map the columns in X to the required isotopes
            # app_state.data_cols contains the column names corresponding to columns in X
            cols = app_state.data_cols
            
            # Exact matching for prescribed headers
            col_206 = "206Pb/204Pb" if "206Pb/204Pb" in cols else None
            col_207 = "207Pb/204Pb" if "207Pb/204Pb" in cols else None
            col_208 = "208Pb/204Pb" if "208Pb/204Pb" in cols else None
            
            if not (col_206 and col_207 and col_208):
                print(f"[ERROR] Could not identify isotope columns in {cols}. Please ensure columns '206Pb/204Pb', '207Pb/204Pb', '208Pb/204Pb' are selected.", flush=True)
                return False
            
            # Extract data
            idx_206 = cols.index(col_206)
            idx_207 = cols.index(col_207)
            idx_208 = cols.index(col_208)
            
            pb206 = X[:, idx_206]
            pb207 = X[:, idx_207]
            pb208 = X[:, idx_208]
            
            try:
                # Get V1V2 parameters from state or engine
                v1v2_params = getattr(app_state, 'v1v2_params', {})
                scale = v1v2_params.get('scale', 1.0)
                # Pass None if not explicitly set in v1v2_params, to allow engine defaults
                a = v1v2_params.get('a')
                b = v1v2_params.get('b')
                c = v1v2_params.get('c')

                results = calculate_all_parameters(
                    pb206, pb207, pb208, 
                    calculate_ages=False,
                    a=a, b=b, c=c, scale=scale
                )
                v1 = results['V1']
                v2 = results['V2']
                embedding = np.column_stack((v1, v2))
                app_state.last_embedding = embedding
                app_state.last_embedding_type = 'V1V2'
            except Exception as e:
                print(f"[ERROR] V1V2 calculation failed: {e}", flush=True)
                return False
        
        # ISOCHRON modes removed; overlays now available in Pb evolution plots
        elif actual_algorithm in ('PB_EVOL_76', 'PB_EVOL_86',
                                  'PB_MU_AGE', 'PB_KAPPA_AGE'):
            print(f"[DEBUG] Computing Geochemistry embedding for {actual_algorithm}", flush=True)
            if geochemistry is None:
                print("[ERROR] Geochemistry module not loaded", flush=True)
                return False

            df_subset, indices = _get_subset_dataframe()
            if df_subset is None:
                return False

            col_206, col_207, col_208 = _get_pb_columns(df_subset.columns)
            if not (col_206 and col_207 and col_208):
                print("[ERROR] Geochemistry plots require 206Pb/204Pb, 207Pb/204Pb, 208Pb/204Pb columns.", flush=True)
                return False

            pb206 = pd.to_numeric(df_subset[col_206], errors='coerce').values
            pb207 = pd.to_numeric(df_subset[col_207], errors='coerce').values
            pb208 = pd.to_numeric(df_subset[col_208], errors='coerce').values

            if actual_algorithm in ('PB_MU_AGE', 'PB_KAPPA_AGE'):
                age_col = _find_age_column(df_subset.columns)
                if not age_col:
                    print("[ERROR] Age column not found for Mu/Kappa plots.", flush=True)
                    return False
                t_ma = pd.to_numeric(df_subset[age_col], errors='coerce').values

                if actual_algorithm == 'PB_MU_AGE':
                    mu_vals = geochemistry.calculate_mu_sk_model(pb206, pb207, t_ma)
                    embedding = np.column_stack((t_ma, mu_vals))
                else:
                    kappa_vals = geochemistry.calculate_kappa_sk_model(pb208, pb206, t_ma)
                    embedding = np.column_stack((t_ma, kappa_vals))
            else:
                if actual_algorithm == 'PB_EVOL_76':
                    embedding = np.column_stack((pb206, pb207))
                else:
                    embedding = np.column_stack((pb206, pb208))

            app_state.last_embedding = embedding
            app_state.last_embedding_type = actual_algorithm

        elif actual_algorithm == 'TERNARY':
            print(f"[DEBUG] Computing Ternary embedding", flush=True)
            cols = getattr(app_state, 'selected_ternary_cols', [])
            if not cols or len(cols) != 3:
                print("[ERROR] Ternary columns not selected", flush=True)
                return False
            
            try:
                # We need data rows corresponding to the analysis subset
                X, indices = _get_analysis_data()
                if indices is None: return False
                
                if app_state.df_global is None: return False
                
                # Fetch data directly from df using indices
                # Note: indices are integer locations in df_global if we map them right
                # But _get_analysis_data handles subset logic.
                # If subset is active, indices are the subset indices.
                # So df_global.iloc[indices] gives the rows.
                
                df_subset = app_state.df_global.iloc[indices]
                
                c_top, c_left, c_right = cols
                
                # Ensure columns exist
                missing = [c for c in cols if c not in df_subset.columns]
                if missing:
                    print(f"[ERROR] Missing columns for ternary plot: {missing}", flush=True)
                    return False
                    
                top_vals = pd.to_numeric(df_subset[c_top], errors='coerce').fillna(0).values
                left_vals = pd.to_numeric(df_subset[c_left], errors='coerce').fillna(0).values
                right_vals = pd.to_numeric(df_subset[c_right], errors='coerce').fillna(0).values
                
                # total/mask not needed here; normalization handled later
                # Standard Ternary Logic:
                # Just use raw values. mpltern or normalization handles the rest.
                # However, for meaningful ternary plotting of arbitrary data (e.g. isotopes),
                # we conceptually plot proportions: x / (x+y+z).
                # We do NOT perform min-max scaling specific to the data range, 
                # because the user requested "Standard Ternary Plot".
                # Standard means vertices are 100% (or 1.0).
                
                # We simply pass the raw values to mpltern.
                # mpltern expects (t, l, r). It will normalize them internally to sum to 1 for plotting position.
                # But to be safe and explicit, let's just pass raw.
                
                # Order matters:
                # If we want:
                # Top Axis -> Variable 1 (c_top)
                # Left Axis -> Variable 2 (c_left)
                # Right Axis -> Variable 3 (c_right)
                
                # In mpltern:
                # ax.scatter(t, l, r)
                # t correlates with Top Vertex.
                # l correlates with Left Vertex.
                # r correlates with Right Vertex.
                
                embedding = np.column_stack((top_vals, left_vals, right_vals))
                app_state.last_embedding = embedding
                app_state.last_embedding_type = 'TERNARY'
                
                # Clear manual ranges if any, to avoid confusion in plotting
                if hasattr(app_state, 'ternary_manual_ranges'):
                    del app_state.ternary_manual_ranges
                if hasattr(app_state, 'ternary_ranges'):
                    del app_state.ternary_ranges

            except Exception as e:

                print(f"[ERROR] Ternary calculation failed: {e}", flush=True)
                traceback.print_exc()
                return False
        else:
            print(f"[ERROR] Unknown algorithm: {algorithm}", flush=True)
            return False
            
        if embedding is None:
            print(f"[ERROR] Failed to compute {algorithm} embedding", flush=True)
            return False
        
        # Determine which data subset we are plotting
        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_source = app_state.df_global.iloc[indices_to_plot].copy()
        else:
            indices_to_plot = list(range(len(app_state.df_global)))
            df_source = app_state.df_global.copy()

        if embedding.shape[0] != len(df_source):
            print(f"[ERROR] Embedding size {embedding.shape[0]} does not match data size {len(df_source)}", flush=True)
            return False
        
        def _reset_plot_dataframe():
            base = df_source
            if group_col not in base.columns:
                return None
            base[group_col] = base[group_col].fillna('Unknown').astype(str)
            try:
                # Use selected components for PCA/RobustPCA if available
                if actual_algorithm == 'TERNARY':
                    base['_emb_t'] = embedding[:, 0]
                    base['_emb_l'] = embedding[:, 1]
                    base['_emb_r'] = embedding[:, 2]
                elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
                    idx_x = app_state.pca_component_indices[0]
                    idx_y = app_state.pca_component_indices[1]
                    
                    # Ensure indices are within bounds
                    n_comps = embedding.shape[1]
                    if idx_x >= n_comps: idx_x = 0
                    if idx_y >= n_comps: idx_y = 1 if n_comps > 1 else 0
                    
                    base['_emb_x'] = embedding[:, idx_x]
                    base['_emb_y'] = embedding[:, idx_y]
                    print(f"[DEBUG] Plotting components {idx_x+1} and {idx_y+1}", flush=True)
                else:
                    base['_emb_x'] = embedding[:, 0]
                    base['_emb_y'] = embedding[:, 1]
            except Exception as emb_error:
                print(f"[ERROR] Unable to align embedding with data: {emb_error}", flush=True)
                return None
            return base

        df_plot = _reset_plot_dataframe()
        if df_plot is None:
            print(f"[ERROR] Unable to prepare plotting data for column: {group_col}", flush=True)
            return False
        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False

        all_groups = sorted(df_plot[group_col].unique())
        app_state.available_groups = all_groups

        visible_groups = app_state.visible_groups
        if visible_groups:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not mask.any():
                print("[INFO] No data matches the selected legend filter; showing all groups instead.", flush=True)
                app_state.visible_groups = None
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    print("[INFO] Filtered 3D data is empty; showing all groups instead.", flush=True)
                    df_plot = _reset_plot_dataframe()
                    if df_plot is None:
                        return False
                    app_state.visible_groups = None
                    app_state.available_groups = sorted(df_plot[group_col].unique())

        unique_cats = sorted(df_plot[group_col].unique())
        print(f"[DEBUG] Unique categories in {group_col}: {unique_cats}", flush=True)
        
        # Build palette while preserving user overrides
        new_palette = _build_group_palette(unique_cats)
        
        # Initialize custom ternary plot settings
        if actual_algorithm == 'TERNARY':
            t_cols = getattr(app_state, 'selected_ternary_cols', ['Top', 'Left', 'Right'])
            
            # Draw Triangle Boundary
            # Vertices: Left (0,0), Right (1,0), Top (0.5, sqrt(3)/2)
            # But we must respect the physical Scale for axis ticks.
            h = np.sqrt(3) / 2
            
            # Triangle Vertices in Cartesian coords (x,y)
            # Left corner (Left component=scale, others=0) -> (0,0) ? No.
            # Standard Ternary Plot definition:
            # Axis 1 (Top): T
            # Axis 2 (Left): L
            # Axis 3 (Right): R
            # Coordinates (t, l, r) where sum = Scale.
            # Basis vectors:
            # Let's use normalized basis (sum=1), then scale by Scale.
            # Origin at Left vertex (L=1, T=0, R=0)? No.
            # Let's stick to the standard symmetric equilateral triangle.
            # Bottom-Left: (0, 0) -> Corresponds to Left=Scale check?
            # Actually let's assume standard orientation:
            # Left (0, 0), Right (1, 0), Top (0.5, h).
            # If normalized composition is (t, l, r) with sum 1:
            # x = 0.5 * t + 1.0 * r
            # y = h * t
            # Note: l (Left) is "implicit" at (0,0).
            # At Top (t=1), x=0.5, y=h. Correct.
            # At Right (r=1), x=1, y=0. Correct.
            # At Left (l=1 => t=0, r=0), x=0, y=0. Correct.
            
            # Draw Boundary
            app_state.ax.plot([0, 1, 0.5, 0], [0, 0, h, 0], 'k-', linewidth=1.5, zorder=0)

            # Draw Ternary Grid (standard geochemical style)
            # Grid for levels 0.1..0.9 (Top, Left, Right)
            grid_color = '#e2e8f0'
            for i in range(1, 10):
                val = i * 0.1
                # Constant Top (t=val)
                app_state.ax.plot([val*0.5, 1 - val*0.5], [val*h, val*h], '-', color=grid_color, lw=0.6, zorder=0)

                # Constant Left (l=val)
                x1, y1 = (1 - val), 0
                x2, y2 = (0.5 * (1 - val)), h * (1 - val)
                app_state.ax.plot([x1, x2], [y1, y2], '-', color=grid_color, lw=0.6, zorder=0)

                # Constant Right (r=val)
                x3, y3 = val, 0
                x4, y4 = (0.5 + 0.5 * val), h * (1 - val)
                app_state.ax.plot([x3, x4], [y3, y4], '-', color=grid_color, lw=0.6, zorder=0)
            
            # Labels
            app_state.ax.text(0.5, h + 0.05, t_cols[0], ha='center', va='bottom', fontsize=10, fontweight='bold')
            app_state.ax.text(-0.05, -0.05, t_cols[1], ha='right', va='top', fontsize=10, fontweight='bold')
            app_state.ax.text(1.05, -0.05, t_cols[2], ha='left', va='top', fontsize=10, fontweight='bold')
            
            # Remove axes
            app_state.ax.axis('off')
            app_state.ax.set_aspect('equal')
            
            # Adjust limits slightly to fit labels
            app_state.ax.set_xlim(-0.1, 1.1)
            app_state.ax.set_ylim(-0.1, h + 0.1)

        # Kernel Density Estimation (KDE)
        if getattr(app_state, 'show_kde', False):
            try:
                # For Ternary, we need to pre-calculate cartesian coordinates
                if actual_algorithm == 'TERNARY':
                    print("[INFO] Generating KDE for Ternary Plot...", flush=True)
                    # Iterate groups to apply same normalization logic as scatter
                    for cat in unique_cats:
                        subset = df_plot[df_plot[group_col] == cat].copy()
                        if subset.empty: continue
                        
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
                        
                        sns.kdeplot(
                            x=x_cart, y=y_cart,
                            color=new_palette[cat],
                            ax=app_state.ax,
                            levels=10, fill=True, alpha=0.6,
                            warn_singular=False,
                            legend=False, zorder=1
                        )
                else:
                    # Standard 2D KDE
                    print(f"[INFO] Generating KDE for {actual_algorithm}...", flush=True)
                    sns.kdeplot(
                        data=df_plot,
                        x='_emb_x',
                        y='_emb_y',
                        hue=group_col,
                        palette=new_palette,
                        ax=app_state.ax,
                        levels=10, fill=True, alpha=0.6,
                        warn_singular=False,
                        legend=False,
                        zorder=1
                    )
            except Exception as kde_err:
                print(f"[WARN] Failed to render KDE: {kde_err}", flush=True)

        scatters = []
        is_kde_mode = getattr(app_state, 'show_kde', False)
        
        # If KDE is not active, we draw scatters normally.
        # If KDE IS active, we SKIP drawing scatters to achieve the "heatmap only" look requested.
        
        for i, cat in enumerate(unique_cats):
            if is_kde_mode:
                continue

            try:
                subset = df_plot[df_plot[group_col] == cat]
                if subset.empty:
                    continue
                indices = subset.index.tolist()
                
                # Check algorithm type for appropriate coordinate usage
                if actual_algorithm == 'TERNARY':
                    ts = subset['_emb_t'].to_numpy(dtype=float, copy=False)
                    ls = subset['_emb_l'].to_numpy(dtype=float, copy=False)
                    rs = subset['_emb_r'].to_numpy(dtype=float, copy=False)
                    
                    if len(ts) == 0: continue
                    
                    # No explicit normalization (user requested raw values)
                    # We rely on 'scale' being set correctly above to accommodate the data range.
                    valid_indices = indices

                    # Apply axis scaling factors
                    # REMOVED: User requested to remove manual axis factors. We now only rely on raw data 
                    # or the "Stretch to Fill" option.
                    t_vals = ts
                    l_vals = ls
                    r_vals = rs

                    # Apply compositional stretching if enabled
                    t_vals, l_vals, r_vals = _apply_ternary_stretch(t_vals, l_vals, r_vals)

                    # Normalize to sum to 1.0
                    sums = t_vals + l_vals + r_vals
                    # Avoid division by zero
                    with np.errstate(divide='ignore', invalid='ignore'):
                        sums[sums == 0] = 1.0 
                        
                        # Normalize components
                        t_norm = t_vals / sums
                        l_norm = l_vals / sums
                        r_norm = r_vals / sums

                    # Cartesian Mapping
                    # x = 0.5 * t + 1.0 * r
                    # y = (sqrt(3)/2) * t
                    
                    h = np.sqrt(3) / 2
                    x_cart = 0.5 * t_norm + 1.0 * r_norm
                    y_cart = h * t_norm

                    marker_size = getattr(app_state, 'plot_marker_size', size)
                    marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                    color = app_state.current_palette[cat]
                    
                    # Manual scatter using matplotlib
                    sc = app_state.ax.scatter(
                        x_cart, y_cart,
                        label=cat, color=color, s=marker_size,
                        alpha=marker_alpha,
                        edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                        linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                        zorder=2,
                        picker=5
                    )
                    
                    # Store metadata for tooltips
                    # Note: We store (x,y) cartesian coords for picking logic
                    # We might want to store original ternary coords too if needed for display
                    offsets = sc.get_offsets()
                    sc.indices = valid_indices
                    scatters.append(sc)
                    
                    for j, idx in enumerate(valid_indices):
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
                    
                    # Use marker size/alpha from state if available, else default
                    marker_size = getattr(app_state, 'plot_marker_size', size)
                    marker_alpha = getattr(app_state, 'plot_marker_alpha', 0.88)
                    
                    color = app_state.current_palette[cat]
                    sc = app_state.ax.scatter(
                        xs, ys, label=cat, color=color, s=marker_size,
                        alpha=marker_alpha,
                        edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                        linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                        zorder=2,
                        picker=5
                    )
                    
                    # Store coordinate-to-index mapping with explicit float conversion
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
                
                # Note: Group-level ellipses are disabled in favor of selection-based ellipses
                # to avoid clutter with large datasets.
                # if app_state.show_ellipses:
                #     try:
                #         draw_confidence_ellipse(xs, ys, app_state.ax, edgecolor=palette[i], zorder=1)
                #     except Exception as e:
                #         print(f"[WARN] Failed to draw ellipse for group {cat}: {e}", flush=True)

            except Exception as e:
                print(f"[WARN] Error plotting category {cat}: {e}", flush=True)
                continue
        
        if not scatters and not is_kde_mode:
            print("[ERROR] No data points plotted", flush=True)
            return False
            
        # Create legend
        try:
            # If KDE mode, construct proxy handles for the legend
            handles = []
            labels = []
            
            if is_kde_mode:
                from matplotlib.patches import Patch
                for cat in unique_cats:
                    color = app_state.current_palette[cat]
                    patch = Patch(facecolor=color, edgecolor='none', label=cat, alpha=0.6)
                    handles.append(patch)
                    labels.append(cat)
            else:
                # Standard scatter handles are handled automatically by ax.legend() if scatters exist? 
                # Or we let legend() gather them but we need to ensure order?
                # The original code relied on auto-detection or order.
                pass

            # Only show matplotlib legend if item count is reasonable
            if len(unique_cats) <= 30:
                ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if len(unique_cats) > 15 else 1)
                
                # If explicit handles created (KDE mode), pass them
                if handles:
                    legend = app_state.ax.legend(
                        handles=handles, labels=labels,
                        title=group_col, bbox_to_anchor=(1.01, 1), loc='upper left',
                        frameon=True, fancybox=True,
                        ncol=ncol
                    )
                else:
                    legend = app_state.ax.legend(
                        title=group_col, bbox_to_anchor=(1.01, 1), loc='upper left',
                        frameon=True, fancybox=True,
                        ncol=ncol
                    )

                try:
                    legend.set_bbox_to_anchor((1.01, 1), transform=app_state.ax.transAxes)
                except Exception:
                    pass

                frame = legend.get_frame()
                frame.set_facecolor("#ffffff")
                frame.set_edgecolor("#cbd5f5")
                frame.set_alpha(0.95)
                
                if not is_kde_mode:
                    for leg_patch, sc in zip(legend.get_patches(), scatters):
                        app_state.legend_to_scatter[leg_patch] = sc
            else:
                print("[INFO] Too many categories for standard legend. Use Control Panel legend.", flush=True)
        except Exception as e:
            print(f"[WARN] Legend creation error: {e}", flush=True)
        
        # Build title with algorithm info
        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        
        if actual_algorithm == 'UMAP':
            title = f'Embedding - UMAP{subset_info} (n_neighbors={umap_params["n_neighbors"]}, min_dist={umap_params["min_dist"]})\nColored by {group_col}'
        elif actual_algorithm == 'TSNE':
            title = f'Embedding - t-SNE{subset_info} (perplexity={tsne_params["perplexity"]}, lr={tsne_params["learning_rate"]})\nColored by {group_col}'
        elif actual_algorithm == 'PCA':
            title = f'Embedding - PCA{subset_info} (n_components={pca_params["n_components"]})\nColored by {group_col}'
        elif actual_algorithm == 'RobustPCA':
            title = f'Embedding - Robust PCA{subset_info} (n_components={robust_pca_params["n_components"]})\nColored by {group_col}'
        elif actual_algorithm == 'V1V2':
            title = f'Geochem - V1-V2 Diagram{subset_info}\nColored by {group_col}'
        # ISOCHRON modes removed
        elif actual_algorithm == 'TERNARY':
            title = f'Raw - Ternary Plot{subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PB_EVOL_76':
            title = f'Geochem - Pb Evolution / Model Curves (206-207){subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PB_EVOL_86':
            title = f'Geochem - Pb Evolution / Model Curves (206-208){subset_info}\nColored by {group_col}'
        # PB_MODEL_AGE removed
        elif actual_algorithm == 'PB_MU_AGE':
            title = f'Geochem - Mu vs Age{subset_info}\nColored by {group_col}'
        elif actual_algorithm == 'PB_KAPPA_AGE':
            title = f'Geochem - Kappa vs Age{subset_info}\nColored by {group_col}'
        else:
            title = f'{actual_algorithm}{subset_info}\nColored by {group_col}'
        
        # Smart Title Font Logic
        # If title contains CJK characters, prioritize the CJK font to avoid mojibake
        title_font_dict = {}
        
        has_cjk = any('\u4e00' <= char <= '\u9fff' for char in title)
        if has_cjk:
            cjk_font = getattr(app_state, 'custom_cjk_font', '')
            if cjk_font:
                title_font_dict['fontname'] = cjk_font
            else:
                # Try to find a preferred CJK font from config that is installed
                # This is a best-effort fallback if user hasn't selected one
                try:
                    available = {f.name for f in font_manager.fontManager.ttflist}
                    for f in CONFIG.get('preferred_plot_fonts', []):
                        if f in available:
                            title_font_dict['fontname'] = f
                            break
                except Exception:
                    pass

        app_state.ax.set_title(title, pad=20, **title_font_dict)
        
        # Set axis labels
        if actual_algorithm == 'V1V2':
            app_state.ax.set_xlabel("V1")
            app_state.ax.set_ylabel("V2")
        elif actual_algorithm == 'PB_EVOL_76':
            app_state.ax.set_xlabel("206Pb/204Pb")
            app_state.ax.set_ylabel("207Pb/204Pb")
        elif actual_algorithm in ('PB_EVOL_86',):
            app_state.ax.set_xlabel("206Pb/204Pb")
            app_state.ax.set_ylabel("208Pb/204Pb")
        elif actual_algorithm == 'PB_MU_AGE':
            app_state.ax.set_xlabel("Age (Ma)")
            app_state.ax.set_ylabel("Mu (238U/204Pb)")
        elif actual_algorithm == 'PB_KAPPA_AGE':
            app_state.ax.set_xlabel("Age (Ma)")
            app_state.ax.set_ylabel("Kappa (232Th/238U)")
        elif actual_algorithm == 'TERNARY':
            # Labels and Grid handled by python-ternary wrapper above
            # We don't need additional labels here as corner labels are set on 'tax'
            
            # Ensure equilateral aspect ratio for the underlying axes to prevent distortion
            app_state.ax.set_aspect('equal')
            
            # Explicitly force a label redraw to fix potential positioning issues
            # This is a documented workaround in python-ternary for some environments
            # try:
            #     if tax:
            #         tax._redraw_labels()
            # except Exception as e:
            #     print(f"[WARN] Failed to redraw ternary labels: {e}", flush=True)

            # Remove custom Auto Zoom Logic to adhere to strict ternary lib usage.
            # python-ternary displays the full simplex by default.
            pass



        elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
            idx_x = app_state.pca_component_indices[0] + 1
            idx_y = app_state.pca_component_indices[1] + 1
            app_state.ax.set_xlabel(f"PC{idx_x}")
            app_state.ax.set_ylabel(f"PC{idx_y}")
        else:
            app_state.ax.set_xlabel(f"{actual_algorithm} Dimension 1")
            app_state.ax.set_ylabel(f"{actual_algorithm} Dimension 2")

        # Geochemistry overlays
        if actual_algorithm in ('PB_EVOL_76', 'PB_EVOL_86'):
            params = geochemistry.engine.get_parameters() if geochemistry else {}
            if getattr(app_state, 'show_model_curves', True):
                params_list = [params]
                _draw_model_curves(app_state.ax, actual_algorithm, params_list)

            if getattr(app_state, 'show_isochrons', True) or getattr(app_state, 'show_growth_curves', True):
                _draw_isochron_overlays(app_state.ax, actual_algorithm)

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
        
        app_state.ax.tick_params()
        
        # Adjust layout to prevent overlap
        try:
            # app_state.fig.tight_layout()
            # Re-adjust margins after tight_layout to ensure legend space
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass
        
        # Initialize annotation (always recreate after ax.clear())
        app_state.annotation = app_state.ax.annotate(
            "", xy=(0, 0), xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass
        
        # Restore selection overlay if available
        if refresh_selection_overlay:
            try:
                refresh_selection_overlay()
            except Exception as e:
                print(f"[WARN] Failed to restore selection overlay: {e}", flush=True)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Plot update failed: {e}")
        traceback.print_exc()
        return False


# Keep backward compatibility
def plot_umap(group_col, params, size):
    """Deprecated: Use plot_embedding instead"""
    return plot_embedding(group_col, 'UMAP', umap_params=params, size=size)


def plot_2d_data(group_col, data_columns, size=60, show_kde=False):
    """Render a 2D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            print("[ERROR] Plot figure not initialized", flush=True)
            return False

        if not data_columns or len(data_columns) != 2:
            print("[ERROR] Exactly two data columns are required for a 2D scatter plot", flush=True)
            return False

        if app_state.df_global is None or len(app_state.df_global) == 0:
            print("[WARN] No data available for plotting", flush=True)
            return False

        missing = [col for col in data_columns if col not in app_state.df_global.columns]
        if missing:
            print(f"[ERROR] Missing columns for 2D plot: {missing}", flush=True)
            return False

        _ensure_axes(dimensions=2)

        if app_state.ax is None:
            print("[ERROR] Failed to configure 2D axes", flush=True)
            return False

        # Determine which data subset we are plotting
        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_plot = app_state.df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = app_state.df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            print("[WARN] No complete rows available for the selected 2D columns", flush=True)
            return False

        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False

        # Ensure data columns are numeric for KDE and Plotting
        try:
            for col in data_columns:
                df_plot[col] = pd.to_numeric(df_plot[col], errors='coerce')
            
            # Drop rows that became NaN after strict numeric conversion to avoid KDE errors
            df_plot = df_plot.dropna(subset=data_columns)
            
            if df_plot.empty:
                print("[WARN] No valid numeric data available for 2D plot.", flush=True)
                return False
        except Exception as e:
            print(f"[ERROR] Failed to convert columns to numeric: {e}", flush=True)
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        all_groups = sorted(df_plot[group_col].unique())
        app_state.available_groups = all_groups

        visible_groups = app_state.visible_groups
        if visible_groups:
            allowed = set(visible_groups)
            mask = df_plot[group_col].isin(allowed)
            if not mask.any():
                print("[INFO] No 2D data matches the selected legend filter; reverting to all groups.", flush=True)
                app_state.visible_groups = None
            else:
                df_plot = df_plot[mask].copy()
                if df_plot.empty:
                    print("[INFO] Filtered 2D data is empty; reverting to all groups.", flush=True)
                    df_plot = app_state.df_global.dropna(subset=data_columns).copy()
                    df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)
                    app_state.visible_groups = None
                    all_groups = sorted(df_plot[group_col].unique())
                    app_state.available_groups = all_groups

        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        try:
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass

        # Manual styling removed in favor of scienceplots
        # app_state.fig.patch.set_facecolor("#f8fafc")
        # app_state.ax.set_facecolor("#ffffff")
        # app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.8)
        # app_state.ax.set_axisbelow(True)
        # for spine in app_state.ax.spines.values():
        #     spine.set_color("#cbd5f5")
        #     spine.set_linewidth(1.0)

        unique_cats = sorted(df_plot[group_col].unique())
        
        # Build palette while preserving user overrides
        new_palette = _build_group_palette(unique_cats)

        if show_kde:
            try:
                sns.kdeplot(
                    data=df_plot,
                    x=data_columns[0],
                    y=data_columns[1],
                    hue=group_col,
                    palette=new_palette,
                    ax=app_state.ax,
                    levels=10, fill=True, alpha=0.6,
                    warn_singular=False,
                    legend=False,
                    zorder=1
                )
            except Exception as e:
                print(f"[WARN] Failed to render KDE: {e}", flush=True)

        scatters = []
        
        # If Active 2D KDE mode, skip scatter plots
        if not show_kde:
            for i, cat in enumerate(unique_cats):
                subset = df_plot[df_plot[group_col] == cat]
                if subset.empty:
                    continue

                xs = subset[data_columns[0]].astype(float).values
                ys = subset[data_columns[1]].astype(float).values
                indices = subset.index.tolist()
                
                color = app_state.current_palette[cat]

                sc = app_state.ax.scatter(
                    xs,
                    ys,
                    label=cat,
                    color=color,
                    s=size,
                    alpha=0.88,
                    edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                    linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                    zorder=2
                )
                app_state.scatter_collections.append(sc)
                scatters.append(sc)
                app_state.group_to_scatter[cat] = sc

                # Note: Group-level ellipses are disabled in favor of selection-based ellipses
                # if app_state.show_ellipses:
                #     try:
                #         draw_confidence_ellipse(xs, ys, app_state.ax, edgecolor=palette[i], zorder=1)
                #     except Exception as e:
                #         print(f"[WARN] Failed to draw ellipse for group {cat}: {e}", flush=True)

                for j, idx in enumerate(indices):
                    key = (round(float(xs[j]), 3), round(float(ys[j]), 3))
                    app_state.sample_index_map[key] = idx
                    app_state.sample_coordinates[idx] = (float(xs[j]), float(ys[j]))
                    app_state.artist_to_sample[(id(sc), j)] = idx

        if not scatters and not show_kde:
            print("[ERROR] No points were plotted in 2D", flush=True)
            return False

        try:
            # Prepare Legend
            handles = []
            labels = []
            
            if show_kde:
                from matplotlib.patches import Patch
                for cat in unique_cats:
                    if cat not in app_state.current_palette: continue
                    color = app_state.current_palette[cat]
                    patch = Patch(facecolor=color, edgecolor='none', label=cat, alpha=0.6)
                    handles.append(patch)
                    labels.append(cat)
            
            if len(unique_cats) <= 30:
                ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if len(unique_cats) > 15 else 1)
                
                # Use handles if available, otherwise just call legend which picks up scatters automatically
                if handles:
                    legend = app_state.ax.legend(
                        handles=handles, labels=labels,
                        title=group_col,
                        bbox_to_anchor=(1.01, 1),
                        loc='upper left',
                        frameon=True,
                        fancybox=True,
                        ncol=ncol
                    )
                else:
                    # For scatter plots, calling legend without handles picks up artists with labels automatically
                    legend = app_state.ax.legend(
                        title=group_col,
                        bbox_to_anchor=(1.01, 1),
                        loc='upper left',
                        frameon=True,
                        fancybox=True,
                        ncol=ncol
                    )
                
                # Check if legend was actually created (migth fail if no labeled artists)
                if legend:
                    try:
                        legend.set_bbox_to_anchor((1.01, 1), transform=app_state.ax.transAxes)
                        frame = legend.get_frame()
                        frame.set_facecolor("#ffffff")
                        frame.set_edgecolor("#cbd5f5")
                        frame.set_alpha(0.95)
                        
                        if not show_kde:
                            # Map legend items to scatter collections for interactivity
                            for leg_patch, sc in zip(legend.get_patches(), scatters):
                                app_state.legend_to_scatter[leg_patch] = sc
                    except Exception as e:
                        print(f"[WARN] Legend styling failed: {e}", flush=True)

            else:
                print("[INFO] Too many categories for standard legend. Use Control Panel legend.", flush=True)

        except Exception as legend_err:
            print(f"[WARN] 2D legend creation error: {legend_err}", flush=True)

        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        title = (
            f"2D Scatter Plot{subset_info} ({data_columns[0]} vs {data_columns[1]})\n"
            f"Colored by {group_col}"
        )
        app_state.ax.set_title(title, pad=20)
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.tick_params()
        
        # Adjust layout to prevent overlap
        try:
            # app_state.fig.tight_layout()
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass


        app_state.annotation = app_state.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(20, 20),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#cbd5e1", alpha=0.95),
            arrowprops=dict(arrowstyle="->", color="#475569"),
            zorder=15
        )
        app_state.annotation.set_visible(False)
        try:
            if app_state.annotation.arrow_patch is not None:
                app_state.annotation.arrow_patch.set_zorder(14)
        except Exception:
            pass

        return True

    except Exception as err:
        print(f"[ERROR] 2D plot failed: {err}", flush=True)
        traceback.print_exc()
        return False


def plot_3d_data(group_col, data_columns, size=60):
    """Render a 3D scatter plot using selected raw measurement columns."""
    try:
        if app_state.fig is None:
            print("[ERROR] Plot figure not initialized", flush=True)
            return False

        if not data_columns or len(data_columns) != 3:
            print("[ERROR] Exactly three data columns are required for a 3D scatter plot", flush=True)
            return False

        if app_state.df_global is None or len(app_state.df_global) == 0:
            print("[WARN] No data available for plotting", flush=True)
            return False

        missing = [col for col in data_columns if col not in app_state.df_global.columns]
        if missing:
            print(f"[ERROR] Missing columns for 3D plot: {missing}", flush=True)
            return False

        _ensure_axes(dimensions=3)

        if app_state.ax is None:
            print("[ERROR] Failed to configure 3D axes", flush=True)
            return False

        # Determine which data subset we are plotting
        if app_state.active_subset_indices is not None:
            indices_to_plot = sorted(list(app_state.active_subset_indices))
            df_plot = app_state.df_global.iloc[indices_to_plot].dropna(subset=data_columns).copy()
        else:
            df_plot = app_state.df_global.dropna(subset=data_columns).copy()

        if df_plot.empty:
            print("[WARN] No complete rows available for the selected 3D columns", flush=True)
            return False

        if group_col not in df_plot.columns:
            print(f"[ERROR] Column not found: {group_col}", flush=True)
            return False

        df_plot[group_col] = df_plot[group_col].fillna('Unknown').astype(str)

        # Apply style before clearing
        _apply_current_style()

        app_state.ax.clear()
        _enforce_plot_style(app_state.ax)
        app_state.clear_plot_state()

        # Manual styling removed in favor of scienceplots
        # app_state.fig.patch.set_facecolor("#f8fafc")
        # app_state.ax.set_facecolor("#ffffff")
        # app_state.ax.grid(True, color="#e2e8f0", linewidth=0.7, alpha=0.6)

        unique_cats = sorted(df_plot[group_col].unique())

        new_palette = _build_group_palette(unique_cats)

        for i, cat in enumerate(unique_cats):
            subset = df_plot[df_plot[group_col] == cat]
            if subset.empty:
                continue

            xs = subset[data_columns[0]].astype(float).values
            ys = subset[data_columns[1]].astype(float).values
            zs = subset[data_columns[2]].astype(float).values

            sc = app_state.ax.scatter(
                xs,
                ys,
                zs,
                label=cat,
                color=app_state.current_palette[cat],
                s=size,
                alpha=0.85,
                edgecolors=getattr(app_state, 'scatter_edgecolor', '#1e293b'),
                linewidth=getattr(app_state, 'scatter_edgewidth', 0.4),
                zorder=2
            )
            app_state.scatter_collections.append(sc)

        if not app_state.scatter_collections:
            print("[ERROR] No points were plotted in 3D", flush=True)
            return False

        try:
            if len(unique_cats) <= 30:
                ncol = app_state.legend_columns if getattr(app_state, 'legend_columns', 0) > 0 else (2 if len(unique_cats) > 15 else 1)
                legend = app_state.ax.legend(
                    title=group_col,
                    bbox_to_anchor=(1.01, 1),
                    loc='upper left',
                    frameon=True,
                    fancybox=True,
                    ncol=ncol
                )
                legend.set_bbox_to_anchor((1.01, 1), transform=app_state.ax.transAxes)
                frame = legend.get_frame()
                frame.set_facecolor("#ffffff")
                frame.set_edgecolor("#cbd5f5")
                frame.set_alpha(0.95)
            else:
                print("[INFO] Too many categories for standard legend. Use Control Panel legend.", flush=True)
        except Exception as legend_err:
            print(f"[WARN] 3D legend creation error: {legend_err}", flush=True)

        subset_info = " (Subset)" if app_state.active_subset_indices is not None else ""
        title = (
            f"3D Scatter Plot{subset_info} ({data_columns[0]}, {data_columns[1]}, {data_columns[2]})\n"
            f"Colored by {group_col}"
        )
        app_state.ax.set_title(title, pad=20)
        app_state.ax.set_xlabel(data_columns[0])
        app_state.ax.set_ylabel(data_columns[1])
        app_state.ax.set_zlabel(data_columns[2])
        
        # Adjust layout to prevent overlap
        try:
            # app_state.fig.tight_layout()
            # app_state.fig.subplots_adjust(left=0.05, bottom=0.08, right=0.85, top=0.88)
            pass
        except Exception:
            pass

        # Disable 2D annotations for 3D renderings
        app_state.annotation = None
        return True

    except Exception as err:
        print(f"[ERROR] 3D plot failed: {err}", flush=True)
        traceback.print_exc()
        return False


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








    



