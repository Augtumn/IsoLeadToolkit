"""Geo overlay rendering helpers for embedding plots."""
from __future__ import annotations

import pandas as pd

from core import app_state
from ..core import _get_subset_dataframe, _get_pb_columns
from ..data import _lazy_import_geochemistry
from ..geo import (
    _draw_equation_overlays,
    _draw_isochron_overlays,
    _draw_model_age_lines,
    _draw_model_age_lines_86,
    _draw_model_curves,
    _draw_mu_kappa_paleoisochrons,
    _draw_paleoisochrons,
    _draw_plumbotectonics_curves,
    _draw_plumbotectonics_isoage_lines,
    _draw_selected_isochron,
)


def _render_geo_overlays(actual_algorithm, prev_ax, prev_embedding_type, prev_xlim, prev_ylim):
    if actual_algorithm in ('PB_EVOL_76', 'PB_EVOL_86'):
        geochemistry, _ = _lazy_import_geochemistry()
        params = geochemistry.engine.get_parameters() if geochemistry else {}
        if getattr(app_state, 'show_model_curves', True):
            _draw_model_curves(app_state.ax, actual_algorithm, [params])

        if getattr(app_state, 'show_isochrons', True):
            _draw_isochron_overlays(app_state.ax, actual_algorithm)

        if app_state.selected_isochron_data is not None:
            _draw_selected_isochron(app_state.ax)

        if getattr(app_state, 'show_paleoisochrons', True):
            ages = getattr(app_state, 'paleoisochron_ages', [3000, 2000, 1000, 0])
            _draw_paleoisochrons(app_state.ax, actual_algorithm, ages, params)

        if getattr(app_state, 'show_model_age_lines', True):
            df_subset, _ = _get_subset_dataframe()
            if df_subset is not None:
                col_206, col_207, _ = _get_pb_columns(df_subset.columns)
                if col_206 and col_207:
                    pb206 = pd.to_numeric(df_subset[col_206], errors='coerce').values
                    pb207 = pd.to_numeric(df_subset[col_207], errors='coerce').values
                    if actual_algorithm == 'PB_EVOL_76':
                        _draw_model_age_lines(app_state.ax, pb206, pb207, params)
                    else:
                        col_208 = "208Pb/204Pb" if "208Pb/204Pb" in df_subset.columns else None
                        if col_208:
                            pb208 = pd.to_numeric(df_subset[col_208], errors='coerce').values
                            _draw_model_age_lines_86(app_state.ax, pb206, pb207, pb208, params)

    if actual_algorithm in ('PLUMBOTECTONICS_76', 'PLUMBOTECTONICS_86'):
        if getattr(app_state, 'show_paleoisochrons', True):
            _draw_plumbotectonics_isoage_lines(app_state.ax, actual_algorithm)
        if getattr(app_state, 'show_plumbotectonics_curves', True):
            _draw_plumbotectonics_curves(app_state.ax, actual_algorithm)

    if actual_algorithm in ('PB_MU_AGE', 'PB_KAPPA_AGE'):
        if getattr(app_state, 'show_paleoisochrons', True):
            ages = getattr(app_state, 'paleoisochron_ages', [3000, 2000, 1000, 0])
            _draw_mu_kappa_paleoisochrons(app_state.ax, ages)

    if app_state.ax is prev_ax and prev_xlim and prev_ylim:
        if actual_algorithm != 'TERNARY' and getattr(app_state.ax, 'name', '') != '3d':
            try:
                if prev_embedding_type and str(prev_embedding_type).upper() == str(actual_algorithm).upper():
                    app_state.ax.set_xlim(prev_xlim)
                    app_state.ax.set_ylim(prev_ylim)
            except Exception:
                pass

    if actual_algorithm != 'TERNARY' and getattr(app_state.ax, 'name', '') != '3d':
        _draw_equation_overlays(app_state.ax)
