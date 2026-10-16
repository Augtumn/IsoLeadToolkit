"""Core geochemistry algorithm library.

Provides: model ages (single-stage / Stacey-Kramers two-stage), source-parameter
inversion (μ/ω/κ), initial lead ratios, Δ values and the V1-V2 discriminant
projection, and isochron parameters.

Sources: Geokit (V1V2 projection), the R package PbIso (two-stage parameter
inversion), and the literature: Stacey & Kramers (1975), Jaffey et al. (1971),
Tatsumoto et al. (1973).
"""

import threading
from typing import Any

import numpy as np


# =============================================================================
# 1. Physical constants and reference values
# =============================================================================

# 1.1 Time constants (years)
T_EARTH_1ST = 4430e6  # Earth age (Stacey & Kramers 1st-stage approx.)
T_EARTH_CANON = 4570e6  # Canonical Earth Age
T_SK_STAGE2 = 3700e6    # Stacey-Kramers model stage-2 start time

# 1.2 Decay constants (1/year)
# Source: Jaffey et al. (1971) / Steiger and Jager (1977)
LAMBDA_238 = 1.55125e-10
LAMBDA_235 = 9.8485e-10
LAMBDA_232 = 4.94752e-11

# 1.3 Primordial lead isotope ratios
# Source: Tatsumoto et al. (1973) / Canyon Diablo Troilite (CDT)
A0 = 9.307   # 206Pb/204Pb
B0 = 10.294  # 207Pb/204Pb
C0 = 29.476  # 208Pb/204Pb

# 1.4 Stacey-Kramers two-stage model parameters (stage-2 starting values)
# Source: Stacey & Kramers (1975) EPSL
A1_SK = 11.152
B1_SK = 12.998
C1_SK = 31.23

# 1.5 Mantle reference parameters
# PbIso defaults to the Stacey & Kramers (1975) two-stage parameters
MU_M_DEFAULT = 9.74           # Default mantle mu (238U/204Pb)
OMEGA_M_DEFAULT = 36.84       # Default mantle omega (232Th/204Pb)
MU_V1V2_DEFAULT = 7.8
KAPPA_V1V2_DEFAULT = 4.04
OMEGA_V1V2_DEFAULT = MU_V1V2_DEFAULT * KAPPA_V1V2_DEFAULT

# 1.6 Physical ratios
U_RATIO_NATURAL = 1.0 / 137.88  # Natural 235U/238U ratio
EPSILON = 1e-50  # Shared denominator floor for numerical stability

# 1.7 V1-V2 discriminant-diagram regression-plane parameters
# Source: Zhu (1995, 1998)
REGRESSION_A = 0.0
REGRESSION_B = 2.0367
REGRESSION_C = -6.143

# 1.8 PbIso model-curve evolution parameters (R: E1/E2)
E1_DEFAULT = 0.0
E2_DEFAULT = 0.0
E1_CUMMING_RICHARDS = 5e-11
E2_CUMMING_RICHARDS = 3.7e-11

