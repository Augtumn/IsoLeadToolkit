"""
Control Panel - Interactive Parameter Adjustment
Tkinter-based control panel for UMAP/t-SNE parameters and visualization settings

This module has been refactored into multiple Mixin classes for better maintainability:
- mixins/utils.py: Utility methods (translation, UI helpers)
- mixins/handlers.py: Core event handlers
- mixins/dialogs.py: Dialog windows
- mixins/export.py: Data export functionality
- tabs/: Tab-specific builders (settings, algorithm, tools, style, legend, geochemistry)
"""
import tkinter as tk
from tkinter import ttk

from core.localization import available_languages
from core import app_state

# Import Mixins from subpackages
from .mixins import (
    PanelUtilsMixin,
    PanelHandlersMixin,
    PanelDialogsMixin,
    PanelExportMixin,
)
from .tabs import (
    SettingsTabMixin,
    AlgorithmTabMixin,
    ToolsTabMixin,
    StyleTabMixin,
    LegendTabMixin,
    GeochemistryTabMixin,
)


class ControlPanel(
    PanelUtilsMixin,
    PanelHandlersMixin,
    PanelDialogsMixin,
    PanelExportMixin,
    SettingsTabMixin,
    AlgorithmTabMixin,
    ToolsTabMixin,
    StyleTabMixin,
    LegendTabMixin,
    GeochemistryTabMixin,
):
    """Interactive control panel for algorithm parameters
    
    This class inherits from multiple Mixin classes that provide:
    - PanelUtilsMixin: Translation, scrollable frames, section creation, sliders
    - PanelHandlersMixin: _on_change, update_selection_controls, language handling
    - PanelDialogsMixin: Tooltip and group column configuration dialogs
    - PanelExportMixin: CSV/Excel export, data reload, subset analysis
    - SettingsTabMixin: Settings tab (projection mode, data config)
    - AlgorithmTabMixin: Algorithm tab (UMAP, t-SNE, PCA, Ternary, V1V2 parameters)
    - ToolsTabMixin: Tools tab (selection, export buttons, analysis tools)
    - StyleTabMixin: Style tab (themes, fonts, markers) + style setup
    - LegendTabMixin: Legend tab (group visibility, colors)
    - GeochemistryTabMixin: Geochemistry tab (model parameters)
    """
    
    def __init__(self, callback):
        """
        Initialize control panel
        
        Args:
            callback: function to call when parameters change
        """
        self.callback = callback
        self._translations = []
        self._ternary_update_job = None  # timer for debouncing scale updates

        # Reuse Matplotlib's Tk root when available so the panel shares the
        # same event loop and remains responsive while plt.show() runs.
        master = tk._default_root
        self._owns_master = False
        if master is None:
            master = tk.Tk()
            master.withdraw()
            self._owns_master = True

        self.master = master
        self.root = tk.Toplevel(master)
        self.root.title(self._translate("Control Panel"))
        self._register_translation(self.root, "Control Panel", attr='title')
        self.root.geometry("560x860")
        self.root.minsize(520, 740)
        self.root.resizable(True, True)
        self.root.configure(bg="#edf2f7")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.is_visible = True

        self.primary_bg = "#edf2f7"
        self.card_bg = "#ffffff"
        self.style = None
        self._language_labels = dict(available_languages())
        self.language_choice = None
        self.language_combobox = None
        self._setup_styles()
        
        # Store slider references
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self.check_vars = {}  # For checkboxes
        self.style_vars = {}  # For style checkboxes
        self.geo_vars = {}    # For geochemistry parameters (shared across tabs)
        self._slider_after = {}
        self._slider_steps = {}
        self._slider_delay_ms = 350

        self.selection_button = None
        self.ellipse_selection_button = None
        self.selection_status = None
        self.export_csv_button = None
        self.export_excel_button = None
        
        self._create_widgets()
        self._refresh_language()
        self.update_selection_controls()
        app_state.register_language_listener(self.refresh_language)

        # Try to raise the panel so it is not hidden behind the figure window.
        try:
            if master is not None:
                self.root.transient(master)
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass
    
    def _create_widgets(self):
        """Create GUI widgets with improved styling using Tabs"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main container
        container = ttk.Frame(self.root, padding=(10, 10, 10, 10), style='ControlPanel.TFrame')
        container.pack(fill=tk.BOTH, expand=True)

        # Header
        header_frame = ttk.Frame(container, style='ControlPanel.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        header = ttk.Label(header_frame, text=self._translate("Visualization Controls"), style='Header.TLabel')
        header.pack(side=tk.LEFT)
        self._register_translation(header, "Visualization Controls")

        # Data Count Label
        self.data_count_label = ttk.Label(header_frame, text="", style='Subheader.TLabel')
        self.data_count_label.pack(side=tk.RIGHT, padx=10)

        # Notebook (Tabs)
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Projection
        self.tab_settings = ttk.Frame(self.notebook, style='ControlPanel.TFrame')
        self.notebook.add(self.tab_settings, text=self._translate("Projection"))
        self._register_translation(self.notebook, "Projection", attr='tab', formatter=lambda: {'tab_id': 0})

        # Tab 2: Algorithm (Parameters)
        self.tab_algo = ttk.Frame(self.notebook, style='ControlPanel.TFrame')
        self.notebook.add(self.tab_algo, text=self._translate("Algorithm"))
        self._register_translation(self.notebook, "Algorithm", attr='tab', formatter=lambda: {'tab_id': 1})

        # Tab 3: Tools (Selection & Export)
        self.tab_tools = ttk.Frame(self.notebook, style='ControlPanel.TFrame')
        self.notebook.add(self.tab_tools, text=self._translate("Tools"))
        self._register_translation(self.notebook, "Tools", attr='tab', formatter=lambda: {'tab_id': 2})
        
        # Tab 4: Style (New!)
        self.tab_style = ttk.Frame(self.notebook, style='ControlPanel.TFrame')
        self.notebook.add(self.tab_style, text=self._translate("Style"))
        self._register_translation(self.notebook, "Style", attr='tab', formatter=lambda: {'tab_id': 3})

        # Tab 5: Legend
        self.tab_legend = ttk.Frame(self.notebook, style='ControlPanel.TFrame')
        self.notebook.add(self.tab_legend, text=self._translate("Legend"))
        self._register_translation(self.notebook, "Legend", attr='tab', formatter=lambda: {'tab_id': 4})
        
        # Tab 6: Geochemistry
        self.tab_geo = ttk.Frame(self.notebook, style='ControlPanel.TFrame')
        self.notebook.add(self.tab_geo, text=self._translate("Geochemistry"))
        self._register_translation(self.notebook, "Geochemistry", attr='tab', formatter=lambda: {'tab_id': 5})

        # --- Populate Tab 1: Settings ---
        self._build_settings_tab(self.tab_settings)

        # --- Populate Tab 2: Algorithm ---
        self._build_algorithm_tab(self.tab_algo)

        # --- Populate Tab 3: Tools ---
        self._build_tools_tab(self.tab_tools)
        
        # --- Populate Tab 4: Style ---
        self._build_style_tab(self.tab_style)
        
        # --- Populate Tab 5: Legend ---
        self._build_legend_tab(self.tab_legend)
        
        # --- Populate Tab 6: Geochemistry ---
        self._build_geo_tab(self.tab_geo)

        # Footer
        action_frame = ttk.Frame(container, style='ControlPanel.TFrame')
        action_frame.pack(fill=tk.X, pady=(10, 0))

        close_button = ttk.Button(
            action_frame,
            text=self._translate("Close Panel"),
            style='Accent.TButton',
            command=self._on_close
        )
        close_button.pack(side=tk.RIGHT)
        self._register_translation(close_button, "Close Panel")

        self.update_selection_controls()
        self._update_data_count_label()

    def show(self):
        """Show the control panel"""
        print("[INFO] Control panel displayed", flush=True)
        self.root.mainloop()

    def destroy(self):
        """Destroy the control panel and master if owned"""
        try:
            for pending in list(self._slider_after.values()):
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
            self._slider_after.clear()
            self.root.destroy()
        finally:
            try:
                if self.refresh_language in getattr(app_state, 'language_listeners', []):
                    app_state.language_listeners.remove(self.refresh_language)
            except Exception:
                pass
            if getattr(self, "_owns_master", False) and getattr(self, "master", None) is not None:
                try:
                    self.master.destroy()
                except Exception:
                    pass

    def open(self):
        """Bring the control panel window back if it was hidden"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_visible = True
        except Exception as exc:
            print(f"[WARN] Unable to reopen control panel: {exc}", flush=True)

    def _on_close(self):
        """Handle window close without tearing down shared Tk root"""
        try:
            self.root.withdraw()
            self.is_visible = False
        except Exception:
            pass


def create_control_panel(callback):
    """
    Create and return a control panel instance
    
    Args:
        callback: function to call when parameters change
    
    Returns:
        ControlPanel instance
    """
    return ControlPanel(callback)
