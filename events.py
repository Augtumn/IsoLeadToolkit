"""
Event Handlers
Manages user interactions: hover, click, and legend events
"""
import pandas as pd
import os
from config import CONFIG
from state import app_state
import state as state_module


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
                # Check if cursor is over this scatter
                cont, ind = sc.contains(event)
                if not cont or not ind or "ind" not in ind or len(ind["ind"]) == 0:
                    continue
                
                idx_in_scatter = int(ind["ind"][0])
                offsets = sc.get_offsets()
                
                if offsets is None or len(offsets) <= idx_in_scatter:
                    continue
                
                # Get the exact coordinates
                x, y = offsets[idx_in_scatter]
                x, y = float(x), float(y)
                
                # Search through all mapped points with distance tolerance
                best_distance = float('inf')
                best_idx = None
                
                for (mapped_x, mapped_y), sample_idx in app_state.sample_index_map.items():
                    mapped_x, mapped_y = float(mapped_x), float(mapped_y)
                    distance = ((x - mapped_x) ** 2 + (y - mapped_y) ** 2) ** 0.5
                    
                    if distance < 0.1 and distance < best_distance:
                        best_distance = distance
                        best_idx = sample_idx
                
                if best_idx is not None:
                    row = app_state.df_global.iloc[best_idx]
                    
                    lab_no = row['Lab No.'] if 'Lab No.' in app_state.df_global.columns else 'N/A'
                    site = row['Discovery site'] if 'Discovery site' in app_state.df_global.columns else 'N/A'
                    period = row['Period'] if 'Period' in app_state.df_global.columns else 'N/A'
                    
                    # Handle NaN values
                    lab_no = str(lab_no) if pd.notna(lab_no) else 'N/A'
                    site = str(site) if pd.notna(site) else 'N/A'
                    period = str(period) if pd.notna(period) else 'N/A'
                    
                    txt = f"Lab: {lab_no}\nSite: {site}\nPeriod: {period}"
                    app_state.annotation.xy = (x, y)
                    app_state.annotation.set_text(txt)
                    app_state.annotation.set_visible(True)
                    visible = True

                    break
                    
            except Exception as inner_e:
                continue
        
        if not visible:
            try:
                app_state.annotation.set_visible(False)
            except:
                pass
            
    except Exception as e:
        pass


