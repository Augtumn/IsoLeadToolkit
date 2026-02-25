"""Event handlers for user interactions (hover, click, legend)."""
from __future__ import annotations

import logging

import matplotlib
import numpy as np
import pandas as pd
import scipy.stats
from matplotlib.patches import Ellipse
from matplotlib.path import Path
from matplotlib.widgets import RectangleSelector, LassoSelector

from core import app_state, translate
from visualization.plotting.isochron import resolve_isochron_errors as _resolve_isochron_errors

logger = logging.getLogger(__name__)

# Minimum box size to register a rectangle selection (data units)
_SELECTION_MIN_SPAN = 1e-9
# Maximum distance (data units) for hover nearest-neighbor lookup
_HOVER_DISTANCE_THRESHOLD = 0.15

def draw_confidence_ellipse(x, y, ax, confidence: float = 0.95, facecolor: str = 'none', **kwargs) -> Ellipse | None:
    """
    Create a plot of the covariance confidence ellipse of *x* and *y*.
    confidence: float, e.g. 0.95 for 95% confidence interval
    """
    if x.size < 2 or y.size < 2:
        return None

    # Calculate n_std based on confidence level for 2D (Chi-squared with 2 DoF)
    # ppf is the inverse of cdf
    chi2_val = scipy.stats.chi2.ppf(confidence, df=2)
    n_std = np.sqrt(chi2_val)

    cov = np.cov(x, y)
    if not np.all(np.isfinite(cov)):
        return None

    var_x = cov[0, 0]
    var_y = cov[1, 1]
    if var_x <= 0 or var_y <= 0:
        return None

    pearson = cov[0, 1] / np.sqrt(var_x * var_y)
    pearson = float(np.clip(pearson, -1.0, 1.0))
    
    ell_radius_x = np.sqrt(1 + pearson)
    ell_radius_y = np.sqrt(1 - pearson)
    
    ellipse = Ellipse((0, 0), width=ell_radius_x * 2, height=ell_radius_y * 2,
                      facecolor=facecolor, **kwargs)

    scale_x = np.sqrt(cov[0, 0]) * n_std
    mean_x = np.mean(x)
    scale_y = np.sqrt(cov[1, 1]) * n_std
    mean_y = np.mean(y)

    theta = 0.5 * np.arctan2(2 * cov[0, 1], var_x - var_y)
    transf = (
        matplotlib.transforms.Affine2D()
        .rotate(theta)
        .scale(scale_x, scale_y)
        .translate(mean_x, mean_y)
    )

    ellipse.set_transform(transf + ax.transData)
    return ax.add_patch(ellipse)


def _notify_selection_ui():
    """Ask the control panel to refresh selection-related widgets."""
    panel = getattr(app_state, 'control_panel_ref', None)
    if panel is None:
        return

    update_fn = getattr(panel, 'update_selection_controls', None)
    if not callable(update_fn):
        return

    try:
        update_fn()
    except Exception as err:
        logger.warning("Unable to update selection controls: %s", err)


def _disable_rectangle_selector():
    selector = getattr(app_state, 'rectangle_selector', None)
    if selector is None:
        return
    try:
        selector.set_active(False)
    except Exception:
        pass


def _disable_lasso_selector():
    selector = getattr(app_state, 'lasso_selector', None)
    if selector is None:
        return
    try:
        selector.set_active(False)
    except Exception:
        pass


def _ensure_rectangle_selector():
    if not app_state.selection_mode or app_state.render_mode == '3D':
        _disable_rectangle_selector()
        return

    if app_state.selection_tool == 'lasso':
        _disable_rectangle_selector()
        return

    if app_state.ax is None:
        return

    selector = getattr(app_state, 'rectangle_selector', None)

    if selector is not None:
        try:
            # If the selector is bound to a different axes, rebuild it
            if getattr(selector, 'ax', None) is not app_state.ax:
                try:
                    selector.disconnect_events()
                except Exception:
                    pass
                app_state.rectangle_selector = None
                selector = None
            else:
                selector.set_active(True)
        except Exception:
            app_state.rectangle_selector = None
            selector = None

    if selector is None:
        try:
            app_state.rectangle_selector = RectangleSelector(
                app_state.ax,
                _handle_rectangle_select,
                useblit=True,
                button=[1],
                spancoords='data',
                interactive=False
            )
        except Exception as err:
            logger.warning("Unable to initialize rectangle selector: %s", err)
            app_state.rectangle_selector = None


