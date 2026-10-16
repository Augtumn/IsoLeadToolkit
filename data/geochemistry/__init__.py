"""Geochemistry package exports."""
from __future__ import annotations

import logging
from typing import Any

import numpy as np

from .engine import (
    PRESET_MODELS,
    GeochemistryEngine,
    engine,
    calculate_modelcurve,
    calculate_model_slope,
    T_EARTH_1ST,
    T_EARTH_CANON,
    T_SK_STAGE2,
    LAMBDA_238,
    LAMBDA_235,
    LAMBDA_232,
    A0,
    B0,
    C0,
    A1_SK,
    B1_SK,
    C1_SK,
    MU_M_DEFAULT,
    OMEGA_M_DEFAULT,
    U_RATIO_NATURAL,
    EPSILON,
    E1_DEFAULT,
    E2_DEFAULT,
    ALBAREDE_T0,
    ALBAREDE_X_STAR,
    ALBAREDE_Y_STAR,
    ALBAREDE_Z_STAR,
    ALBAREDE_MU_STAR,
    ALBAREDE_KAPPA_STAR,
    ALBAREDE_OMEGA_STAR,
    ALBAREDE_U238_235,
    U_RATIO_AJ84,
    ALBAREDE_X0,
    ALBAREDE_Y0,
    ALBAREDE_Z0,
)
from .age import (
    calculate_single_stage_age,
    calculate_two_stage_age,
    calculate_albarede_model_age,
    calculate_albarede_age_sensitivity,
    albarede_model_age_residual,
)
from .source import (
    _invert_mu,
    _invert_omega,
    calculate_source_mu,
    calculate_source_omega,
    calculate_source_nu,
    calculate_model_mu,
    calculate_model_kappa,
    calculate_initial_ratio_64,
    calculate_initial_ratio_74,
    calculate_initial_ratio_84,
    calculate_albarede_delta_mu,
    calculate_albarede_mu,
    calculate_albarede_delta_kappa,
    calculate_albarede_kappa,
)
from .delta import (
    calculate_deltas,
    calculate_v1v2_coordinates,
)
from .isochron import (
    calculate_paleoisochron_line,
    calculate_isochron1_growth_curve,
    calculate_isochron2_growth_curve,
    york_regression,
    calculate_pbpb_age_from_ratio,
    calculate_isochron_age_from_slope,
    calculate_source_mu_from_isochron,
    calculate_source_kappa_from_slope,
)


logger = logging.getLogger(__name__)
_AGE_MODEL_PARAM_DELTA_FLOOR = 1e-6


def resolve_age_model(params: dict | None = None, model_name: str | None = None) -> str:
    """Resolve age model mode from params and model name."""
    if params is None:
        params = engine.params
    if model_name is None:
        model_name = getattr(engine, 'current_model_name', '')

    # Prefer the explicit age_model flag.
    age_model = params.get('age_model')
    if isinstance(age_model, str):
        mode = age_model.strip().lower().replace('_', '-')
        if mode in ('two-stage', 'two stage', '2-stage', '2nd', 'second'):
            return 'two_stage'
        if mode in ('single-stage', 'single stage', '1-stage', '1st', 'first'):
            return 'single_stage'

    # Custom parameter sets may omit the flag; infer from the parameter shape instead.
    logger.debug("age_model flag not found in params, falling back to heuristics for model '%s'", model_name)

    if isinstance(model_name, str):
        if 'Geokit' in model_name:
            return 'single_stage'
        if '1st Stage' in model_name:
            return 'single_stage'
        if '2nd Stage' in model_name:
            return 'two_stage'

    # A custom set without Tsec means "no second stage"; a non-numeric Tsec raises
    # in float() rather than being silently read as 0.
    tsec = float(params.get('Tsec', 0.0))
    if not np.isfinite(tsec) or tsec <= 0:
        return 'single_stage'

    # Only with all six coefficients do the a0/a1 ... deltas argue for a single line;
    # a missing coefficient keeps the model two-stage.
    coefficients = (
        params.get('a0'), params.get('b0'), params.get('c0'),
        params.get('a1'), params.get('b1'), params.get('c1'),
    )
    if all(value is not None and np.isfinite(value) for value in coefficients):
        a0, b0, c0, a1, b1, c1 = coefficients
        delta = max(abs(a1 - a0), abs(b1 - b0), abs(c1 - c0))
        if delta < _AGE_MODEL_PARAM_DELTA_FLOOR:
            return 'single_stage'

    return 'two_stage'