def on_click(event):
    """Handle mouse click events - export sample"""
    try:
        if app_state.render_mode == '3D':
            return

        if event is None or not hasattr(event, 'inaxes'):
            return
        
        if event.inaxes != app_state.ax:
            return
        
        if not hasattr(event, 'button') or event.button != 1:
            return
        
        for sc in app_state.scatter_collections:
            if sc is None:
                continue
            
            try:
                cont, ind = sc.contains(event)
                if not cont or not ind or "ind" not in ind or len(ind["ind"]) == 0:
                    continue
                
                idx_in_scatter = int(ind["ind"][0])
                offsets = sc.get_offsets()
                
                if offsets is None or len(offsets) <= idx_in_scatter:
                    continue
                
                x, y = offsets[idx_in_scatter]
                x, y = float(x), float(y)
                
                # Find the sample index using distance tolerance
                best_distance = float('inf')
                best_idx = None
                
                for (mapped_x, mapped_y), sample_idx in app_state.sample_index_map.items():
                    mapped_x, mapped_y = float(mapped_x), float(mapped_y)
                    distance = ((x - mapped_x) ** 2 + (y - mapped_y) ** 2) ** 0.5
                    
                    if distance < 0.1 and distance < best_distance:
                        best_distance = distance
                        best_idx = sample_idx
                
                if best_idx is not None:
                    # Check if already exported to prevent duplicates
                    if best_idx in app_state.exported_indices:
                        return
                    
                    app_state.exported_indices.add(best_idx)
                    sample = app_state.df_global.iloc[[best_idx]]
                    
                    export_file = CONFIG['export_csv']
                    try:
                        if os.path.exists(export_file):
                            existing = pd.read_csv(export_file, dtype=str)
                            sample_export = pd.concat([existing, sample], ignore_index=True)
                        else:
                            sample_export = sample
                        
                        sample_export.to_csv(export_file, index=False, encoding='utf-8')
                        lab_no = sample.iloc[0]['Lab No.'] if 'Lab No.' in sample.columns else 'N/A'
                        lab_no = str(lab_no) if pd.notna(lab_no) else 'N/A'
                        print(f"[OK] Sample exported to {export_file}: Lab No. = {lab_no}", flush=True)
                    except Exception as export_err:
                        print(f"[ERROR] Export failed: {export_err}", flush=True)
                    return
                    
            except Exception as inner_e:
                continue
                
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
                            scatter.set_zorder(10)
                            for other in app_state.scatter_collections:
                                if other and other != scatter:
                                    other.set_zorder(1)
                            print(f"[OK] Brought to front: {label}", flush=True)
                            try:
                                app_state.fig.canvas.draw_idle()
                            except:
                                pass
                            return
                except:
                    pass
        
        # Fallback: if legend contains event, try to bring the first matching scatter to front
        if legend.contains(event)[0]:
            for label, scatter in scatter_labels.items():
                scatter.set_zorder(10)
                for other in app_state.scatter_collections:
                    if other and other != scatter:
                        other.set_zorder(1)
                print(f"[OK] Brought to front: {label}", flush=True)
                try:
                    app_state.fig.canvas.draw_idle()
                except:
                    pass
                return
                
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

            if render_mode == '3D':
                available_cols = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                print(f"[DEBUG] Available numeric columns for 3D: {available_cols}", flush=True)

                if len(available_cols) < 3:
                    print("[WARN] Not enough numeric columns for 3D view; reverting to 2D", flush=True)
                    render_mode = '2D'
                else:
                    preselected = [c for c in selected_columns_3d if c in available_cols]
                    if len(preselected) == 3 and app_state.selected_3d_confirmed:
                        selected_columns_3d = preselected
                        print(f"[DEBUG] Reusing confirmed 3D columns: {selected_columns_3d}", flush=True)
                    elif len(available_cols) == 3:
                        selected_columns_3d = available_cols[:3]
                        app_state.selected_3d_cols = selected_columns_3d
                        app_state.selected_3d_confirmed = True
                        print(f"[INFO] Auto-selected 3D columns: {selected_columns_3d}", flush=True)
                    else:
                        need_prompt = prompt_allowed and not app_state.selected_3d_confirmed
                        if not prompt_allowed or not need_prompt:
                            selected_columns_3d = available_cols[:3]
                            app_state.selected_3d_cols = selected_columns_3d
                            app_state.selected_3d_confirmed = False
                            print(f"[INFO] Using default 3D columns: {selected_columns_3d}", flush=True)
                        else:
                            try:
                                from three_d_dialog import select_3d_columns
                            except Exception as dialog_import_err:
                                print(f"[WARN] Failed to import 3D selection dialog: {dialog_import_err}", flush=True)
                                selected_columns_3d = available_cols[:3]
                                app_state.selected_3d_cols = selected_columns_3d
                                app_state.selected_3d_confirmed = False
                            else:
                                print("[INFO] Prompting user to choose 3D columns", flush=True)
                                selection = select_3d_columns(available_cols, preselected=preselected)
                                if selection and len(selection) == 3:
                                    selected_columns_3d = selection
                                    app_state.selected_3d_cols = selection
                                    app_state.selected_3d_confirmed = True
                                    print(f"[INFO] User selected 3D columns: {selection}", flush=True)
                                else:
                                    print("[INFO] 3D column selection cancelled or invalid; using first three columns by default", flush=True)
                                    selected_columns_3d = available_cols[:3]
                                    app_state.selected_3d_cols = selected_columns_3d
                                    app_state.selected_3d_confirmed = False

            if render_mode == '2D':
                available_cols_2d = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                print(f"[DEBUG] Available numeric columns for 2D: {available_cols_2d}", flush=True)

                if len(available_cols_2d) < 2:
                    print("[WARN] Not enough numeric columns for 2D view; falling back to UMAP", flush=True)
                    render_mode = 'UMAP'
                else:
                    preselected_2d = [c for c in selected_columns_2d if c in available_cols_2d][:2]
                    need_prompt_2d = len(available_cols_2d) > 2 and (not app_state.selected_2d_confirmed)

                    if len(preselected_2d) == 2 and app_state.selected_2d_confirmed:
                        selected_columns_2d = preselected_2d
                        print(f"[DEBUG] Reusing confirmed 2D columns: {selected_columns_2d}", flush=True)
                    elif len(available_cols_2d) == 2:
                        selected_columns_2d = available_cols_2d[:2]
                        app_state.selected_2d_cols = selected_columns_2d
                        app_state.selected_2d_confirmed = True
                        print(f"[INFO] Auto-selected 2D columns: {selected_columns_2d}", flush=True)
                    else:
                        if not prompt_allowed or not need_prompt_2d:
                            selected_columns_2d = available_cols_2d[:2]
                            app_state.selected_2d_cols = selected_columns_2d
                            app_state.selected_2d_confirmed = False
                            print(f"[INFO] Using default 2D columns: {selected_columns_2d}", flush=True)
                        else:
                            try:
                                from two_d_dialog import select_2d_columns
                            except Exception as dialog_import_err:
                                print(f"[WARN] Failed to import 2D selection dialog: {dialog_import_err}", flush=True)
                                selected_columns_2d = available_cols_2d[:2]
                                app_state.selected_2d_cols = selected_columns_2d
                                app_state.selected_2d_confirmed = False
                            else:
                                print("[INFO] Prompting user to choose 2D columns", flush=True)
                                selection_2d = select_2d_columns(available_cols_2d, preselected=preselected_2d)
                                if selection_2d and len(selection_2d) == 2:
                                    selected_columns_2d = selection_2d
                                    app_state.selected_2d_cols = selection_2d
                                    app_state.selected_2d_confirmed = True
                                    print(f"[INFO] User selected 2D columns: {selection_2d}", flush=True)
                                else:
                                    print("[INFO] 2D column selection cancelled or invalid; using first two columns by default", flush=True)
                                    selected_columns_2d = available_cols_2d[:2]
                                    app_state.selected_2d_cols = selected_columns_2d
                                    app_state.selected_2d_confirmed = False

            if render_mode != app_state.render_mode:
                print(f"[DEBUG] Adjusted render mode: {app_state.render_mode} -> {render_mode}", flush=True)
                app_state.render_mode = render_mode
                if app_state.render_mode in ('UMAP', 'tSNE'):
                    app_state.algorithm = 'UMAP' if app_state.render_mode == 'UMAP' else 'tSNE'
                try:
                    panel = getattr(app_state, 'control_panel_ref', None) or getattr(state_module, 'control_panel', None)
                    if panel is not None and 'render_mode' in panel.radio_vars:
                        panel.radio_vars['render_mode'].set(render_mode)
                except Exception as sync_err:
                    print(f"[WARN] Unable to sync control panel render mode: {sync_err}", flush=True)

            rendered_ok = False
            if app_state.render_mode == '3D':
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
                    rendered_ok = plot_2d_data(
                        group_col,
                        selected_columns_2d,
                        size=app_state.point_size
                    )
            else:
                algorithm = 'UMAP' if app_state.render_mode == 'UMAP' else 'tSNE'
                print(f"[DEBUG] Calling plot_embedding with algorithm={algorithm}, group_col={group_col}", flush=True)
                rendered_ok = plot_embedding(
                    group_col,
                    algorithm,
                    umap_params=app_state.umap_params,
                    tsne_params=app_state.tsne_params,
                    size=app_state.point_size
                )

            if rendered_ok:
                print("[DEBUG] Plot rendered successfully, calling draw_idle", flush=True)
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