def _ensure_lasso_selector():
    if not app_state.selection_mode or app_state.render_mode == '3D':
        _disable_lasso_selector()
        return

    if app_state.selection_tool != 'lasso':
        _disable_lasso_selector()
        return

    if app_state.ax is None:
        return

    selector = getattr(app_state, 'lasso_selector', None)

    if selector is not None:
        try:
            if getattr(selector, 'ax', None) is not app_state.ax:
                try:
                    selector.disconnect_events()
                except Exception:
                    pass
                app_state.lasso_selector = None
                selector = None
            else:
                selector.set_active(True)
        except Exception:
            app_state.lasso_selector = None
            selector = None

    if selector is None:
        try:
            app_state.lasso_selector = LassoSelector(
                app_state.ax,
                _handle_lasso_select,
                button=[1]
            )
        except Exception as err:
            logger.warning("Unable to initialize lasso selector: %s", err)
            app_state.lasso_selector = None


def _handle_rectangle_select(eclick, erelease):
    try:
        if not app_state.selection_mode or app_state.render_mode == '3D':
            return

        if any(val is None for val in (eclick.xdata, erelease.xdata, eclick.ydata, erelease.ydata)):
            return

        x_min, x_max = sorted([float(eclick.xdata), float(erelease.xdata)])
        y_min, y_max = sorted([float(eclick.ydata), float(erelease.ydata)])

        if abs(x_max - x_min) < _SELECTION_MIN_SPAN or abs(y_max - y_min) < _SELECTION_MIN_SPAN:
            return

        indices_in_box = [
            idx for idx, (x_val, y_val) in app_state.sample_coordinates.items()
            if x_min <= x_val <= x_max and y_min <= y_val <= y_max
        ]

        if not indices_in_box:
            return

        current = app_state.selected_indices
        if all(idx in current for idx in indices_in_box):
            for idx in indices_in_box:
                current.discard(idx)
            logger.info("Deselected %d samples via box selection.", len(indices_in_box))
        else:
            for idx in indices_in_box:
                current.add(idx)
            logger.info("Selected %d samples via box selection.", len(indices_in_box))

        refresh_selection_overlay()
        _notify_selection_ui()

        # If isochron tool is active, calculate isochron age
        if app_state.selection_tool == 'isochron':
            calculate_selected_isochron()
            # Trigger plot refresh to show the isochron
            try:
                from visualization.events import on_slider_change
                on_slider_change()
            except Exception as e:
                logger.warning("Failed to refresh plot after isochron calculation: %s", e)
    except Exception as err:
        logger.warning("Rectangle selection failed: %s", err)


def _handle_lasso_select(vertices):
    try:
        if not app_state.selection_mode or app_state.render_mode == '3D':
            return

        if not vertices:
            return

        path = Path(vertices)

        indices_in_shape = [
            idx for idx, (x_val, y_val) in app_state.sample_coordinates.items()
            if path.contains_point((x_val, y_val))
        ]

        if not indices_in_shape:
            return

        current = app_state.selected_indices
        if all(idx in current for idx in indices_in_shape):
            for idx in indices_in_shape:
                current.discard(idx)
            logger.info("Deselected %d samples via custom shape.", len(indices_in_shape))
        else:
            for idx in indices_in_shape:
                current.add(idx)
            logger.info("Selected %d samples via custom shape.", len(indices_in_shape))

        refresh_selection_overlay()
        _notify_selection_ui()
    except Exception as err:
        logger.warning("Custom shape selection failed: %s", err)


