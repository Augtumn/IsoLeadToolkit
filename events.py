"""
Event Handlers
Manages user interactions: hover, click, and legend events
"""
import pandas as pd
import os
from config import CONFIG
from state import app_state


def on_hover(event):
    """Handle mouse hover events"""
    try:
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
        from visualization import plot_embedding
        
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
            algorithm = app_state.algorithm
            print(f"[DEBUG] Current algorithm: {algorithm}", flush=True)
            
            # Render plot with current parameters from app_state
            # Parameters are already updated by control_panel._on_change()
            print(f"[DEBUG] Calling plot_embedding with algorithm={algorithm}, group_col={group_col}", flush=True)
            if plot_embedding(group_col, algorithm, 
                             umap_params=app_state.umap_params,
                             tsne_params=app_state.tsne_params,
                             size=app_state.point_size):
                print("[DEBUG] Plot rendered successfully, calling draw_idle", flush=True)
                try:
                    app_state.fig.canvas.draw_idle()
                except Exception as draw_err:
                    print(f"[WARN] Draw error: {draw_err}", flush=True)
            else:
                print("[WARN] plot_embedding returned False", flush=True)
        except Exception as plot_err:
            print(f"[ERROR] Plotting error: {plot_err}", flush=True)
            import traceback
            traceback.print_exc()
    except Exception as e:
        print(f"[ERROR] on_slider_change error: {e}", flush=True)
        import traceback
        traceback.print_exc()
