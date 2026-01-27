"""
Application Initialization and Lifecycle Management
Handles application startup, configuration, and cleanup
"""
import sys
import warnings
import traceback
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import font_manager
import tkinter as tk
from tkinter import ttk

from . import (
    CONFIG, app_state,
    load_session_params, save_session_params,
    translate, set_language, validate_language
)
from data.loader import load_data
from visualization.events import on_hover, on_click, on_legend_click, on_slider_change
from ui.panel import create_control_panel


def _enable_high_dpi_awareness():
    """Enable per-monitor DPI awareness on Windows to reduce blurry fonts."""
    if not sys.platform.startswith('win'):
        return
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _configure_matplotlib_fonts():
    """Configure Matplotlib to use a font that supports Chinese glyphs."""
    preferred_fonts = CONFIG.get('preferred_plot_fonts', [])
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    chosen_font = None

    for name in preferred_fonts:
        if name in available_fonts:
            chosen_font = name
            break

    if chosen_font:
        matplotlib.rcParams['font.family'] = 'sans-serif'
        matplotlib.rcParams['font.sans-serif'] = [chosen_font, 'Arial', 'sans-serif']
        print(f"[INFO] Using plot font: {chosen_font}", flush=True)
    else:
        print("[WARN] Preferred plot fonts not found; falling back to default sans-serif font.", flush=True)

    matplotlib.rcParams['axes.unicode_minus'] = False
    dpi_value = CONFIG.get('figure_dpi')
    if dpi_value:
        matplotlib.rcParams['figure.dpi'] = dpi_value
        matplotlib.rcParams['savefig.dpi'] = dpi_value


def _configure_matplotlib():
    """Configure matplotlib backend and fonts."""
    # Configure warnings
    warnings.filterwarnings("ignore", message=".*n_jobs value.*overridden.*random_state.*")
    
    # Configure matplotlib backend
    _enable_high_dpi_awareness()
    try:
        matplotlib.use('TkAgg')
    except Exception:
        print("[WARN] TkAgg backend not available, using Agg", flush=True)
        matplotlib.use('Agg')
    
    _configure_matplotlib_fonts()