def refresh_selection_overlay() -> None:
    """Update selection overlay scatter to highlight chosen points."""
    try:
        if app_state.fig is None or app_state.ax is None or app_state.render_mode == '3D':
            if app_state.selection_overlay is not None:
                try:
                    app_state.selection_overlay.remove()
                except Exception:
                    pass
                app_state.selection_overlay = None
            _notify_selection_ui()
            return

        if app_state.selection_overlay is not None:
            try:
                app_state.selection_overlay.remove()
            except Exception:
                pass
            app_state.selection_overlay = None
        
        # Clear previous selection ellipse
        if app_state.selection_ellipse is not None:
            try:
                app_state.selection_ellipse.remove()
            except Exception:
                pass
            app_state.selection_ellipse = None

        valid_indices = [idx for idx in app_state.selected_indices if idx in app_state.sample_coordinates]
        # Do not remove invisible indices from selection state, just don't draw them
        # removed = set(app_state.selected_indices) - set(valid_indices)
        # if removed:
        #     app_state.selected_indices -= removed

        if not valid_indices:
            app_state.fig.canvas.draw_idle()
            _notify_selection_ui()
            return

        # Save current view limits to prevent auto-scaling
        current_xlim = app_state.ax.get_xlim()
        current_ylim = app_state.ax.get_ylim()

        xs = [app_state.sample_coordinates[idx][0] for idx in valid_indices]
        ys = [app_state.sample_coordinates[idx][1] for idx in valid_indices]

        # Only draw highlight rings when a selection tool is active
        if app_state.selection_tool:
            base_marker_size = getattr(app_state, 'plot_marker_size', app_state.point_size)
            highlight_size = max(int(base_marker_size * 1.8), 20)

            app_state.selection_overlay = app_state.ax.scatter(
                xs,
                ys,
                s=[highlight_size] * len(xs),
                facecolors='none',
                edgecolors='#f97316',
                linewidths=1.6,
                zorder=6
            )
        
        # Draw confidence ellipse for selected points if enabled
        should_draw_ellipse = app_state.show_ellipses or getattr(app_state, 'draw_selection_ellipse', False)
        
        if should_draw_ellipse and len(xs) >= 3:
            try:
                x_arr = np.array(xs)
                y_arr = np.array(ys)
                # Use a distinct style for the selection ellipse
                app_state.selection_ellipse = draw_confidence_ellipse(
                    x_arr, y_arr, app_state.ax, 
                    confidence=app_state.ellipse_confidence,
                    edgecolor='#f97316', linestyle='--', linewidth=2, zorder=5, alpha=0.8
                )
                logger.info("Drawn %.0f%% confidence ellipse for %d selected points.", app_state.ellipse_confidence * 100, len(xs))
            except Exception as e:
                logger.warning("Failed to draw selection ellipse: %s", e)

        # Restore view limits
        app_state.ax.set_xlim(current_xlim)
        app_state.ax.set_ylim(current_ylim)

        app_state.fig.canvas.draw_idle()
        _notify_selection_ui()
    except Exception as err:
        logger.warning("Unable to refresh selection overlay: %s", err)


