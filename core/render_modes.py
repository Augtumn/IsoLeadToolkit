"""The render modes the application offers, and what each one needs.

One list, and for every mode one record of what it needs. Both live here, in the layer every other
layer may import, because both are asked for from more than one place: the controls build their list
from it, the renderer asks which projection a mode uses, and the panels ask which of their sections
apply.

This replaces the separate tuples that used to answer those questions - each one a list of modes that
could fall out of step with this list, and did: a mode left out of one of them quietly lost a feature
(the Plumbotectonics panel showed no controls, editing a model did not redraw, and a session did not
restore the algorithm of a PCA plot).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class ModeCapabilities:
    """What one render mode needs, so nothing has to keep its own list of modes."""

    #: Which axes the mode draws into.
    projection: str = "2d"
    #: How many data columns the user must select, 0 when the mode chooses its own.
    needs_columns: int = 0
    #: Drawn by the embedding renderer rather than the raw 2D/3D ones.
    embedding: bool = False
    #: Computed in the background, so a render may come back with work still pending.
    asynchronous: bool = False
    #: Computed by one of the algorithms the user picks between (UMAP, t-SNE, PCA, RobustPCA).
    has_algorithm: bool = False
    #: Draws from the geochemistry parameters, so editing them is worth a redraw.
    uses_geochem_params: bool = False
    #: The mode has sections in the geochemistry panel.
    shows_geochem_controls: bool = False
    #: ...including the overlay group, which holds the model-curve and Plumbotectonics toggles.
    shows_overlay_controls: bool = False
    #: ...including the model-curve controls.
    shows_model_curve_controls: bool = False
    #: ...including the Plumbotectonics model choice.
    shows_plumbotectonics_model: bool = False
    #: ...including the Mu/Kappa age controls.
    shows_mu_kappa_age_controls: bool = False
    #: ...including the isochron controls (only the 206-207 evolution plot fits an isochron).
    shows_isochron_controls: bool = False


#: Every render mode, in the order the controls show them: ``(label, value)``. The label is the
#: English key the translation layer looks up; the value is what the state stores and what a render is
#: dispatched by.
RENDER_MODE_CHOICES: Final[tuple[tuple[str, str], ...]] = (
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
RENDER_MODE_VALUES: Final[tuple[str, ...]] = tuple(value for _label, value in RENDER_MODE_CHOICES)

#: The label a mode is shown under, falling back to the value itself.
LABEL_FOR_MODE: Final[dict[str, str]] = {
    value: label for label, value in RENDER_MODE_CHOICES
}

#: What each mode needs. Keyed by the mode values above, and checked against them by
#: ``scripts/check_render_modes.py``: a mode without a record, or a record without a mode, fails.
MODE_CAPABILITIES: Final[dict[str, ModeCapabilities]] = {
    "UMAP": ModeCapabilities(embedding=True, asynchronous=True, has_algorithm=True),
    "tSNE": ModeCapabilities(embedding=True, asynchronous=True, has_algorithm=True),
    "PCA": ModeCapabilities(embedding=True, asynchronous=True, has_algorithm=True),
    "RobustPCA": ModeCapabilities(embedding=True, asynchronous=True, has_algorithm=True),
    "2D": ModeCapabilities(needs_columns=2),
    "3D": ModeCapabilities(projection="3d", needs_columns=3),
    "Ternary": ModeCapabilities(projection="ternary", needs_columns=3, embedding=True),
    "V1V2": ModeCapabilities(
        embedding=True,
        uses_geochem_params=True,
        shows_geochem_controls=True,
    ),
    "PB_EVOL_76": ModeCapabilities(
        embedding=True,
        uses_geochem_params=True,
        shows_geochem_controls=True,
        shows_overlay_controls=True,
        shows_model_curve_controls=True,
        shows_isochron_controls=True,
    ),
    "PB_EVOL_86": ModeCapabilities(
        embedding=True,
        uses_geochem_params=True,
        shows_geochem_controls=True,
        shows_overlay_controls=True,
        shows_model_curve_controls=True,
    ),
    "PLUMBOTECTONICS_76": ModeCapabilities(
        embedding=True,
        uses_geochem_params=True,
        shows_geochem_controls=True,
        shows_overlay_controls=True,
        shows_plumbotectonics_model=True,
    ),
    "PLUMBOTECTONICS_86": ModeCapabilities(
        embedding=True,
        uses_geochem_params=True,
        shows_geochem_controls=True,
        shows_overlay_controls=True,
        shows_plumbotectonics_model=True,
    ),
    "PB_MU_AGE": ModeCapabilities(
        embedding=True,
        uses_geochem_params=True,
        shows_geochem_controls=True,
        shows_overlay_controls=True,
        shows_mu_kappa_age_controls=True,
    ),
    "PB_KAPPA_AGE": ModeCapabilities(
        embedding=True,
        uses_geochem_params=True,
        shows_geochem_controls=True,
        shows_overlay_controls=True,
        shows_mu_kappa_age_controls=True,
    ),
}


def capabilities_for(mode: object) -> ModeCapabilities:
    """What *mode* needs; an unknown mode has no capabilities of its own."""
    return MODE_CAPABILITIES.get(str(mode), ModeCapabilities())


def modes_using_geochem_params() -> tuple[str, ...]:
    """The modes that draw from the geochemistry parameters.

    Editing a model or a parameter is worth a redraw in these modes and in no others.
    """
    return tuple(mode for mode in RENDER_MODE_VALUES if MODE_CAPABILITIES[mode].uses_geochem_params)


def asynchronous_modes() -> tuple[str, ...]:
    """The modes whose embedding is computed in the background."""
    return tuple(mode for mode in RENDER_MODE_VALUES if MODE_CAPABILITIES[mode].asynchronous)