class Application:
    """Main application class managing initialization and lifecycle"""
    
    def __init__(self):
        """Initialize the application"""
        self.control_panel = None
        _configure_matplotlib()
    
    def _save_session(self):
        """Helper function to save session parameters"""
        from core import state  # Import here to avoid circular dependency
        
        print("[INFO] Saving session parameters...", flush=True)
        group_col = app_state.last_group_col or 'Province'
        try:
            if state.radio_g is not None:
                group_col = state.radio_g.value_selected
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
            selected_3d_cols=app_state.selected_3d_cols,
            language=app_state.language,
            tooltip_columns=getattr(app_state, 'tooltip_columns', None),
            ui_theme=getattr(app_state, 'ui_theme', 'Modern Light')
        )
    
    def _load_session(self):
        """Load session parameters and restore application state"""
        print("[INFO] Loading session parameters...", flush=True)
        session_data = load_session_params()

        requested_language = None
        if session_data:
            requested_language = session_data.get('language')
        if not requested_language:
            requested_language = app_state.language or CONFIG.get('default_language')
        if not validate_language(requested_language):
            requested_language = CONFIG.get('default_language', 'en')
        set_language(requested_language)
        
        return session_data
    
    def _restore_session_state(self, session_data):
        """Restore application state from session data"""
        if not session_data:
            # No session data: ensure algorithm is UMAP by default
            app_state.algorithm = 'UMAP'
            app_state.render_mode = 'UMAP'
            print(f"[INFO] No session data, using default algorithm: UMAP", flush=True)
            return
        
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
        
        # Restore tooltip columns
        saved_cols = session_data.get('tooltip_columns')
        if saved_cols is not None:
            app_state.tooltip_columns = saved_cols
            print(f"[DEBUG] Restored tooltip columns from session: {saved_cols}", flush=True)
        else:
            print(f"[DEBUG] No tooltip columns in session, using default: {app_state.tooltip_columns}", flush=True)

        # Restore UI Theme
        app_state.ui_theme = session_data.get('ui_theme') or 'Modern Light'
        print(f"[INFO] Restored UI theme: {app_state.ui_theme}", flush=True)

        # Group column: restore from session if it exists in current data
        session_group_col = session_data.get('group_col')
        if session_group_col and session_group_col in app_state.group_cols:
            app_state.last_group_col = session_group_col
            print(f"[INFO] Group column restored from session: {app_state.last_group_col}", flush=True)
    
    def _validate_render_mode(self):
        """Validate and adjust render mode based on available numeric columns"""
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
    
    def _create_plot_figure(self):
        """Create the main plot figure"""
        print("[INFO] Creating plot figure...", flush=True)
        # Use constrained_layout for adaptive layout
        app_state.fig, app_state.ax = plt.subplots(figsize=CONFIG['figure_size'], constrained_layout=True)

        # Auto-adjust layout on resize to avoid clipping
        def _on_resize(event):
            try:
                if app_state.fig is None:
                    return
                app_state.fig.set_constrained_layout(True)
                app_state.fig.tight_layout()
                app_state.fig.canvas.draw_idle()
            except Exception:
                pass
        try:
            app_state.fig.canvas.mpl_connect('resize_event', _on_resize)
        except Exception:
            pass
        
        def _apply_language_to_main_ui():
            if app_state.control_panel_button is not None:
                label_text = translate("Control Panel")
                if isinstance(app_state.control_panel_button, tk.Button):
                    app_state.control_panel_button.config(text=label_text)
                elif hasattr(app_state.control_panel_button, 'label'):
                    app_state.control_panel_button.label.set_text(label_text)

        app_state.register_language_listener(_apply_language_to_main_ui)
        _apply_language_to_main_ui()
        print("[INFO] Plot figure created.", flush=True)
        
        plt.ion()
    
    def _add_control_panel_button(self):
        """Add Control Panel button to Matplotlib Toolbar"""
        import core.state as state  # Import here to avoid circular dependency
        
        def _show_control_panel(event=None):
            try:
                if hasattr(state, 'control_panel') and state.control_panel is not None:
                    state.control_panel.open()
                else:
                    print('[WARN] Control panel is unavailable', flush=True)
            except Exception as btn_err:
                print(f"[WARN] Failed to open control panel: {btn_err}", flush=True)

        try:
            toolbar = app_state.fig.canvas.toolbar
            if toolbar and isinstance(toolbar, tk.Widget):
                # Add a separator
                try:
                    ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=2)
                except Exception:
                    pass  # ttk might not be initialized on this root
                
                # Create Tkinter button
                cp_btn = tk.Button(
                    toolbar,
                    text=translate("Control Panel"),
                    command=_show_control_panel,
                    bg='#2563eb',
                    fg='white',
                    font=('Segoe UI', 9),
                    relief='flat',
                    padx=8
                )
                cp_btn.pack(side=tk.LEFT, padx=2, pady=2)
                
                # Hover effect
                def on_enter(e): cp_btn['background'] = '#1d4ed8'
                def on_leave(e): cp_btn['background'] = '#2563eb'
                cp_btn.bind("<Enter>", on_enter)
                cp_btn.bind("<Leave>", on_leave)
                
                app_state.control_panel_button = cp_btn
                
        except Exception as tb_err:
            print(f"[WARN] Failed to add button to toolbar: {tb_err}", flush=True)
    
    def _setup_control_panel(self):
        """Create and setup the control panel"""
        from core import state  # Import here to avoid circular dependency
        
        print("[INFO] Creating control panel...", flush=True)
        control_panel = create_control_panel(on_slider_change)
        
        # Store reference in state module for callbacks
        state.control_panel = control_panel
        app_state.control_panel_ref = control_panel
        self.control_panel = control_panel
    
    def _connect_event_handlers(self):
        """Connect event handlers to plot figure"""
        print("[INFO] Connecting event handlers...", flush=True)
        app_state.fig.canvas.mpl_connect('motion_notify_event', on_hover)
        app_state.fig.canvas.mpl_connect('button_press_event', on_click)
        app_state.fig.canvas.mpl_connect('button_press_event', on_legend_click)
        print("[INFO] Event handlers connected.", flush=True)
    
    def _render_initial_plot(self):
        """Render the initial plot"""
        print("[INFO] Rendering initial plot...", flush=True)
        on_slider_change()
        print("[INFO] Plot ready.", flush=True)
    
    def _print_instructions(self):
        """Print application usage instructions"""
        print("[INFO] Application Controls:", flush=True)
        print("  * Use the Control Panel window to adjust parameters", flush=True)
        print("  * Algorithm selector -> Choose UMAP or t-SNE", flush=True)
        print("  * Point size -> Adjust marker size", flush=True)
        print("  * Hover over points -> View Lab No. / Site / Period", flush=True)
        print("  * Left click point -> Export sample to CSV", flush=True)
        print("  * Click legend item -> Bring group to front", flush=True)
        print("[INFO] Application started. Close the windows to exit.", flush=True)
    
    def _cleanup(self):
        """Cleanup resources"""
        from core import state  # Import here to avoid circular dependency
        
        if hasattr(state, 'control_panel') and state.control_panel is not None:
            try:
                state.control_panel.destroy()
            except Exception:
                pass
    
    def run(self):
        """Initialize and run the application"""
        import core.state  # Import here to avoid circular dependency
        
        print("[INFO] Initializing application...", flush=True)
        
        try:
            # Load session
            session_data = self._load_session()
            if session_data:
                app_state.file_path = session_data.get('file_path') or app_state.file_path
                app_state.sheet_name = session_data.get('sheet_name') or app_state.sheet_name
                app_state.group_cols = session_data.get('group_cols') or []
                app_state.data_cols = session_data.get('data_cols') or []
            
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
            
            # Restore session parameters
            self._restore_session_state(session_data)
            
            # Validate render mode
            self._validate_render_mode()
            
            # Create plot figure
            self._create_plot_figure()
            
            # Add control panel button
            self._add_control_panel_button()
            
            # Setup control panel
            self._setup_control_panel()
            
            # Connect event handlers
            self._connect_event_handlers()
            
            # Render initial plot
            self._render_initial_plot()
            
            # Print instructions
            self._print_instructions()
            
            # Show windows
            print("[INFO] Showing windows...", flush=True)
            try:
                backend = matplotlib.get_backend()
                print(f"[INFO] Using backend: {backend}", flush=True)
                
                plt.show(block=True)
                print("[INFO] Windows closed normally.", flush=True)
                self._save_session()
                self._cleanup()
                return True
            except KeyboardInterrupt:
                print("[INFO] Application terminated by user.", flush=True)
                self._save_session()
                self._cleanup()
                return True
            except Exception as show_err:
                print(f"[ERROR] plt.show() error: {show_err}", flush=True)
                print("[INFO] Attempting to close figures...", flush=True)
                self._save_session()
                try:
                    plt.close(app_state.fig)
                    self._cleanup()
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"[ERROR] Application error: {e}", flush=True)
            traceback.print_exc()
            return False
        finally:
            print("[INFO] Cleanup complete.", flush=True)
