"""The render modes the application offers.

One list, used by the control that picks the mode and by the window that picks a mode per panel,
so the two can never drift apart. Each entry is ``(label, value)``: the label is the English key
the translation layer looks up, the value is what the state stores.
"""
from __future__ import annotations

#: Every render mode, in the order the controls show them.
RENDER_MODE_CHOICES: tuple[tuple[str, str], ...] = (
    ("UMAP", "UMAP"),
    ("t-SNE", "tSNE"),
    ("PCA", "PCA"),
    ("RobustPCA", "RobustPCA"),
    ("2D", "2D"),
    ("3D", "3D"),
    ("Ternary", "Ternary"),
    ("V1-V2 Diagram", "V1V2"),
    ("PB_EVOL_76", "PB_EVOL_76"),
    ("PB_EVOL_86", "PB_EVOL_86"),
    ("PLUMBOTECTONICS_76", "PLUMBOTECTONICS_76"),
    ("PLUMBOTECTONICS_86", "PLUMBOTECTONICS_86"),
    ("PB_MU_AGE", "PB_MU_AGE"),
    ("PB_KAPPA_AGE", "PB_KAPPA_AGE"),
)

#: Just the mode values, for validating one.
RENDER_MODE_VALUES: tuple[str, ...] = tuple(value for _label, value in RENDER_MODE_CHOICES)

#: The label a mode is shown under, falling back to the value itself.
LABEL_FOR_MODE: dict[str, str] = {value: label for label, value in RENDER_MODE_CHOICES}