def calculate_selected_isochron() -> None:
    """Calculate isochron age for selected data points."""
    try:
        # Check if we have selected points
        if not app_state.selected_indices or len(app_state.selected_indices) < 2:
            logger.warning("Isochron calculation requires at least 2 selected points.")
            app_state.selected_isochron_data = None
            return

        # Check if we're in a Pb evolution mode
        if app_state.render_mode != 'PB_EVOL_76':
            logger.warning("Isochron calculation is only available for Pb evolution plot (PB_EVOL_76).")
            app_state.selected_isochron_data = None
            return

        # Determine isochron mode
        mode = 'ISOCHRON1'
        x_col = "206Pb/204Pb"
        y_col = "207Pb/204Pb"

        # Get data
        df = app_state.df_global
        if df is None or x_col not in df.columns or y_col not in df.columns:
            logger.warning("Required columns %s and %s not found in data.", x_col, y_col)
            app_state.selected_isochron_data = None
            return

        # Extract selected points
        selected_list = list(app_state.selected_indices)
        df_selected = df.iloc[selected_list]

        x_data = pd.to_numeric(df_selected[x_col], errors='coerce').values
        y_data = pd.to_numeric(df_selected[y_col], errors='coerce').values

        sx_data, sy_data, rxy_data = _resolve_isochron_errors(df_selected, len(x_data))

        # Remove NaN values
        valid = ~np.isnan(x_data) & ~np.isnan(y_data)
        valid = valid & np.isfinite(sx_data) & np.isfinite(sy_data) & np.isfinite(rxy_data)
        valid = valid & (sx_data > 0) & (sy_data > 0) & (np.abs(rxy_data) <= 1)
        x_data = x_data[valid]
        y_data = y_data[valid]
        sx_data = sx_data[valid]
        sy_data = sy_data[valid]
        rxy_data = rxy_data[valid]

        if len(x_data) < 2:
            logger.warning("Not enough valid data points for isochron calculation.")
            app_state.selected_isochron_data = None
            return

        # Perform York regression
        try:
            from data.geochemistry import york_regression, calculate_pbpb_age_from_ratio, engine
            fit = york_regression(x_data, sx_data, y_data, sy_data, rxy_data)
            slope = fit['b']
            intercept = fit['a']
            slope_err = fit['sb']
            intercept_err = fit['sa']
            mswd = fit['mswd']
            p_value = fit['p_value']
        except Exception as e:
            logger.warning("Isochron regression failed: %s", e)
            app_state.selected_isochron_data = None
            return

        # Calculate R² value
        y_pred = slope * x_data + intercept
        ss_res = np.sum((y_data - y_pred) ** 2)
        ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Calculate age from slope
        try:
            params = engine.get_parameters()
            age_ma, age_err = calculate_pbpb_age_from_ratio(slope, slope_err, params)
        except Exception as e:
            logger.warning("Age calculation failed: %s", e)
            age_ma = 0.0
            age_err = None

        # Store results
        x_min, x_max = np.min(x_data), np.max(x_data)
        span = x_max - x_min
        x_range = [x_min - span * 0.1, x_max + span * 0.1]
        y_range = [slope * x_range[0] + intercept, slope * x_range[1] + intercept]

        app_state.selected_isochron_data = {
            'slope': slope,
            'intercept': intercept,
            'slope_err': slope_err,
            'intercept_err': intercept_err,
            'age': age_ma,
            'age_err': age_err,
            'r_squared': r_squared,
            'mswd': mswd,
            'p_value': p_value,
            'n_points': len(x_data),
            'mode': mode,
            'x_range': x_range,
            'y_range': y_range,
            'x_col': x_col,
            'y_col': y_col
        }

        logger.info("Isochron calculated: Age = %.1f Ma, n = %d, R² = %.4f", age_ma, len(x_data), r_squared)
        logger.info("Slope = %.6f, Intercept = %.6f", slope, intercept)

    except Exception as err:
        logger.warning("Isochron calculation failed: %s", err)
        app_state.selected_isochron_data = None


def _resolve_sample_index(event):
    """Attempt to map a Matplotlib event to a sample index."""
    try:
        for sc in app_state.scatter_collections:
            if sc is None:
                continue
            try:
                cont, ind = sc.contains(event)
            except Exception:
                continue
            if not cont or 'ind' not in ind or not ind['ind']:
                continue
            idx_in_scatter = int(ind['ind'][0])
            sample_idx = app_state.artist_to_sample.get((id(sc), idx_in_scatter))
            if sample_idx is not None:
                return sample_idx

        if event is not None and event.xdata is not None and event.ydata is not None:
            x_val = float(event.xdata)
            y_val = float(event.ydata)
            best_idx = None
            best_distance = float('inf')
            for idx, (sx, sy) in app_state.sample_coordinates.items():
                distance = ((x_val - sx) ** 2 + (y_val - sy) ** 2) ** 0.5
                if distance < _HOVER_DISTANCE_THRESHOLD and distance < best_distance:
                    best_distance = distance
                    best_idx = idx
            return best_idx
    except Exception:
        return None
    return None


