"""
Settings Tab - General settings for the Control Panel
"""
import tkinter as tk
from tkinter import ttk

from core import app_state


class SettingsTabMixin:
    """Mixin providing the Settings tab builder"""

    def _build_settings_tab(self, parent):
        """Build the Settings tab content"""
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
            ("207Pb/204Pb - 206Pb/204Pb", "ISOCHRON1"),
            ("208Pb/204Pb - 206Pb/204Pb", "ISOCHRON2"),
            ("2D Scatter (raw)", "2D"),
            ("3D Scatter (raw)", "3D"),
        ]

        for idx, (label_key, value) in enumerate(options):
            # Use 2 columns to prevent overlap and accommodate long labels
            column = idx % 2 
            row = idx // 2
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
