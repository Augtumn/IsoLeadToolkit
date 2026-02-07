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

        # Main content area with side navigation
        content_wrap = ttk.Frame(container, style='ControlPanel.TFrame')
        content_wrap.pack(fill=tk.BOTH, expand=True)

        nav_frame = ttk.Frame(content_wrap, style='ControlPanel.TFrame')
        nav_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        content_frame = ttk.Frame(content_wrap, style='ControlPanel.TFrame')
        content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        nav_header = ttk.Label(nav_frame, text=self._translate("Sections"), style='Subheader.TLabel')
        nav_header.pack(anchor=tk.W, pady=(0, 6))
        self._register_translation(nav_header, "Sections")

        self.section_frames = {}
        self._section_buttons = {}

        def _build_modeling_section(parent):
            scroll_frame = self._build_scrollable_frame(parent)
            self._build_settings_content(scroll_frame)
            self._build_algorithm_content(scroll_frame)

        def _build_display_section(parent):
            scroll_frame = self._build_scrollable_frame(parent)
            self._build_style_content(scroll_frame)

        sections = [
            ("Modeling", _build_modeling_section),
            ("Display", _build_display_section),
            ("Legend", self._build_legend_tab),
            ("Tools", self._build_tools_tab),
            ("Geochemistry", self._build_geo_tab),
        ]

        def show_section(key):
            for name, frame in self.section_frames.items():
                frame.pack_forget()
            target = self.section_frames.get(key)
            if target is not None:
                target.pack(fill=tk.BOTH, expand=True)
            for name, btn in self._section_buttons.items():
                btn.configure(style='Secondary.TButton' if name == key else 'TButton')

        for key, builder in sections:
            btn = ttk.Button(nav_frame, text=self._translate(key), command=lambda k=key: show_section(k))
            btn.pack(fill=tk.X, pady=2)
            self._register_translation(btn, key)
            self._section_buttons[key] = btn

            frame = ttk.Frame(content_frame, style='ControlPanel.TFrame')
            builder(frame)
            self.section_frames[key] = frame

        show_section(sections[0][0])

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
