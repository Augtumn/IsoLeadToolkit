"""
Tools Tab - Selection, export, and data management tools
"""
import tkinter as tk
from tkinter import ttk

from state import app_state


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
