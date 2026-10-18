"""The data panel declares its widgets once, and the reset follows the declaration.

The panel used to set thirty widget attributes to None (or to a fresh dict or list) one per line in reset_state. They
are a declaration now: one table naming every widget and its fallback, and a helper the reset calls. That is the
explicit container the review asked for, for one panel - the reads did not have to move, which is what makes it safe.
"""
from __future__ import annotations

import pathlib

from ui.panels.data.build import _WIDGET_DEFAULTS, reset_widget_state


class _Host:
    pass


#: The widgets the panel had before the declaration existed. Pinned so a widget cannot be dropped from the reset
#: without a test saying so.
EXPECTED = (
    'algo_combo',
    'algo_group',
    'group_placeholder_label',
    'group_radio_group',
    'group_radio_layout',
    'metric_combo',
    'pca_group',
    'pca_x_spin',
    'pca_y_spin',
    'plumbotectonics_model_keys',
    'render_combo',
    'robust_pca_group',
    'rpca_x_spin',
    'rpca_y_spin',
    'spinboxes',
    'ternary_auto_zoom_check',
    'ternary_group',
    'ternary_limit_mode_combo',
    'ternary_limit_spins',
    'ternary_manual_limits_check',
    'ternary_render_margin_spin',
    'tooltip_check',
    'tsne_group',
    'twod_group',
    'umap_group',
    'v1v2_group',
    'v1v2_t1_spin',
    'v1v2_t2_spin',
    'xaxis_combo',
    'yaxis_combo',
)


def test_the_declaration_names_the_measured_widgets() -> None:
    assert sorted(_WIDGET_DEFAULTS) == sorted(EXPECTED)
    assert len(_WIDGET_DEFAULTS) == 30


def test_a_reset_sets_every_declared_widget() -> None:
    host = _Host()
    host.spinboxes = {"stale": 1}
    reset_widget_state(host)
    for name, default in _WIDGET_DEFAULTS.items():
        assert getattr(host, name) == (default() if callable(default) else default), name


def test_a_mutable_default_is_fresh_on_every_reset() -> None:
    host = _Host()
    reset_widget_state(host)
    host.spinboxes["polluted"] = True
    reset_widget_state(host)
    assert host.spinboxes == {}, "a second reset must not hand back the first reset's dict"


def test_the_mixin_reset_calls_the_shared_helper() -> None:
    root = pathlib.Path(__file__).resolve().parents[1]
    source = (root / "ui/panels/data/build.py").read_text(encoding="utf-8").replace("\r\n", "\n")
    start = source.index("def reset_state")
    end = source.index("def _update_translations", start)
    assert "reset_widget_state(self)" in source[start:end]