# 1.9 Albarède & Juteau (1984) T–μ–κ reference-model parameters
# Source: Albarède, F. & Juteau, M. (1984). GCA 48(1), 207-212.
#       doi:10.1016/0016-7037(84)90364-8
# Constants and solver cross-checked against ASTR::albarede_juteau_1984()
# (transcribed from Albarède's MATLAB script v2020-11-06). The 2012 Archaeometry
# T–μ–κ revision is not recommended by the author himself, hence AJ84 only;
# comparison with third-party ore libraries in docs/geochemistry.md §16.
ALBAREDE_T0 = 3.8e9           # T0 = 3.8 Ga (reference anchor, years)
ALBAREDE_X_STAR = 18.750      # modern common Pb 206Pb/204Pb (x*)
ALBAREDE_Y_STAR = 15.63       # modern common Pb 207Pb/204Pb (y*)
ALBAREDE_Z_STAR = 38.83       # modern common Pb 208Pb/204Pb (z*; ASTR uses 38.86)
ALBAREDE_MU_STAR = 9.66       # modern common Pb 238U/204Pb (μ*)
ALBAREDE_KAPPA_STAR = 3.90    # modern common Pb 232Th/238U (κ*)
#: ω* = μ*·κ*
ALBAREDE_OMEGA_STAR = ALBAREDE_MU_STAR * ALBAREDE_KAPPA_STAR
#: ²³⁸U/²³⁵U of AJ84/ASTR (the 2012 edition prints 137.88; ~0.02 Ma effect on T)
ALBAREDE_U238_235 = 137.79
U_RATIO_AJ84 = 1.0 / ALBAREDE_U238_235
#: Primordial-lead anchor back-solved from the reference composition so the model
#: curve passes through x*/y*/z* at t = 0: x0 = x* − μ*(e^{λT0} − 1) etc. Yields
#: 10.993/12.742/31.038, far from CDT: a consequence of the T0 = 3.8 Ga anchor,
#: not physical primordial lead - do not "fix" it to CDT.
ALBAREDE_X0 = ALBAREDE_X_STAR - ALBAREDE_MU_STAR * (np.exp(LAMBDA_238 * ALBAREDE_T0) - 1.0)
ALBAREDE_Y0 = ALBAREDE_Y_STAR - ALBAREDE_MU_STAR * U_RATIO_AJ84 * (np.exp(LAMBDA_235 * ALBAREDE_T0) - 1.0)
ALBAREDE_Z0 = ALBAREDE_Z_STAR - ALBAREDE_OMEGA_STAR * (np.exp(LAMBDA_232 * ALBAREDE_T0) - 1.0)

# =============================================================================
# 2. Preset model library
# =============================================================================