def toggle_selection_mode(tool_type: str = 'export') -> None:
    """
    Toggle interactive selection mode.
    tool_type: 'export', 'lasso', or 'isochron'
    """
    try:
        # If switching to the same tool that is already active, toggle it off
        if app_state.selection_tool == tool_type:
            new_tool = None
        else:
            new_tool = tool_type

        if new_tool and app_state.render_mode == '3D':
            logger.warning('Selection mode is only available for 2D projections.')
            return

        # Disable existing tool if any
        if app_state.selection_tool:
             _disable_rectangle_selector()
             _disable_lasso_selector()
             # Clear selection only if ellipse is not active
             if app_state.selected_indices and not getattr(app_state, 'draw_selection_ellipse', False):
                 app_state.selected_indices.clear()
             # Clear isochron data if switching away from isochron tool
             if app_state.selection_tool == 'isochron':
                 app_state.selected_isochron_data = None

        app_state.selection_tool = new_tool
        app_state.selection_mode = (new_tool is not None) # Keep legacy flag in sync

        if app_state.selection_tool:
            logger.info("Selection tool '%s' enabled.", new_tool)
            if new_tool == 'lasso':
                _ensure_lasso_selector()
            else:
                _ensure_rectangle_selector()

            # Disable Matplotlib toolbar zoom/pan if active
            try:
                if app_state.fig.canvas.toolbar.mode == 'zoom rect':
                    app_state.fig.canvas.toolbar.zoom()
                elif app_state.fig.canvas.toolbar.mode == 'pan/zoom':
                    app_state.fig.canvas.toolbar.pan()
            except Exception:
                pass

        else:
            logger.info("Selection tool disabled.")
            _disable_rectangle_selector()
            _disable_lasso_selector()

        _notify_selection_ui()
        refresh_selection_overlay()

        # If we just disabled isochron tool, refresh plot to remove the isochron line
        if new_tool is None and app_state.selection_tool is None:
            try:
                from visualization.events import on_slider_change
                on_slider_change()
            except Exception as e:
                logger.warning("Failed to refresh plot after disabling selection tool: %s", e)
    except Exception as err:
        logger.warning("Failed to toggle selection mode: %s", err)


def sync_selection_tools() -> None:
    """Ensure selection helpers stay in sync with current axes."""
    if app_state.selection_tool == 'lasso':
        _ensure_lasso_selector()
        _disable_rectangle_selector()
    elif app_state.selection_tool:
        _ensure_rectangle_selector()
        _disable_lasso_selector()
    else:
        _disable_rectangle_selector()
        _disable_lasso_selector()


def on_hover(event) -> None:
    """Handle mouse hover events"""
    try:
        if app_state.render_mode == '3D':
            return

        if event is None or not hasattr(event, 'inaxes'):
            return
        
        if event.inaxes != app_state.ax or app_state.annotation is None:
            return
        if not getattr(app_state, 'show_tooltip', True):
            try:
                app_state.annotation.set_visible(False)
            except Exception:
                pass
            return
        
        visible = False

        for sc in app_state.scatter_collections:
            if sc is None:
                continue

            try:
                cont, ind = sc.contains(event)
                if not cont or not ind or "ind" not in ind or len(ind["ind"]) == 0:
                    continue

                idx_in_scatter = int(ind["ind"][0])
                sample_idx = app_state.artist_to_sample.get((id(sc), idx_in_scatter))
                if sample_idx is None:
                    continue

                offsets = sc.get_offsets()
                if offsets is None or len(offsets) <= idx_in_scatter:
                    continue

                x, y = offsets[idx_in_scatter]
                x, y = float(x), float(y)

                # Use .loc instead of .iloc to ensure we get the correct row by index label
                # sample_idx is the original index label from df_global
                try:
                    row = app_state.df_global.loc[sample_idx]
                    # Handle case where index is not unique (returns DataFrame)
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                except KeyError:
                    continue

                lines = []
                # Use configured columns if available, otherwise fallback to defaults
                cols_to_show = getattr(app_state, 'tooltip_columns', None)
                if cols_to_show is None:
                    cols_to_show = ['Lab No.', 'Discovery site', 'Period']

                # If user deselected all columns, show at least the ID
                if not cols_to_show:
                     lines.append(f"ID: {sample_idx}")
                else:
                    found_any = False
                    for col in cols_to_show:
                        if col in app_state.df_global.columns:
                            val = row[col]
                            val_str = str(val) if pd.notna(val) else 'N/A'
                            lines.append(f"{col}: {val_str}")
                            found_any = True
                    
                    if not found_any:
                        lines.append(f"ID: {sample_idx}")
                
                txt = "\n".join(lines)
                if sample_idx in app_state.selected_indices:
                    txt += "\n" + translate("Status: Selected")

                app_state.annotation.xy = (x, y)
                app_state.annotation.set_text(txt)
                app_state.annotation.set_visible(True)
                visible = True
                break

            except Exception:
                continue

        if not visible:
            try:
                app_state.annotation.set_visible(False)
            except Exception:
                pass

    except Exception:
        pass


