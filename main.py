"""
Isotopes Analysis - UMAP Visualization Tool
A robust interactive visualization for lead isotope data analysis

Modular structure:
- config.py: Configuration management
- state.py: Global application state
- data.py: Data loading and processing
- visualization.py: UMAP embedding and plotting
- events.py: Event handlers for user interactions
- session.py: Session parameter persistence
- main.py: Application entry point
"""
import sys
import warnings
import traceback
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

from config import CONFIG
from state import app_state
from data import load_data
from visualization import plot_umap
from events import on_hover, on_click, on_legend_click, on_slider_change
from session import load_session_params, save_session_params
from control_panel import create_control_panel

# Configure warnings
warnings.filterwarnings("ignore", message=".*n_jobs value.*overridden.*random_state.*")

# Configure matplotlib backend
try:
    matplotlib.use('TkAgg')
except Exception:
    print("[WARN] TkAgg backend not available, using Agg", flush=True)
    matplotlib.use('Agg')


def _save_session(state_module):
    """Helper function to save session parameters"""
    print("[INFO] Saving session parameters...", flush=True)
    group_col = app_state.last_group_col or 'Province'
    try:
        if state_module.radio_g is not None:
            group_col = state_module.radio_g.value_selected
    except:
        pass
    
    save_session_params(
        algorithm=app_state.algorithm,
        umap_params=app_state.umap_params,
        tsne_params=app_state.tsne_params,
        point_size=app_state.point_size,
        group_col=group_col,
        group_cols=app_state.group_cols,
        data_cols=app_state.data_cols,
        file_path=app_state.file_path,
        sheet_name=app_state.sheet_name,
        render_mode=app_state.render_mode,
        selected_2d_cols=getattr(app_state, 'selected_2d_cols', []),
        selected_3d_cols=app_state.selected_3d_cols
    )


