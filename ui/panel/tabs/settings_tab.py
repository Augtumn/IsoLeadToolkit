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
        self._build_settings_content(frame)

    def _build_settings_content(self, frame):
        """Build the Settings tab content (no scroll wrapper)."""
        # Projection Mode
        if not getattr(app_state, 'render_mode', None):
            app_state.render_mode = getattr(app_state, 'algorithm', 'UMAP')
        if app_state.render_mode in ('PB_MODELS_76', 'PB_MODELS_86'):
            app_state.render_mode = 'PB_EVOL_76' if app_state.render_mode.endswith('_76') else 'PB_EVOL_86'
        self.radio_vars['render_mode'] = tk.StringVar(value=app_state.render_mode)

        algo_section = self._create_section(
            frame,
            "Projection Mode",
            "Select between UMAP or t-SNE embeddings, or display raw measurements in either 2D or 3D space."
        )

        selection_grid = ttk.Frame(algo_section, style='CardBody.TFrame')
        selection_grid.pack(fill=tk.X, pady=(4, 0))

        def add_mode_group(parent, title_key, options):
            title = ttk.Label(parent, text=self._translate(title_key), style='FieldLabel.TLabel')
            title.pack(anchor=tk.W, pady=(6, 2))
            self._register_translation(title, title_key)

            grid = ttk.Frame(parent, style='CardBody.TFrame')
            grid.pack(fill=tk.X, pady=(0, 4))

            for idx, (label_key, value) in enumerate(options):
                column = idx % 2
                row = idx // 2
                cell = ttk.Frame(grid, style='CardBody.TFrame')
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

        add_mode_group(selection_grid, "Embedding Modes", [
            ("UMAP Embedding", "UMAP"),
            ("t-SNE Embedding", "tSNE"),
            ("PCA Embedding", "PCA"),
            ("Robust PCA", "RobustPCA"),
        ])

        add_mode_group(selection_grid, "Visualization Modes", [
            ("2D Scatter (raw)", "2D"),
            ("3D Scatter (raw)", "3D"),
            ("Ternary Plot", "Ternary"),
        ])

        add_mode_group(selection_grid, "Geochemistry Modes", [
            ("V1-V2 Diagram", "V1V2"),
            ("Pb Evolution 206-207", "PB_EVOL_76"),
            ("Pb Evolution 206-208", "PB_EVOL_86"),
            ("Mu vs Age", "PB_MU_AGE"),
            ("Kappa vs Age", "PB_KAPPA_AGE"),
        ])

        # Tooltip configuration moved to Tools tab