def on_click(event) -> None:
    """Handle mouse click events for interactive selection."""
    try:
        if app_state.render_mode == '3D':
            return

        if event is None or not hasattr(event, 'inaxes'):
            return
        
        if event.inaxes != app_state.ax:
            return
        
        if not hasattr(event, 'button') or event.button != 1:
            return
        
        if app_state.selection_mode:
            if getattr(event, 'dblclick', False):
                sample_idx = _resolve_sample_index(event)
                if sample_idx is None:
                    logger.warning("No point detected for selection.")
                    return

                try:
                    row = app_state.df_global.loc[sample_idx]
                    lab_value = row['Lab No.'] if 'Lab No.' in app_state.df_global.columns else sample_idx
                    if pd.notna(lab_value):
                        lab_label = str(lab_value)
                    else:
                        lab_label = str(sample_idx)
                except Exception:
                    lab_label = str(sample_idx)

                if sample_idx in app_state.selected_indices:
                    app_state.selected_indices.discard(sample_idx)
                    logger.info("Deselected sample %s.", lab_label)
                else:
                    app_state.selected_indices.add(sample_idx)
                    logger.info("Selected sample %s.", lab_label)

                refresh_selection_overlay()
            return

        logger.info(translate("Click export has been removed. Use the control panel export instead."))
        return
                
    except Exception as e:
        logger.warning("Click handler error: %s", e)


def on_legend_click(event) -> None:
    """Handle legend click events - bring group to front"""
    try:
        if event is None or not hasattr(event, 'inaxes'):
            return
        
        # Skip if not a button press event or wrong button
        if not hasattr(event, 'button') or event.button != 1:
            return
        
        legend = app_state.ax.get_legend()
        if legend is None or not app_state.scatter_collections:
            return
        
        # Check if click is within legend bounds
        try:
            contains, leg_info = legend.contains(event)
            if not contains:
                return
        except Exception:
            return

        # Get all legend labels and their corresponding scatter objects
        leg_texts = legend.get_texts()
        scatter_labels = {sc.get_label(): sc for sc in app_state.scatter_collections if sc}
        
        # Find which legend entry was clicked
        for i, leg_text in enumerate(leg_texts):
            label = leg_text.get_text()
            if label in scatter_labels:
                # Try to detect which legend item was clicked by checking bbox
                try:
                    bbox = leg_text.get_window_extent()
                    if event.x is not None and event.y is not None:
                        if bbox.contains(event.x, event.y):
                            scatter = scatter_labels[label]
                            
                            # Toggle visibility
                            new_visible = not scatter.get_visible()
                            scatter.set_visible(new_visible)
                            
                            # Update legend text alpha
                            leg_text.set_alpha(1.0 if new_visible else 0.5)
                            
                            # Update legend handle alpha
                            if i < len(legend.legendHandles):
                                legend.legendHandles[i].set_alpha(1.0 if new_visible else 0.5)

                            # Update app_state.visible_groups
                            if app_state.visible_groups is None:
                                # If None, it means all were visible. Initialize with all.
                                app_state.visible_groups = list(app_state.current_groups)
                            
                            if new_visible:
                                if label not in app_state.visible_groups:
                                    app_state.visible_groups.append(label)
                            else:
                                if label in app_state.visible_groups:
                                    app_state.visible_groups.remove(label)
                            
                            # If all are visible again, set to None to indicate "all"
                            if len(app_state.visible_groups) == len(app_state.current_groups):
                                app_state.visible_groups = None

                            # Notify Control Panel to update checkboxes
                            panel = getattr(app_state, 'control_panel_ref', None)
                            if panel is not None and hasattr(panel, 'sync_legend_ui'):
                                try:
                                    panel.sync_legend_ui()
                                except Exception as e:
                                    logger.warning("Failed to sync legend UI: %s", e)

                            logger.info("Toggled visibility for: %s to %s", label, new_visible)
                            try:
                                app_state.fig.canvas.draw_idle()
                            except Exception:
                                pass
                            return
                except Exception:
                    pass
                
    except Exception as e:
        pass


