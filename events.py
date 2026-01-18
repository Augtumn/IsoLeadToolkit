"""
Event Handlers
Manages user interactions: hover, click, and legend events
"""
import pandas as pd
import numpy as np
import matplotlib
from matplotlib.patches import Ellipse
from state import app_state
import state as state_module
from matplotlib.widgets import RectangleSelector


import scipy.stats

def draw_confidence_ellipse(x, y, ax, confidence=0.95, facecolor='none', **kwargs):
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


def _notify_selection_ui():
    """Ask the control panel to refresh selection-related widgets."""
    panel = getattr(app_state, 'control_panel_ref', None) or getattr(state_module, 'control_panel', None)
    if panel is None:
        return

    update_fn = getattr(panel, 'update_selection_controls', None)
    if not callable(update_fn):
        return

    try:
        update_fn()
    except Exception as err:
        print(f"[WARN] Unable to update selection controls: {err}", flush=True)


def _disable_rectangle_selector():
    selector = getattr(app_state, 'rectangle_selector', None)
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
            print(f"[WARN] Unable to initialize rectangle selector: {err}", flush=True)
            app_state.rectangle_selector = None


def _handle_rectangle_select(eclick, erelease):
    try:
        if not app_state.selection_mode or app_state.render_mode == '3D':
            return

        if any(val is None for val in (eclick.xdata, erelease.xdata, eclick.ydata, erelease.ydata)):
            return

        x_min, x_max = sorted([float(eclick.xdata), float(erelease.xdata)])
        y_min, y_max = sorted([float(eclick.ydata), float(erelease.ydata)])

        if abs(x_max - x_min) < 1e-9 or abs(y_max - y_min) < 1e-9:
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
            print(f"[INFO] Deselected {len(indices_in_box)} samples via box selection.", flush=True)
        else:
            for idx in indices_in_box:
                current.add(idx)
            print(f"[INFO] Selected {len(indices_in_box)} samples via box selection.", flush=True)

        refresh_selection_overlay()
        _notify_selection_ui()
    except Exception as err:
        print(f"[WARN] Rectangle selection failed: {err}", flush=True)


def refresh_selection_overlay():
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
        highlight_size = max(int(app_state.point_size * 1.8), 20)

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
                print(f"[INFO] Drawn {app_state.ellipse_confidence*100:.0f}% confidence ellipse for {len(xs)} selected points.", flush=True)
            except Exception as e:
                print(f"[WARN] Failed to draw selection ellipse: {e}", flush=True)

        # Restore view limits
        app_state.ax.set_xlim(current_xlim)
        app_state.ax.set_ylim(current_ylim)

        app_state.fig.canvas.draw_idle()
        _notify_selection_ui()
    except Exception as err:
        print(f"[WARN] Unable to refresh selection overlay: {err}", flush=True)


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
                if distance < 0.15 and distance < best_distance:
                    best_distance = distance
                    best_idx = idx
            return best_idx
    except Exception:
        return None
    return None


def toggle_selection_mode(tool_type='export'):
    """
    Toggle interactive selection mode.
    tool_type: 'export' or 'ellipse'
    """
    try:
        # If switching to the same tool that is already active, toggle it off
        if app_state.selection_tool == tool_type:
            new_tool = None
        else:
            new_tool = tool_type

        if new_tool and app_state.render_mode == '3D':
            print('[WARN] Selection mode is only available for 2D projections.', flush=True)
            return

        # Disable existing tool if any
        if app_state.selection_tool:
             _disable_rectangle_selector()
             # Clear selection if we are switching tools or turning off
             if app_state.selected_indices:
                 app_state.selected_indices.clear()
        
        app_state.selection_tool = new_tool
        app_state.selection_mode = (new_tool is not None) # Keep legacy flag in sync

        if app_state.selection_tool:
            print(f"[INFO] Selection tool '{new_tool}' enabled.", flush=True)
            _ensure_rectangle_selector()
            
            # Disable Matplotlib toolbar zoom/pan if active
            try:
                if app_state.fig.canvas.toolbar.mode == 'zoom rect':
                    app_state.fig.canvas.toolbar.zoom()
                elif app_state.fig.canvas.toolbar.mode == 'pan/zoom':
                    app_state.fig.canvas.toolbar.pan()
            except Exception:
                pass

            if new_tool == 'ellipse':
                app_state.draw_selection_ellipse = True
            else:
                app_state.draw_selection_ellipse = False

        else:
            print("[INFO] Selection tool disabled.", flush=True)
            app_state.draw_selection_ellipse = False
            _disable_rectangle_selector()

        _notify_selection_ui()
        refresh_selection_overlay()
    except Exception as err:
        print(f"[WARN] Failed to toggle selection mode: {err}", flush=True)


