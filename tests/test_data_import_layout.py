"""Importing a dataset decides how many figures the window shows."""
from __future__ import annotations

import pandas as pd

from core import app_state, state_gateway


def _request(frame):
    from application.use_cases.load_dataset import DatasetImport

    return DatasetImport(
        file_path="x.xlsx",
        sheet_name="Sheet1",
        frame=frame,
        group_cols=("Site",),
        data_cols=("Pb206",),
        render_mode="UMAP",
    )


def test_importing_a_dataset_resets_the_panel_layout(qapp, monkeypatch) -> None:
    """Reported: one algorithm chosen in the wizard, two windows in the main window.

    The panel list describes the previous layout and a session restore keeps it on purpose; an
    import left it in place, so the panels of the old layout were built again for a single mode.
    """
    from ui.panels.data.dialogs.data_import import load_flow

    frame = pd.DataFrame({"Site": ["A", "B"], "Pb206": [1.0, 2.0]})
    state_gateway.set_plot_panels(["2D", "UMAP"])
    monkeypatch.setattr(load_flow, "_collect_import", lambda: _request(frame))
    monkeypatch.setattr(load_flow, "load_dataset", lambda request: None)

    assert load_flow.load_dataset_via_dialogs() is True

    assert app_state.plot_panels == [], (
        "the imported dataset is drawn as one figure, in the mode the wizard chose"
    )