def calculate_all_parameters(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    calculate_ages: bool = True,
    a: float | None = None,
    b: float | None = None,
    c: float | None = None,
    scale: float = 1.0,
    t_Ma: np.ndarray | float | None = None,
    **kwargs: Any,
) -> dict[str, np.ndarray | float | int | str | None]:
    """Compute every geochemistry parameter (the main entry point).

    Integrates:
    1. single-stage (CDT) and two-stage (SK) model ages
    2. delta values and V1-V2 coordinates
    3. source characteristics (Mu, Omega, Kappa)
    4. initial isotope ratios

    Args:
        Pb206_204_S, ...: isotope-ratio data
        a, b, c: optional V1V2 regression-parameter overrides
        t_Ma: real sample age (Ma) for CalcMu/CalcKa/Calc*in (tSK when omitted)

    Returns:
        dict: all computed results
    """
    # 1. Data normalization.
    Pb206 = np.asarray(Pb206_204_S)
    Pb207 = np.asarray(Pb207_204_S)
    Pb208 = np.asarray(Pb208_204_S)

    results = {
        'Pb206_204_S': Pb206,
        'Pb207_204_S': Pb207,
        'Pb208_204_S': Pb208,
    }

    # Current model settings.
    params_calc = engine.get_parameters()
    current_model = getattr(engine, 'current_model_name', '')
    # V1V2 (Geokit) mode: compute tCDT with T1 = 4.43 Ga.
    is_geokit = "Geokit" in current_model
    # Resolve the age model from parameters and name.
    age_model = resolve_age_model(params_calc, current_model)
    is_two_stage = age_model == 'two_stage'

    # 2. Model ages.
    if is_geokit:
        tCDT = calculate_single_stage_age(Pb206, Pb207, initial_age=engine.params['T1'])
    else:
        tCDT = calculate_single_stage_age(Pb206, Pb207)

    if calculate_ages:
        tSK = calculate_two_stage_age(Pb206, Pb207)
    else:
        # Callers that only need single-stage quantities (the V1V2 discriminant)
        # skip the two-stage solve and reuse tCDT so values stay finite.
        tSK = tCDT

    t_model = tSK if is_two_stage else tCDT
    # Either solver may fail (None/NaN) while the other stays valid: fall back
    # to each other.
    if is_two_stage:
        if t_model is None:
            t_model = tCDT
        elif tCDT is not None:
            t_model = np.where(np.isfinite(t_model), t_model, tCDT)
    if t_model is None:
        t_model = np.nan

    if t_Ma is None:
        t_input = t_model
    else:
        t_input = np.asarray(t_Ma, dtype=float)
        if t_input.ndim == 0:
            if not np.isfinite(t_input):
                t_input = t_model
        else:
            t_input = np.where(np.isfinite(t_input), t_input, t_model)

    results['tCDT (Ma)'] = tCDT
    results['tSK (Ma)'] = tSK
    # The single model-age output: tSK or tCDT per the resolved age_model - the
    # "model age" column used by the UI, exports and validation.
    results['t_Model (Ma)'] = t_model

    # 3. Deltas.
    E1_val = kwargs.get('E1', None)
    E2_val = kwargs.get('E2', None)

    if is_two_stage:
        t_model = tSK
        d_alpha, d_beta, d_gamma = calculate_deltas(
            Pb206, Pb207, Pb208, t_model, params=params_calc, use_two_stage=True, E1=E1_val, E2=E2_val
        )
    else:
        # Single-stage: Geokit computes the age with T1, but the delta mantle
        # reference uses T2.
        t_calc = tCDT if is_geokit else calculate_single_stage_age(Pb206, Pb207, params=params_calc, initial_age=params_calc.get('T2'))
        if t_calc is None:
            # Scalar solve failed: fall back to tCDT so the np.maximum below cannot crash.
            logger.warning("Single-stage age solve failed; falling back to tCDT")
            t_calc = tCDT
        if t_calc is None:
            # Both solves failed: continue with NaN so the remaining outputs degrade
            # together instead of raising TypeError.
            logger.warning("No finite single-stage age available; deltas will be NaN")
            t_calc = np.nan
        if is_geokit or params_calc.get('v1v2_formula') == 'zhu1993':
            t_calc = np.maximum(t_calc, 0)
        t_mantle = params_calc.get('T2') if is_geokit else None
        d_alpha, d_beta, d_gamma = calculate_deltas(
            Pb206,
            Pb207,
            Pb208,
            t_calc,
            params=params_calc,
            T_mantle=t_mantle,
            use_two_stage=False,
            E1=E1_val,
            E2=E2_val,
        )

    results.update({
        'Delta_alpha': d_alpha,
        'Delta_beta': d_beta,
        'Delta_gamma': d_gamma
    })

    # 4. V1-V2 coordinates.
    params_temp = params_calc.copy()
    if a is not None:
        params_temp['a'] = a
    if b is not None:
        params_temp['b'] = b
    if c is not None:
        params_temp['c'] = c

    v1, v2 = calculate_v1v2_coordinates(d_alpha, d_beta, d_gamma, params=params_temp)
    results['V1'] = v1
    results['V2'] = v2

    # 5. Source-parameter inversion - reference parameters follow the model.
    if is_two_stage:
        X_ref, Y_ref, Z_ref = params_calc['a1'], params_calc['b1'], params_calc['c1']
        T_ref = params_calc['T1']
    else:
        X_ref, Y_ref, Z_ref = params_calc['a0'], params_calc['b0'], params_calc['c0']
        T_ref = params_calc['T2']

    mu_val = _invert_mu(Pb206, Pb207, t_input, X_ref, Y_ref, T_ref, params_calc)
    omega_val = _invert_omega(Pb208, t_input, Z_ref, T_ref, params_calc)
    if mu_val is None:
        # Solve failed: continue with NaN so calculate_source_nu and the initial-ratio
        # inversion cannot crash.
        logger.warning("Mu inversion failed; using NaN for affected samples")
        mu_val = np.nan
    if omega_val is None:
        logger.warning("Omega inversion failed; using NaN for affected samples")
        omega_val = np.nan
    results['mu'] = mu_val
    results['nu'] = calculate_source_nu(mu_val, params=params_calc)
    results['omega'] = omega_val

    # 5.2 Model reference parameters (the reference follows age_model).
    mu_model = calculate_model_mu(Pb206, Pb207, t_input, params=params_calc)
    kappa_model = calculate_model_kappa(Pb206, Pb208, t_input, params=params_calc)
    results['mu_model'] = mu_model
    results['kappa_model'] = kappa_model
    results['omega_model'] = kappa_model * mu_model

    # 6. Initial-ratio inversion (real age when given, else tSK).
    results['Init_206_204'] = calculate_initial_ratio_64(t_input, Pb206, Pb207, params=params_calc)
    results['Init_207_204'] = calculate_initial_ratio_74(t_input, Pb206, Pb207, params=params_calc)
    results['Init_208_204'] = calculate_initial_ratio_84(t_input, Pb206, Pb207, Pb208, params=params_calc)

    return results