def sync_selection_tools():
    """Ensure selection helpers stay in sync with current axes."""
    if app_state.selection_tool:
        _ensure_rectangle_selector()
    else:
        _disable_rectangle_selector()


def on_hover(event):
    """Handle mouse hover events"""
    try:
        if app_state.render_mode == '3D':
            return

        if event is None or not hasattr(event, 'inaxes'):
            return
        
        if event.inaxes != app_state.ax or app_state.annotation is None:
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
                    txt += "\n状态: 已选中"

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
            except:
                pass
            
    except Exception:
        pass


def on_click(event):
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
                    print("[WARN] No point detected for selection.", flush=True)
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
                    print(f"[INFO] Deselected sample {lab_label}.", flush=True)
                else:
                    app_state.selected_indices.add(sample_idx)
                    print(f"[INFO] Selected sample {lab_label}.", flush=True)

                refresh_selection_overlay()
            return

        print("[INFO] 单击导出已移除，请使用控制面板中的导出功能。", flush=True)
        return
                
    except Exception as e:
        print(f"[WARN] Click handler error: {e}", flush=True)


def on_legend_click(event):
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
        except:
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
                            panel = getattr(app_state, 'control_panel_ref', None) or getattr(state_module, 'control_panel', None)
                            if panel is not None and hasattr(panel, 'sync_legend_ui'):
                                try:
                                    panel.sync_legend_ui()
                                except Exception as e:
                                    print(f"[WARN] Failed to sync legend UI: {e}", flush=True)

                            print(f"[OK] Toggled visibility for: {label} to {new_visible}", flush=True)
                            try:
                                app_state.fig.canvas.draw_idle()
                            except:
                                pass
                            return
                except:
                    pass
                
    except Exception as e:
        pass