def _resolve_group_col():
    """Resolve the current group column, falling back to the first available."""
    group_col = app_state.last_group_col
    if not group_col or group_col not in app_state.group_cols:
        if app_state.group_cols:
            group_col = app_state.group_cols[0]
            logger.debug("Using default group_col: %s", group_col)
        else:
            return None
    return group_col


def _sync_visible_groups(group_col):
    """Refresh available_groups and prune visible_groups."""
    try:
        df_groups_source = app_state.df_global[group_col].fillna('Unknown').astype(str)
        all_groups = sorted(df_groups_source.unique())
    except Exception:
        all_groups = []

    app_state.available_groups = all_groups
    if app_state.visible_groups:
        filtered = [g for g in app_state.visible_groups if g in all_groups]
        app_state.visible_groups = filtered if filtered else None


def _validate_render_columns(render_mode, selected_columns_2d, selected_columns_3d):
    """Validate and adjust render mode / column selections.

    Returns (render_mode, selected_columns_2d, selected_columns_3d).
    """
    if render_mode == '3D':
        available_cols = [c for c in app_state.data_cols if c in app_state.df_global.columns]
        logger.debug("Available numeric columns for 3D: %s", available_cols)
        if len(available_cols) < 3:
            logger.warning("Not enough numeric columns for 3D view; reverting to 2D")
            render_mode = '2D'
        else:
            preselected = [c for c in selected_columns_3d if c in available_cols]
            if len(preselected) == 3:
                selected_columns_3d = preselected
            elif len(available_cols) >= 3:
                selected_columns_3d = available_cols[:3]
                app_state.selected_3d_cols = selected_columns_3d
                app_state.selected_3d_confirmed = False
                logger.info("Using default 3D columns: %s", selected_columns_3d)

    if render_mode == '2D':
        available_cols_2d = [c for c in app_state.data_cols if c in app_state.df_global.columns]
        logger.debug("Available numeric columns for 2D: %s", available_cols_2d)
        if len(available_cols_2d) < 2:
            logger.warning("Not enough numeric columns for 2D view; falling back to UMAP")
            render_mode = 'UMAP'
        else:
            preselected_2d = [c for c in selected_columns_2d if c in available_cols_2d][:2]
            if len(preselected_2d) == 2:
                selected_columns_2d = preselected_2d
            elif len(available_cols_2d) >= 2:
                selected_columns_2d = available_cols_2d[:2]
                app_state.selected_2d_cols = selected_columns_2d
                app_state.selected_2d_confirmed = False
                logger.info("Using default 2D columns: %s", selected_columns_2d)

    if render_mode == 'Ternary':
        available_cols_ternary = [c for c in app_state.data_cols if c in app_state.df_global.columns]
        if len(available_cols_ternary) < 3:
            logger.warning("Not enough numeric columns for Ternary view; falling back to UMAP")
            render_mode = 'UMAP'
        else:
            preselected = getattr(app_state, 'selected_ternary_cols', [])
            valid_preselected = [c for c in preselected if c in available_cols_ternary]
            if len(valid_preselected) == 3:
                if not app_state.selected_ternary_confirmed:
                    app_state.selected_ternary_cols = valid_preselected
            elif len(available_cols_ternary) >= 3:
                app_state.selected_ternary_cols = available_cols_ternary[:3]
                app_state.selected_ternary_confirmed = False

    return render_mode, selected_columns_2d, selected_columns_3d


def _sync_render_mode(render_mode):
    """Update app_state and control panel if render_mode changed."""
    if render_mode == app_state.render_mode:
        return
    logger.debug("Adjusted render mode: %s -> %s", app_state.render_mode, render_mode)
    app_state.render_mode = render_mode
    if app_state.render_mode in ('UMAP', 'tSNE', 'PCA', 'RobustPCA'):
        app_state.algorithm = app_state.render_mode
    try:
        panel = getattr(app_state, 'control_panel_ref', None)
        if panel is not None and 'render_mode' in panel.radio_vars:
            panel.radio_vars['render_mode'].set(render_mode)
    except Exception as sync_err:
        logger.warning("Unable to sync control panel render mode: %s", sync_err)