PRESET_MODELS = {
    "V1V2 (Geokit)": {
        # Geokit parameter set (kept in years like the other algorithms)
        'age_model': 'single_stage',
        'T1': T_EARTH_1ST,      # Age01
        'T2': T_EARTH_CANON,      # Age02
        'Tsec': T_SK_STAGE2,    # Age1
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A1_SK, 'b1': B1_SK, 'c1': C1_SK,
        'mu_M': MU_V1V2_DEFAULT,
        'omega_M': OMEGA_V1V2_DEFAULT,
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT,
        'v1v2_formula': 'default',
    },
    "V1V2 (Zhu 1993)": {
        # Zhu (1993): Pb isotope 3D topological projection (forced through origin)
        'age_model': 'single_stage',
        'T1': T_EARTH_CANON,
        'T2': T_EARTH_CANON,
        'Tsec': 0.0,
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A1_SK, 'b1': B1_SK, 'c1': C1_SK,
        'mu_M': MU_V1V2_DEFAULT,
        'omega_M': OMEGA_V1V2_DEFAULT,
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT,
        'v1v2_formula': 'zhu1993',
    },
    "Stacey & Kramers (2nd Stage)": {
        # PbIso Table 1: T1 = 3700 Ma for SK2
        'age_model': 'two_stage',
        'T1': T_SK_STAGE2,
        'T2': T_EARTH_CANON,
        'Tsec': T_SK_STAGE2,
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A1_SK, 'b1': B1_SK, 'c1': C1_SK,
        'mu_M': MU_M_DEFAULT,
        'omega_M': OMEGA_M_DEFAULT, # Derived from kappa=3.78 or similar
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT,
        'v1v2_formula': 'default',
    },
    "Stacey & Kramers (1st Stage)": {
        'age_model': 'single_stage',
        'T1': T_EARTH_CANON,
        'T2': T_EARTH_CANON,
        'Tsec': T_SK_STAGE2,
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A0, 'b1': B0, 'c1': C0, # Start from primordial
        # PbIso Table 3: Mu1=7.2, W1=33.2
        'mu_M': 7.2,
        'omega_M': 33.2,
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT,
        'v1v2_formula': 'default',
    },
    "Cumming & Richards (Model III)": {
        'age_model': 'single_stage',
        'T1': 4509e6, 'T2': 4509e6, 'Tsec': 0, # Continuous
        'a0': A0, 'b0': B0, 'c0': C0,
        'a1': A0, 'b1': B0, 'c1': C0,
        # PbIso Table 3: Mu1=10.8, W1=41.2, E1/E2 non-zero
        'mu_M': 10.8,
        'omega_M': 41.2,
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_CUMMING_RICHARDS,
        'E2': E2_CUMMING_RICHARDS,
        'v1v2_formula': 'default',
    },
    "Maltese & Mezger (2020)": {
        # BSE evolution model: initial BSE composition at t1 = 4.5 Ga
        # From Maltese & Mezger (2020), GCA; parameters as tabulated in
        # PbIso (Armistead et al. 2023, Table 3: MM20 model):
        #   T1=4500, X1=9.345, Y1=10.37, Z1=29.51, Mu1=8.63, W1=34.9515
        'age_model': 'single_stage',
        'T1': 4500e6,
        'T2': 4500e6,
        'Tsec': 0.0,
        'a0': 9.345, 'b0': 10.37, 'c0': 29.51,
        'a1': 9.345, 'b1': 10.37, 'c1': 29.51,
        'mu_M': 8.63,
        'omega_M': 34.9515,  # PbIso MM20 W1
        'U_ratio': U_RATIO_NATURAL,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT,
        'v1v2_formula': 'default',
    },
    "Albarède & Juteau (1984)": {
        # Constants in §1.9. Initial ratios use the back-solved anchor, so the
        # curve passes through x*/y*/z* at t = 0; deposits are treated as
        # sulfides (no U/Th after T_i); T_i/μ_i/κ_i inversion lives in age.py
        # and source.py.
        'age_model': 'single_stage',
        'T1': ALBAREDE_T0,
        'T2': ALBAREDE_T0,
        'Tsec': 0.0,
        'a0': ALBAREDE_X0, 'b0': ALBAREDE_Y0, 'c0': ALBAREDE_Z0,
        'a1': ALBAREDE_X0, 'b1': ALBAREDE_Y0, 'c1': ALBAREDE_Z0,
        'mu_M': ALBAREDE_MU_STAR,
        'omega_M': ALBAREDE_OMEGA_STAR,
        'U_ratio': U_RATIO_AJ84,
        'E1': E1_DEFAULT,
        'E2': E2_DEFAULT,
        'v1v2_formula': 'default',
    }
}

# =============================================================================
# 3. Parameter-management engine
# =============================================================================