def on_slider_change(val=None):
    """Handle slider and radio button changes from tkinter control panel"""
    try:
        print(f"[DEBUG] on_slider_change called, val={val}", flush=True)
        from visualization import plot_embedding, plot_3d_data, plot_2d_data
        
        # At this point, app_state has been updated by control_panel callbacks
        # We just need to re-render the plot with the current parameters
        
        if app_state.df_global is None or len(app_state.df_global) == 0:
            print("[WARN] No data available", flush=True)
            return
        
        try:
            # Get current group column
            group_col = app_state.last_group_col
            print(f"[DEBUG] Current group_col: {group_col}, available: {app_state.group_cols}", flush=True)
            
            if not group_col or group_col not in app_state.group_cols:
                if app_state.group_cols:
                    group_col = app_state.group_cols[0]
                    print(f"[DEBUG] Using default group_col: {group_col}", flush=True)
                else:
                    print("[WARN] No group columns available", flush=True)
                    return
            
            # Get algorithm
            render_mode = app_state.render_mode
            print(f"[DEBUG] Current render_mode: {render_mode}", flush=True)
            selected_columns_3d = list(app_state.selected_3d_cols)
            selected_columns_2d = list(getattr(app_state, 'selected_2d_cols', []))

            prompt_allowed = app_state.initial_render_done

            try:
                df_groups_source = app_state.df_global[group_col].fillna('Unknown').astype(str)
                all_groups = sorted(df_groups_source.unique())
            except Exception:
                all_groups = []

            app_state.available_groups = all_groups
            if app_state.visible_groups:
                filtered_visible = [g for g in app_state.visible_groups if g in all_groups]
                if filtered_visible:
                    app_state.visible_groups = filtered_visible
                else:
                    app_state.visible_groups = None

            if render_mode == '3D':
                available_cols = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                print(f"[DEBUG] Available numeric columns for 3D: {available_cols}", flush=True)

                if len(available_cols) < 3:
                    print("[WARN] Not enough numeric columns for 3D view; reverting to 2D", flush=True)
                    render_mode = '2D'
                else:
                    preselected = [c for c in selected_columns_3d if c in available_cols]
                    if len(preselected) == 3:
                        selected_columns_3d = preselected
                        if app_state.selected_3d_confirmed:
                            print(f"[DEBUG] Reusing confirmed 3D columns: {selected_columns_3d}", flush=True)
                        else:
                            print(f"[DEBUG] Using existing 3D columns (unconfirmed): {selected_columns_3d}", flush=True)
                    elif len(available_cols) >= 3:
                        selected_columns_3d = available_cols[:3]
                        app_state.selected_3d_cols = selected_columns_3d
                        app_state.selected_3d_confirmed = False
                        print(f"[INFO] Using default 3D columns: {selected_columns_3d}", flush=True)
                    
                    # Removed auto-prompt logic. User must use the button in Control Panel.

            if render_mode == '2D':
                available_cols_2d = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                print(f"[DEBUG] Available numeric columns for 2D: {available_cols_2d}", flush=True)

                if len(available_cols_2d) < 2:
                    print("[WARN] Not enough numeric columns for 2D view; falling back to UMAP", flush=True)
                    render_mode = 'UMAP'
                else:
                    preselected_2d = [c for c in selected_columns_2d if c in available_cols_2d][:2]
                    need_prompt_2d = len(available_cols_2d) > 2 and (not app_state.selected_2d_confirmed)

                    if len(preselected_2d) == 2:
                        selected_columns_2d = preselected_2d
                        # If confirmed, great. If not, we just use them without prompting.
                        # The user can change them via the "Select Axis Columns" button.
                        if app_state.selected_2d_confirmed:
                            print(f"[DEBUG] Reusing confirmed 2D columns: {selected_columns_2d}", flush=True)
                        else:
                            print(f"[DEBUG] Using existing 2D columns (unconfirmed): {selected_columns_2d}", flush=True)
                    elif len(available_cols_2d) >= 2:
                        # Default to first two
                        selected_columns_2d = available_cols_2d[:2]
                        app_state.selected_2d_cols = selected_columns_2d
                        # We don't set confirmed=True here so we know they are defaults
                        app_state.selected_2d_confirmed = False 
                        print(f"[INFO] Using default 2D columns: {selected_columns_2d}", flush=True)
                    
                    # Removed auto-prompt logic. User must use the button in Control Panel.

            if render_mode == 'Ternary':
                available_cols_ternary = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                if len(available_cols_ternary) < 3:
                     print("[WARN] Not enough numeric columns for Ternary view; falling back to UMAP", flush=True)
                     render_mode = 'UMAP'
                else:
                    preselected = getattr(app_state, 'selected_ternary_cols', [])
                    
                    # Validate existing selection
                    valid_preselected = [c for c in preselected if c in available_cols_ternary]
                    
                    if len(valid_preselected) == 3:
                         if app_state.selected_ternary_confirmed:
                             pass
                         else:
                             app_state.selected_ternary_cols = valid_preselected
                    elif len(available_cols_ternary) >= 3:
                         # Default
                         app_state.selected_ternary_cols = available_cols_ternary[:3]
                         app_state.selected_ternary_confirmed = False

            if render_mode != app_state.render_mode:
                print(f"[DEBUG] Adjusted render mode: {app_state.render_mode} -> {render_mode}", flush=True)
                app_state.render_mode = render_mode
                if app_state.render_mode in ('UMAP', 'tSNE', 'PCA', 'RobustPCA'):
                    app_state.algorithm = app_state.render_mode
                try:
                    panel = getattr(app_state, 'control_panel_ref', None) or getattr(state_module, 'control_panel', None)
                    if panel is not None and 'render_mode' in panel.radio_vars:
                        panel.radio_vars['render_mode'].set(render_mode)
                except Exception as sync_err:
                    print(f"[WARN] Unable to sync control panel render mode: {sync_err}", flush=True)

            rendered_ok = False
            if app_state.render_mode == '3D':
                if app_state.selection_mode:
                    app_state.selection_mode = False
                    _disable_rectangle_selector()
                    refresh_selection_overlay()
                    _notify_selection_ui()
                    print("[INFO] Selection mode automatically disabled for 3D view.", flush=True)
                if len(selected_columns_3d) != 3:
                    print("[WARN] Invalid 3D column selection; skipping plot", flush=True)
                else:
                    print(f"[DEBUG] Rendering 3D plot with columns={selected_columns_3d}", flush=True)
                    rendered_ok = plot_3d_data(
                        group_col,
                        selected_columns_3d,
                        size=app_state.point_size
                    )
            elif app_state.render_mode == '2D':
                if len(selected_columns_2d) != 2:
                    print("[WARN] Invalid 2D column selection; skipping plot", flush=True)
                else:
                    print(f"[DEBUG] Rendering 2D plot with columns={selected_columns_2d}", flush=True)
                    # Check both global KDE setting and specific 2D KDE setting
                    is_kde = getattr(app_state, 'show_kde', False) or getattr(app_state, 'show_2d_kde', False)
                    rendered_ok = plot_2d_data(
                        group_col,
                        selected_columns_2d,
                        size=app_state.point_size,
                        show_kde=is_kde
                    )
            else:
                # Use the current render mode as the algorithm name
                # This supports UMAP, tSNE, PCA, RobustPCA
                algorithm = app_state.render_mode
                print(f"[DEBUG] Calling plot_embedding with algorithm={algorithm}, group_col={group_col}", flush=True)
                rendered_ok = plot_embedding(
                    group_col,
                    algorithm,
                    umap_params=app_state.umap_params,
                    tsne_params=app_state.tsne_params,
                    pca_params=app_state.pca_params,
                    robust_pca_params=app_state.robust_pca_params,
                    size=app_state.point_size
                )

            if rendered_ok:
                print("[DEBUG] Plot rendered successfully, calling draw_idle", flush=True)
                refresh_selection_overlay()
                sync_selection_tools()
                _notify_selection_ui()
                try:
                    app_state.fig.canvas.draw_idle()
                except Exception as draw_err:
                    print(f"[WARN] Draw error: {draw_err}", flush=True)
            else:
                print("[WARN] Plot rendering failed", flush=True)
                if app_state.render_mode in ('2D', '3D'):
                    print("[INFO] Falling back to UMAP embedding for display", flush=True)
                    app_state.render_mode = 'UMAP'
                    app_state.algorithm = 'UMAP'
                    try:
                        panel = getattr(app_state, 'control_panel_ref', None) or getattr(state_module, 'control_panel', None)
                        if panel is not None and 'render_mode' in panel.radio_vars:
                            panel.radio_vars['render_mode'].set('UMAP')
                    except Exception:
                        pass

                    fallback_ok = plot_embedding(
                        group_col,
                        'UMAP',
                        umap_params=app_state.umap_params,
                        tsne_params=app_state.tsne_params,
                        size=app_state.point_size
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
                        print("[WARN] Fallback UMAP plot also failed", flush=True)

            app_state.initial_render_done = True
        except Exception as plot_err:
            print(f"[ERROR] Plotting error: {plot_err}", flush=True)
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"[ERROR] on_slider_change error: {e}", flush=True)
        import traceback
        traceback.print_exc()