def main():
    """Initialize and run the application"""
    import state
    
    print("[INFO] Initializing application...", flush=True)
    
    try:
        # Load previous session to get file/sheet info
        print("[INFO] Loading session parameters...", flush=True)
        session_data = load_session_params()
        
        # Load data with dialogs
        print("[INFO] Loading data...", flush=True)
        if not load_data(show_file_dialog=True, show_config_dialog=True):
            print("[ERROR] Failed to load data. Exiting.", flush=True)
            return False
        
        print("[INFO] Data loaded successfully.", flush=True)
        
        # Ensure last_group_col is set from data (highest priority)
        if not app_state.last_group_col and app_state.group_cols:
            app_state.last_group_col = app_state.group_cols[0]
            print(f"[INFO] Set default group column: {app_state.last_group_col}", flush=True)
        
        # Restore session parameters if available (but don't override group_cols/data_cols from data)
        if session_data:
            # Algorithm parameters
            app_state.algorithm = session_data.get('algorithm', 'UMAP')
            print(f"[INFO] Algorithm from session: {app_state.algorithm}", flush=True)

            app_state.umap_params.update(session_data.get('umap_params', {}))
            app_state.tsne_params.update(session_data.get('tsne_params', {}))
            app_state.point_size = session_data.get('point_size', app_state.point_size)

            render_mode = session_data.get('render_mode')
            if not render_mode:
                legacy_mode = session_data.get('plot_mode')
                if legacy_mode == '3D':
                    render_mode = '3D'
                elif legacy_mode == '2D':
                    render_mode = '2D'
                else:
                    render_mode = app_state.algorithm

            app_state.render_mode = render_mode or 'UMAP'
            app_state.selected_2d_cols = session_data.get('selected_2d_cols', [])
            app_state.selected_3d_cols = session_data.get('selected_3d_cols', [])

            # Group column: restore from session if it exists in current data
            session_group_col = session_data.get('group_col')
            if session_group_col and session_group_col in app_state.group_cols:
                app_state.last_group_col = session_group_col
                print(f"[INFO] Group column restored from session: {app_state.last_group_col}", flush=True)
        else:
            # No session data: ensure algorithm is UMAP by default
            app_state.algorithm = 'UMAP'
            app_state.render_mode = 'UMAP'
            print(f"[INFO] No session data, using default algorithm: UMAP", flush=True)
        
        # Determine sensible default plot mode based on available numeric columns
        num_numeric_cols = len(app_state.data_cols)
        if app_state.render_mode == '3D' and num_numeric_cols < 3:
            if num_numeric_cols >= 2:
                print("[INFO] Not enough numeric columns for 3D; switching to 2D scatter.", flush=True)
                app_state.render_mode = '2D'
            else:
                print("[INFO] Not enough numeric columns for 3D; switching to UMAP.", flush=True)
                app_state.render_mode = 'UMAP'

        if app_state.render_mode == '2D' and num_numeric_cols < 2:
            print("[INFO] Not enough numeric columns for 2D; switching to UMAP.", flush=True)
            app_state.render_mode = 'UMAP'

        if app_state.render_mode == '3D':
            if num_numeric_cols == 3:
                app_state.selected_3d_cols = app_state.data_cols[:3]
            else:
                valid_cols = [col for col in app_state.selected_3d_cols if col in app_state.data_cols][:3]
                if len(valid_cols) == 3:
                    app_state.selected_3d_cols = valid_cols
                else:
                    app_state.selected_3d_cols = []
                    print("[INFO] Stored 3D column selection invalid or incomplete; will prompt user on demand.", flush=True)

        if app_state.render_mode == '2D':
            if num_numeric_cols == 2:
                app_state.selected_2d_cols = app_state.data_cols[:2]
            else:
                valid_2d = [col for col in app_state.selected_2d_cols if col in app_state.data_cols][:2]
                if len(valid_2d) == 2:
                    app_state.selected_2d_cols = valid_2d
                else:
                    app_state.selected_2d_cols = []
                    print("[INFO] Stored 2D column selection invalid or incomplete; will prompt user on demand.", flush=True)

        if app_state.render_mode in ('UMAP', 'tSNE'):
            app_state.algorithm = 'UMAP' if app_state.render_mode == 'UMAP' else 'tSNE'

        # Create plot figure (main window for visualization)
        print("[INFO] Creating plot figure...", flush=True)
        app_state.fig, app_state.ax = plt.subplots(figsize=CONFIG['figure_size'])
        app_state.fig.suptitle(
            "Lead Isotope Analysis - UMAP/t-SNE Visualization",
            fontsize=13,
            fontweight='bold',
            y=0.98
        )
        print("[INFO] Plot figure created.", flush=True)
        
        plt.ion()
        app_state.fig.subplots_adjust(left=0.08, bottom=0.12, right=0.78, top=0.9)

        # Add quick access button to reopen the control panel if it is hidden
        button_ax = app_state.fig.add_axes([0.82, 0.035, 0.14, 0.05])
        button = Button(button_ax, 'Control Panel', color='#2563eb', hovercolor='#1d4ed8')
        button.label.set_color('white')
        button.label.set_fontsize(10)

        def _show_control_panel(event=None):
            try:
                if hasattr(state, 'control_panel') and state.control_panel is not None:
                    state.control_panel.open()
                else:
                    print('[WARN] Control panel is unavailable', flush=True)
            except Exception as btn_err:
                print(f"[WARN] Failed to open control panel: {btn_err}", flush=True)

        button.on_clicked(_show_control_panel)
        app_state.control_panel_button = button
        
        # Create tkinter control panel (separate window)
        print("[INFO] Creating control panel...", flush=True)
        control_panel = create_control_panel(on_slider_change)
        
        # Store reference in state module for callbacks
        state.control_panel = control_panel
        app_state.control_panel_ref = control_panel
        
        # Connect event handlers to plot figure
        print("[INFO] Connecting event handlers...", flush=True)
        app_state.fig.canvas.mpl_connect('motion_notify_event', on_hover)
        app_state.fig.canvas.mpl_connect('button_press_event', on_click)
        app_state.fig.canvas.mpl_connect('button_press_event', on_legend_click)
        print("[INFO] Event handlers connected.", flush=True)
        
        # Initial plot
        print("[INFO] Rendering initial plot...", flush=True)
        on_slider_change()
        print("[INFO] Plot ready.", flush=True)
        
        # Print instructions
        print("[INFO] Application Controls:", flush=True)
        print("  * Use the Control Panel window to adjust parameters", flush=True)
        print("  * Algorithm selector -> Choose UMAP or t-SNE", flush=True)
        print("  * Point size -> Adjust marker size", flush=True)
        print("  * Hover over points -> View Lab No. / Site / Period", flush=True)
        print("  * Left click point -> Export sample to CSV", flush=True)
        print("  * Click legend item -> Bring group to front", flush=True)
        print("[INFO] Application started. Close the windows to exit.", flush=True)
        
        # Show both plots
        print("[INFO] Showing windows...", flush=True)
        try:
            backend = matplotlib.get_backend()
            print(f"[INFO] Using backend: {backend}", flush=True)
            
            plt.show(block=True)
            print("[INFO] Windows closed normally.", flush=True)
            _save_session(state)
            if hasattr(state, 'control_panel'):
                try:
                    state.control_panel.destroy()
                except Exception:
                    pass
            return True
        except KeyboardInterrupt:
            print("[INFO] Application terminated by user.", flush=True)
            _save_session(state)
            if hasattr(state, 'control_panel'):
                try:
                    state.control_panel.destroy()
                except Exception:
                    pass
            return True
        except Exception as show_err:
            print(f"[ERROR] plt.show() error: {show_err}", flush=True)
            print("[INFO] Attempting to close figures...", flush=True)
            _save_session(state)
            try:
                plt.close(app_state.fig)
                if hasattr(state, 'control_panel'):
                    try:
                        state.control_panel.destroy()
                    except Exception:
                        pass
            except:
                pass
            return False
            
    except Exception as e:
        print(f"[ERROR] Application error: {e}", flush=True)
        traceback.print_exc()
        return False
    finally:
        print("[INFO] Cleanup complete.", flush=True)


if __name__ == "__main__":
    try:
        print("[START] Application launching...", flush=True)
        success = main()
        print(f"[END] Application exit code: {0 if success else 1}", flush=True)
        sys.exit(0 if success else 1)
    except Exception as final_err:
        print(f"[FATAL] Uncaught exception: {final_err}", flush=True)
        traceback.print_exc()
        sys.exit(1)