class GeochemistryEngine:
    """Geochemistry calculation-engine singleton.

    Manages the global parameters required by the current computation (Earth
    age, initial ratios, decay constants, ...) and supports loading preset
    models or custom parameters.
    """

    def __init__(self) -> None:
        # Default parameters (matching the PbIso literature default: SK stage 2)
        self.params: dict[str, float | str] = {
            'age_model': 'two_stage',
            'T1': T_SK_STAGE2,
            'T2': T_EARTH_CANON,
            'Tsec': T_SK_STAGE2,
            'lambda_238': LAMBDA_238,
            'lambda_235': LAMBDA_235,
            'lambda_232': LAMBDA_232,
            'a0': A0, 'b0': B0, 'c0': C0,
            'a1': A1_SK, 'b1': B1_SK, 'c1': C1_SK,
            'mu_M': MU_M_DEFAULT,
            'omega_M': OMEGA_M_DEFAULT,
            'U_ratio': U_RATIO_NATURAL,
            'a': REGRESSION_A, 'b': REGRESSION_B, 'c': REGRESSION_C,
            'v1v2_formula': 'default',
            'E1': E1_DEFAULT, 'E2': E2_DEFAULT,
        }
        self.current_model_name = "Stacey & Kramers (2nd Stage)"
        self._lock = threading.RLock()
        self._update_derived_params()

    def _update_derived_params(self) -> None:
        """Update derived parameters (internal)."""
        mu = self.params.get('mu_M', MU_M_DEFAULT)
        u_r = self.params.get('U_ratio', U_RATIO_NATURAL)
        # v = 235U/204Pb = mu * (235U/238U)
        self.params['v_M'] = mu * u_r

    def get_available_models(self) -> list[str]:
        """Return the names of the available preset models."""
        return list(PRESET_MODELS.keys())

    def load_preset(self, model_name: str) -> bool:
        """Load preset-model parameters.

        Args:
            model_name (str): model name

        Returns:
            bool: whether the load succeeded
        """
        with self._lock:
            if model_name in PRESET_MODELS:
                preset = PRESET_MODELS[model_name]
                self.update_parameters(preset)
                self.current_model_name = model_name
                return True
            return False

    def update_parameters(self, new_params: dict[str, Any]) -> None:
        """Update calculation parameters.

        Args:
            new_params (dict): mapping of parameter names to values
        """
        with self._lock:
            for k, v in new_params.items():
                if k in self.params:
                    if k in ('age_model', 'v1v2_formula'):
                        self.params[k] = str(v)
                    else:
                        # An unusable value is a caller error, not something to ignore:
                        # silently keeping the old value looked like the update worked.
                        try:
                            self.params[k] = float(v)
                        except (ValueError, TypeError) as err:
                            raise ValueError(
                                f"parameter {k!r} is not numeric: {v!r}"
                            ) from err
            self._update_derived_params()

    def get_parameters(self) -> dict[str, float | str]:
        """Return a copy of the current parameters."""
        return self.params.copy()


# Global singleton instance
engine = GeochemistryEngine()


def _is_zero_like(value: float, floor: float = EPSILON) -> bool:
    """Return True when value is effectively zero under the configured floor."""
    return abs(float(value)) <= float(floor)


def calculate_model_slope(
    t0_years: np.ndarray | float,
    t_years: np.ndarray | float,
    params: dict[str, Any] | None = None,
) -> np.ndarray | float:
    """Slope of the reference evolution curve at time T.

    s(T0, T) = (1/U)·(e^{λ'T0} − e^{λ'T}) / (e^{λT0} − e^{λT}), i.e. the slope
    of the 207Pb/204Pb–206Pb/204Pb growth line at time T (U comes from
    params['U_ratio']). At T0 = T (including the T = 0 self-ratio) the result
    is 0/0; the L'Hôpital limit (1/U)·(λ'/λ)·e^{(λ'−λ)T} is returned.

    Args:
        t0_years, t_years: reference start time and evaluation time (years),
            scalar or array
        params: parameter dict (optional)

    Returns:
        np.ndarray or float: the slope
    """
    if params is None:
        params = engine.params
    l238 = float(params['lambda_238'])
    l235 = float(params['lambda_235'])
    u_ratio = float(params['U_ratio'])

    t0 = np.asarray(t0_years, dtype=float)
    t = np.asarray(t_years, dtype=float)
    numerator = np.exp(l235 * t0) - np.exp(l235 * t)
    denominator = np.exp(l238 * t0) - np.exp(l238 * t)
    with np.errstate(divide='ignore', invalid='ignore'):
        result = u_ratio * numerator / denominator

    # For tiny age differences the closed form cancels (e^{λT0} − e^{λT} can even
    # underflow to 0); the tangent limit is the exact value. The test must include
    # the exponent difference: the year-gap test loses its relative scale when
    # both arguments approach 0 (e.g. s(T, 0) with T → 0).
    nearly_equal = (np.abs(t0 - t) < 1e-9 * np.maximum(np.abs(t0), 1.0)) | (
        np.abs(l238 * (t0 - t)) < 1e-9
    )
    if np.any(nearly_equal):
        limit = u_ratio * (l235 / l238) * np.exp((l235 - l238) * t)
        result = np.where(nearly_equal, limit, result)

    if np.ndim(result) == 0:
        return float(result)
    return result


