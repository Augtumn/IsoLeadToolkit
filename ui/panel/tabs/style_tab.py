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
        self._build_style_content(frame)

    def _build_style_content(self, frame):
        """Build the Style tab content (no scroll wrapper)."""
        # --- Theme Management ---
        theme_section = self._create_section(
            frame,
            "Interface Theme",
            "Select the overall look and feel of the application."
        )

        ui_theme_frame = ttk.Frame(theme_section, style='CardBody.TFrame')
        ui_theme_frame.pack(fill=tk.X, pady=(0, 8))
        ui_theme_grid = self._create_form_grid(ui_theme_frame)
        ui_theme_grid.pack(fill=tk.X)

        self.ui_theme_var = tk.StringVar(value=getattr(app_state, 'ui_theme', 'Modern Light'))
        ui_theme_combo = ttk.Combobox(
            ui_theme_grid, 
            textvariable=self.ui_theme_var, 
            values=style_manager_instance.get_ui_theme_names(),
            state="readonly"
        )
        self._add_form_row(ui_theme_grid, 0, "UI Theme:", ui_theme_combo)
        ui_theme_combo.bind("<<ComboboxSelected>>", self._on_ui_theme_change)

        # --- Saved Plot Settings ---
        saved_section = self._create_collapsible_section(
            frame,
            "Saved Plot Settings",
            "Save and load custom plot parameter sets (Grid, Fonts, Palette).",
            start_open=False
        )
        
        theme_frame = ttk.Frame(saved_section, style='CardBody.TFrame')
        theme_frame.pack(fill=tk.X, pady=(0, 8))
        theme_grid = self._create_form_grid(theme_frame)
        theme_grid.pack(fill=tk.X)

        self.theme_name_var = tk.StringVar()
        name_controls = ttk.Frame(theme_grid, style='CardBody.TFrame')
        ttk.Entry(name_controls, textvariable=self.theme_name_var, width=15).pack(side=tk.LEFT, padx=(0, 10))

        # Save Button
        btn_save = ttk.Button(name_controls, text=self._translate("Save"), command=self._save_theme, style='Secondary.TButton', width=6)
        btn_save.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(btn_save, "Save")
        self._add_form_row(theme_grid, 0, "Theme Name:", name_controls)
        
        # Load/Delete Frame
        load_frame = ttk.Frame(saved_section, style='CardBody.TFrame')
        load_frame.pack(fill=tk.X)
        load_grid = self._create_form_grid(load_frame)
        load_grid.pack(fill=tk.X)

        load_controls = ttk.Frame(load_grid, style='CardBody.TFrame')

        self.theme_load_combo = ttk.Combobox(load_controls, state="readonly", width=15)
        self.theme_load_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.theme_load_combo.bind("<<ComboboxSelected>>", self._load_theme)
        
        btn_delete = ttk.Button(load_controls, text=self._translate("Delete"), command=self._delete_theme, style='Secondary.TButton', width=6)
        btn_delete.pack(side=tk.LEFT)
        self._register_translation(btn_delete, "Delete")
        self._add_form_row(load_grid, 0, "Load Theme:", load_controls)
        
        # Initialize themes
        self._refresh_theme_list()

        # --- General Settings ---
        general_section = self._create_collapsible_section(
            frame,
            "General Settings",
            "Basic plot appearance.",
            start_open=True
        )
        
        # Grid Checkbox
        self.grid_var = tk.BooleanVar(value=getattr(app_state, 'plot_style_grid', False))
        grid_check = ttk.Checkbutton(
            general_section,
            text=self._translate("Show Grid"),
            variable=self.grid_var,
            command=self._on_style_change,
            style='Option.TCheckbutton'
        )
        grid_check.pack(anchor=tk.W, pady=(0, 12))
        self._register_translation(grid_check, "Show Grid")
        
        # Color Scheme
        color_form = self._create_form_grid(general_section)
        color_form.pack(fill=tk.X, pady=(0, 8))

        color_options = style_manager_instance.get_palette_names()
        self.color_scheme_var = tk.StringVar(value=getattr(app_state, 'color_scheme', 'vibrant'))
        color_combo = ttk.Combobox(
            color_form, 
            textvariable=self.color_scheme_var, 
            values=color_options,
            state="readonly"
        )
        self._add_form_row(color_form, 0, "Palette", color_combo, label_style='FieldLabel.TLabel')
        color_combo.bind("<<ComboboxSelected>>", self._on_style_change)

        # --- Font Settings ---
        font_section = self._create_collapsible_section(
            frame,
            "Font Settings",
            "Customize fonts and text sizes.",
            start_open=True
        )

        # Description handled by collapsible section
        
        # Get available fonts
        all_system_fonts = sorted(style_manager_instance.get_available_fonts())
        preferred_fonts = CONFIG.get('preferred_plot_fonts', [])
        installed_preferred = [f for f in preferred_fonts if f in all_system_fonts]
        other_fonts = [f for f in all_system_fonts if f not in installed_preferred]
        font_options = ['<Default>'] + installed_preferred + other_fonts
        
        font_form = self._create_form_grid(font_section)
        font_form.pack(fill=tk.X, pady=(0, 8))

        # Primary Font
        # Handle empty string as <Default> for display
        current_primary = getattr(app_state, 'custom_primary_font', '')
        if not current_primary:
            current_primary = '<Default>'
        
        self.primary_font_var = tk.StringVar(value=current_primary)
        primary_font_combo = ttk.Combobox(
            font_form,
            textvariable=self.primary_font_var,
            values=font_options,
            state="readonly"
        )
        self._add_form_row(font_form, 0, "Primary Font (English)", primary_font_combo, label_style='FieldLabel.TLabel')
        primary_font_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        
        # CJK Font
        # Handle empty string as <Default> for display
        current_cjk = getattr(app_state, 'custom_cjk_font', '')
        if not current_cjk:
            current_cjk = '<Default>'
        
        self.cjk_font_var = tk.StringVar(value=current_cjk)
        cjk_font_combo = ttk.Combobox(
            font_form,
            textvariable=self.cjk_font_var,
            values=font_options,
            state="readonly"
        )
        self._add_form_row(font_form, 1, "CJK Font (Chinese)", cjk_font_combo, label_style='FieldLabel.TLabel')
        cjk_font_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        
        # Font Sizes
        size_frame = ttk.Frame(font_section, style='CardBody.TFrame')
        size_frame.pack(fill=tk.X, pady=(8, 0))
        size_grid = self._create_form_grid(size_frame, columns=3)
        size_grid.pack(fill=tk.X)
        size_grid.columnconfigure(0, weight=0)
        size_grid.columnconfigure(1, weight=1)
        size_grid.columnconfigure(2, weight=0)
        
        # Helper to create size slider
        def add_size_slider(grid, label_key, key, default, row):
            # Variable
            var = tk.IntVar(value=app_state.plot_font_sizes.get(key, default))
            
            # Value Display
            val_lbl = ttk.Label(grid, text=str(var.get()), width=3)
            
            # Slider
            def on_change(val):
                v = int(float(val))
                var.set(v)
                val_lbl.configure(text=str(v))
                
            scale = ttk.Scale(grid, from_=6, to=36, variable=var, command=on_change)
            self._add_form_row_with_value(grid, row, label_key, scale, val_lbl)
            scale.bind("<ButtonRelease-1>", lambda e: self._on_style_change())
            
            return var

        self.font_size_vars = {}
        self.font_size_vars['title'] = add_size_slider(size_grid, "Title", 'title', 14, 0)
        self.font_size_vars['label'] = add_size_slider(size_grid, "Label", 'label', 12, 1)
        self.font_size_vars['tick'] = add_size_slider(size_grid, "Tick", 'tick', 10, 2)
        self.font_size_vars['legend'] = add_size_slider(size_grid, "Legend", 'legend', 10, 3)

        self.show_title_var = tk.BooleanVar(value=getattr(app_state, 'show_plot_title', False))
        show_title_chk = ttk.Checkbutton(
            font_section,
            text=self._translate("Show Plot Title"),
            variable=self.show_title_var,
            command=self._on_style_change,
            style='Option.TCheckbutton'
        )
        show_title_chk.pack(anchor=tk.W, pady=(6, 0))
        self._register_translation(show_title_chk, "Show Plot Title")

        # --- Marker Settings ---
        marker_section = self._create_collapsible_section(
            frame,
            "Marker Settings",
            "Customize data point appearance.",
            start_open=False
        )

        # Description handled by collapsible section
        
        marker_grid = self._create_form_grid(marker_section)
        marker_grid.pack(fill=tk.X)
        
        # Size
        self.marker_size_var = tk.IntVar(value=getattr(app_state, 'plot_marker_size', 60))
        size_scale = ttk.Scale(marker_grid, from_=10, to=500, variable=self.marker_size_var)
        self._add_form_row(marker_grid, 0, "Size", size_scale)
        size_scale.bind("<ButtonRelease-1>", lambda e: self._on_style_change())
        
        # Alpha
        self.marker_alpha_var = tk.DoubleVar(value=getattr(app_state, 'plot_marker_alpha', 0.8))
        alpha_scale = ttk.Scale(marker_grid, from_=0.1, to=1.0, variable=self.marker_alpha_var)
        self._add_form_row(marker_grid, 1, "Opacity", alpha_scale)
        alpha_scale.bind("<ButtonRelease-1>", lambda e: self._on_style_change())

        # --- Axes & Lines ---
        axes_section = self._create_collapsible_section(
            frame,
            "Axes & Lines",
            "Common plot layout and line styles.",
            start_open=False
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
            form = self._create_form_grid(cell)
            form.pack(fill=tk.X)
            entry = ttk.Entry(form, textvariable=var, width=width)
            self._add_form_row(form, 0, label_key, entry)
            entry.bind('<Return>', lambda e: self._on_style_change())
            entry.bind('<FocusOut>', lambda e: self._on_style_change())
            return cell

        def add_slider_with_spin(parent, label_key, var, row, col, min_val, max_val, step, decimals=2):
            cell = ttk.Frame(parent, style='CardBody.TFrame')
            cell.grid(row=row, column=col, sticky=tk.EW, padx=(0 if col == 0 else 16, 0), pady=3)
            form = self._create_form_grid(cell)
            form.pack(fill=tk.X)

            control = ttk.Frame(form, style='CardBody.TFrame')

            def _format_value(value):
                return f"{value:.{decimals}f}"

            def _on_scale(val):
                try:
                    value = float(val)
                except (TypeError, ValueError):
                    return
                var.set(value)
                spin_var.set(_format_value(value))

            def _on_spin_change(_event=None):
                try:
                    value = float(spin_var.get())
                except (TypeError, ValueError):
                    return
                value = max(min_val, min(max_val, value))
                var.set(value)
                scale.set(value)
                spin_var.set(_format_value(value))
                self._on_style_change()

            scale = ttk.Scale(control, from_=min_val, to=max_val, variable=var, command=_on_scale)
            scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

            spin_var = tk.StringVar(value=_format_value(var.get()))
            spin = ttk.Spinbox(
                control,
                from_=min_val,
                to=max_val,
                increment=step,
                width=6,
                textvariable=spin_var
            )
            spin.pack(side=tk.LEFT, padx=(8, 0))
            spin.bind('<Return>', _on_spin_change)
            spin.bind('<FocusOut>', _on_spin_change)

            self._add_form_row(form, 0, label_key, control)
            scale.bind("<ButtonRelease-1>", lambda e: self._on_style_change())
            return cell

        def add_check_row(parent, label_key, var, row, col):
            cell = ttk.Frame(parent, style='CardBody.TFrame')
            cell.grid(row=row, column=col, sticky=tk.EW, padx=(0 if col == 0 else 16, 0), pady=3)
            form = self._create_form_grid(cell)
            form.pack(fill=tk.X)
            chk = ttk.Checkbutton(
                form,
                variable=var,
                command=self._on_style_change,
                style='Option.TCheckbutton'
            )
            self._add_form_row(form, 0, label_key, chk)
            return cell

        # DPI
        self.figure_dpi_var = tk.StringVar(value=str(getattr(app_state, 'plot_dpi', 130)))
        axes_cells = []
        axes_cells.append(add_labeled_entry(axes_grid, "Figure DPI", self.figure_dpi_var, 0, 0))

        # Background colors
        self.figure_bg_var = tk.StringVar(value=getattr(app_state, 'plot_facecolor', '#ffffff'))
        self.axes_bg_var = tk.StringVar(value=getattr(app_state, 'axes_facecolor', '#ffffff'))
        axes_cells.append(add_labeled_entry(axes_grid, "Figure Background", self.figure_bg_var, 0, 1))
        axes_cells.append(add_labeled_entry(axes_grid, "Axes Background", self.axes_bg_var, 1, 0))

        # Grid style
        self.grid_color_var = tk.StringVar(value=getattr(app_state, 'grid_color', '#e2e8f0'))
        self.grid_width_var = tk.DoubleVar(value=float(getattr(app_state, 'grid_linewidth', 0.6)))
        self.grid_alpha_var = tk.DoubleVar(value=float(getattr(app_state, 'grid_alpha', 0.7)))
        axes_cells.append(add_labeled_entry(axes_grid, "Grid Color", self.grid_color_var, 1, 1))
        axes_cells.append(add_slider_with_spin(axes_grid, "Grid Linewidth", self.grid_width_var, 2, 0, 0.1, 3.0, 0.1, decimals=2))
        axes_cells.append(add_slider_with_spin(axes_grid, "Grid Alpha", self.grid_alpha_var, 2, 1, 0.0, 1.0, 0.05, decimals=2))

        grid_style_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        grid_style_cell.grid(row=3, column=0, sticky=tk.EW, pady=3)
        self.grid_style_var = tk.StringVar(value=getattr(app_state, 'grid_linestyle', '--'))
        grid_style_form = self._create_form_grid(grid_style_cell)
        grid_style_form.pack(fill=tk.X)
        grid_style_combo = ttk.Combobox(
            grid_style_form,
            textvariable=self.grid_style_var,
            values=['-', '--', '-.', ':'],
            state='readonly'
        )
        self._add_form_row(grid_style_form, 0, "Grid Style", grid_style_combo)
        grid_style_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        axes_cells.append(grid_style_cell)

        # Tick direction & axis linewidth
        self.tick_dir_var = tk.StringVar(value=getattr(app_state, 'tick_direction', 'out'))
        tick_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        tick_cell.grid(row=3, column=1, sticky=tk.EW, pady=3)
        tick_form = self._create_form_grid(tick_cell)
        tick_form.pack(fill=tk.X)
        tick_combo = ttk.Combobox(
            tick_form,
            textvariable=self.tick_dir_var,
            values=['out', 'in', 'inout'],
            state='readonly'
        )
        self._add_form_row(tick_form, 0, "Tick Direction", tick_combo)
        tick_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        axes_cells.append(tick_cell)

        self.tick_color_var = tk.StringVar(value=getattr(app_state, 'tick_color', '#1f2937'))
        axes_cells.append(add_labeled_entry(axes_grid, "Tick Color", self.tick_color_var, 4, 0))

        self.tick_length_var = tk.DoubleVar(value=float(getattr(app_state, 'tick_length', 4.0)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Tick Length", self.tick_length_var, 4, 1, 0.0, 12.0, 0.5, decimals=1))

        self.tick_width_var = tk.DoubleVar(value=float(getattr(app_state, 'tick_width', 0.8)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Tick Width", self.tick_width_var, 5, 0, 0.2, 3.0, 0.1, decimals=2))

        self.minor_ticks_var = tk.BooleanVar(value=getattr(app_state, 'minor_ticks', False))
        axes_cells.append(add_check_row(axes_grid, "Minor Ticks", self.minor_ticks_var, 5, 1))

        self.minor_tick_length_var = tk.DoubleVar(value=float(getattr(app_state, 'minor_tick_length', 2.5)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Minor Tick Length", self.minor_tick_length_var, 6, 0, 0.0, 8.0, 0.5, decimals=1))

        self.minor_tick_width_var = tk.DoubleVar(value=float(getattr(app_state, 'minor_tick_width', 0.6)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Minor Tick Width", self.minor_tick_width_var, 6, 1, 0.2, 2.0, 0.1, decimals=2))

        self.axis_linewidth_var = tk.DoubleVar(value=float(getattr(app_state, 'axis_linewidth', 1.0)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Axis Line Width", self.axis_linewidth_var, 7, 0, 0.2, 3.0, 0.1, decimals=2))

        self.axis_line_color_var = tk.StringVar(value=getattr(app_state, 'axis_line_color', '#1f2937'))
        axes_cells.append(add_labeled_entry(axes_grid, "Axis Line Color", self.axis_line_color_var, 7, 1))

        # Spine visibility
        spine_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        spine_cell.grid(row=4, column=1, sticky=tk.W, pady=3)
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
        axes_cells.append(spine_cell)

        self.minor_grid_var = tk.BooleanVar(value=getattr(app_state, 'minor_grid', False))
        axes_cells.append(add_check_row(axes_grid, "Minor Grid", self.minor_grid_var, 8, 0))

        self.minor_grid_color_var = tk.StringVar(value=getattr(app_state, 'minor_grid_color', '#e2e8f0'))
        axes_cells.append(add_labeled_entry(axes_grid, "Minor Grid Color", self.minor_grid_color_var, 8, 1))

        self.minor_grid_width_var = tk.DoubleVar(value=float(getattr(app_state, 'minor_grid_linewidth', 0.4)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Minor Grid Linewidth", self.minor_grid_width_var, 9, 0, 0.1, 2.0, 0.1, decimals=2))

        self.minor_grid_alpha_var = tk.DoubleVar(value=float(getattr(app_state, 'minor_grid_alpha', 0.4)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Minor Grid Alpha", self.minor_grid_alpha_var, 9, 1, 0.0, 1.0, 0.05, decimals=2))

        minor_grid_style_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        minor_grid_style_cell.grid(row=10, column=0, sticky=tk.EW, pady=3)
        self.minor_grid_style_var = tk.StringVar(value=getattr(app_state, 'minor_grid_linestyle', ':'))
        minor_grid_style_form = self._create_form_grid(minor_grid_style_cell)
        minor_grid_style_form.pack(fill=tk.X)
        minor_grid_style_combo = ttk.Combobox(
            minor_grid_style_form,
            textvariable=self.minor_grid_style_var,
            values=['-', '--', '-.', ':'],
            state='readonly'
        )
        self._add_form_row(minor_grid_style_form, 0, "Minor Grid Style", minor_grid_style_combo)
        minor_grid_style_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        axes_cells.append(minor_grid_style_cell)

        # Scatter edge style
        self.scatter_edgecolor_var = tk.StringVar(value=getattr(app_state, 'scatter_edgecolor', '#1e293b'))
        self.scatter_edgewidth_var = tk.DoubleVar(value=float(getattr(app_state, 'scatter_edgewidth', 0.4)))
        axes_cells.append(add_labeled_entry(axes_grid, "Scatter Edge Color", self.scatter_edgecolor_var, 11, 0))
        axes_cells.append(add_slider_with_spin(axes_grid, "Scatter Edge Width", self.scatter_edgewidth_var, 11, 1, 0.0, 2.0, 0.05, decimals=2))

        self.label_color_var = tk.StringVar(value=getattr(app_state, 'label_color', '#1f2937'))
        axes_cells.append(add_labeled_entry(axes_grid, "Label Color", self.label_color_var, 12, 0))

        self.label_weight_var = tk.StringVar(value=getattr(app_state, 'label_weight', 'normal'))
        label_weight_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        label_weight_cell.grid(row=12, column=1, sticky=tk.EW, pady=3)
        label_weight_form = self._create_form_grid(label_weight_cell)
        label_weight_form.pack(fill=tk.X)
        label_weight_combo = ttk.Combobox(
            label_weight_form,
            textvariable=self.label_weight_var,
            values=['normal', 'bold'],
            state='readonly'
        )
        self._add_form_row(label_weight_form, 0, "Label Weight", label_weight_combo)
        label_weight_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        axes_cells.append(label_weight_cell)

        self.label_pad_var = tk.DoubleVar(value=float(getattr(app_state, 'label_pad', 6.0)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Label Pad", self.label_pad_var, 13, 0, 0.0, 30.0, 1.0, decimals=0))

        self.title_color_var = tk.StringVar(value=getattr(app_state, 'title_color', '#111827'))
        axes_cells.append(add_labeled_entry(axes_grid, "Title Color", self.title_color_var, 13, 1))

        self.title_weight_var = tk.StringVar(value=getattr(app_state, 'title_weight', 'bold'))
        title_weight_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        title_weight_cell.grid(row=14, column=0, sticky=tk.EW, pady=3)
        title_weight_form = self._create_form_grid(title_weight_cell)
        title_weight_form.pack(fill=tk.X)
        title_weight_combo = ttk.Combobox(
            title_weight_form,
            textvariable=self.title_weight_var,
            values=['normal', 'bold'],
            state='readonly'
        )
        self._add_form_row(title_weight_form, 0, "Title Weight", title_weight_combo)
        title_weight_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        axes_cells.append(title_weight_cell)

        self.title_pad_var = tk.DoubleVar(value=float(getattr(app_state, 'title_pad', 20.0)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Title Pad", self.title_pad_var, 14, 1, 0.0, 40.0, 1.0, decimals=0))

        self.legend_location_var = tk.StringVar(value=getattr(app_state, 'legend_location', 'outside_right'))
        legend_loc_cell = ttk.Frame(axes_grid, style='CardBody.TFrame')
        legend_loc_cell.grid(row=15, column=0, sticky=tk.EW, pady=3)
        legend_loc_form = self._create_form_grid(legend_loc_cell)
        legend_loc_form.pack(fill=tk.X)
        legend_location_options = {
            "Outside Right": "outside_right",
            "Upper Left": "upper left",
            "Upper Right": "upper right",
            "Lower Left": "lower left",
            "Lower Right": "lower right",
            "Best": "best",
            "Center Left": "center left",
            "Center Right": "center right",
            "Upper Center": "upper center",
            "Lower Center": "lower center",
            "Center": "center",
        }
        self.legend_location_map = {self._translate(k): v for k, v in legend_location_options.items()}
        legend_loc_combo = ttk.Combobox(
            legend_loc_form,
            textvariable=self.legend_location_var,
            values=list(self.legend_location_map.keys()),
            state='readonly'
        )
        self._add_form_row(legend_loc_form, 0, "Legend Location", legend_loc_combo)
        legend_loc_combo.bind("<<ComboboxSelected>>", self._on_style_change)
        current_loc = getattr(app_state, 'legend_location', 'outside_right')
        for label, value in self.legend_location_map.items():
            if value == current_loc:
                self.legend_location_var.set(label)
                break
        axes_cells.append(legend_loc_cell)

        self.legend_frame_on_var = tk.BooleanVar(value=getattr(app_state, 'legend_frame_on', True))
        axes_cells.append(add_check_row(axes_grid, "Legend Frame", self.legend_frame_on_var, 15, 1))

        self.legend_frame_alpha_var = tk.DoubleVar(value=float(getattr(app_state, 'legend_frame_alpha', 0.95)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Legend Frame Alpha", self.legend_frame_alpha_var, 16, 0, 0.0, 1.0, 0.05, decimals=2))

        self.legend_frame_facecolor_var = tk.StringVar(value=getattr(app_state, 'legend_frame_facecolor', '#ffffff'))
        axes_cells.append(add_labeled_entry(axes_grid, "Legend Frame Face Color", self.legend_frame_facecolor_var, 16, 1))

        self.legend_frame_edgecolor_var = tk.StringVar(value=getattr(app_state, 'legend_frame_edgecolor', '#cbd5f5'))
        axes_cells.append(add_labeled_entry(axes_grid, "Legend Frame Edge Color", self.legend_frame_edgecolor_var, 17, 0))

        # Line widths
        self.model_curve_width_var = tk.DoubleVar(value=float(getattr(app_state, 'model_curve_width', 1.2)))
        self.paleoisochron_width_var = tk.DoubleVar(value=float(getattr(app_state, 'paleoisochron_width', 0.9)))
        self.model_age_width_var = tk.DoubleVar(value=float(getattr(app_state, 'model_age_line_width', 0.7)))
        self.isochron_width_var = tk.DoubleVar(value=float(getattr(app_state, 'isochron_line_width', 1.5)))
        axes_cells.append(add_slider_with_spin(axes_grid, "Model Curve Width", self.model_curve_width_var, 18, 0, 0.2, 4.0, 0.1, decimals=2))
        axes_cells.append(add_slider_with_spin(axes_grid, "Paleoisochron Width", self.paleoisochron_width_var, 18, 1, 0.2, 4.0, 0.1, decimals=2))
        axes_cells.append(add_slider_with_spin(axes_grid, "Model Age Line Width", self.model_age_width_var, 19, 0, 0.2, 4.0, 0.1, decimals=2))
        axes_cells.append(add_slider_with_spin(axes_grid, "Isochron Line Width", self.isochron_width_var, 19, 1, 0.2, 4.0, 0.1, decimals=2))

        def _relayout_axes_grid(_event=None):
            width = axes_grid.winfo_width()
            columns = 2 if width >= 720 else 1
            current = getattr(axes_grid, '_layout_columns', None)
            if current == columns:
                return
            axes_grid._layout_columns = columns
            for cell in axes_cells:
                try:
                    cell.grid_forget()
                except Exception:
                    pass
            if columns == 1:
                axes_grid.columnconfigure(0, weight=1)
                axes_grid.columnconfigure(1, weight=0)
            else:
                axes_grid.columnconfigure(0, weight=1)
                axes_grid.columnconfigure(1, weight=1)
            for idx, cell in enumerate(axes_cells):
                row = idx // columns
                col = idx % columns
                padx = (0, 16) if (columns == 2 and col == 0) else (0, 0)
                cell.grid(row=row, column=col, sticky=tk.EW, padx=padx, pady=3)

        axes_grid.bind('<Configure>', _relayout_axes_grid)

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
            'figure_dpi': self.figure_dpi_var.get(),
            'figure_bg': self.figure_bg_var.get(),
            'axes_bg': self.axes_bg_var.get(),
            'grid_color': self.grid_color_var.get(),
            'grid_linewidth': self.grid_width_var.get(),
            'grid_alpha': self.grid_alpha_var.get(),
            'grid_linestyle': self.grid_style_var.get(),
            'tick_direction': self.tick_dir_var.get(),
            'tick_color': self.tick_color_var.get(),
            'tick_length': self.tick_length_var.get(),
            'tick_width': self.tick_width_var.get(),
            'minor_ticks': self.minor_ticks_var.get(),
            'minor_tick_length': self.minor_tick_length_var.get(),
            'minor_tick_width': self.minor_tick_width_var.get(),
            'axis_linewidth': self.axis_linewidth_var.get(),
            'axis_line_color': self.axis_line_color_var.get(),
            'show_top_spine': self.show_top_spine_var.get(),
            'show_right_spine': self.show_right_spine_var.get(),
            'minor_grid': self.minor_grid_var.get(),
            'minor_grid_color': self.minor_grid_color_var.get(),
            'minor_grid_linewidth': self.minor_grid_width_var.get(),
            'minor_grid_alpha': self.minor_grid_alpha_var.get(),
            'minor_grid_linestyle': self.minor_grid_style_var.get(),
            'scatter_edgecolor': self.scatter_edgecolor_var.get(),
            'scatter_edgewidth': self.scatter_edgewidth_var.get(),
            'model_curve_width': self.model_curve_width_var.get(),
            'paleoisochron_width': self.paleoisochron_width_var.get(),
            'model_age_line_width': self.model_age_width_var.get(),
            'isochron_line_width': self.isochron_width_var.get(),
            'label_color': self.label_color_var.get(),
            'label_weight': self.label_weight_var.get(),
            'label_pad': self.label_pad_var.get(),
            'title_color': self.title_color_var.get(),
            'title_weight': self.title_weight_var.get(),
            'title_pad': self.title_pad_var.get(),
            'legend_location': self.legend_location_map.get(self.legend_location_var.get(), 'outside_right'),
            'legend_frame_on': self.legend_frame_on_var.get(),
            'legend_frame_alpha': self.legend_frame_alpha_var.get(),
            'legend_frame_facecolor': self.legend_frame_facecolor_var.get(),
            'legend_frame_edgecolor': self.legend_frame_edgecolor_var.get(),
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

        self.figure_dpi_var.set(str(data.get('figure_dpi', 130)))
        self.figure_bg_var.set(data.get('figure_bg', '#ffffff'))
        self.axes_bg_var.set(data.get('axes_bg', '#ffffff'))
        self.grid_color_var.set(data.get('grid_color', '#e2e8f0'))
        self.grid_width_var.set(float(data.get('grid_linewidth', 0.6)))
        self.grid_alpha_var.set(float(data.get('grid_alpha', 0.7)))
        self.grid_style_var.set(data.get('grid_linestyle', '--'))
        self.tick_dir_var.set(data.get('tick_direction', 'out'))
        self.tick_color_var.set(data.get('tick_color', '#1f2937'))
        self.tick_length_var.set(float(data.get('tick_length', 4.0)))
        self.tick_width_var.set(float(data.get('tick_width', 0.8)))
        self.minor_ticks_var.set(bool(data.get('minor_ticks', False)))
        self.minor_tick_length_var.set(float(data.get('minor_tick_length', 2.5)))
        self.minor_tick_width_var.set(float(data.get('minor_tick_width', 0.6)))
        self.axis_linewidth_var.set(float(data.get('axis_linewidth', 1.0)))
        self.axis_line_color_var.set(data.get('axis_line_color', '#1f2937'))
        self.show_top_spine_var.set(bool(data.get('show_top_spine', True)))
        self.show_right_spine_var.set(bool(data.get('show_right_spine', True)))
        self.minor_grid_var.set(bool(data.get('minor_grid', False)))
        self.minor_grid_color_var.set(data.get('minor_grid_color', '#e2e8f0'))
        self.minor_grid_width_var.set(float(data.get('minor_grid_linewidth', 0.4)))
        self.minor_grid_alpha_var.set(float(data.get('minor_grid_alpha', 0.4)))
        self.minor_grid_style_var.set(data.get('minor_grid_linestyle', ':'))
        self.scatter_edgecolor_var.set(data.get('scatter_edgecolor', '#1e293b'))
        self.scatter_edgewidth_var.set(float(data.get('scatter_edgewidth', 0.4)))
        self.model_curve_width_var.set(float(data.get('model_curve_width', 1.2)))
        self.paleoisochron_width_var.set(float(data.get('paleoisochron_width', 0.9)))
        self.model_age_width_var.set(float(data.get('model_age_line_width', 0.7)))
        self.isochron_width_var.set(float(data.get('isochron_line_width', 1.5)))
        self.label_color_var.set(data.get('label_color', '#1f2937'))
        self.label_weight_var.set(data.get('label_weight', 'normal'))
        self.label_pad_var.set(float(data.get('label_pad', 6.0)))
        self.title_color_var.set(data.get('title_color', '#111827'))
        self.title_weight_var.set(data.get('title_weight', 'bold'))
        self.title_pad_var.set(float(data.get('title_pad', 20.0)))
        self.legend_frame_on_var.set(bool(data.get('legend_frame_on', True)))
        self.legend_frame_alpha_var.set(float(data.get('legend_frame_alpha', 0.95)))
        self.legend_frame_facecolor_var.set(data.get('legend_frame_facecolor', '#ffffff'))
        self.legend_frame_edgecolor_var.set(data.get('legend_frame_edgecolor', '#cbd5f5'))
        # Legend location (display label)
        legend_loc = data.get('legend_location', 'outside_right')
        for label, value in self.legend_location_map.items():
            if value == legend_loc:
                self.legend_location_var.set(label)
                break
        
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
        previous_scheme = getattr(app_state, 'color_scheme', None)
        previous_fonts = (
            getattr(app_state, 'custom_primary_font', ''),
            getattr(app_state, 'custom_cjk_font', '')
        )
        previous_font_sizes = dict(getattr(app_state, 'plot_font_sizes', {}))
        previous_show_title = bool(getattr(app_state, 'show_plot_title', False))
        previous_title_pad = float(getattr(app_state, 'title_pad', 20.0))
        previous_line_widths = (
            getattr(app_state, 'model_curve_width', 1.2),
            getattr(app_state, 'paleoisochron_width', 0.9),
            getattr(app_state, 'model_age_line_width', 0.7),
            getattr(app_state, 'isochron_line_width', 1.5),
        )

        app_state.plot_style_grid = self.grid_var.get()
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

        app_state.plot_dpi = int(_safe_float(self.figure_dpi_var, 130))
        app_state.plot_facecolor = self.figure_bg_var.get() or '#ffffff'
        app_state.axes_facecolor = self.axes_bg_var.get() or '#ffffff'
        app_state.grid_color = self.grid_color_var.get() or '#e2e8f0'
        app_state.grid_linewidth = _safe_float(self.grid_width_var, 0.6)
        app_state.grid_alpha = _safe_float(self.grid_alpha_var, 0.7)
        app_state.grid_linestyle = self.grid_style_var.get() or '--'
        app_state.tick_direction = self.tick_dir_var.get() or 'out'
        app_state.tick_color = self.tick_color_var.get() or '#1f2937'
        app_state.tick_length = _safe_float(self.tick_length_var, 4.0)
        app_state.tick_width = _safe_float(self.tick_width_var, 0.8)
        app_state.minor_ticks = bool(self.minor_ticks_var.get())
        app_state.minor_tick_length = _safe_float(self.minor_tick_length_var, 2.5)
        app_state.minor_tick_width = _safe_float(self.minor_tick_width_var, 0.6)
        app_state.axis_linewidth = _safe_float(self.axis_linewidth_var, 1.0)
        app_state.axis_line_color = self.axis_line_color_var.get() or '#1f2937'
        app_state.show_top_spine = bool(self.show_top_spine_var.get())
        app_state.show_right_spine = bool(self.show_right_spine_var.get())
        app_state.minor_grid = bool(self.minor_grid_var.get())
        app_state.minor_grid_color = self.minor_grid_color_var.get() or '#e2e8f0'
        app_state.minor_grid_linewidth = _safe_float(self.minor_grid_width_var, 0.4)
        app_state.minor_grid_alpha = _safe_float(self.minor_grid_alpha_var, 0.4)
        app_state.minor_grid_linestyle = self.minor_grid_style_var.get() or ':'
        app_state.scatter_edgecolor = self.scatter_edgecolor_var.get() or '#1e293b'
        app_state.scatter_edgewidth = _safe_float(self.scatter_edgewidth_var, 0.4)
        app_state.model_curve_width = _safe_float(self.model_curve_width_var, 1.2)
        app_state.paleoisochron_width = _safe_float(self.paleoisochron_width_var, 0.9)
        app_state.model_age_line_width = _safe_float(self.model_age_width_var, 0.7)
        app_state.isochron_line_width = _safe_float(self.isochron_width_var, 1.5)
        app_state.label_color = self.label_color_var.get() or '#1f2937'
        app_state.label_weight = self.label_weight_var.get() or 'normal'
        app_state.label_pad = _safe_float(self.label_pad_var, 6.0)
        app_state.title_color = self.title_color_var.get() or '#111827'
        app_state.title_weight = self.title_weight_var.get() or 'bold'
        app_state.title_pad = _safe_float(self.title_pad_var, 20.0)
        app_state.legend_location = self.legend_location_map.get(self.legend_location_var.get(), 'outside_right')
        app_state.legend_frame_on = bool(self.legend_frame_on_var.get())
        app_state.legend_frame_alpha = _safe_float(self.legend_frame_alpha_var, 0.95)
        app_state.legend_frame_facecolor = self.legend_frame_facecolor_var.get() or '#ffffff'
        app_state.legend_frame_edgecolor = self.legend_frame_edgecolor_var.get() or '#cbd5f5'

        if app_state.fig is not None:
            try:
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

        # Decide whether to replot or just refresh style
        requires_replot = False
        if new_scheme != previous_scheme:
            requires_replot = True
        if (p_font, c_font) != previous_fonts:
            requires_replot = True
        if app_state.plot_font_sizes != previous_font_sizes:
            requires_replot = True
        if app_state.show_plot_title != previous_show_title:
            requires_replot = True
        if app_state.title_pad != previous_title_pad:
            requires_replot = True
        if (
            app_state.model_curve_width,
            app_state.paleoisochron_width,
            app_state.model_age_line_width,
            app_state.isochron_line_width,
        ) != previous_line_widths:
            requires_replot = True

        if requires_replot:
            if self.callback:
                self.callback()
        else:
            try:
                from visualization import refresh_plot_style
                refresh_plot_style()
            except Exception:
                if self.callback:
                    self.callback()

    def _apply_auto_layout(self):
        """Apply automatic layout adjustment to the figure."""
        if app_state.fig is None:
            return
        try:
            app_state.fig.set_constrained_layout(True)
            app_state.fig.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)
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
