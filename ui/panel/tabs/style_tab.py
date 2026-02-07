"""
Style Tab - Theme and appearance settings
"""
import tkinter as tk
from tkinter import ttk, messagebox
import json

from visualization.style_manager import style_manager_instance
from core import app_state, CONFIG


class StyleTabMixin:
    """Mixin providing the Style tab builder and theme management"""

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
            values=style_manager_instance.get_ui_theme_names(),
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
        
        color_options = style_manager_instance.get_palette_names()
        self.color_scheme_var = tk.StringVar(value=getattr(app_state, 'color_scheme', 'vibrant'))
        color_combo = ttk.Combobox(
            general_section, 
            textvariable=self.color_scheme_var, 
            values=color_options,
            state="readonly"
        )
        color_combo.pack(fill=tk.X, pady=(0, 8))
        color_combo.bind("<<ComboboxSelected>>", self._on_style_change)

        # --- Style Columns (Font + Marker) ---
        style_columns = ttk.Frame(frame, style='ControlPanel.TFrame')
        style_columns.pack(fill=tk.X, pady=(4, 0))
        style_columns.columnconfigure(0, weight=1)
        style_columns.columnconfigure(1, weight=1)

        font_section = ttk.LabelFrame(style_columns, text=self._translate("Font Settings"), padding=14, style='Card.TLabelframe')
        font_section.grid(row=0, column=0, sticky=tk.EW, padx=(6, 6), pady=6)
        self._register_translation(font_section, "Font Settings")

        font_desc = ttk.Label(font_section, text=self._translate("Customize fonts and text sizes."), style='Body.TLabel', wraplength=240, justify=tk.LEFT)
        font_desc.pack(fill=tk.X, pady=(0, 10))
        self._register_translation(font_desc, "Customize fonts and text sizes.")
        
        # Get available fonts
        all_system_fonts = sorted(style_manager_instance.get_available_fonts())
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
        if not current_primary:
            current_primary = '<Default>'
        
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
        if not current_cjk:
            current_cjk = '<Default>'
        
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

        self.show_title_var = tk.BooleanVar(value=getattr(app_state, 'show_plot_title', True))
        show_title_chk = ttk.Checkbutton(
            font_section,
            text=self._translate("Show Plot Title"),
            variable=self.show_title_var,
            command=self._on_style_change,
            style='Option.TCheckbutton'
        )
        show_title_chk.pack(anchor=tk.W, pady=(6, 0))
        self._register_translation(show_title_chk, "Show Plot Title")

        marker_section = ttk.LabelFrame(style_columns, text=self._translate("Marker Settings"), padding=14, style='Card.TLabelframe')
        marker_section.grid(row=0, column=1, sticky=tk.EW, padx=(6, 6), pady=6)
        self._register_translation(marker_section, "Marker Settings")

        marker_desc = ttk.Label(marker_section, text=self._translate("Customize data point appearance."), style='Body.TLabel', wraplength=240, justify=tk.LEFT)
        marker_desc.pack(fill=tk.X, pady=(0, 10))
        self._register_translation(marker_desc, "Customize data point appearance.")
        
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

        # --- Axes & Lines ---
        axes_section = self._create_section(
            frame,
            "Axes & Lines",
            "Common plot layout and line styles."
        )

        axes_grid = ttk.Frame(axes_section, style='CardBody.TFrame')
        axes_grid.pack(fill=tk.X, pady=(4, 0))
        axes_grid.columnconfigure(0, weight=1)
        axes_grid.columnconfigure(1, weight=1)

        auto_layout_btn = ttk.Button(
            axes_section,
            text=self._translate("Auto Layout"),
            style='Secondary.TButton',
            command=self._apply_auto_layout
        )
        auto_layout_btn.pack(anchor=tk.W, pady=(0, 8))
        self._register_translation(auto_layout_btn, "Auto Layout")

        def add_labeled_entry(parent, label_key, var, row, col, width=10):
            cell = ttk.Frame(parent, style='CardBody.TFrame')
            cell.grid(row=row, column=col, sticky=tk.EW, padx=(0 if col == 0 else 16, 0), pady=3)
            lbl = ttk.Label(cell, text=self._translate(label_key), style='Body.TLabel')
            lbl.pack(anchor=tk.W)
            self._register_translation(lbl, label_key)
            entry = ttk.Entry(cell, textvariable=var, width=width)
            entry.pack(fill=tk.X)
            entry.bind('<Return>', lambda e: self._on_style_change())
            entry.bind('<FocusOut>', lambda e: self._on_style_change())

        # Figure size & DPI
        fig_w, fig_h = getattr(app_state, 'plot_figsize', (13, 9))
        self.figure_width_var = tk.StringVar(value=str(fig_w))
        self.figure_height_var = tk.StringVar(value=str(fig_h))
        self.figure_dpi_var = tk.StringVar(value=str(getattr(app_state, 'plot_dpi', 130)))
        add_labeled_entry(axes_grid, "Figure Width (in)", self.figure_width_var, 0, 0)
        add_labeled_entry(axes_grid, "Figure Height (in)", self.figure_height_var, 0, 1)
        add_labeled_entry(axes_grid, "Figure DPI", self.figure_dpi_var, 1, 0)

        # Background colors
        self.figure_bg_var = tk.StringVar(value=getattr(app_state, 'plot_facecolor', '#ffffff'))
        self.axes_bg_var = tk.StringVar(value=getattr(app_state, 'axes_facecolor', '#ffffff'))
        add_labeled_entry(axes_grid, "Figure Background", self.figure_bg_var, 1, 1)
        add_labeled_entry(axes_grid, "Axes Background", self.axes_bg_var, 2, 0)

        # Grid style
        self.grid_color_var = tk.StringVar(value=getattr(app_state, 'grid_color', '#e2e8f0'))
        self.grid_width_var = tk.StringVar(value=str(getattr(app_state, 'grid_linewidth', 0.6)))
        self.grid_alpha_var = tk.StringVar(value=str(getattr(app_state, 'grid_alpha', 0.7)))
        add_labeled_entry(axes_grid, "Grid Color", self.grid_color_var, 2, 1)
        add_labeled_entry(axes_grid, "Grid Linewidth", self.grid_width_var, 3, 0)
        add_labeled_entry(axes_grid, "Grid Alpha", self.grid_alpha_var, 3, 1)

        grid_style_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        grid_style_cell.grid(row=4, column=0, sticky=tk.EW, pady=3)
        grid_style_label = ttk.Label(grid_style_cell, text=self._translate("Grid Style"), style='Body.TLabel')
        grid_style_label.pack(anchor=tk.W)
        self._register_translation(grid_style_label, "Grid Style")
        self.grid_style_var = tk.StringVar(value=getattr(app_state, 'grid_linestyle', '--'))
        grid_style_combo = ttk.Combobox(
            grid_style_cell,
            textvariable=self.grid_style_var,
            values=['-', '--', '-.', ':'],
            state='readonly'
        )
        grid_style_combo.pack(fill=tk.X)
        grid_style_combo.bind("<<ComboboxSelected>>", self._on_style_change)

        # Tick direction & axis linewidth
        self.tick_dir_var = tk.StringVar(value=getattr(app_state, 'tick_direction', 'out'))
        tick_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        tick_cell.grid(row=4, column=1, sticky=tk.EW, pady=3)
        tick_label = ttk.Label(tick_cell, text=self._translate("Tick Direction"), style='Body.TLabel')
        tick_label.pack(anchor=tk.W)
        self._register_translation(tick_label, "Tick Direction")
        tick_combo = ttk.Combobox(
            tick_cell,
            textvariable=self.tick_dir_var,
            values=['out', 'in', 'inout'],
            state='readonly'
        )
        tick_combo.pack(fill=tk.X)
        tick_combo.bind("<<ComboboxSelected>>", self._on_style_change)

        self.axis_linewidth_var = tk.StringVar(value=str(getattr(app_state, 'axis_linewidth', 1.0)))
        add_labeled_entry(axes_grid, "Axis Line Width", self.axis_linewidth_var, 5, 0)

        # Spine visibility
        spine_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        spine_cell.grid(row=5, column=1, sticky=tk.W, pady=3)
        self.show_top_spine_var = tk.BooleanVar(value=getattr(app_state, 'show_top_spine', True))
        self.show_right_spine_var = tk.BooleanVar(value=getattr(app_state, 'show_right_spine', True))
        top_chk = ttk.Checkbutton(
            spine_cell,
            text=self._translate("Show Top Spine"),
            variable=self.show_top_spine_var,
            command=self._on_style_change,
            style='Option.TCheckbutton'
        )
        top_chk.pack(anchor=tk.W)
        self._register_translation(top_chk, "Show Top Spine")
        right_chk = ttk.Checkbutton(
            spine_cell,
            text=self._translate("Show Right Spine"),
            variable=self.show_right_spine_var,
            command=self._on_style_change,
            style='Option.TCheckbutton'
        )
        right_chk.pack(anchor=tk.W)
        self._register_translation(right_chk, "Show Right Spine")

        # Scatter edge style
        self.scatter_edgecolor_var = tk.StringVar(value=getattr(app_state, 'scatter_edgecolor', '#1e293b'))
        self.scatter_edgewidth_var = tk.StringVar(value=str(getattr(app_state, 'scatter_edgewidth', 0.4)))
        add_labeled_entry(axes_grid, "Scatter Edge Color", self.scatter_edgecolor_var, 6, 0)
        add_labeled_entry(axes_grid, "Scatter Edge Width", self.scatter_edgewidth_var, 6, 1)

        # Line widths
        self.model_curve_width_var = tk.StringVar(value=str(getattr(app_state, 'model_curve_width', 1.2)))
        self.paleoisochron_width_var = tk.StringVar(value=str(getattr(app_state, 'paleoisochron_width', 0.9)))
        self.model_age_width_var = tk.StringVar(value=str(getattr(app_state, 'model_age_line_width', 0.7)))
        self.isochron_width_var = tk.StringVar(value=str(getattr(app_state, 'isochron_line_width', 1.5)))
        add_labeled_entry(axes_grid, "Model Curve Width", self.model_curve_width_var, 7, 0)
        add_labeled_entry(axes_grid, "Paleoisochron Width", self.paleoisochron_width_var, 7, 1)
        add_labeled_entry(axes_grid, "Model Age Line Width", self.model_age_width_var, 8, 0)
        add_labeled_entry(axes_grid, "Isochron Line Width", self.isochron_width_var, 8, 1)

    def _refresh_theme_list(self):
        """Load themes from disk and update combobox"""
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
            'marker_alpha': self.marker_alpha_var.get(),
            'figure_size': [self.figure_width_var.get(), self.figure_height_var.get()],
            'figure_dpi': self.figure_dpi_var.get(),
            'figure_bg': self.figure_bg_var.get(),
            'axes_bg': self.axes_bg_var.get(),
            'grid_color': self.grid_color_var.get(),
            'grid_linewidth': self.grid_width_var.get(),
            'grid_alpha': self.grid_alpha_var.get(),
            'grid_linestyle': self.grid_style_var.get(),
            'tick_direction': self.tick_dir_var.get(),
            'axis_linewidth': self.axis_linewidth_var.get(),
            'show_top_spine': self.show_top_spine_var.get(),
            'show_right_spine': self.show_right_spine_var.get(),
            'scatter_edgecolor': self.scatter_edgecolor_var.get(),
            'scatter_edgewidth': self.scatter_edgewidth_var.get(),
            'model_curve_width': self.model_curve_width_var.get(),
            'paleoisochron_width': self.paleoisochron_width_var.get(),
            'model_age_line_width': self.model_age_width_var.get(),
            'isochron_line_width': self.isochron_width_var.get()
        }
        
        app_state.saved_themes[name] = theme_data
        
        # Save to disk
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

        fig_size = data.get('figure_size', [13, 9])
        if isinstance(fig_size, (list, tuple)) and len(fig_size) == 2:
            self.figure_width_var.set(str(fig_size[0]))
            self.figure_height_var.set(str(fig_size[1]))
        self.figure_dpi_var.set(str(data.get('figure_dpi', 130)))
        self.figure_bg_var.set(data.get('figure_bg', '#ffffff'))
        self.axes_bg_var.set(data.get('axes_bg', '#ffffff'))
        self.grid_color_var.set(data.get('grid_color', '#e2e8f0'))
        self.grid_width_var.set(str(data.get('grid_linewidth', 0.6)))
        self.grid_alpha_var.set(str(data.get('grid_alpha', 0.7)))
        self.grid_style_var.set(data.get('grid_linestyle', '--'))
        self.tick_dir_var.set(data.get('tick_direction', 'out'))
        self.axis_linewidth_var.set(str(data.get('axis_linewidth', 1.0)))
        self.show_top_spine_var.set(bool(data.get('show_top_spine', True)))
        self.show_right_spine_var.set(bool(data.get('show_right_spine', True)))
        self.scatter_edgecolor_var.set(data.get('scatter_edgecolor', '#1e293b'))
        self.scatter_edgewidth_var.set(str(data.get('scatter_edgewidth', 0.4)))
        self.model_curve_width_var.set(str(data.get('model_curve_width', 1.2)))
        self.paleoisochron_width_var.set(str(data.get('paleoisochron_width', 0.9)))
        self.model_age_width_var.set(str(data.get('model_age_line_width', 0.7)))
        self.isochron_width_var.set(str(data.get('isochron_line_width', 1.5)))
        
        # Trigger update
        self._on_style_change()

    def _delete_theme(self):
        """Delete selected theme"""
        name = self.theme_load_combo.get()
        if not name:
            return
        
        if messagebox.askyesno(self._translate("Confirm"), self._translate("Delete theme '{name}'?", name=name)):
            if name in app_state.saved_themes:
                del app_state.saved_themes[name]
                
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
        def _safe_float(var, default):
            try:
                return float(var.get())
            except Exception:
                return default

        app_state.plot_style_grid = self.grid_var.get()
        previous_scheme = getattr(app_state, 'color_scheme', None)
        new_scheme = self.color_scheme_var.get()
        app_state.color_scheme = new_scheme
        
        # Handle <Default> font selection
        p_font = self.primary_font_var.get()
        if p_font == '<Default>':
            p_font = ''
        app_state.custom_primary_font = p_font
        
        c_font = self.cjk_font_var.get()
        if c_font == '<Default>':
            c_font = ''
        app_state.custom_cjk_font = c_font
        
        # Update advanced settings
        app_state.plot_font_sizes = {k: v.get() for k, v in self.font_size_vars.items()}
        app_state.plot_marker_size = self.marker_size_var.get()
        app_state.plot_marker_alpha = self.marker_alpha_var.get()
        app_state.show_plot_title = bool(self.show_title_var.get())

        fig_w = _safe_float(self.figure_width_var, 13)
        fig_h = _safe_float(self.figure_height_var, 9)
        app_state.plot_figsize = (fig_w, fig_h)
        app_state.plot_dpi = int(_safe_float(self.figure_dpi_var, 130))
        app_state.plot_facecolor = self.figure_bg_var.get() or '#ffffff'
        app_state.axes_facecolor = self.axes_bg_var.get() or '#ffffff'
        app_state.grid_color = self.grid_color_var.get() or '#e2e8f0'
        app_state.grid_linewidth = _safe_float(self.grid_width_var, 0.6)
        app_state.grid_alpha = _safe_float(self.grid_alpha_var, 0.7)
        app_state.grid_linestyle = self.grid_style_var.get() or '--'
        app_state.tick_direction = self.tick_dir_var.get() or 'out'
        app_state.axis_linewidth = _safe_float(self.axis_linewidth_var, 1.0)
        app_state.show_top_spine = bool(self.show_top_spine_var.get())
        app_state.show_right_spine = bool(self.show_right_spine_var.get())
        app_state.scatter_edgecolor = self.scatter_edgecolor_var.get() or '#1e293b'
        app_state.scatter_edgewidth = _safe_float(self.scatter_edgewidth_var, 0.4)
        app_state.model_curve_width = _safe_float(self.model_curve_width_var, 1.2)
        app_state.paleoisochron_width = _safe_float(self.paleoisochron_width_var, 0.9)
        app_state.model_age_line_width = _safe_float(self.model_age_width_var, 0.7)
        app_state.isochron_line_width = _safe_float(self.isochron_width_var, 1.5)

        if app_state.fig is not None:
            try:
                app_state.fig.set_size_inches(fig_w, fig_h, forward=True)
                app_state.fig.set_dpi(app_state.plot_dpi)
                app_state.fig.patch.set_facecolor(app_state.plot_facecolor)
            except Exception:
                pass
        if app_state.ax is not None:
            try:
                app_state.ax.set_facecolor(app_state.axes_facecolor)
            except Exception:
                pass
        
        # Clear palette cache only when scheme actually changes
        if new_scheme != previous_scheme and hasattr(app_state, 'current_palette'):
            app_state.current_palette = {}
        
        # Trigger update
        if self.callback:
            self.callback()

    def _apply_auto_layout(self):
        """Apply automatic layout adjustment to the figure."""
        if app_state.fig is None:
            return
        try:
            app_state.fig.set_constrained_layout(True)
            app_state.fig.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)
            app_state.fig.tight_layout()
            if app_state.fig.canvas:
                app_state.fig.canvas.draw_idle()
        except Exception:
            pass

    def _on_ui_theme_change(self, event=None):
        """Handle UI theme change event"""
        name = self.ui_theme_var.get()
        self._apply_ui_theme(name)

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
            
        theme = style_manager_instance.get_ui_theme(theme_name)
        if not theme:
            return

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
        card_bg = theme['panel_bg']
        
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
        
        # Secondary button
        sec_fg = accent
        sec_bg = '#ffffff' if 'Light' in theme_name or 'Blue' in theme_name else '#374151'
        if 'Dark' in theme_name:
            sec_fg = '#ffffff'
            sec_bg = '#4b5563'
        if 'Retro' in theme_name:
            sec_bg = '#fde68a'
             
        self.style.configure('Secondary.TButton', background=sec_bg, foreground=sec_fg, font=(ui_font, 10, 'bold'), padding=(12, 6))
        self.style.map('Secondary.TButton', background=[('active', sec_bg)], foreground=[('active', sec_fg)])

        # Update Figure background
        try:
            if app_state.fig:
                app_state.fig.patch.set_facecolor(theme['plot_bg'])
                app_state.fig.canvas.draw_idle()
        except:
            pass