def _exp_evolution_term(lmbda: float, t_years, E: float = 0.0) -> np.ndarray | float:
    """Exponential evolution term of the PbIso model curve.

    Corresponds to R's exp(lambda*t) * (1 - E * (t - 1/lambda)).
    """
    if _is_zero_like(E):
        return np.exp(lmbda * t_years)
    return np.exp(lmbda * t_years) * (1.0 - E * (t_years - (1.0 / lmbda)))


def calculate_modelcurve(
    t_Ma: np.ndarray | float,
    params: dict[str, Any] | None = None,
    T1: float | None = None,
    X1: float | None = None,
    Y1: float | None = None,
    Z1: float | None = None,
    Mu1: float | None = None,
    W1: float | None = None,
    U8U5: float | None = None,
    L5: float | None = None,
    L8: float | None = None,
    L2: float | None = None,
    E1: float | None = None,
    E2: float | None = None,
) -> dict[str, np.ndarray]:
    """Generate a PbIso-style model curve (equivalent to R's modelcurve).

    Args:
        t_Ma: time or age (Ma), scalar or array
        T1: model start time (Ma); defaults to params['Tsec'] (in years)
        X1/Y1/Z1: starting isotope ratios
        Mu1/W1: model 238U/204Pb and 232Th/204Pb
        U8U5: 238U/235U ratio (137.88 in R)
        L5/L8/L2: decay constants
        E1/E2: evolution parameters (default 0)

    Returns:
        dict: {'t_Ma', 'Pb206_204', 'Pb207_204', 'Pb208_204'}
    """
    if params is None:
        with engine._lock:
            params = engine.params

    t_years = np.asarray(t_Ma, dtype=float) * 1e6

    T1_years = params['T1'] if T1 is None else float(T1) * 1e6
    X1_val = params['a1'] if X1 is None else float(X1)
    Y1_val = params['b1'] if Y1 is None else float(Y1)
    Z1_val = params['c1'] if Z1 is None else float(Z1)

    Mu1_val = params.get('mu_M', MU_M_DEFAULT) if Mu1 is None else float(Mu1)
    W1_val = params.get('omega_M', OMEGA_M_DEFAULT) if W1 is None else float(W1)

    U8U5_val = (1.0 / params['U_ratio']) if U8U5 is None else float(U8U5)
    L5_val = params['lambda_235'] if L5 is None else float(L5)
    L8_val = params['lambda_238'] if L8 is None else float(L8)
    L2_val = params['lambda_232'] if L2 is None else float(L2)

    E1_val = params.get('E1', E1_DEFAULT) if E1 is None else float(E1)
    E2_val = params.get('E2', E2_DEFAULT) if E2 is None else float(E2)

    e8_T1 = _exp_evolution_term(L8_val, T1_years, E1_val)
    e8_t = _exp_evolution_term(L8_val, t_years, E1_val)
    e5_T1 = _exp_evolution_term(L5_val, T1_years, E1_val)
    e5_t = _exp_evolution_term(L5_val, t_years, E1_val)
    e2_T1 = _exp_evolution_term(L2_val, T1_years, E2_val)
    e2_t = _exp_evolution_term(L2_val, t_years, E2_val)

    x = X1_val + Mu1_val * (e8_T1 - e8_t)
    y = Y1_val + (Mu1_val / U8U5_val) * (e5_T1 - e5_t)
    z = Z1_val + W1_val * (e2_T1 - e2_t)

    return {
        't_Ma': np.asarray(t_Ma, dtype=float),
        'Pb206_204': x,
        'Pb207_204': y,
        'Pb208_204': z
    }
