"""
Tools Tab - Selection, export, and data management tools
"""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import uuid
import re
import numpy as np

from core import app_state
from visualization.kde_styles import open_kde_style_dialog


class ToolsTabMixin:
    """Mixin providing the Tools tab builder"""

    def _add_equation_overlay_row(self, overlay):
        """Add a single equation overlay row to the UI."""
        overlay_id = overlay.get('id')
        if not overlay_id or not hasattr(self, 'equation_overlay_frame'):
            return

        row = ttk.Frame(self.equation_overlay_frame, style='CardBody.TFrame')
        row.pack(fill=tk.X, pady=1)

        var_key = f"equation_overlay_{overlay_id}"
        self.check_vars[var_key] = tk.BooleanVar(value=overlay.get('enabled', True))
        label_text = overlay.get('label', 'Equation')
        eq_chk = ttk.Checkbutton(
            row,
            text=self._translate(label_text),
            variable=self.check_vars[var_key],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        eq_chk.pack(side=tk.LEFT, anchor=tk.W)
        self._register_translation(eq_chk, label_text)

        color_val = overlay.get('color', '#ef4444')
        swatch = tk.Label(row, width=2, height=1, bg=color_val, relief='solid', bd=1)
        swatch.pack(side=tk.LEFT, padx=(8, 0))
        swatch.bind(
            "<Button-1>",
            lambda e, ov=overlay, sw=swatch: self._open_equation_style_dialog(ov, sw)
        )
        self.equation_overlay_swatches[overlay_id] = swatch

    def _open_equation_style_dialog(self, overlay, swatch):
        """Open a dialog to edit line style for an equation overlay."""
        dialog = tk.Toplevel(self.root)
        dialog.title(self._translate("Edit Equation Style"))
        dialog.geometry("420x260")
        dialog.transient(self.root)
        dialog.grab_set()

        body = ttk.Frame(dialog, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        style_grid = ttk.Frame(body, style='CardBody.TFrame')
        style_grid.pack(fill=tk.X)

        line_color = tk.StringVar(value=overlay.get('color', '#ef4444'))
        line_width = tk.DoubleVar(value=float(overlay.get('linewidth', 1.0)))
        line_style = tk.StringVar(value=overlay.get('linestyle', '--'))
        line_alpha = tk.DoubleVar(value=float(overlay.get('alpha', 0.85)))

        color_row = ttk.Frame(style_grid, style='CardBody.TFrame')
        color_row.pack(fill=tk.X, pady=4)
        ttk.Label(color_row, text=self._translate("Line Color"), style='Body.TLabel').pack(side=tk.LEFT)
        color_swatch = tk.Label(color_row, width=3, height=1, bg=line_color.get(), relief='solid', bd=1)
        color_swatch.pack(side=tk.LEFT, padx=(8, 0))

        def _pick_color():
            chosen = colorchooser.askcolor(initialcolor=line_color.get(), parent=dialog)
            if chosen and chosen[1]:
                line_color.set(chosen[1])
                color_swatch.configure(bg=chosen[1])

        ttk.Button(
            color_row,
            text=self._translate("Choose Color"),
            style='Secondary.TButton',
            command=_pick_color
        ).pack(side=tk.LEFT, padx=(8, 0))

        width_row = ttk.Frame(style_grid, style='CardBody.TFrame')
        width_row.pack(fill=tk.X, pady=4)
        ttk.Label(width_row, text=self._translate("Line Width"), style='Body.TLabel').pack(side=tk.LEFT)
        ttk.Spinbox(width_row, from_=0.2, to=6.0, increment=0.1, textvariable=line_width, width=6).pack(side=tk.LEFT, padx=(8, 0))

        style_row = ttk.Frame(style_grid, style='CardBody.TFrame')
        style_row.pack(fill=tk.X, pady=4)
        ttk.Label(style_row, text=self._translate("Line Style"), style='Body.TLabel').pack(side=tk.LEFT)
        ttk.Combobox(style_row, textvariable=line_style, values=['-', '--', '-.', ':'], state='readonly', width=6).pack(side=tk.LEFT, padx=(8, 0))

        alpha_row = ttk.Frame(style_grid, style='CardBody.TFrame')
        alpha_row.pack(fill=tk.X, pady=4)
        ttk.Label(alpha_row, text=self._translate("Opacity"), style='Body.TLabel').pack(side=tk.LEFT)
        ttk.Spinbox(alpha_row, from_=0.1, to=1.0, increment=0.05, textvariable=line_alpha, width=6).pack(side=tk.LEFT, padx=(8, 0))

        btn_row = ttk.Frame(body)
        btn_row.pack(fill=tk.X, pady=(12, 0))
        btn_row.columnconfigure(0, weight=1)

        def _apply():
            overlay['color'] = line_color.get() or '#ef4444'
            overlay['linewidth'] = float(line_width.get())
            overlay['linestyle'] = line_style.get() or '--'
            overlay['alpha'] = float(line_alpha.get())
            if swatch is not None:
                swatch.configure(bg=overlay['color'])
            dialog.destroy()
            self._on_change()

        ttk.Button(btn_row, text=self._translate("Cancel"), style='Secondary.TButton', command=dialog.destroy).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text=self._translate("Save"), style='Accent.TButton', command=_apply).pack(side=tk.RIGHT, padx=(0, 8))

    def _open_add_equation_dialog(self):
        """Open a dialog to add a custom equation overlay."""
        dialog = tk.Toplevel(self.root)
        dialog.title(self._translate("Add Equation"))
        dialog.geometry("520x340")
        dialog.transient(self.root)
        dialog.grab_set()

        body = ttk.Frame(dialog, padding=12)
        body.pack(fill=tk.BOTH, expand=True)

        name_var = tk.StringVar(value="")
        latex_var = tk.StringVar(value="y=x")
        expr_var = tk.StringVar(value="x")

        form = ttk.Frame(body, style='CardBody.TFrame')
        form.pack(fill=tk.X)

        ttk.Label(form, text=self._translate("Equation Name"), style='Body.TLabel').grid(row=0, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=name_var, width=42).grid(row=0, column=1, sticky=tk.W, pady=4)

        ttk.Label(form, text=self._translate("Equation (LaTeX)"), style='Body.TLabel').grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=latex_var, width=42).grid(row=1, column=1, sticky=tk.W, pady=4)

        ttk.Label(form, text=self._translate("Expression (Python, x only)"), style='Body.TLabel').grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(form, textvariable=expr_var, width=42).grid(row=2, column=1, sticky=tk.W, pady=4)

        hint = ttk.Label(
            body,
            text=self._translate("Use LaTeX for display, and Python expression for computation. Example: 1.0049*x+20.259"),
            style='BodyMuted.TLabel',
            wraplength=470
        )
        hint.pack(anchor=tk.W, pady=(8, 0))

        btn_row = ttk.Frame(body)
        btn_row.pack(fill=tk.X, pady=(12, 0))
        btn_row.columnconfigure(0, weight=1)

        def _latex_to_expression(latex_text):
            expr = latex_text.strip()
            expr = expr.strip('$')
            expr = re.sub(r'^y\s*=\s*', '', expr)
            expr = expr.replace('\\times', '*').replace('\\cdot', '*')
            expr = expr.replace('^', '**')
            expr = expr.replace('{', '').replace('}', '')
            expr = re.sub(r'(\d)\s*(x)', r'\1*\2', expr)
            expr = re.sub(r'(\d)\s*\(', r'\1*(', expr)
            expr = re.sub(r'\s+', '', expr)
            return expr

        def _apply():
            label = name_var.get().strip() or latex_var.get().strip()
            latex = latex_var.get().strip()
            expr = expr_var.get().strip()
            if not expr and latex:
                expr = _latex_to_expression(latex)
            if not expr:
                messagebox.showwarning(self._translate("Add Equation"), self._translate("Expression cannot be empty."), parent=dialog)
                return
            try:
                test_x = np.array([0.0, 1.0])
                eval(expr, {"__builtins__": {}}, {"x": test_x, "np": np})
            except Exception:
                messagebox.showwarning(self._translate("Add Equation"), self._translate("Invalid expression."), parent=dialog)
                return

            overlay_id = f"eq_custom_{uuid.uuid4().hex[:8]}"
            overlay = {
                'id': overlay_id,
                'label': label or 'Equation',
                'latex': latex,
                'expression': expr,
                'enabled': True,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85
            }
            app_state.equation_overlays.append(overlay)
            app_state.show_equation_overlays = True
            if 'show_equation_overlays' in self.check_vars:
                self.check_vars['show_equation_overlays'].set(True)
            self._add_equation_overlay_row(overlay)
            dialog.destroy()
            self._on_change()

        ttk.Button(btn_row, text=self._translate("Cancel"), style='Secondary.TButton', command=dialog.destroy).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text=self._translate("Save"), style='Accent.TButton', command=_apply).pack(side=tk.RIGHT, padx=(0, 8))

    def _build_tools_tab(self, parent):
        """Build the Tools tab content"""
        frame = self._build_scrollable_frame(parent)

        # Data Analysis Tools
        analysis_section = self._create_section(
            frame,
            "Data Analysis",
            "Tools for exploring data relationships and statistics."
        )
        
        analysis_row = ttk.Frame(analysis_section, style='CardBody.TFrame')
        analysis_row.pack(fill=tk.X)
        analysis_row.columnconfigure(0, weight=1)
        analysis_row.columnconfigure(1, weight=1)
        
        from visualization import show_correlation_heatmap, show_embedding_correlation, show_shepard_diagram
        
        corr_btn = ttk.Button(
            analysis_row,
            text=self._translate("Correlation Heatmap"),
            style='Secondary.TButton',
            command=lambda: show_correlation_heatmap(self.root)
        )
        corr_btn.grid(row=0, column=0, sticky=tk.EW, padx=(0, 10), pady=(0, 6))
        self._register_translation(corr_btn, "Correlation Heatmap")

        axis_corr_btn = ttk.Button(
            analysis_row,
            text=self._translate("Show Axis Corr."),
            style='Secondary.TButton',
            command=lambda: show_embedding_correlation(self.root)
        )
        axis_corr_btn.grid(row=0, column=1, sticky=tk.EW, padx=(0, 0), pady=(0, 6))
        self._register_translation(axis_corr_btn, "Show Axis Corr.")
        
        shepard_btn = ttk.Button(
            analysis_row,
            text=self._translate("Show Shepard Plot"),
            style='Secondary.TButton',
            command=lambda: show_shepard_diagram(self.root)
        )
        shepard_btn.grid(row=1, column=0, sticky=tk.EW)
        self._register_translation(shepard_btn, "Show Shepard Plot")

        # Plot Enhancement Tools
        plot_section = self._create_section(
            frame,
            "Plot Enhancements",
            "Optional overlays to improve plot interpretation."
        )
        
        plot_frame = ttk.Frame(plot_section, style='CardBody.TFrame')
        plot_frame.pack(fill=tk.X)
        
        self.check_vars['show_kde'] = tk.BooleanVar(value=getattr(app_state, 'show_kde', False))
        kde_row = ttk.Frame(plot_frame, style='CardBody.TFrame')
        kde_row.pack(fill=tk.X, pady=(0, 4))
        kde_chk = ttk.Checkbutton(
            kde_row,
            text=self._translate("Show Kernel Density"),
            variable=self.check_vars['show_kde'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        kde_chk.pack(side=tk.LEFT, anchor=tk.W)
        self._register_translation(kde_chk, "Show Kernel Density")
        kde_swatch = tk.Label(kde_row, width=2, height=1, bg='#e2e8f0', relief='solid', bd=1)
        kde_swatch.pack(side=tk.LEFT, padx=(8, 0))
        kde_swatch.bind(
            "<Button-1>",
            lambda e: open_kde_style_dialog(self.root, self._translate, app_state, target='kde', swatch=kde_swatch, on_apply=self._on_change)
        )

        self.check_vars['show_marginal_kde'] = tk.BooleanVar(
            value=getattr(app_state, 'show_marginal_kde', False)
        )
        mkde_row = ttk.Frame(plot_frame, style='CardBody.TFrame')
        mkde_row.pack(fill=tk.X)
        marginal_kde_chk = ttk.Checkbutton(
            mkde_row,
            text=self._translate("Show Marginal KDE"),
            variable=self.check_vars['show_marginal_kde'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        marginal_kde_chk.pack(side=tk.LEFT, anchor=tk.W)
        self._register_translation(marginal_kde_chk, "Show Marginal KDE")
        mkde_swatch = tk.Label(mkde_row, width=2, height=1, bg='#e2e8f0', relief='solid', bd=1)
        mkde_swatch.pack(side=tk.LEFT, padx=(8, 0))
        mkde_swatch.bind(
            "<Button-1>",
            lambda e: open_kde_style_dialog(self.root, self._translate, app_state, target='marginal', swatch=mkde_swatch, on_apply=self._on_change)
        )

        self.check_vars['show_equation_overlays'] = tk.BooleanVar(
            value=getattr(app_state, 'show_equation_overlays', False)
        )
        eq_overlay_chk = ttk.Checkbutton(
            plot_frame,
            text=self._translate("Show Equation Overlays"),
            variable=self.check_vars['show_equation_overlays'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        eq_overlay_chk.pack(anchor=tk.W, pady=(8, 2))
        self._register_translation(eq_overlay_chk, "Show Equation Overlays")

        eq_list_frame = ttk.Frame(plot_frame, style='CardBody.TFrame')
        eq_list_frame.pack(fill=tk.X)
        self.equation_overlay_frame = eq_list_frame
        self.equation_overlay_swatches = {}

        for overlay in getattr(app_state, 'equation_overlays', []):
            self._add_equation_overlay_row(overlay)

        add_eq_btn = ttk.Button(
            plot_frame,
            text=self._translate("Add Equation"),
            style='Secondary.TButton',
            command=self._open_add_equation_dialog
        )
        add_eq_btn.pack(anchor=tk.W, pady=(6, 0))
        self._register_translation(add_eq_btn, "Add Equation")

        # Tooltip Settings
        tooltip_section = self._create_section(
            frame,
            "Tooltip",
            "Configure data to display when hovering over points."
        )
        tooltip_frame = ttk.Frame(tooltip_section, style='CardBody.TFrame')
        tooltip_frame.pack(fill=tk.X)

        self.check_vars['show_tooltip'] = tk.BooleanVar(
            value=getattr(app_state, 'show_tooltip', True)
        )
        tooltip_chk = ttk.Checkbutton(
            tooltip_frame,
            text=self._translate("Show Tooltip"),
            variable=self.check_vars['show_tooltip'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        tooltip_chk.pack(anchor=tk.W, pady=(0, 6))
        self._register_translation(tooltip_chk, "Show Tooltip")

        tooltip_btn = ttk.Button(
            tooltip_frame,
            text=self._translate("Configure Tooltip"),
            command=self._open_tooltip_settings,
            style='Secondary.TButton'
        )
        tooltip_btn.pack(anchor=tk.W)
        self._register_translation(tooltip_btn, "Configure Tooltip")

        # Mixing Group Tools
        mixing_section = self._create_collapsible_section(
            frame,
            "Mixing Groups",
            "Assign selected samples as endmember or mixture groups.",
            start_open=False
        )
        mixing_frame = ttk.Frame(mixing_section, style='CardBody.TFrame')
        mixing_frame.pack(fill=tk.X)

        mixing_grid = self._create_form_grid(mixing_frame)
        mixing_grid.pack(fill=tk.X, pady=(0, 6))

        self.mixing_group_name_var = tk.StringVar(value="")
        name_entry = ttk.Entry(mixing_grid, textvariable=self.mixing_group_name_var)
        self._add_form_row(mixing_grid, 0, "Group Name:", name_entry)

        btn_row = ttk.Frame(mixing_frame, style='CardBody.TFrame')
        btn_row.pack(fill=tk.X, pady=(0, 6))
        self.set_endmember_btn = ttk.Button(
            btn_row,
            text=self._translate("Set as Endmember"),
            style='Secondary.TButton',
            command=lambda: self._set_mixing_group('endmembers')
        )
        self.set_endmember_btn.pack(side=tk.LEFT, padx=(0, 8))
        self._register_translation(self.set_endmember_btn, "Set as Endmember")

        self.set_mixture_btn = ttk.Button(
            btn_row,
            text=self._translate("Set as Mixture"),
            style='Secondary.TButton',
            command=lambda: self._set_mixing_group('mixtures')
        )
        self.set_mixture_btn.pack(side=tk.LEFT)
        self._register_translation(self.set_mixture_btn, "Set as Mixture")

        info_row = ttk.Frame(mixing_frame, style='CardBody.TFrame')
        info_row.pack(fill=tk.X, pady=(4, 6))
        self.mixing_group_status = ttk.Label(
            info_row,
            text=self._translate("Endmembers: {count} | Mixtures: {count2}", count=0, count2=0),
            style='BodyMuted.TLabel'
        )
        self.mixing_group_status.pack(anchor=tk.W)
        self._register_translation(
            self.mixing_group_status,
            "Endmembers: {count} | Mixtures: {count2}",
            formatter=lambda: {
                'count': len(getattr(app_state, 'mixing_groups', {}).get('endmembers', {})),
                'count2': len(getattr(app_state, 'mixing_groups', {}).get('mixtures', {}))
            }
        )

        clear_btn = ttk.Button(
            mixing_frame,
            text=self._translate("Clear Mixing Groups"),
            style='Secondary.TButton',
            command=self._clear_mixing_groups
        )
        clear_btn.pack(anchor=tk.W)
        self._register_translation(clear_btn, "Clear Mixing Groups")

        compute_btn = ttk.Button(
            mixing_frame,
            text=self._translate("Compute Mixing"),
            style='Secondary.TButton',
            command=self._open_mixing_calculator
        )
        compute_btn.pack(anchor=tk.W, pady=(6, 0))
        self._register_translation(compute_btn, "Compute Mixing")

        # Confidence Ellipse Settings
        conf_section = self._create_collapsible_section(
            frame,
            "Confidence Ellipse",
            "Set the confidence level for selection ellipses.",
            start_open=False
        )
        
        conf_frame = ttk.Frame(conf_section, style='CardBody.TFrame')
        conf_frame.pack(fill=tk.X, pady=(0, 8))

        conf_grid = self._create_form_grid(conf_frame)
        conf_grid.pack(fill=tk.X)

        conf_options = ttk.Frame(conf_grid, style='CardBody.TFrame')
        self._add_form_row(conf_grid, 0, "Confidence Level", conf_options)
        
        self.radio_vars['confidence'] = tk.DoubleVar(value=app_state.ellipse_confidence)
        
        for level in [0.68, 0.95, 0.99]:
            rb = ttk.Radiobutton(
                conf_options,
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

        self.export_plot_button = ttk.Button(
            export_row,
            text=self._translate("Export Plot (Plotnine)"),
            style='Secondary.TButton',
            command=self._export_plotnine_image
        )
        self.export_plot_button.pack(side=tk.LEFT, padx=(12, 0))
        self._register_translation(self.export_plot_button, "Export Plot (Plotnine)")

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
        data_mgmt_section = self._create_collapsible_section(
            frame,
            "Data Management",
            "Import new data files into the application.",
            start_open=False
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