def _dispatch_render(group_col, selected_columns_2d, selected_columns_3d):
    """Dispatch to the appropriate plot function. Returns True on success."""
    from .plotting import plot_embedding, plot_3d_data, plot_2d_data

    if app_state.render_mode == '3D':
        if app_state.selection_mode:
            app_state.selection_mode = False
            _disable_rectangle_selector()
            refresh_selection_overlay()
            _notify_selection_ui()
            logger.info("Selection mode automatically disabled for 3D view.")
        if len(selected_columns_3d) != 3:
            logger.warning("Invalid 3D column selection; skipping plot")
            return False
        logger.debug("Rendering 3D plot with columns=%s", selected_columns_3d)
        return plot_3d_data(group_col, selected_columns_3d, size=app_state.point_size)

    if app_state.render_mode == '2D':
        if len(selected_columns_2d) != 2:
            logger.warning("Invalid 2D column selection; skipping plot")
            return False
        logger.debug("Rendering 2D plot with columns=%s", selected_columns_2d)
        is_kde = getattr(app_state, 'show_kde', False) or getattr(app_state, 'show_2d_kde', False)
        return plot_2d_data(group_col, selected_columns_2d, size=app_state.point_size, show_kde=is_kde)

    algorithm = app_state.render_mode
    logger.debug("Calling plot_embedding with algorithm=%s, group_col=%s", algorithm, group_col)
    return plot_embedding(
        group_col,
        algorithm,
        umap_params=app_state.umap_params,
        tsne_params=app_state.tsne_params,
        pca_params=app_state.pca_params,
        robust_pca_params=app_state.robust_pca_params,
        size=app_state.point_size,
    )


def _handle_render_fallback(group_col):
    """Fall back to UMAP when 2D/3D rendering fails."""
    from .plotting import plot_embedding

    if app_state.render_mode not in ('2D', '3D'):
        return
    logger.info("Falling back to UMAP embedding for display")
    app_state.render_mode = 'UMAP'
    app_state.algorithm = 'UMAP'
    try:
        panel = getattr(app_state, 'control_panel_ref', None)
        if panel is not None and 'render_mode' in panel.radio_vars:
            panel.radio_vars['render_mode'].set('UMAP')
    except Exception:
        pass

    fallback_ok = plot_embedding(
        group_col,
        'UMAP',
        umap_params=app_state.umap_params,
        tsne_params=app_state.tsne_params,
        size=app_state.point_size,
    )
    if fallback_ok:
        refresh_selection_overlay()
        sync_selection_tools()
        _notify_selection_ui()
        try:
            app_state.fig.canvas.draw_idle()
        except Exception:
            pass
    else:
        logger.warning("Fallback UMAP plot also failed")


def on_slider_change(val=None) -> None:
    """Handle slider and radio button changes from the control panel."""
    try:
        logger.debug("on_slider_change called, val=%s", val)

        if app_state.df_global is None or len(app_state.df_global) == 0:
            logger.warning("No data available")
            return

        try:
            group_col = _resolve_group_col()
            if group_col is None:
                logger.warning("No group columns available")
                return

            render_mode = app_state.render_mode
            selected_columns_3d = list(app_state.selected_3d_cols)
            selected_columns_2d = list(getattr(app_state, 'selected_2d_cols', []))

            _sync_visible_groups(group_col)

            render_mode, selected_columns_2d, selected_columns_3d = _validate_render_columns(
                render_mode, selected_columns_2d, selected_columns_3d,
            )
            _sync_render_mode(render_mode)

            rendered_ok = _dispatch_render(group_col, selected_columns_2d, selected_columns_3d)

            if rendered_ok:
                logger.debug("Plot rendered successfully, calling draw_idle")
                refresh_selection_overlay()
                sync_selection_tools()
                _notify_selection_ui()
                try:
                    app_state.fig.canvas.draw_idle()
                except Exception as draw_err:
                    logger.warning("Draw error: %s", draw_err)
            else:
                logger.warning("Plot rendering failed")
                _handle_render_fallback(group_col)

            app_state.initial_render_done = True
        except Exception as plot_err:
            logger.error("Plotting error: %s", plot_err)
            import traceback
            traceback.print_exc()
    except Exception as e:
        logger.error("on_slider_change error: %s", e)
        import traceback
        traceback.print_exc()
