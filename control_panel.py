"""
Control Panel - Interactive Parameter Adjustment
Tkinter-based control panel for UMAP/t-SNE parameters and visualization settings
"""
import os
import re
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, simpledialog, filedialog, colorchooser

import pandas as pd
import numpy as np
from matplotlib import font_manager
import style_manager
from localization import translate, available_languages, set_language
from state import app_state
import state as state_module
from events import toggle_selection_mode
from session import save_session_params

try:
    from V1V2 import calculate_all_parameters
except ImportError:
    calculate_all_parameters = None


class ControlPanel:
    """Interactive control panel for algorithm parameters"""
    
    def __init__(self, callback):
        """
        Initialize control panel
        
        Args:
            callback: function to call when parameters change
        """
        self.callback = callback
        self._translations = []
        self._ternary_update_job = None # timer for debouncing scale updates

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
        self.root.geometry("520x820")
        self.root.minsize(420, 620)
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

        # Tab 1: Settings (General)
        self.tab_settings = ttk.Frame(self.notebook, style='ControlPanel.TFrame')
        self.notebook.add(self.tab_settings, text=self._translate("Settings"))
        self._register_translation(self.notebook, "Settings", attr='tab', formatter=lambda: {'tab_id': 0})

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

    def _update_data_count_label(self):
        """Update the label showing the number of loaded data rows."""
        if app_state.df_global is not None:
            count = len(app_state.df_global)
            text = self._translate("Loaded Data: {count} rows", count=count)
            self.data_count_label.config(text=text)
        else:
            self.data_count_label.config(text="")

    def _build_scrollable_frame(self, parent):
        """
        Helper to create a scrollable frame inside a tab.
        
        Creates a Canvas and Scrollbar. The Scrollbar is packed to the right,
        and the Canvas fills the remaining space to the left.
        A frame is placed inside the canvas window.
        
        Args:
            parent: The parent widget (usually a tab frame)
            
        Returns:
            ttk.Frame: The inner scrollable frame where widgets should be added.
        """
        canvas = tk.Canvas(parent, highlightthickness=0, bd=0, background=self.primary_bg)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='ControlPanel.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind canvas configure to update frame width
        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to canvas and its children
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        return scrollable_frame

    def _build_settings_tab(self, parent):
        frame = self._build_scrollable_frame(parent)
        
        # Projection Mode
        if not getattr(app_state, 'render_mode', None):
            app_state.render_mode = getattr(app_state, 'algorithm', 'UMAP')
        self.radio_vars['render_mode'] = tk.StringVar(value=app_state.render_mode)

        algo_section = self._create_section(
            frame,
            "Projection Mode",
            "Select between UMAP or t-SNE embeddings, or display raw measurements in either 2D or 3D space."
        )

        selection_grid = ttk.Frame(algo_section, style='CardBody.TFrame')
        selection_grid.pack(fill=tk.X, pady=(4, 0))

        options = [
            ("UMAP Embedding", "UMAP"),
            ("t-SNE Embedding", "tSNE"),
            ("PCA Embedding", "PCA"),
            ("Robust PCA", "RobustPCA"),
            ("V1-V2 Diagram", "V1V2"),
            ("Ternary Plot", "Ternary"),
            ("2D Scatter (raw)", "2D"),
            ("3D Scatter (raw)", "3D"),
        ]

        for idx, (label_key, value) in enumerate(options):
            column = idx // 3  # 2 columns
            row = idx % 3
            cell = ttk.Frame(selection_grid, style='CardBody.TFrame')
            cell.grid(row=row, column=column, sticky=tk.W, padx=(0 if column == 0 else 16, 0), pady=2)
            radio = ttk.Radiobutton(
                cell,
                text=self._translate(label_key),
                variable=self.radio_vars['render_mode'],
                value=value,
                command=self._on_change,
                style='Option.TRadiobutton'
            )
            radio.pack(anchor=tk.W)
            self._register_translation(radio, label_key)

        # Add "Select Axis Columns" button
        col_select_btn = ttk.Button(
            algo_section,
            text=self._translate("Select Axis Columns"),
            command=self._open_column_selection,
            style='Secondary.TButton'
        )
        col_select_btn.pack(anchor=tk.W, pady=(8, 4))
        self._register_translation(col_select_btn, "Select Axis Columns")

        # Data Configuration
        data_section = self._create_section(
            frame,
            "Data Configuration",
            "Configure data to display when hovering over points."
        )

        # Tooltip Settings
        tooltip_btn = ttk.Button(
            data_section,
            text=self._translate("Configure Tooltip"),
            command=self._open_tooltip_settings,
            style='Accent.TButton'
        )
        tooltip_btn.pack(anchor=tk.W, pady=(12, 4))
        self._register_translation(tooltip_btn, "Configure Tooltip")

    def _build_style_tab(self, parent):
        """Build the Style tab"""
        frame = self._build_scrollable_frame(parent)
        
        # --- Theme Management ---
        theme_section = self._create_section(
            frame,
            "Interface Theme",
            "Select the overall look and feel of the application."
        )

        ui_theme_frame = ttk.Frame(theme_section, style='CardBody.TFrame')
        ui_theme_frame.pack(fill=tk.X, pady=(0, 8))
        
        lbl_ui_theme = ttk.Label(ui_theme_frame, text=self._translate("UI Theme:"), style='Body.TLabel')
        lbl_ui_theme.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(lbl_ui_theme, "UI Theme:")

        self.ui_theme_var = tk.StringVar(value=getattr(app_state, 'ui_theme', 'Modern Light'))
        ui_theme_combo = ttk.Combobox(
            ui_theme_frame, 
            textvariable=self.ui_theme_var, 
            values=style_manager.style_manager_instance.get_ui_theme_names(),
            state="readonly"
        )
        ui_theme_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ui_theme_combo.bind("<<ComboboxSelected>>", self._on_ui_theme_change)

        # --- Saved Plot Settings ---
        saved_section = self._create_section(
            frame,
            "Saved Plot Settings",
            "Save and load custom plot parameter sets (Grid, Fonts, Palette)."
        )
        
        theme_frame = ttk.Frame(saved_section, style='CardBody.TFrame')
        theme_frame.pack(fill=tk.X, pady=(0, 8))
        
        # Theme Name Entry
        lbl_name = ttk.Label(theme_frame, text=self._translate("Theme Name:"), style='Body.TLabel')
        lbl_name.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(lbl_name, "Theme Name:")

        self.theme_name_var = tk.StringVar()
        ttk.Entry(theme_frame, textvariable=self.theme_name_var, width=15).pack(side=tk.LEFT, padx=(0, 10))
        
        # Save Button
        btn_save = ttk.Button(theme_frame, text=self._translate("Save"), command=self._save_theme, style='Secondary.TButton', width=6)
        btn_save.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(btn_save, "Save")
        
        # Load/Delete Frame
        load_frame = ttk.Frame(theme_section, style='CardBody.TFrame')
        load_frame.pack(fill=tk.X)
        
        lbl_load = ttk.Label(load_frame, text=self._translate("Load Theme:"), style='Body.TLabel')
        lbl_load.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(lbl_load, "Load Theme:")

        self.theme_load_combo = ttk.Combobox(load_frame, state="readonly", width=15)
        self.theme_load_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.theme_load_combo.bind("<<ComboboxSelected>>", self._load_theme)
        
        btn_delete = ttk.Button(load_frame, text=self._translate("Delete"), command=self._delete_theme, style='Secondary.TButton', width=6)
        btn_delete.pack(side=tk.LEFT)
        self._register_translation(btn_delete, "Delete")
        
        # Initialize themes
        self._refresh_theme_list()

        # --- General Settings ---
        general_section = self._create_section(
            frame,
            "General Settings",
            "Basic plot appearance."
        )
        
        # Grid Checkbox
        self.grid_var = tk.BooleanVar(value=getattr(app_state, 'plot_style_grid', False))
        grid_check = ttk.Checkbutton(
            general_section,
            text=self._translate("Show Grid"),
            variable=self.grid_var,
            command=self._on_style_change,
            style='Option.TRadiobutton'
        )
        grid_check.pack(anchor=tk.W, pady=(0, 12))
        self._register_translation(grid_check, "Show Grid")
        
        # Color Scheme
        color_label = ttk.Label(general_section, text=self._translate("Palette"), style='FieldLabel.TLabel')
        color_label.pack(anchor=tk.W, pady=(0, 4))
        self._register_translation(color_label, "Palette")
        
        color_options = style_manager.style_manager_instance.get_palette_names()
        self.color_scheme_var = tk.StringVar(value=getattr(app_state, 'color_scheme', 'vibrant'))
        color_combo = ttk.Combobox(
            general_section, 
            textvariable=self.color_scheme_var, 
            values=color_options,
            state="readonly"
        )
        color_combo.pack(fill=tk.X, pady=(0, 8))
        color_combo.bind("<<ComboboxSelected>>", self._on_style_change)

        # --- Font Settings ---
        font_section = self._create_section(
            frame,
            "Font Settings",
            "Customize fonts and text sizes."
        )
        
        # Get available fonts
        all_system_fonts = sorted(style_manager.style_manager_instance.get_available_fonts())
        from config import CONFIG
        preferred_fonts = CONFIG.get('preferred_plot_fonts', [])
        installed_preferred = [f for f in preferred_fonts if f in all_system_fonts]
        other_fonts = [f for f in all_system_fonts if f not in installed_preferred]
        font_options = ['<Default>'] + installed_preferred + other_fonts
        
        # Primary Font
        primary_font_label = ttk.Label(font_section, text=self._translate("Primary Font (English)"), style='FieldLabel.TLabel')
        primary_font_label.pack(anchor=tk.W, pady=(0, 4))
        self._register_translation(primary_font_label, "Primary Font (English)")
        
        # Handle empty string as <Default> for display
        current_primary = getattr(app_state, 'custom_primary_font', '')
        if not current_primary: current_primary = '<Default>'
        
        self.primary_font_var = tk.StringVar(value=current_primary)
        primary_font_combo = ttk.Combobox(
            font_section,
            textvariable=self.primary_font_var,
            values=font_options,
            state="readonly"
        )
        primary_font_combo.pack(fill=tk.X, pady=(0, 8))
        primary_font_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        
        # CJK Font
        cjk_font_label = ttk.Label(font_section, text=self._translate("CJK Font (Chinese)"), style='FieldLabel.TLabel')
        cjk_font_label.pack(anchor=tk.W, pady=(0, 4))
        self._register_translation(cjk_font_label, "CJK Font (Chinese)")
        
        # Handle empty string as <Default> for display
        current_cjk = getattr(app_state, 'custom_cjk_font', '')
        if not current_cjk: current_cjk = '<Default>'
        
        self.cjk_font_var = tk.StringVar(value=current_cjk)
        cjk_font_combo = ttk.Combobox(
            font_section,
            textvariable=self.cjk_font_var,
            values=font_options,
            state="readonly"
        )
        cjk_font_combo.pack(fill=tk.X, pady=(0, 8))
        cjk_font_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        
        # Font Sizes
        size_frame = ttk.Frame(font_section, style='CardBody.TFrame')
        size_frame.pack(fill=tk.X, pady=(8, 0))
        
        # Helper to create size slider
        def add_size_slider(parent, label_key, key, default):
            container = ttk.Frame(parent)
            container.pack(fill=tk.X, pady=2)
            
            # Label
            lbl = ttk.Label(container, text=self._translate(label_key), width=8, style='Body.TLabel')
            lbl.pack(side=tk.LEFT)
            self._register_translation(lbl, label_key)
            
            # Variable
            var = tk.IntVar(value=app_state.plot_font_sizes.get(key, default))
            
            # Value Display
            val_lbl = ttk.Label(container, text=str(var.get()), width=3)
            val_lbl.pack(side=tk.RIGHT)
            
            # Slider
            def on_change(val):
                v = int(float(val))
                var.set(v)
                val_lbl.configure(text=str(v))
                
            scale = ttk.Scale(container, from_=6, to=36, variable=var, command=on_change)
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
            scale.bind("<ButtonRelease-1>", lambda e: self._on_style_change())
            
            return var

        self.font_size_vars = {}
        self.font_size_vars['title'] = add_size_slider(size_frame, "Title", 'title', 14)
        self.font_size_vars['label'] = add_size_slider(size_frame, "Label", 'label', 12)
        self.font_size_vars['tick'] = add_size_slider(size_frame, "Tick", 'tick', 10)
        self.font_size_vars['legend'] = add_size_slider(size_frame, "Legend", 'legend', 10)

        # --- Marker Settings ---
        marker_section = self._create_section(
            frame,
            "Marker Settings",
            "Customize data point appearance."
        )
        
        marker_frame = ttk.Frame(marker_section, style='CardBody.TFrame')
        marker_frame.pack(fill=tk.X)
        
        # Size
        size_lbl = ttk.Label(marker_frame, text=self._translate("Size"), style='Body.TLabel')
        size_lbl.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(size_lbl, "Size")
        self.marker_size_var = tk.IntVar(value=getattr(app_state, 'plot_marker_size', 60))
        size_scale = ttk.Scale(marker_frame, from_=10, to=500, variable=self.marker_size_var)
        size_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15))
        size_scale.bind("<ButtonRelease-1>", lambda e: self._on_style_change())
        
        # Alpha
        alpha_lbl = ttk.Label(marker_frame, text=self._translate("Opacity"), style='Body.TLabel')
        alpha_lbl.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(alpha_lbl, "Opacity")
        self.marker_alpha_var = tk.DoubleVar(value=getattr(app_state, 'plot_marker_alpha', 0.8))
        alpha_scale = ttk.Scale(marker_frame, from_=0.1, to=1.0, variable=self.marker_alpha_var)
        alpha_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
        alpha_scale.bind("<ButtonRelease-1>", lambda e: self._on_style_change())

    def _refresh_theme_list(self):
        """Load themes from disk and update combobox"""
        from config import CONFIG
        import json
        theme_file = CONFIG['temp_dir'] / 'user_themes.json'
        if theme_file.exists():
            try:
                with open(theme_file, 'r', encoding='utf-8') as f:
                    app_state.saved_themes = json.load(f)
            except Exception as e:
                print(f"[WARN] Failed to load themes: {e}", flush=True)
                app_state.saved_themes = {}
        
        self.theme_load_combo['values'] = sorted(list(app_state.saved_themes.keys()))

    def _save_theme(self):
        """Save current settings as a theme"""
        name = self.theme_name_var.get().strip()
        if not name:
            messagebox.showwarning(self._translate("Warning"), self._translate("Please enter a theme name."))
            return
            
        theme_data = {
            'grid': self.grid_var.get(),
            'color_scheme': self.color_scheme_var.get(),
            'primary_font': self.primary_font_var.get(),
            'cjk_font': self.cjk_font_var.get(),
            'font_sizes': {k: v.get() for k, v in self.font_size_vars.items()},
            'marker_size': self.marker_size_var.get(),
            'marker_alpha': self.marker_alpha_var.get()
        }
        
        app_state.saved_themes[name] = theme_data
        
        # Save to disk
        from config import CONFIG
        import json
        theme_file = CONFIG['temp_dir'] / 'user_themes.json'
        try:
            with open(theme_file, 'w', encoding='utf-8') as f:
                json.dump(app_state.saved_themes, f, indent=2)
            messagebox.showinfo(self._translate("Success"), self._translate("Theme '{name}' saved.", name=name))
            self._refresh_theme_list()
        except Exception as e:
            messagebox.showerror(self._translate("Error"), self._translate("Failed to save theme: {error}", error=e))

    def _load_theme(self, event=None):
        """Load selected theme"""
        name = self.theme_load_combo.get()
        if name not in app_state.saved_themes:
            return
            
        data = app_state.saved_themes[name]
        
        # Apply to UI vars
        self.grid_var.set(data.get('grid', False))
        self.color_scheme_var.set(data.get('color_scheme', 'vibrant'))
        self.primary_font_var.set(data.get('primary_font', ''))
        self.cjk_font_var.set(data.get('cjk_font', ''))
        
        sizes = data.get('font_sizes', {})
        for k, v in self.font_size_vars.items():
            if k in sizes:
                v.set(sizes[k])
                
        self.marker_size_var.set(data.get('marker_size', 60))
        self.marker_alpha_var.set(data.get('marker_alpha', 0.8))
        
        # Trigger update
        self._on_style_change()

    def _delete_theme(self):
        """Delete selected theme"""
        name = self.theme_load_combo.get()
        if not name: return
        
        if messagebox.askyesno(self._translate("Confirm"), self._translate("Delete theme '{name}'?", name=name)):
            if name in app_state.saved_themes:
                del app_state.saved_themes[name]
                
                from config import CONFIG
                import json
                theme_file = CONFIG['temp_dir'] / 'user_themes.json'
                try:
                    with open(theme_file, 'w', encoding='utf-8') as f:
                        json.dump(app_state.saved_themes, f, indent=2)
                    self.theme_load_combo.set('')
                    self._refresh_theme_list()
                except Exception as e:
                    messagebox.showerror(self._translate("Error"), self._translate("Failed to delete theme: {error}", error=e))

    def _on_style_change(self, event=None):
        """Handle style changes"""
        app_state.plot_style_grid = self.grid_var.get()
        app_state.color_scheme = self.color_scheme_var.get()
        
        # Handle <Default> font selection
        p_font = self.primary_font_var.get()
        if p_font == '<Default>': p_font = ''
        app_state.custom_primary_font = p_font
        
        c_font = self.cjk_font_var.get()
        if c_font == '<Default>': c_font = ''
        app_state.custom_cjk_font = c_font
        
        # Update advanced settings
        app_state.plot_font_sizes = {k: v.get() for k, v in self.font_size_vars.items()}
        app_state.plot_marker_size = self.marker_size_var.get()
        app_state.plot_marker_alpha = self.marker_alpha_var.get()
        
        # Clear palette cache to force regeneration of colors based on new scheme
        if hasattr(app_state, 'current_palette'):
            app_state.current_palette = {}
        
        # Trigger update
        if self.callback:
            self.callback()

    def _refresh_group_list(self):
        """Refresh the list of group column radio buttons"""
        if not hasattr(self, 'group_container'):
            return
            
        for widget in self.group_container.winfo_children():
            widget.destroy()

        if app_state.group_cols:
            for col in app_state.group_cols:
                ttk.Radiobutton(
                    self.group_container,
                    text=col,
                    variable=self.radio_vars['group'],
                    value=col,
                    command=self._on_change,
                    style='Option.TRadiobutton'
                ).pack(anchor=tk.W, pady=2)
        else:
            placeholder = ttk.Label(
                self.group_container,
                text=self._translate("Load data to unlock grouping options."),
                style='BodyMuted.TLabel',
                wraplength=400,
                justify=tk.LEFT
            )
            placeholder.pack(anchor=tk.W, pady=4)
            self.group_placeholder = placeholder
            self._register_translation(placeholder, "Load data to unlock grouping options.")

    def _build_algorithm_tab(self, parent):
        from visualization import show_scree_plot, show_pca_loadings
        
        frame = self._build_scrollable_frame(parent)

        # --- Grouping Controls ---
        self.group_section = self._create_section(
            frame,
            "Coloring / Grouping",
            "Select column for coloring points."
        )
        
        self.radio_vars['group'] = tk.StringVar(value=app_state.last_group_col or '')
        
        self.group_container = ttk.Frame(self.group_section, style='CardBody.TFrame')
        self.group_container.pack(fill=tk.X)
        self.group_placeholder = None

        self._refresh_group_list()

        # KDE Checkbox
        self.check_vars['show_kde'] = tk.BooleanVar(value=getattr(app_state, 'show_kde', False))
        kde_chk = ttk.Checkbutton(
            self.group_section,
            text=self._translate("Show Kernel Density"),
            variable=self.check_vars['show_kde'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        kde_chk.pack(anchor=tk.W, pady=(4, 4))
        self._register_translation(kde_chk, "Show Kernel Density")

        group_config_btn = ttk.Button(
            self.group_section,
            text=self._translate("Configure Group Columns"),
            command=self._open_group_col_settings,
            style='Secondary.TButton'
        )
        group_config_btn.pack(anchor=tk.W, pady=(4, 0))
        self._register_translation(group_config_btn, "Configure Group Columns")

        # UMAP Parameters
        self.umap_section = self._create_section(
            frame,
            "UMAP Parameters",
            "Control neighbourhood size and how tightly points cluster."
        )

        self._add_slider(
            self.umap_section,
            key='umap_n',
            label_text="n_neighbors",
            minimum=2,
            maximum=50,
            initial=app_state.umap_params['n_neighbors'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.umap_section,
            key='umap_d',
            label_text="min_dist",
            minimum=0.0,
            maximum=1.0,
            initial=app_state.umap_params['min_dist'],
            formatter=lambda v: f"{float(v):.2f}",
            step=0.01
        )

        self._add_slider(
            self.umap_section,
            key='umap_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.umap_params['random_state'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )
        
        # t-SNE Parameters
        self.tsne_section = self._create_section(
            frame,
            "t-SNE Parameters",
            "Adjust perplexity and learning rate to refine t-SNE embeddings."
        )

        self._add_slider(
            self.tsne_section,
            key='tsne_p',
            label_text="perplexity",
            minimum=5,
            maximum=100,
            initial=app_state.tsne_params['perplexity'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.tsne_section,
            key='tsne_lr',
            label_text="learning_rate",
            minimum=10,
            maximum=1000,
            initial=app_state.tsne_params['learning_rate'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.tsne_section,
            key='tsne_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.tsne_params.get('random_state', 42),
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        # PCA Parameters
        self.pca_section = self._create_section(
            frame,
            "PCA Parameters",
            "Standard Principal Component Analysis settings."
        )

        self._add_slider(
            self.pca_section,
            key='pca_n',
            label_text="n_components",
            minimum=2,
            maximum=10,
            initial=app_state.pca_params['n_components'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.pca_section,
            key='pca_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.pca_params.get('random_state', 42),
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )
        
        # PCA Dimension Selection & Scree Plot
        pca_tools = ttk.Frame(self.pca_section, style='CardBody.TFrame')
        pca_tools.pack(fill=tk.X, pady=(8, 0))
        
        scree_btn = ttk.Button(
            pca_tools,
            text=self._translate("Show Scree Plot"),
            style='Secondary.TButton',
            command=lambda: show_scree_plot(self.root)
        )
        scree_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(scree_btn, "Show Scree Plot")

        loadings_btn = ttk.Button(
            pca_tools,
            text=self._translate("Show Loadings"),
            style='Secondary.TButton',
            command=lambda: show_pca_loadings(self.root)
        )
        loadings_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(loadings_btn, "Show Loadings")
        
        dim_frame = ttk.Frame(pca_tools, style='CardBody.TFrame')
        dim_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(dim_frame, text=self._translate("X:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.pca_x_var = tk.StringVar(value=str(app_state.pca_component_indices[0] + 1))
        self.pca_x_spin = ttk.Spinbox(dim_frame, from_=1, to=10, width=3, textvariable=self.pca_x_var, command=self._on_pca_dim_change)
        self.pca_x_spin.pack(side=tk.LEFT, padx=(0, 8))
        self.pca_x_spin.bind('<Return>', lambda e: self._on_pca_dim_change())
        
        ttk.Label(dim_frame, text=self._translate("Y:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.pca_y_var = tk.StringVar(value=str(app_state.pca_component_indices[1] + 1))
        self.pca_y_spin = ttk.Spinbox(dim_frame, from_=1, to=10, width=3, textvariable=self.pca_y_var, command=self._on_pca_dim_change)
        self.pca_y_spin.pack(side=tk.LEFT)
        self.pca_y_spin.bind('<Return>', lambda e: self._on_pca_dim_change())

        # Robust PCA Parameters
        self.rpca_section = self._create_section(
            frame,
            "Robust PCA Parameters",
            "Minimum Covariance Determinant (MCD) based PCA. Resistant to outliers."
        )

        self._add_slider(
            self.rpca_section,
            key='rpca_n',
            label_text="n_components",
            minimum=2,
            maximum=10,
            initial=app_state.robust_pca_params['n_components'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.rpca_section,
            key='rpca_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.robust_pca_params['random_state'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.rpca_section,
            key='rpca_sf',
            label_text="support_fraction",
            minimum=0.5,
            maximum=0.99,
            initial=app_state.robust_pca_params.get('support_fraction', 0.75),
            formatter=lambda v: f"{float(v):.2f}",
            step=0.01
        )
        
        rpca_tools = ttk.Frame(self.rpca_section, style='CardBody.TFrame')
        rpca_tools.pack(fill=tk.X, pady=(8, 0))
        
        rpca_scree_btn = ttk.Button(
            rpca_tools,
            text=self._translate("Show Scree Plot"),
            style='Secondary.TButton',
            command=lambda: show_scree_plot(self.root)
        )
        rpca_scree_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(rpca_scree_btn, "Show Scree Plot")

        rpca_loadings_btn = ttk.Button(
            rpca_tools,
            text=self._translate("Show Loadings"),
            style='Secondary.TButton',
            command=lambda: show_pca_loadings(self.root)
        )
        rpca_loadings_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(rpca_loadings_btn, "Show Loadings")

        # RPCA Dimensions
        r_dim_frame = ttk.Frame(rpca_tools, style='CardBody.TFrame')
        r_dim_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(r_dim_frame, text=self._translate("X:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.rpca_x_spin = ttk.Spinbox(r_dim_frame, from_=1, to=10, width=3, textvariable=self.pca_x_var, command=self._on_pca_dim_change)
        self.rpca_x_spin.pack(side=tk.LEFT, padx=(0, 8))
        self.rpca_x_spin.bind('<Return>', lambda e: self._on_pca_dim_change())
        
        ttk.Label(r_dim_frame, text=self._translate("Y:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.rpca_y_spin = ttk.Spinbox(r_dim_frame, from_=1, to=10, width=3, textvariable=self.pca_y_var, command=self._on_pca_dim_change)
        self.rpca_y_spin.pack(side=tk.LEFT)
        self.rpca_y_spin.bind('<Return>', lambda e: self._on_pca_dim_change())

        # --- Ternary Parameters ---
        self._build_ternary_section(frame)

        # V1V2 Parameters
        self.v1v2_section = self._create_section(
            frame,
            "V1V2 Parameters",
            "Adjust parameters for V1-V2 diagram calculation."
        )

        self._add_slider(
            self.v1v2_section,
            key='v1v2_scale',
            label_text="Scale Factor",
            minimum=0.1,
            maximum=10.0,
            initial=app_state.v1v2_params.get('scale', 1.0),
            formatter=lambda v: f"{float(v):.1f}",
            step=0.1
        )

        self._add_slider(
            self.v1v2_section,
            key='v1v2_a',
            label_text="Parameter a",
            minimum=-10.0,
            maximum=10.0,
            initial=app_state.v1v2_params.get('a', 0.0),
            formatter=lambda v: f"{float(v):.2f}",
            step=0.1
        )

        self._add_slider(
            self.v1v2_section,
            key='v1v2_b',
            label_text="Parameter b",
            minimum=-10.0,
            maximum=10.0,
            initial=app_state.v1v2_params.get('b', 2.0367),
            formatter=lambda v: f"{float(v):.4f}",
            step=0.0001
        )

        self._add_slider(
            self.v1v2_section,
            key='v1v2_c',
            label_text="Parameter c",
            minimum=-20.0,
            maximum=20.0,
            initial=app_state.v1v2_params.get('c', -6.143),
            formatter=lambda v: f"{float(v):.3f}",
            step=0.001
        )

        reset_btn = ttk.Button(
            self.v1v2_section,
            text=self._translate("Reset to Defaults"),
            style='Secondary.TButton',
            command=self._reset_v1v2_defaults
        )
        reset_btn.pack(anchor=tk.W, pady=(8, 0))
        self._register_translation(reset_btn, "Reset to Defaults")
        
        # Initial visibility update
        self._update_algorithm_visibility()
        
        # Initialize sliders state if needed
        # if app_state.render_mode == 'Ternary':
        #     self.update_ternary_sliders_from_data(preserve_existing=True)

    def _build_ternary_section(self, parent):
        """Build the Ternary Plot controls."""

        self.ternary_section = self._create_section(
            parent,
            "Ternary Plot",
            "Standard Ternary Diagram (mpltern)"
        )
        
        # Standard Ternary Plot - No manual range sliders (Zoom is handled by plot toolbar if needed, or Auto)
        info_label = ttk.Label(
            self.ternary_section, 
            text=self._translate("Using Standard Ternary Plot.\nData is plotted as relative proportions."),
            style='BodyMuted.TLabel',
            wraplength=250
        )
        info_label.pack(anchor=tk.W, pady=8)
        self._register_translation(info_label, "Using Standard Ternary Plot.\nData is plotted as relative proportions.")

        # Auto Zoom Checkbox
        self.ternary_auto_zoom_var = tk.BooleanVar(value=False)
        self.ternary_auto_zoom_chk = ttk.Checkbutton(
            self.ternary_section,
            text=self._translate("Auto-Zoom to Data"),
            variable=self.ternary_auto_zoom_var,
            command=self._on_ternary_zoom_change,
            style='Option.TCheckbutton'
        )
        self.ternary_auto_zoom_chk.pack(anchor=tk.W, pady=5)
        self._register_translation(self.ternary_auto_zoom_chk, "Auto-Zoom to Data")

        # Scale Control
        scale_frame = ttk.Frame(self.ternary_section)
        scale_frame.pack(fill=tk.X, pady=8)
        
        # Header with Label and Value
        header_frame = ttk.Frame(scale_frame)
        header_frame.pack(fill=tk.X, pady=(0, 2))
        
        lbl_scale = ttk.Label(header_frame, text=self._translate("Scale:"), style='Body.TLabel')
        lbl_scale.pack(side=tk.LEFT)
        self._register_translation(lbl_scale, "Scale:")
        
        current_val = getattr(app_state, 'ternary_scale', 100.0)
        self.lbl_ternary_scale_val = ttk.Label(header_frame, text=f"{int(current_val)}")
        self.lbl_ternary_scale_val.pack(side=tk.RIGHT)

        self.ternary_scale_var = tk.DoubleVar(value=current_val)
        
        # Debounced Slider
        self.ternary_scale_slider = ttk.Scale(
            scale_frame,
            from_=1.0,
            to=200.0,
            variable=self.ternary_scale_var,
            orient=tk.HORIZONTAL,
            command=self._on_ternary_scale_slide
        )
        self.ternary_scale_slider.pack(fill=tk.X)

        # Stretch Checkbox
        self.ternary_stretch_var = tk.BooleanVar(value=getattr(app_state, 'ternary_stretch', False))
        chk_stretch = ttk.Checkbutton(
            self.ternary_section, 
            text=self._translate("Stretch to Fill"), 
            variable=self.ternary_stretch_var,
            command=self._on_stretch_change
        )
        chk_stretch.pack(fill=tk.X, pady=8)
        self._register_translation(chk_stretch, "Stretch to Fill")

    def _on_stretch_change(self):
        """Handle stretch toggle."""
        app_state.ternary_stretch = self.ternary_stretch_var.get()
        if self.callback:
            self.callback('alg_params')

    def _on_ternary_scale_slide(self, val):
        """Handle slider movement with debounce."""
        try:
            val = float(val)
            # Update label immediately for feedback
            self.lbl_ternary_scale_val.configure(text=f"{int(val)}")
            
            # Cancel previous timer
            if self._ternary_update_job:
                self.root.after_cancel(self._ternary_update_job)
            
            # Schedule new update in 150ms
            self._ternary_update_job = self.root.after(150, lambda v=val: self._trigger_ternary_update(v))
            
        except ValueError:
            pass

    def _trigger_ternary_update(self, val):
        """Execute the actual update."""
        app_state.ternary_scale = val
        if self.callback:
            self.callback('alg_params')
        self._ternary_update_job = None

    def _on_ternary_zoom_change(self):
        """Handle Auto Zoom toggle."""
        app_state.ternary_auto_zoom = self.ternary_auto_zoom_var.get()
        if self.callback:
            self.callback()





    def _build_tools_tab(self, parent):
        frame = self._build_scrollable_frame(parent)

        # Data Analysis Tools
        analysis_section = self._create_section(
            frame,
            "Data Analysis",
            "Tools for exploring data relationships and statistics."
        )
        
        analysis_row = ttk.Frame(analysis_section, style='CardBody.TFrame')
        analysis_row.pack(fill=tk.X)
        
        from visualization import show_correlation_heatmap, show_embedding_correlation, show_shepard_diagram
        
        corr_btn = ttk.Button(
            analysis_row,
            text=self._translate("Correlation Heatmap"),
            style='Secondary.TButton',
            command=lambda: show_correlation_heatmap(self.root)
        )
        corr_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(corr_btn, "Correlation Heatmap")

        axis_corr_btn = ttk.Button(
            analysis_row,
            text=self._translate("Show Axis Corr."),
            style='Secondary.TButton',
            command=lambda: show_embedding_correlation(self.root)
        )
        axis_corr_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(axis_corr_btn, "Show Axis Corr.")
        
        shepard_btn = ttk.Button(
            analysis_row,
            text=self._translate("Show Shepard Plot"),
            style='Secondary.TButton',
            command=lambda: show_shepard_diagram(self.root)
        )
        shepard_btn.pack(side=tk.LEFT)
        self._register_translation(shepard_btn, "Show Shepard Plot")

        # Confidence Ellipse Settings
        conf_section = self._create_section(
            frame,
            "Confidence Ellipse",
            "Set the confidence level for selection ellipses."
        )
        
        conf_frame = ttk.Frame(conf_section, style='CardBody.TFrame')
        conf_frame.pack(fill=tk.X, pady=(0, 8))
        
        conf_label = ttk.Label(conf_frame, text=self._translate("Confidence Level"), style='Body.TLabel')
        conf_label.pack(side=tk.LEFT, padx=(0, 8))
        self._register_translation(conf_label, "Confidence Level")
        
        self.radio_vars['confidence'] = tk.DoubleVar(value=app_state.ellipse_confidence)
        
        for level in [0.68, 0.95, 0.99]:
            rb = ttk.Radiobutton(
                conf_frame,
                text=f"{int(level*100)}%",
                variable=self.radio_vars['confidence'],
                value=level,
                command=self._on_change,
                style='Option.TRadiobutton'
            )
            rb.pack(side=tk.LEFT, padx=4)

        selection_section = self._create_section(
            frame,
            "Selection Tools",
            "Enable selection mode to pick samples in 2D or embedding views, then export the results."
        )

        selection_row = ttk.Frame(selection_section, style='CardBody.TFrame')
        selection_row.pack(fill=tk.X, pady=(0, 6))

        self.selection_button = ttk.Button(
            selection_row,
            text=self._translate("Enable Selection"),
            style='Secondary.TButton',
            command=self._on_toggle_selection
        )
        self.selection_button.pack(side=tk.LEFT)
        self._register_translation(self.selection_button, "Enable Selection")

        self.ellipse_selection_button = ttk.Button(
            selection_row,
            text=self._translate("Draw Ellipse"),
            style='Secondary.TButton',
            command=self._on_toggle_ellipse_selection
        )
        self.ellipse_selection_button.pack(side=tk.LEFT, padx=(12, 0))
        self._register_translation(self.ellipse_selection_button, "Draw Ellipse")

        self.selection_status = ttk.Label(
            selection_row,
            text=self._translate("Selected Samples: {count}", count=0),
            style='BodyMuted.TLabel'
        )
        self.selection_status.pack(side=tk.LEFT, padx=(12, 0))
        self._register_translation(
            self.selection_status,
            "Selected Samples: {count}",
            formatter=lambda: {'count': len(getattr(app_state, 'selected_indices', []))}
        )

        export_row = ttk.Frame(selection_section, style='CardBody.TFrame')
        export_row.pack(fill=tk.X)

        self.export_csv_button = ttk.Button(
            export_row,
            text=self._translate("Export CSV"),
            style='Secondary.TButton',
            command=self._export_selected_csv
        )
        self.export_csv_button.pack(side=tk.LEFT, padx=(0, 12))
        self._register_translation(self.export_csv_button, "Export CSV")

        self.export_excel_button = ttk.Button(
            export_row,
            text=self._translate("Export Excel"),
            style='Secondary.TButton',
            command=self._export_selected_excel
        )
        self.export_excel_button.pack(side=tk.LEFT)
        self._register_translation(self.export_excel_button, "Export Excel")

        # Subset Analysis Tools
        subset_row = ttk.Frame(selection_section, style='CardBody.TFrame')
        subset_row.pack(fill=tk.X, pady=(12, 0))

        self.analyze_subset_button = ttk.Button(
            subset_row,
            text=self._translate("Analyze Subset"),
            style='Accent.TButton',
            command=self._analyze_subset
        )
        self.analyze_subset_button.pack(side=tk.LEFT, padx=(0, 12))
        self._register_translation(self.analyze_subset_button, "Analyze Subset")

        self.reset_data_button = ttk.Button(
            subset_row,
            text=self._translate("Reset Data"),
            style='Secondary.TButton',
            command=self._reset_data
        )
        self.reset_data_button.pack(side=tk.LEFT)
        self._register_translation(self.reset_data_button, "Reset Data")

        # Data Management
        data_mgmt_section = self._create_section(
            frame,
            "Data Management",
            "Import new data files into the application."
        )

        data_mgmt_row = ttk.Frame(data_mgmt_section, style='CardBody.TFrame')
        data_mgmt_row.pack(fill=tk.X)

        self.load_data_btn = ttk.Button(
            data_mgmt_row,
            text=self._translate("Load New Data"),
            style='Accent.TButton',
            command=self._reload_data
        )
        self.load_data_btn.pack(side=tk.LEFT)
        self._register_translation(self.load_data_btn, "Load New Data")

    def _build_legend_tab(self, parent):
        """Build the interactive legend tab"""
        frame = self._build_scrollable_frame(parent)
        self.legend_container = frame
        
        # Legend Settings Section
        settings_frame = ttk.Frame(frame, style='ControlPanel.TFrame')
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Legend Columns Slider
        self._add_slider(
            settings_frame,
            key='legend_cols',
            label_text="Columns",
            minimum=0,
            maximum=10,
            initial=getattr(app_state, 'legend_columns', 0),
            formatter=lambda v: "Auto" if int(float(v)) == 0 else str(int(float(v))),
            step=1
        )

        # Add a refresh button
        refresh_btn = ttk.Button(
            frame,
            text=self._translate("Refresh Legend"),
            style='Secondary.TButton',
            command=self._refresh_legend_tab
        )
        refresh_btn.pack(anchor=tk.W, pady=(0, 10))
        self._register_translation(refresh_btn, "Refresh Legend")
        
        self.legend_items_frame = ttk.Frame(frame, style='ControlPanel.TFrame')
        self.legend_items_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initial population
        self._refresh_legend_tab()

    def _refresh_legend_tab(self):
        """
        Populate the legend tab with current groups and colors.
        
        Features:
        - Lists all groups (up to a limit) with checkboxes for visibility.
        - Shows a color swatch for each group (clickable to change color).
        - Provides a 'Top' button to bring a group's points to the front (z-order).
        - Includes a 'Select All' toggle.
        """
        if not hasattr(self, 'legend_items_frame'):
            return
            
        # Clear existing
        for child in self.legend_items_frame.winfo_children():
            child.destroy()
            
        if not app_state.current_groups:
            lbl = ttk.Label(self.legend_items_frame, text=self._translate("No legend data available."), style='BodyMuted.TLabel')
            lbl.pack(anchor=tk.W, pady=10)
            self._register_translation(lbl, "No legend data available.")
            return

        # Checkbox var for "Select All"
        self.select_all_var = tk.BooleanVar(value=True)
        
        def toggle_all():
            state = self.select_all_var.get()
            for var in self.legend_vars.values():
                var.set(state)
            self._apply_legend_filter()

        select_all_cb = ttk.Checkbutton(
            self.legend_items_frame,
            text=self._translate("Select all"),
            variable=self.select_all_var,
            command=toggle_all,
            style='Option.TRadiobutton'
        )
        select_all_cb.pack(anchor=tk.W, pady=(0, 5))
        self._register_translation(select_all_cb, "Select all")
        
        self.legend_vars = {}
        
        visible = set(app_state.visible_groups) if app_state.visible_groups else set(app_state.current_groups)

        # Limit the number of items to prevent UI freeze
        max_items = 100
        groups_to_show = app_state.current_groups[:max_items]
        
        if len(app_state.current_groups) > max_items:
            warning_lbl = ttk.Label(
                self.legend_items_frame, 
                text=self._translate("Showing first {max} groups only.", max=max_items),
                style='BodyMuted.TLabel'
            )
            warning_lbl.pack(anchor=tk.W, pady=(0, 5))
            self._register_translation(warning_lbl, "Showing first {max} groups only.", formatter=lambda: {'max': max_items})

        for group in groups_to_show:
            row = ttk.Frame(self.legend_items_frame, style='ControlPanel.TFrame')
            row.pack(fill=tk.X, pady=2)
            
            # Color swatch (Clickable)
            color = app_state.current_palette.get(group, '#cccccc')
            swatch = tk.Canvas(row, width=16, height=16, bg=color, highlightthickness=0, cursor="hand2")
            swatch.pack(side=tk.LEFT, padx=(0, 8))
            swatch.bind("<Button-1>", lambda e, g=group, s=swatch: self._pick_color(g, s))
            
            # Checkbox
            is_visible = group in visible
            var = tk.BooleanVar(value=is_visible)
            self.legend_vars[group] = var
            
            cb = ttk.Checkbutton(
                row,
                text=str(group),
                variable=var,
                command=self._apply_legend_filter,
                style='Option.TRadiobutton'
            )
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Top Button (Bring to front)
            top_btn = ttk.Button(
                row,
                text=self._translate("Top"),
                width=4,
                style='Secondary.TButton',
                command=lambda g=group: self._bring_to_front(g)
            )
            top_btn.pack(side=tk.RIGHT, padx=(4, 0))
            self._register_translation(top_btn, "Top")

    def sync_legend_ui(self):
        """Update legend checkboxes to match app_state.visible_groups without rebuilding."""
        if not hasattr(self, 'legend_vars'):
            return
            
        visible = set(app_state.visible_groups) if app_state.visible_groups else set(app_state.current_groups)
        
        for group, var in self.legend_vars.items():
            var.set(group in visible)
            
        # Update Select All checkbox state
        if hasattr(self, 'select_all_var'):
            # If visible_groups is None, it means all are visible
            all_visible = (app_state.visible_groups is None) or (len(visible) == len(app_state.current_groups))
            self.select_all_var.set(all_visible)

    def _pick_color(self, group, swatch):
        """
        Open a color picker dialog for a specific group.
        
        Updates the global palette and immediately redraws the scatter plot
        if the group is currently displayed.
        
        Args:
            group: The group identifier (e.g., name).
            swatch: The canvas widget displaying the current color (to be updated).
        """
        current_color = app_state.current_palette.get(group, '#cccccc')
        color = colorchooser.askcolor(initialcolor=current_color, title=f"Color for {group}")
        
        if color[1]: # color is ((r,g,b), hex)
            new_hex = color[1]
            app_state.current_palette[group] = new_hex
            swatch.configure(bg=new_hex)
            
            # Update plot immediately
            if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
                sc = app_state.group_to_scatter[group]
                try:
                    sc.set_color(new_hex)
                    # Restore edge color which set_color might overwrite
                    sc.set_edgecolor("#1e293b") 
                    if app_state.fig:
                        app_state.fig.canvas.draw_idle()
                except Exception as e:
                    print(f"[WARN] Failed to update color for {group}: {e}")

    def _bring_to_front(self, group):
        """
        Bring a group's scatter points to the front of the plot.
        
        Adjusts the z-order of the scatter collection corresponding to the group
        to be higher than all other collections.
        
        Args:
            group: The group identifier.
        """
        if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
            sc = app_state.group_to_scatter[group]
            try:
                # Find max zorder
                max_z = 2 # Default base zorder
                if hasattr(app_state, 'scatter_collections'):
                    for c in app_state.scatter_collections:
                        max_z = max(max_z, c.get_zorder())
                
                sc.set_zorder(max_z + 1)
                if app_state.fig:
                    app_state.fig.canvas.draw_idle()
            except Exception as e:
                print(f"[WARN] Failed to bring {group} to front: {e}")

    def _apply_legend_filter(self):
        """
        Apply the visibility filter from the legend tab.
        
        Updates `app_state.visible_groups` based on the checked state of each group
        in the legend list, then triggers a plot refresh via the callback.
        """
        selected = [g for g, var in self.legend_vars.items() if var.get()]
        
        if not selected:
            # Don't allow empty selection, maybe show warning or just keep last state?
            # For now, let's allow it but it will show "No data" in plot
            pass
            
        if len(selected) == len(app_state.current_groups):
            app_state.visible_groups = None
        else:
            app_state.visible_groups = selected
            
        if self.callback:
            self.callback()

    def _apply_translation(self, widget, attr, value):
        """Apply translated text to a widget attribute."""
        if widget is None or value is None:
            return
        try:
            if attr == 'title' and hasattr(widget, 'title'):
                widget.title(value)
            elif attr == 'tab':
                # Special handling for notebook tabs
                tab_id = value.get('tab_id')
                text = self._translate(self._translations[tab_id + 3]['key']) # Hacky index access, need better way
                # Actually, let's just use the widget (notebook) and tab_id
                self.notebook.tab(tab_id, text=text)
            else:
                widget.configure(**{attr: value})
        except Exception:
            pass

    def _refresh_language(self):
        """Reapply translations for all registered widgets."""
        for entry in self._translations:
            kwargs = {}
            if entry.get('formatter') is not None:
                result = entry['formatter']()
                if isinstance(result, dict):
                    kwargs = result
                elif isinstance(result, str):
                    self._apply_translation(entry['widget'], entry['attr'], result)
                    continue
            
            # Special handling for tabs
            if entry.get('attr') == 'tab':
                tab_id = kwargs.get('tab_id')
                text = self._translate(entry['key'])
                self.notebook.tab(tab_id, text=text)
                continue

            translated = self._translate(entry['key'], **kwargs)
            self._apply_translation(entry['widget'], entry['attr'], translated)
            
        # Refresh legend tab text
        self._refresh_legend_tab()

    # ... (rest of the methods need to be preserved or adapted) ...


    def _setup_styles(self):
        """Configure ttk styles for a polished appearance"""
        self.style = ttk.Style(self.master)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass
        
        # Apply initial theme
        current_theme = getattr(app_state, 'ui_theme', 'Modern Light')
        self._apply_ui_theme(current_theme)

    def _apply_ui_theme(self, theme_name):
        """Apply the selected UI theme to all widgets"""
        if not theme_name:
            theme_name = 'Modern Light'
            
        theme = style_manager.style_manager_instance.get_ui_theme(theme_name)
        if not theme: return

        # Store for future reference
        self.current_ui_theme = theme
        app_state.ui_theme = theme_name
        
        # Colors
        bg = theme['bg']
        fg = theme['fg']
        panel_bg = theme['panel_bg']
        header_bg = theme['header_bg']
        accent = theme['accent']
        secondary = theme['secondary']
        card_bg = theme['panel_bg'] # Use panel bg as card bg for seamless look or define separate
        
        self.primary_bg = panel_bg
        self.card_bg = card_bg
        
        # Root and main containers
        try:
            self.root.configure(bg=panel_bg)
        except:
            pass
            
        # Unified Font Configuration
        ui_font = 'Microsoft YaHei UI'
        
        # Apply to TTK Styles
        self.style.configure('ControlPanel.TFrame', background=panel_bg)
        self.style.configure('Header.TLabel', background=header_bg, foreground=fg, font=(ui_font, 16, 'bold'))
        self.style.configure('Subheader.TLabel', background=header_bg, foreground=secondary, font=(ui_font, 10))
        self.style.configure('Footer.TLabel', background=panel_bg, foreground=secondary, font=(ui_font, 9))
        self.style.configure('SectionSeparator.TSeparator', background=secondary)

        self.style.configure('Card.TLabelframe', background=card_bg, borderwidth=1, relief='solid')
        self.style.configure('Card.TLabelframe.Label', background=card_bg, foreground=fg, font=(ui_font, 12, 'bold'))
        self.style.configure('CardBody.TFrame', background=card_bg)
        self.style.configure('Body.TLabel', background=card_bg, foreground=secondary, font=(ui_font, 10))
        self.style.configure('BodyMuted.TLabel', background=card_bg, foreground=secondary, font=(ui_font, 10))
        self.style.configure('FieldLabel.TLabel', background=card_bg, foreground=fg, font=(ui_font, 10, 'bold'))
        self.style.configure('ValueLabel.TLabel', background=card_bg, foreground=fg, font=(ui_font, 10, 'bold'))

        self.style.configure('Option.TRadiobutton', background=card_bg, foreground=fg, padding=4, font=(ui_font, 10))
        self.style.map('Option.TRadiobutton', background=[('active', card_bg)], foreground=[('active', fg)])
        
        self.style.configure('Option.TCheckbutton', background=card_bg, foreground=fg, padding=4, font=(ui_font, 10))
        self.style.map('Option.TCheckbutton', background=[('active', card_bg)], foreground=[('active', fg)])
        
        # Buttons
        self.style.configure('Accent.TButton', background=accent, foreground='#ffffff', font=(ui_font, 10, 'bold'), padding=(12, 6))
        self.style.map('Accent.TButton', background=[('active', accent), ('pressed', accent)], foreground=[('disabled', '#d1d5db'), ('active', '#ffffff'), ('pressed', '#ffffff')])
        
        # Secondary button often behaves differently in themes
        # For dark themes, might need lighter text
        sec_fg = accent
        sec_bg = '#ffffff' if 'Light' in theme_name or 'Blue' in theme_name else '#374151'
        if 'Dark' in theme_name:
            sec_fg = '#ffffff'
            sec_bg = '#4b5563'
        if 'Retro' in theme_name:
            sec_bg = '#fde68a'
             
        self.style.configure('Secondary.TButton', background=sec_bg, foreground=sec_fg, font=(ui_font, 10, 'bold'), padding=(12, 6))
        self.style.map('Secondary.TButton', background=[('active', sec_bg)], foreground=[('active', sec_fg)])

        # Refresh matplotlib style if needed (Optional: auto-switch plot theme)
        # Update Figure background only to match UI (keep plot area user-defined)
        try:
            if app_state.fig:
                app_state.fig.patch.set_facecolor(theme['plot_bg'])
                app_state.fig.canvas.draw_idle()
        except:
            pass

    def _on_ui_theme_change(self, event=None):
        """Handle UI theme change event"""
        name = self.ui_theme_var.get()
        self._apply_ui_theme(name)
        # We might need to refresh widgets that don't auto-update
        # Re-creating widgets is heavy, but config updates should propagate via style

    def _translate(self, key, **kwargs):
        """Translate helper bound to the current app language."""
        language = getattr(app_state, 'language', None)
        return translate(key, language=language, **kwargs)

    def _register_translation(self, widget, key, attr='text', formatter=None):
        """Track a widget attribute for future language refreshes."""
        if widget is None:
            return
        self._translations.append({
            'widget': widget,
            'key': key,
            'attr': attr,
            'formatter': formatter,
        })

    def _language_label(self, code):
        """Return the human-readable label for a language code."""
        return self._language_labels.get(code, code)

    def _create_section(self, parent, title, description=None):
        """Create a styled section container"""
        section = ttk.LabelFrame(parent, text=self._translate(title), padding=14, style='Card.TLabelframe')
        section.pack(fill=tk.X, padx=6, pady=6)
        self._register_translation(section, title)

        if description:
            # Use a smaller wraplength to ensure it fits in narrow windows (minsize=420)
            # 420 - 2*10(panel pad) - 2*6(section pad) - 2*14(inner pad) ≈ 360
            desc = ttk.Label(section, text=self._translate(description), style='Body.TLabel', wraplength=340, justify=tk.LEFT)
            desc.pack(fill=tk.X, pady=(0, 10))
            
            # Bind configure event to update wraplength dynamically
            def _update_wraplength(event):
                # Adjust wraplength to be slightly less than the width of the label
                # This ensures text wraps correctly when window is resized
                if event.width > 20:
                    desc.configure(wraplength=event.width - 20)
            
            desc.bind('<Configure>', _update_wraplength)
            
            self._register_translation(desc, description)

        return section

    def _add_slider(self, parent, key, label_text, minimum, maximum, initial, formatter, step=1):
        """Add a labeled slider with value indicator and micro-adjust controls."""
        row = ttk.Frame(parent, style='CardBody.TFrame')
        row.pack(fill=tk.X, pady=6)

        label_widget = ttk.Label(row, text=self._translate(label_text), style='FieldLabel.TLabel')
        label_widget.pack(anchor=tk.W)
        self._register_translation(label_widget, label_text)

        slider_container = ttk.Frame(row, style='CardBody.TFrame')
        slider_container.pack(fill=tk.X, pady=(4, 0))

        value_label = ttk.Label(slider_container, text=formatter(initial), style='ValueLabel.TLabel')
        value_label.pack(side=tk.RIGHT)

        control_frame = ttk.Frame(slider_container, style='CardBody.TFrame')
        control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        decrement = ttk.Button(
            control_frame,
            text="<",
            width=3,
            style='Secondary.TButton',
            command=lambda k=key: self._nudge_slider(k, -step)
        )
        decrement.pack(side=tk.LEFT, padx=(0, 6))

        slider = ttk.Scale(
            control_frame,
            from_=minimum,
            to=maximum,
            orient=tk.HORIZONTAL
        )
        slider.set(initial)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        increment = ttk.Button(
            control_frame,
            text=">",
            width=3,
            style='Secondary.TButton',
            command=lambda k=key: self._nudge_slider(k, step)
        )
        increment.pack(side=tk.LEFT)

        def _handle_slider(value, slider_key=key):
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                numeric_value = value
            else:
                step_value = self._slider_steps.get(slider_key, 0) or 0
                if step_value:
                    snapped = round(numeric_value / step_value) * step_value
                    if step_value < 1:
                        step_str = f"{step_value:.6f}".rstrip('0').rstrip('.')
                        if '.' in step_str:
                            decimals = len(step_str.split('.')[1])
                            snapped = round(snapped, decimals)
                    if abs(snapped - numeric_value) > 1e-9:
                        numeric_value = snapped
                        slider_widget = self.sliders.get(slider_key)
                        if slider_widget is not None:
                            slider_widget.set(numeric_value)
            try:
                value_label.config(text=formatter(numeric_value))
            except Exception:
                pass
            self._schedule_slider_callback(slider_key)

        slider.configure(command=_handle_slider)
        slider.bind("<ButtonRelease-1>", lambda _e, k=key: self._apply_slider_change(k))
        slider.bind("<FocusOut>", lambda _e, k=key: self._apply_slider_change(k))
        slider.bind("<KeyRelease>", lambda _e, k=key: self._apply_slider_change(k))

        self.sliders[key] = slider
        self.labels[key] = value_label
        self._slider_steps[key] = float(step)

        return slider

    def _create_language_controls(self, parent):
        """Add language selection controls."""
        section = self._create_section(parent, "Language", "Choose the interface language.")

        values = dict(available_languages()) or self._language_labels or {'en': 'English'}
        self._language_labels = values
        current_label = self._language_label(app_state.language)
        if current_label not in values.values():
            current_label = next(iter(values.values()))

        label = ttk.Label(section, text=self._translate("Select Language"), style='FieldLabel.TLabel')
        label.pack(anchor=tk.W, pady=(0, 6))
        self._register_translation(label, "Select Language")

        self.language_choice = tk.StringVar(value=current_label)
        combo = ttk.Combobox(
            section,
            textvariable=self.language_choice,
            values=list(values.values()),
            state='readonly'
        )
        combo.pack(fill=tk.X)
        combo.bind('<<ComboboxSelected>>', self._on_language_change)
        self.language_combobox = combo

    def _on_language_change(self, _event=None):
        """Handle selection of a new interface language."""
        if self.language_choice is None:
            return

        selection = self.language_choice.get()
        target_code = None
        for code, label in self._language_labels.items():
            if label == selection:
                target_code = code
                break

        if target_code is None:
            return

        if target_code == getattr(app_state, 'language', None):
            return

        if not set_language(target_code):
            messagebox.showerror(
                self._translate("Language"),
                self._translate("Language switch failed. Please try again."),
                parent=self.root
            )
            self.language_choice.set(self._language_label(app_state.language))
            return

        self.language_choice.set(self._language_label(target_code))
        self._refresh_language()
        self.update_selection_controls()

        messagebox.showinfo(
            self._translate("Language"),
            self._translate("Language updated to {language}", language=self._language_label(target_code)),
            parent=self.root
        )

    def _schedule_slider_callback(self, key):
        """Debounce expensive recomputation while the slider is moving."""
        existing = self._slider_after.get(key)
        if existing is not None:
            try:
                self.root.after_cancel(existing)
            except Exception:
                pass

        self._slider_after[key] = self.root.after(
            self._slider_delay_ms,
            lambda k=key: self._apply_slider_change(k)
        )

    def _apply_slider_change(self, key):
        """Commit the slider value and trigger downstream updates."""
        pending = self._slider_after.pop(key, None)
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except Exception:
                pass

        self._on_change()

    def _nudge_slider(self, key, delta):
        """Micro-adjust the slider value using the auxiliary buttons."""
        slider = self.sliders.get(key)
        if slider is None:
            return

        step = self._slider_steps.get(key, 1.0)
        try:
            current = float(slider.get())
            minimum = float(slider.cget('from'))
            maximum = float(slider.cget('to'))
        except (TypeError, ValueError):
            return

        new_value = current + delta
        if step:
            new_value = round(new_value / step) * step

        new_value = max(minimum, min(maximum, new_value))

        # Limit floating-point noise to six decimal places at most.
        if step < 1:
            step_str = f"{step:.6f}".rstrip('0').rstrip('.')
            if '.' in step_str:
                decimals = len(step_str.split('.')[1])
                new_value = round(new_value, decimals)

        slider.set(new_value)
        self._apply_slider_change(key)

    def _refresh_group_options(self):
        """Rebuild group radio buttons to match the latest dataset."""
        if not hasattr(self, 'group_container') or self.group_container is None:
            return

        for child in list(self.group_container.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        self.group_placeholder = None

        if app_state.group_cols:
            for col in app_state.group_cols:
                ttk.Radiobutton(
                    self.group_container,
                    text=col,
                    variable=self.radio_vars['group'],
                    value=col,
                    command=self._on_change,
                    style='Option.TRadiobutton'
                ).pack(anchor=tk.W, pady=2)
        else:
            placeholder = ttk.Label(
                self.group_container,
                text=self._translate("Load data to unlock grouping options."),
                style='BodyMuted.TLabel',
                wraplength=400,
                justify=tk.LEFT
            )
            placeholder.pack(anchor=tk.W, pady=4)
            self.group_placeholder = placeholder
            self._register_translation(placeholder, "Load data to unlock grouping options.")

    def _open_legend_filter(self):
        """Launch legend filter dialog to hide/show groups."""
        if not app_state.available_groups:
            messagebox.showinfo(
                self._translate("Legend Filter"),
                self._translate("No legend entries are available yet."),
                parent=self.root
            )
            return

        try:
            from legend_dialog import select_visible_groups
        except Exception as exc:
            messagebox.showerror(
                self._translate("Legend Filter"),
                self._translate("Unable to open filter dialog: {error}", error=exc),
                parent=self.root
            )
            return

        current = app_state.visible_groups or app_state.available_groups
        selection = select_visible_groups(app_state.available_groups, selected=current)
        if selection is None:
            return

        if len(selection) == len(app_state.available_groups):
            app_state.visible_groups = None
        else:
            app_state.visible_groups = selection

        if self.callback:
            self.callback()

    def update_selection_controls(self):
        """Refresh selection-related widgets to reflect current state."""
        if not hasattr(self, 'selection_button'):
            return

        count = len(getattr(app_state, 'selected_indices', []))

        if getattr(self, 'selection_status', None) is not None:
            try:
                self.selection_status.config(
                    text=self._translate("Selected Samples: {count}", count=count)
                )
            except Exception:
                pass

        for button_attr in ('export_csv_button', 'export_excel_button'):
            btn = getattr(self, button_attr, None)
            if btn is None:
                continue
            try:
                if count == 0:
                    btn.state(['disabled'])
                else:
                    btn.state(['!disabled'])
            except Exception:
                pass
        
        # Reset Focus Button Logic - DISABLED
        # if hasattr(self, 'reset_focus_button') and self.reset_focus_button:
        #     if app_state.active_subset_indices is None:
        #         self.reset_focus_button.state(['disabled'])
        #     else:
        #         self.reset_focus_button.state(['!disabled'])

        toggle_btn = getattr(self, 'selection_button', None)
        if toggle_btn is None:
            return

        try:
            if app_state.selection_mode:
                toggle_btn.config(
                    text=self._translate("Disable Selection"),
                    style='Accent.TButton'
                )
            else:
                toggle_btn.config(
                    text=self._translate("Enable Selection"),
                    style='Secondary.TButton'
                )

            if app_state.render_mode == '3D':
                toggle_btn.state(['disabled'])
            else:
                toggle_btn.state(['!disabled'])
        except Exception:
            pass

    def refresh_language(self):
        """Public entry point for reapplying translations."""
        self._refresh_language()
        self.update_selection_controls()

    def _get_selected_dataframe(self):
        """Return a DataFrame with the currently selected samples."""
        if not app_state.selected_indices:
            messagebox.showinfo(
                self._translate("Export Selected Data"),
                self._translate("Please select at least one sample before exporting."),
                parent=self.root
            )
            return None

        if app_state.df_global is None or app_state.df_global.empty:
            messagebox.showwarning(
                self._translate("Export Selected Data"),
                self._translate("No data is available to export."),
                parent=self.root
            )
            return None

        try:
            indices = sorted(app_state.selected_indices)
            df = app_state.df_global.iloc[indices].copy()
            
            # Attempt to calculate and append V1V2 parameters
            if calculate_all_parameters:
                all_cols = df.columns.tolist()
                # Exact matching for prescribed headers
                col_206 = "206Pb/204Pb" if "206Pb/204Pb" in all_cols else None
                col_207 = "207Pb/204Pb" if "207Pb/204Pb" in all_cols else None
                col_208 = "208Pb/204Pb" if "208Pb/204Pb" in all_cols else None
                
                if col_206 and col_207 and col_208:
                    try:
                        pb206 = pd.to_numeric(df[col_206], errors='coerce').values
                        pb207 = pd.to_numeric(df[col_207], errors='coerce').values
                        pb208 = pd.to_numeric(df[col_208], errors='coerce').values
                        
                        # Get V1V2 parameters from state
                        v1v2_params = getattr(app_state, 'v1v2_params', {})
                        scale = v1v2_params.get('scale', 1.0)
                        a = v1v2_params.get('a', 0.0)
                        b = v1v2_params.get('b', 2.0367)
                        c = v1v2_params.get('c', -6.143)

                        results = calculate_all_parameters(
                            pb206, pb207, pb208, 
                            calculate_ages=True,
                            a=a, b=b, c=c, scale=scale
                        )
                        
                        # Append new columns
                        df['Δα'] = results['Delta_alpha']
                        df['Δβ'] = results['Delta_beta']
                        df['Δγ'] = results['Delta_gamma']
                        df['V1'] = results['V1']
                        df['V2'] = results['V2']
                        df['tCDT (Ma)'] = results['tCDT (Ma)']
                        df['tSK (Ma)'] = results['tSK (Ma)']
                        df['μ'] = results.get('mu', np.nan)
                        df['ν'] = results.get('nu', np.nan)
                        df['ω'] = results.get('omega', np.nan)
                        
                        print("[INFO] Appended V1V2 parameters to export data.", flush=True)
                    except Exception as e:
                        print(f"[WARN] Failed to calculate V1V2 parameters for export: {e}", flush=True)

        except Exception as exc:
            messagebox.showerror(
                self._translate("Export Selected Data"),
                self._translate("Unable to extract selected samples: {error}", error=exc),
                parent=self.root
            )
            return None
        return df

    def _sanitize_filename(self, value):
        """Sanitize user-provided filename fragments for safe saving."""
        sanitized = re.sub(r'[\/\\:*?"<>|]+', '_', value)
        sanitized = sanitized.strip().strip('.')
        return sanitized

    def _on_toggle_selection(self):
        """Toggle export selection mode from the control panel."""
        if app_state.render_mode == '3D':
            messagebox.showinfo(
                self._translate("Selection Mode"),
                self._translate("Selection mode is only available in 2D views"),
                parent=self.root
            )
            return

        toggle_selection_mode('export')
        self.update_selection_controls()

    def _on_toggle_ellipse_selection(self):
        """Toggle ellipse selection mode from the control panel."""
        if app_state.render_mode == '3D':
            messagebox.showinfo(
                self._translate("Selection Mode"),
                self._translate("Selection mode is only available in 2D views"),
                parent=self.root
            )
            return

        toggle_selection_mode('ellipse')
        self.update_selection_controls()

    def _export_selected_csv(self):
        """Export selected samples to a CSV file."""
        df = self._get_selected_dataframe()
        if df is None:
            return

        default_name = f"selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        name = simpledialog.askstring(
            self._translate("Export to CSV"),
            self._translate("Enter a file name (without extension):"),
            initialvalue=default_name,
            parent=self.root
        )
        if name is None:
            return

        name = name.strip()
        sanitized = self._sanitize_filename(name)
        if not sanitized:
            messagebox.showerror(
                self._translate("Export to CSV"),
                self._translate("File name cannot be empty or only invalid characters."),
                parent=self.root
            )
            return

        target_dir = os.path.dirname(app_state.file_path) if app_state.file_path else os.getcwd()
        if not target_dir:
            target_dir = os.getcwd()
        target_path = os.path.join(target_dir, f"{sanitized}.csv")

        if os.path.exists(target_path):
            overwrite = messagebox.askyesno(
                self._translate("Export to CSV"),
                self._translate("File already exists:\n{path}\nOverwrite?", path=target_path),
                parent=self.root
            )
            if not overwrite:
                return

        try:
            df.to_csv(target_path, index=False, encoding='utf-8-sig')
        except Exception as exc:
            messagebox.showerror(
                self._translate("Export to CSV"),
                self._translate("Export failed: {error}", error=exc),
                parent=self.root
            )
            return

        messagebox.showinfo(
            self._translate("Export to CSV"),
            self._translate("Exported {count} records to:\n{path}", count=len(df), path=target_path),
            parent=self.root
        )

    def _export_selected_excel(self):
        """Append selected samples to an Excel sheet."""
        df = self._get_selected_dataframe()
        if df is None:
            return

        if app_state.file_path and app_state.file_path.lower().endswith(('.xlsx', '.xlsm')):
            workbook_path = app_state.file_path
        else:
            workbook_path = filedialog.asksaveasfilename(
                parent=self.root,
                title=self._translate("Select target workbook"),
                defaultextension=".xlsx",
                filetypes=[(self._translate("Excel Workbook"), "*.xlsx")],
                initialfile="selected_data.xlsx"
            )
            if not workbook_path:
                return

        if not workbook_path.lower().endswith('.xlsx'):
            workbook_path = f"{workbook_path}.xlsx"

        sheet_default = f"Selected_{datetime.now().strftime('%Y%m%d_%H%M')}"
        sheet_name = simpledialog.askstring(
            self._translate("Append to Excel"),
            self._translate("Enter a new worksheet name:"),
            initialvalue=sheet_default,
            parent=self.root
        )
        if sheet_name is None:
            return

        sheet_name = sheet_name.strip()
        if not sheet_name:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name cannot be empty."),
                parent=self.root
            )
            return
        if len(sheet_name) > 31:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name cannot exceed 31 characters."),
                parent=self.root
            )
            return
        if any(ch in sheet_name for ch in '[]:*?/\\'):
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name contains invalid characters: []:*?/\\"),
                parent=self.root
            )
            return

        try:
            import openpyxl
        except ImportError:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("openpyxl is required to write Excel files. Please install openpyxl."),
                parent=self.root
            )
            return

        exists = os.path.exists(workbook_path)
        if exists:
            try:
                wb = openpyxl.load_workbook(workbook_path)
            except Exception as exc:
                messagebox.showerror(
                    self._translate("Append to Excel"),
                    self._translate("Unable to open target workbook: {error}", error=exc),
                    parent=self.root
                )
                return
            if sheet_name in wb.sheetnames:
                wb.close()
                messagebox.showerror(
                    self._translate("Append to Excel"),
                    self._translate("Worksheet already exists. Please choose another name."),
                    parent=self.root
                )
                return
            wb.close()

        try:
            if exists:
                with pd.ExcelWriter(workbook_path, mode='a', engine='openpyxl', if_sheet_exists='new') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # Try xlsxwriter for faster writing of new files
                try:
                    with pd.ExcelWriter(workbook_path, mode='w', engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                except Exception:
                    print("[INFO] xlsxwriter not available, falling back to openpyxl", flush=True)
                    print("[TIP] For faster Excel writing, install xlsxwriter: pip install xlsxwriter", flush=True)
                    with pd.ExcelWriter(workbook_path, mode='w', engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as exc:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Failed to write Excel file: {error}", error=exc),
                parent=self.root
            )
            return

        messagebox.showinfo(
            self._translate("Append to Excel"),
            self._translate(
                "Appended {count} records to worksheet '{sheet}'.\nPath: {path}",
                count=len(df),
                sheet=sheet_name,
                path=workbook_path
            ),
            parent=self.root
        )

    def _reload_data(self):
        """Allow the user to pick a new dataset and refresh the UI."""
        try:
            from data import load_data
        except Exception as exc:
            messagebox.showerror(
                self._translate("Reload Data"),
                self._translate("Unable to reload data: {error}", error=exc),
                parent=self.root
            )
            return

        success = load_data(show_file_dialog=True, show_config_dialog=True)
        if not success:
            messagebox.showinfo(
                self._translate("Reload Data"),
                self._translate("Data reload cancelled."),
                parent=self.root
            )
            return
            
        self._update_data_count_label()

        if app_state.group_cols:
            if app_state.last_group_col not in app_state.group_cols:
                app_state.last_group_col = app_state.group_cols[0]
        else:
            app_state.last_group_col = None

        if 'group' in self.radio_vars:
            self.radio_vars['group'].set(app_state.last_group_col or '')

        app_state.visible_groups = None
        app_state.available_groups = []
        app_state.selected_2d_cols = []
        app_state.selected_3d_cols = []
        app_state.selected_2d_confirmed = False
        app_state.selected_3d_confirmed = False
        app_state.initial_render_done = False

        self._refresh_group_options()

        if self.callback:
            self.callback()

        self.update_selection_controls()

        messagebox.showinfo(
            self._translate("Reload Data"),
            self._translate("Dataset reloaded successfully."),
            parent=self.root
        )
    
    def _analyze_subset(self):
        """Set the active subset to the currently selected indices and re-run analysis."""
        if not app_state.selected_indices:
            messagebox.showinfo(
                self._translate("Analyze Subset"),
                self._translate("Please select samples first."),
                parent=self.root
            )
            return
        
        # Set the active subset
        app_state.active_subset_indices = sorted(list(app_state.selected_indices))
        
        # Clear cache to force re-calculation
        app_state.embedding_cache.clear()
        
        # Trigger update
        if self.callback:
            self.callback()
            
        messagebox.showinfo(
            self._translate("Analyze Subset"),
            self._translate("Analysis restricted to {count} selected samples.", count=len(app_state.active_subset_indices)),
            parent=self.root
        )

    def _reset_data(self):
        """Reset to full dataset."""
        if app_state.active_subset_indices is None:
            return

        app_state.active_subset_indices = None
        app_state.embedding_cache.clear()
        
        if self.callback:
            self.callback()
            
        messagebox.showinfo(
            self._translate("Reset Data"),
            self._translate("Analysis reset to full dataset."),
            parent=self.root
        )

    def _reset_v1v2_defaults(self):
        """Reset V1V2 parameters to their default values."""
        defaults = {
            'v1v2_scale': 1.0,
            'v1v2_a': 0.0,
            'v1v2_b': 2.0367,
            'v1v2_c': -6.143
        }
        
        for key, value in defaults.items():
            if key in self.sliders:
                self.sliders[key].set(value)
                # Manually trigger update for each slider to ensure UI and state are synced
                # But to avoid multiple re-renders, we can just update state and UI, then trigger once
        
        # Update state directly
        app_state.v1v2_params['scale'] = defaults['v1v2_scale']
        app_state.v1v2_params['a'] = defaults['v1v2_a']
        app_state.v1v2_params['b'] = defaults['v1v2_b']
        app_state.v1v2_params['c'] = defaults['v1v2_c']
        
        # Update labels
        if 'v1v2_scale' in self.labels: self.labels['v1v2_scale'].config(text=f"{defaults['v1v2_scale']:.1f}")
        if 'v1v2_a' in self.labels: self.labels['v1v2_a'].config(text=f"{defaults['v1v2_a']:.2f}")
        if 'v1v2_b' in self.labels: self.labels['v1v2_b'].config(text=f"{defaults['v1v2_b']:.4f}")
        if 'v1v2_c' in self.labels: self.labels['v1v2_c'].config(text=f"{defaults['v1v2_c']:.3f}")

        # Clear cache
        keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'v1v2']
        for k in keys_to_remove:
            del app_state.embedding_cache[k]

        # Trigger callback
        if self.callback:
            self.callback()

    def _update_algorithm_visibility(self):
        """Show or hide algorithm controls based on current mode."""
        mode = app_state.render_mode
        
        # Hide all sections first
        for section in ['umap_section', 'tsne_section', 'pca_section', 'rpca_section', 'ternary_section', 'v1v2_section']:
            if hasattr(self, section):
                getattr(self, section).pack_forget()

        # Show relevant section
        if mode == 'UMAP' and hasattr(self, 'umap_section'):
            self.umap_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'tSNE' and hasattr(self, 'tsne_section'):
            self.tsne_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'PCA' and hasattr(self, 'pca_section'):
            self.pca_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'RobustPCA' and hasattr(self, 'rpca_section'):
            self.rpca_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'Ternary' and hasattr(self, 'ternary_section'):
            self.ternary_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'V1V2' and hasattr(self, 'v1v2_section'):
            self.v1v2_section.pack(fill=tk.X, padx=6, pady=6)
            
    def _on_change(self):
        """Handle any parameter change - with safety checks"""
        try:
            print(f"[DEBUG] _on_change called", flush=True)
            
            # Verify all dictionaries are initialized
            if not self.sliders or not self.labels or not self.radio_vars:
                print("[DEBUG] Dictionaries not fully initialized yet", flush=True)
                return
            
            algorithm_changed = False

            if 'render_mode' in self.radio_vars:
                requested_mode = self.radio_vars['render_mode'].get()
                previous_mode = app_state.render_mode

                if requested_mode == '3D' and len(app_state.data_cols) < 3:
                    print("[WARN] Need at least three numeric columns for 3D view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != '3D' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)
                elif requested_mode == 'Ternary' and len(app_state.data_cols) < 3:
                    print("[WARN] Need at least three numeric columns for Ternary view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != 'Ternary' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)
                elif requested_mode == '2D' and len(app_state.data_cols) < 2:
                    print("[WARN] Need at least two numeric columns for 2D view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != '2D' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)

                if requested_mode in ('UMAP', 'tSNE', 'PCA', 'RobustPCA'):
                    old_algo = app_state.algorithm
                    if requested_mode == 'UMAP':
                        app_state.algorithm = 'UMAP'
                    elif requested_mode == 'tSNE':
                        app_state.algorithm = 'tSNE'
                    elif requested_mode == 'PCA':
                        app_state.algorithm = 'PCA'
                    else:
                        app_state.algorithm = 'RobustPCA'
                    
                    algorithm_changed = (old_algo != app_state.algorithm)
                    if algorithm_changed:
                        print(f"[DEBUG] Algorithm changed: {old_algo} -> {app_state.algorithm}", flush=True)
                        app_state.embedding_cache.clear()

                if requested_mode != previous_mode:
                    print(f"[DEBUG] Render mode changed: {previous_mode} -> {requested_mode}", flush=True)
                    app_state.render_mode = requested_mode
                    if requested_mode == '2D':
                        app_state.selected_2d_confirmed = False
                    elif requested_mode == '3D':
                        app_state.selected_3d_confirmed = False
                    elif requested_mode == 'Ternary':
                        app_state.selected_ternary_confirmed = False
                    
                    self._update_algorithm_visibility()
                    # Ensure sliders reflect current data/state when switching to Ternary
                    if requested_mode == 'Ternary':
                        self.update_ternary_sliders_from_data(preserve_existing=True)

            if app_state.render_mode in ('UMAP', 'tSNE', 'PCA', 'RobustPCA'):
                if app_state.render_mode == 'UMAP':
                    app_state.algorithm = 'UMAP'
                elif app_state.render_mode == 'tSNE':
                    app_state.algorithm = 'tSNE'
                elif app_state.render_mode == 'PCA':
                    app_state.algorithm = 'PCA'
                else:
                    app_state.algorithm = 'RobustPCA'
            
            # Update Ellipse setting
            if 'ellipses' in self.check_vars:
                app_state.show_ellipses = self.check_vars['ellipses'].get()
            
            # Update KDE setting
            if 'show_kde' in self.check_vars:
                app_state.show_kde = self.check_vars['show_kde'].get()

            if 'confidence' in self.radio_vars:
                app_state.ellipse_confidence = self.radio_vars['confidence'].get()

            # Update UMAP parameters - only if keys exist
            umap_changed = False
            if 'umap_n' in self.sliders and 'umap_n' in self.labels:
                new_val = int(self.sliders['umap_n'].get())
                if app_state.umap_params['n_neighbors'] != new_val:
                    print(f"[DEBUG] UMAP n_neighbors changed: {app_state.umap_params['n_neighbors']} -> {new_val}", flush=True)
                    umap_changed = True
                app_state.umap_params['n_neighbors'] = new_val
                self.labels['umap_n'].config(text=f"{new_val}")
            
            if 'umap_d' in self.sliders and 'umap_d' in self.labels:
                new_val = float(self.sliders['umap_d'].get())
                if app_state.umap_params['min_dist'] != new_val:
                    print(f"[DEBUG] UMAP min_dist changed: {app_state.umap_params['min_dist']} -> {new_val}", flush=True)
                    umap_changed = True
                app_state.umap_params['min_dist'] = new_val
                self.labels['umap_d'].config(text=f"{new_val:.2f}")
            
            if 'umap_r' in self.sliders and 'umap_r' in self.labels:
                new_val = int(self.sliders['umap_r'].get())
                if app_state.umap_params['random_state'] != new_val:
                    print(f"[DEBUG] UMAP random_state changed: {app_state.umap_params['random_state']} -> {new_val}", flush=True)
                    umap_changed = True
                app_state.umap_params['random_state'] = new_val
                self.labels['umap_r'].config(text=f"{new_val}")
            
            # Clear UMAP cache if parameters changed
            if umap_changed:
                print(f"[DEBUG] UMAP parameters changed, clearing UMAP cache", flush=True)
                # Remove UMAP entries from cache
                keys_to_remove = [k for k in app_state.embedding_cache.keys() if k[0] == 'umap']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update t-SNE parameters
            tsne_changed = False
            if 'tsne_p' in self.sliders and 'tsne_p' in self.labels:
                p = int(self.sliders['tsne_p'].get())
                if app_state.df_global is not None and p >= app_state.df_global.shape[0]:
                    p = app_state.df_global.shape[0] - 1
                    self.sliders['tsne_p'].set(p)
                if app_state.tsne_params['perplexity'] != p:
                    print(f"[DEBUG] t-SNE perplexity changed: {app_state.tsne_params['perplexity']} -> {p}", flush=True)
                    tsne_changed = True
                app_state.tsne_params['perplexity'] = p
                self.labels['tsne_p'].config(text=f"{p}")
            
            if 'tsne_lr' in self.sliders and 'tsne_lr' in self.labels:
                new_val = int(self.sliders['tsne_lr'].get())
                if app_state.tsne_params['learning_rate'] != new_val:
                    print(f"[DEBUG] t-SNE learning_rate changed: {app_state.tsne_params['learning_rate']} -> {new_val}", flush=True)
                    tsne_changed = True
                app_state.tsne_params['learning_rate'] = new_val
                self.labels['tsne_lr'].config(text=f"{new_val}")

            if 'tsne_r' in self.sliders and 'tsne_r' in self.labels:
                new_val = int(self.sliders['tsne_r'].get())
                if app_state.tsne_params.get('random_state') != new_val:
                    print(f"[DEBUG] t-SNE random_state changed: {app_state.tsne_params.get('random_state')} -> {new_val}", flush=True)
                    tsne_changed = True
                app_state.tsne_params['random_state'] = new_val
                self.labels['tsne_r'].config(text=f"{new_val}")
            
            # Clear t-SNE cache if parameters changed
            if tsne_changed:
                print(f"[DEBUG] t-SNE parameters changed, clearing t-SNE cache", flush=True)
                # Remove t-SNE entries from cache
                keys_to_remove = [k for k in app_state.embedding_cache.keys() if k[0] == 'tsne']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            # Update PCA parameters
            pca_changed = False
            if 'pca_n' in self.sliders and 'pca_n' in self.labels:
                new_val = int(self.sliders['pca_n'].get())
                if app_state.pca_params.get('n_components') != new_val:
                    print(f"[DEBUG] PCA n_components changed: {app_state.pca_params.get('n_components')} -> {new_val}", flush=True)
                    pca_changed = True
                    app_state.pca_params['n_components'] = new_val
                    self.labels['pca_n'].config(text=f"{new_val}")

            if 'pca_r' in self.sliders and 'pca_r' in self.labels:
                new_val = int(self.sliders['pca_r'].get())
                if app_state.pca_params.get('random_state') != new_val:
                    print(f"[DEBUG] PCA random_state changed: {app_state.pca_params.get('random_state')} -> {new_val}", flush=True)
                    pca_changed = True
                    app_state.pca_params['random_state'] = new_val
                    self.labels['pca_r'].config(text=f"{new_val}")

            if pca_changed:
                print(f"[DEBUG] PCA parameters changed, clearing PCA cache", flush=True)
                keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'pca']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            # Update Robust PCA parameters
            rpca_changed = False
            if 'rpca_n' in self.sliders and 'rpca_n' in self.labels:
                new_val = int(self.sliders['rpca_n'].get())
                if app_state.robust_pca_params.get('n_components') != new_val:
                    print(f"[DEBUG] Robust PCA n_components changed: {app_state.robust_pca_params.get('n_components')} -> {new_val}", flush=True)
                    rpca_changed = True
                    app_state.robust_pca_params['n_components'] = new_val
                    self.labels['rpca_n'].config(text=f"{new_val}")

            if 'rpca_r' in self.sliders and 'rpca_r' in self.labels:
                new_val = int(self.sliders['rpca_r'].get())
                if app_state.robust_pca_params.get('random_state') != new_val:
                    print(f"[DEBUG] Robust PCA random_state changed: {app_state.robust_pca_params.get('random_state')} -> {new_val}", flush=True)
                    rpca_changed = True
                    app_state.robust_pca_params['random_state'] = new_val
                    self.labels['rpca_r'].config(text=f"{new_val}")

            if 'rpca_sf' in self.sliders and 'rpca_sf' in self.labels:
                new_val = float(self.sliders['rpca_sf'].get())
                current_val = app_state.robust_pca_params.get('support_fraction')
                if current_val is None or abs(current_val - new_val) > 1e-6:
                    rpca_changed = True
                    print(f"[DEBUG] Robust PCA support_fraction changed: {current_val} -> {new_val}", flush=True)
                    app_state.robust_pca_params['support_fraction'] = new_val
                    self.labels['rpca_sf'].config(text=f"{new_val:.2f}")

            if rpca_changed:
                print(f"[DEBUG] Robust PCA parameters changed, clearing cache", flush=True)
                keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'robust_pca']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update V1V2 parameters
            v1v2_changed = False
            if 'v1v2_scale' in self.sliders and 'v1v2_scale' in self.labels:
                new_val = float(self.sliders['v1v2_scale'].get())
                if app_state.v1v2_params.get('scale') != new_val:
                    print(f"[DEBUG] V1V2 scale changed: {app_state.v1v2_params.get('scale')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['scale'] = new_val
                    self.labels['v1v2_scale'].config(text=f"{new_val:.1f}")

            if 'v1v2_a' in self.sliders and 'v1v2_a' in self.labels:
                new_val = float(self.sliders['v1v2_a'].get())
                if app_state.v1v2_params.get('a') != new_val:
                    print(f"[DEBUG] V1V2 a changed: {app_state.v1v2_params.get('a')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['a'] = new_val
                    self.labels['v1v2_a'].config(text=f"{new_val:.2f}")

            if 'v1v2_b' in self.sliders and 'v1v2_b' in self.labels:
                new_val = float(self.sliders['v1v2_b'].get())
                if app_state.v1v2_params.get('b') != new_val:
                    print(f"[DEBUG] V1V2 b changed: {app_state.v1v2_params.get('b')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['b'] = new_val
                    self.labels['v1v2_b'].config(text=f"{new_val:.4f}")

            if 'v1v2_c' in self.sliders and 'v1v2_c' in self.labels:
                new_val = float(self.sliders['v1v2_c'].get())
                if app_state.v1v2_params.get('c') != new_val:
                    print(f"[DEBUG] V1V2 c changed: {app_state.v1v2_params.get('c')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['c'] = new_val
                    self.labels['v1v2_c'].config(text=f"{new_val:.3f}")

            if v1v2_changed:
                print(f"[DEBUG] V1V2 parameters changed, clearing cache", flush=True)
                keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'v1v2']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update common parameters
            if 'size' in self.sliders and 'size' in self.labels:
                app_state.point_size = int(self.sliders['size'].get())
                self.labels['size'].config(text=f"{int(self.sliders['size'].get())}")
            
            # Update Legend Columns
            if 'legend_cols' in self.sliders and 'legend_cols' in self.labels:
                val = int(self.sliders['legend_cols'].get())
                app_state.legend_columns = val
                txt = "Auto" if val == 0 else str(val)
                self.labels['legend_cols'].config(text=txt)

            # Update group column if available
            if 'group' in self.radio_vars:
                old_group = app_state.last_group_col
                new_group = self.radio_vars['group'].get()
                if old_group != new_group:
                    app_state.last_group_col = new_group
                    app_state.visible_groups = None  # Reset visibility filter when group changes
                    print(f"[DEBUG] Group column changed: {old_group} -> {new_group}. Reset visible_groups.", flush=True)
            
            # Call the callback
            print(f"[DEBUG] Calling callback", flush=True)
            if self.callback:
                self.callback()
            print(f"[DEBUG] Callback completed", flush=True)
        
        except KeyError as e:
            print(f"[DEBUG] KeyError in _on_change (expected during init): {e}", flush=True)
        except Exception as e:
            print(f"[ERROR] _on_change: {e}", flush=True)

    def _on_pca_dim_change(self):
        """Handle changes to PCA dimension selection spinners"""
        try:
            # Get values from string vars
            try:
                x_dim = int(self.pca_x_var.get())
                y_dim = int(self.pca_y_var.get())
            except ValueError:
                return # Invalid input
            
            # Convert to 0-based indices
            x_idx = max(0, x_dim - 1)
            y_idx = max(0, y_dim - 1)
            
            current_indices = app_state.pca_component_indices
            if current_indices[0] != x_idx or current_indices[1] != y_idx:
                print(f"[DEBUG] PCA dimensions changed: {current_indices} -> [{x_idx}, {y_idx}]", flush=True)
                app_state.pca_component_indices = [x_idx, y_idx]
                
                # Trigger update if we are in PCA or RobustPCA mode
                if app_state.render_mode in ('PCA', 'RobustPCA'):
                    if self.callback:
                        self.callback()
        except Exception as e:
            print(f"[ERROR] _on_pca_dim_change error: {e}", flush=True)
    
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

    def _open_tooltip_settings(self):
        """Open a dialog to select columns for the tooltip."""
        if app_state.df_global is None:
            messagebox.showwarning(
                self._translate("No Data"),
                self._translate("Please load data first.")
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self._translate("Tooltip Configuration"))
        dialog.geometry("300x400")
        
        # Make it modal
        dialog.transient(self.root)
        dialog.grab_set()

        lbl = ttk.Label(dialog, text=self._translate("Select columns to display:"))
        lbl.pack(pady=10, padx=10, anchor=tk.W)
        self._register_translation(lbl, "Select columns to display:")

        # Buttons - Pack FIRST at BOTTOM to avoid being hidden
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        def save_tooltip_config():
            selected = [col for col, var in self.tooltip_vars.items() if var.get()]
            app_state.tooltip_columns = selected
            print(f"[DEBUG] Tooltip columns updated to: {selected}", flush=True)
            
            # Trigger immediate save to disk
            try:
                save_session_params(
                    algorithm=app_state.algorithm,
                    umap_params=app_state.umap_params,
                    tsne_params=app_state.tsne_params,
                    point_size=app_state.point_size,
                    group_col=app_state.last_group_col,
                    group_cols=app_state.group_cols,
                    data_cols=app_state.data_cols,
                    file_path=app_state.file_path,
                    sheet_name=app_state.sheet_name,
                    render_mode=app_state.render_mode,
                    selected_2d_cols=getattr(app_state, 'selected_2d_cols', []),
                    selected_3d_cols=app_state.selected_3d_cols,
                    language=app_state.language,
                    tooltip_columns=app_state.tooltip_columns
                )
            except Exception as e:
                print(f"[WARN] Failed to auto-save session: {e}", flush=True)

            dialog.destroy()

        save_btn = ttk.Button(btn_frame, text=self._translate("Save"), command=save_tooltip_config)
        save_btn.pack(side=tk.RIGHT, padx=5)
        self._register_translation(save_btn, "Save")

        cancel_btn = ttk.Button(btn_frame, text=self._translate("Cancel"), command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT)
        self._register_translation(cancel_btn, "Cancel")

        # Scrollable frame for checkboxes
        # Layout Note: Pack scrollbar to the RIGHT first, then canvas to the LEFT.
        # This ensures the scrollbar remains visible even if the window is resized very narrow.
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Ensure frame width matches canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Checkboxes
        self.tooltip_vars = {}
        all_columns = list(app_state.df_global.columns)
        
        # Ensure default columns are in the list if they exist in dataframe
        current_selection = app_state.tooltip_columns
        if current_selection is None:
             current_selection = []

        for col in all_columns:
            var = tk.BooleanVar(value=col in current_selection)
            self.tooltip_vars[col] = var
            cb = ttk.Checkbutton(scrollable_frame, text=col, variable=var)
            cb.pack(anchor=tk.W, pady=2)

    def _open_column_selection(self):
        """Open dialog to select columns for 2D/3D scatter plots."""
        if app_state.render_mode == '2D':
            try:
                from two_d_dialog import select_2d_columns
                available = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                current = getattr(app_state, 'selected_2d_cols', [])
                current_kde = getattr(app_state, 'show_2d_kde', False)
                result = select_2d_columns(available, preselected=current, preselected_kde=current_kde)
                
                if result:
                    selection, show_kde = result
                    if selection and len(selection) == 2:
                        app_state.selected_2d_cols = selection
                        app_state.show_2d_kde = show_kde
                        # Sync global KDE toggle if changed in dialog
                        app_state.show_kde = show_kde
                        if 'show_kde' in self.check_vars:
                            self.check_vars['show_kde'].set(show_kde)
                        
                        app_state.selected_2d_confirmed = True
                        if self.callback: self.callback()
            except Exception as e:
                print(f"[ERROR] Failed to open 2D column selection: {e}", flush=True)
                messagebox.showerror(self._translate("Error"), str(e))
        elif app_state.render_mode == '3D':
            try:
                from three_d_dialog import select_3d_columns
                available = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                current = app_state.selected_3d_cols
                selection = select_3d_columns(available, preselected=current)
                if selection and len(selection) == 3:
                    app_state.selected_3d_cols = selection
                    app_state.selected_3d_confirmed = True
                    if self.callback: self.callback()
            except Exception as e:
                print(f"[ERROR] Failed to open 3D column selection: {e}", flush=True)
                messagebox.showerror(self._translate("Error"), str(e))
        elif app_state.render_mode == 'Ternary':
            try:
                from ternary_dialog import ask_ternary_columns
                available = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                current = app_state.selected_ternary_cols
                selection = ask_ternary_columns(available, preselected=current)
                if selection and len(selection) == 3:
                    app_state.selected_ternary_cols = selection
                    app_state.selected_ternary_confirmed = True
                    self.update_ternary_sliders_from_data(preserve_existing=False) # Force reset to new data limits
                    if self.callback: self.callback()
            except Exception as e:
                print(f"[ERROR] Failed to open Ternary column selection: {e}", flush=True)
                messagebox.showerror(self._translate("Error"), str(e))
        else:
            messagebox.showinfo(
                self._translate("Info"), 
                self._translate("Column selection is only available for 2D/3D/Ternary modes.")
            )

    def _open_group_col_settings(self):
        """Open a dialog to select columns for grouping."""
        if app_state.df_global is None:
            messagebox.showwarning(
                self._translate("No Data"),
                self._translate("Please load data first.")
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self._translate("Group Columns Configuration"))
        dialog.geometry("300x400")
        
        dialog.transient(self.root)
        dialog.grab_set()

        lbl = ttk.Label(dialog, text=self._translate("Select columns to use for grouping:"))
        lbl.pack(pady=10, padx=10, anchor=tk.W)
        self._register_translation(lbl, "Select columns to use for grouping:")

        # Buttons - Pack FIRST at BOTTOM
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        def save_group_config():
            selected = [col for col, var in self.group_vars.items() if var.get()]
            if not selected:
                messagebox.showwarning(
                    self._translate("Validation Error"),
                    self._translate("Please select at least one grouping column."),
                    parent=dialog
                )
                return

            app_state.group_cols = selected
            print(f"[DEBUG] Group columns updated to: {selected}", flush=True)
            
            # Refresh UI
            self._refresh_group_list()
            
            # Trigger immediate save to disk
            try:
                save_session_params(
                    algorithm=app_state.algorithm,
                    umap_params=app_state.umap_params,
                    tsne_params=app_state.tsne_params,
                    point_size=app_state.point_size,
                    group_col=app_state.last_group_col,
                    group_cols=app_state.group_cols,
                    data_cols=app_state.data_cols,
                    file_path=app_state.file_path,
                    sheet_name=app_state.sheet_name,
                    render_mode=app_state.render_mode,
                    selected_2d_cols=getattr(app_state, 'selected_2d_cols', []),
                    selected_3d_cols=app_state.selected_3d_cols,
                    language=app_state.language,
                    tooltip_columns=app_state.tooltip_columns
                )
            except Exception as e:
                print(f"[WARN] Failed to auto-save session: {e}", flush=True)

            dialog.destroy()

        save_btn = ttk.Button(btn_frame, text=self._translate("Save"), command=save_group_config)
        save_btn.pack(side=tk.RIGHT, padx=5)
        self._register_translation(save_btn, "Save")

        cancel_btn = ttk.Button(btn_frame, text=self._translate("Cancel"), command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT)
        self._register_translation(cancel_btn, "Cancel")

        # Scrollable frame
        # Layout Note: Pack scrollbar to the RIGHT first, then canvas to the LEFT.
        # This ensures the scrollbar remains visible even if the window is resized very narrow.
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Ensure frame width matches canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Checkboxes
        self.group_vars = {}
        all_columns = list(app_state.df_global.columns)
        
        # Identify data columns to exclude
        data_cols = set(app_state.data_cols) if app_state.data_cols else set()
        
        current_selection = app_state.group_cols or []

        for col in all_columns:
            # Skip if it is a data column
            if col in data_cols:
                continue

            var = tk.BooleanVar(value=col in current_selection)
            self.group_vars[col] = var
            cb = ttk.Checkbutton(scrollable_frame, text=col, variable=var)
            cb.pack(anchor=tk.W, pady=2)

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