# =============================================================================
# Albarède & Juteau (1984) T–μ–κ result keys and one-stop inversion
# =============================================================================
# Reference: Albarède, F. & Juteau, M. (1984). GCA 48(1), 207-212.
#       doi:10.1016/0016-7037(84)90364-8
# Constants and solver live in engine.py §1.9 (same as ASTR::albarede_juteau_1984()).
# Kept separate from calculate_all_parameters(): this group's reference composition
# and age anchor (T0 = 3.8 Ga, modern common Pb) differ from the PbIso preset series
# (CDT/a1); mixing both in one dict would let downstream code use the wrong reference.

ALBAREDE_T_MODEL_KEY = 't_Albarede (Ma)'
ALBAREDE_MU_KEY = 'mu_Albarede'
ALBAREDE_KAPPA_KEY = 'kappa_Albarede'
ALBAREDE_OMEGA_KEY = 'omega_Albarede'
ALBAREDE_DELTA_MU_KEY = 'Delta_mu_Albarede'
ALBAREDE_DELTA_KAPPA_KEY = 'Delta_kappa_Albarede'
#: dT_i/dT_0 (dimensionless): sensitivity of the model age to the reference-model T0
#: choice (2012 edition eq. 16)
ALBAREDE_AGE_SENSITIVITY_KEY = 'dT_dT0_Albarede'


