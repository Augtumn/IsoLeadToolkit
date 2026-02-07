"""
Tools Tab - Selection, export, and data management tools
"""
import tkinter as tk
from tkinter import ttk

from core import app_state


class ToolsTabMixin:
    """Mixin providing the Tools tab builder"""

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
        kde_chk = ttk.Checkbutton(
            plot_frame,
            text=self._translate("Show Kernel Density"),
            variable=self.check_vars['show_kde'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        kde_chk.pack(anchor=tk.W, pady=(0, 4))
        self._register_translation(kde_chk, "Show Kernel Density")

        self.check_vars['show_marginal_kde'] = tk.BooleanVar(
            value=getattr(app_state, 'show_marginal_kde', False)
        )
        marginal_kde_chk = ttk.Checkbutton(
            plot_frame,
            text=self._translate("Show Marginal KDE"),
            variable=self.check_vars['show_marginal_kde'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        marginal_kde_chk.pack(anchor=tk.W)
        self._register_translation(marginal_kde_chk, "Show Marginal KDE")

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
        mixing_section = self._create_section(
            frame,
            "Mixing Groups",
            "Assign selected samples as endmember or mixture groups."
        )
        mixing_frame = ttk.Frame(mixing_section, style='CardBody.TFrame')
        mixing_frame.pack(fill=tk.X)

        name_row = ttk.Frame(mixing_frame, style='CardBody.TFrame')
        name_row.pack(fill=tk.X, pady=(0, 6))
        name_label = ttk.Label(name_row, text=self._translate("Group Name:"), style='Body.TLabel')
        name_label.pack(side=tk.LEFT)
        self._register_translation(name_label, "Group Name:")

        self.mixing_group_name_var = tk.StringVar(value="")
        name_entry = ttk.Entry(name_row, textvariable=self.mixing_group_name_var)
        name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

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
