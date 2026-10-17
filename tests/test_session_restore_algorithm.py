"""Restoring a session keeps the dimensionality-reduction algorithm it was saved with.

Reported by the code review, and it was a regression: the condition that decides whether a mode picks an
algorithm was widened to every mode that has one - UMAP, t-SNE, PCA and Robust PCA - but the value stayed
`"UMAP" if mode == "UMAP" else "tSNE"`, so restoring a PCA session turned it into t-SNE, and restoring
Robust PCA did too. `SET_ALGORITHM` then writes the algorithm back into the render mode, so the mode itself
changed.
"""
from __future__ import annotations

import pytest

from core import app_state, state_gateway
from core.render_modes import capabilities_for

from ui.app_parts.session import restore_algorithm_for_mode

#: The modes that pick an algorithm; the mode's own name is the algorithm.
ALGORITHM_MODES = tuple(mode for mode in ("UMAP", "tSNE", "PCA", "RobustPCA"))


@pytest.mark.parametrize("mode", ALGORITHM_MODES)
def test_a_restored_mode_keeps_its_own_algorithm(mode: str) -> None:
    assert capabilities_for(mode).has_algorithm, f"{mode} selects an algorithm"

    state_gateway.set_render_mode(mode)
    # What the session restore does for such a mode.
    if capabilities_for(app_state.render_mode).has_algorithm:
        restore_algorithm_for_mode()

    assert app_state.algorithm == mode, f"{mode} kept its algorithm, got {app_state.algorithm}"
    assert app_state.render_mode == mode, (
        f"{mode} kept its mode; SET_ALGORITHM writes the algorithm into it, got {app_state.render_mode}"
    )


def test_every_mode_with_an_algorithm_names_itself() -> None:
    """The restore relies on the mode's name being the algorithm; that has to stay true."""
    from core.render_modes import RENDER_MODE_VALUES

    named = [mode for mode in RENDER_MODE_VALUES if capabilities_for(mode).has_algorithm]
    assert named, "some mode picks an algorithm"
    for mode in named:
        assert mode in ("UMAP", "tSNE", "PCA", "RobustPCA"), (
            f"{mode} selects an algorithm but is not one; the restore would need its own mapping"
        )