def calculate_albarede_parameters(
    Pb206_204_S: np.ndarray | float,
    Pb207_204_S: np.ndarray | float,
    Pb208_204_S: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> dict[str, np.ndarray]:
    """Albarède & Juteau (1984) T–μ–κ one-stop inversion.

    Solves (T_i, μ_i) from the two AJ84 growth equations and κ_i from the z growth
    equation (ω_i = μ_i·κ_i); also returns Δμ_i/Δκ_i relative to the modern
    common-Pb reference and the T0 sensitivity dT_i/dT0. T_i is NaN when the
    equations have no root inside (−4·T0, T0) (negative ages are legitimate results).

    Args:
        Pb206_204_S, Pb207_204_S, Pb208_204_S: sample 206/204, 207/204, 208/204
        params: parameter dict (optional; should be the AJ84 preset, U_ratio = 1/137.79)

    Returns:
        dict: keyed by the ALBAREDE_*_KEY constants (T_i, μ, κ, ω, Δμ, Δκ, dT/dT0)
    """
    if params is None:
        params = engine.params

    age = calculate_albarede_model_age(Pb206_204_S, Pb207_204_S, params)
    if age is None:
        age = np.full(np.shape(Pb206_204_S), np.nan, dtype=float)

    mu = calculate_albarede_mu(Pb206_204_S, Pb207_204_S, age, params)
    kappa = calculate_albarede_kappa(Pb206_204_S, Pb208_204_S, age, mu, params)
    delta_mu = mu - ALBAREDE_MU_STAR

    return {
        ALBAREDE_T_MODEL_KEY: age,
        ALBAREDE_MU_KEY: mu,
        ALBAREDE_KAPPA_KEY: kappa,
        ALBAREDE_OMEGA_KEY: mu * kappa,
        ALBAREDE_DELTA_MU_KEY: delta_mu,
        ALBAREDE_DELTA_KAPPA_KEY: kappa - ALBAREDE_KAPPA_STAR,
        ALBAREDE_AGE_SENSITIVITY_KEY: calculate_albarede_age_sensitivity(age, delta_mu, mu, params),
    }


__all__ = [
    'T_EARTH_1ST',
    'T_EARTH_CANON',
    'T_SK_STAGE2',
    'LAMBDA_238',
    'LAMBDA_235',
    'LAMBDA_232',
    'A0',
    'B0',
    'C0',
    'A1_SK',
    'B1_SK',
    'C1_SK',
    'MU_M_DEFAULT',
    'OMEGA_M_DEFAULT',
    'U_RATIO_NATURAL',
    'EPSILON',
    'E1_DEFAULT',
    'E2_DEFAULT',
    'ALBAREDE_T0',
    'ALBAREDE_X_STAR',
    'ALBAREDE_Y_STAR',
    'ALBAREDE_Z_STAR',
    'ALBAREDE_MU_STAR',
    'ALBAREDE_KAPPA_STAR',
    'ALBAREDE_OMEGA_STAR',
    'ALBAREDE_U238_235',
    'U_RATIO_AJ84',
    'ALBAREDE_X0',
    'ALBAREDE_Y0',
    'ALBAREDE_Z0',
    'PRESET_MODELS',
    'GeochemistryEngine',
    'engine',
    'calculate_modelcurve',
    'calculate_model_slope',
    'calculate_single_stage_age',
    'calculate_two_stage_age',
    'calculate_source_mu',
    'calculate_source_omega',
    'calculate_source_nu',
    'calculate_model_mu',
    'calculate_model_kappa',
    'calculate_initial_ratio_64',
    'calculate_initial_ratio_74',
    'calculate_initial_ratio_84',
    'calculate_deltas',
    'calculate_v1v2_coordinates',
    'calculate_albarede_model_age',
    'calculate_albarede_age_sensitivity',
    'albarede_model_age_residual',
    'calculate_albarede_mu',
    'calculate_albarede_delta_mu',
    'calculate_albarede_kappa',
    'calculate_albarede_delta_kappa',
    'calculate_albarede_parameters',
    'ALBAREDE_T_MODEL_KEY',
    'ALBAREDE_MU_KEY',
    'ALBAREDE_KAPPA_KEY',
    'ALBAREDE_OMEGA_KEY',
    'ALBAREDE_DELTA_MU_KEY',
    'ALBAREDE_DELTA_KAPPA_KEY',
    'ALBAREDE_AGE_SENSITIVITY_KEY',
    'calculate_paleoisochron_line',
    'calculate_isochron1_growth_curve',
    'calculate_isochron2_growth_curve',
    'york_regression',
    'calculate_pbpb_age_from_ratio',
    'calculate_isochron_age_from_slope',
    'calculate_source_mu_from_isochron',
    'calculate_source_kappa_from_slope',
    'resolve_age_model',
    'calculate_all_parameters',
]
