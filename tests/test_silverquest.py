"""Tests for the SilverQuest port (:mod:`data.silverquest`).

Three kinds of evidence are used, and none of them is the implementation's own
arithmetic:

1. **An independent scalar transcription of R lines 297-342**
   (``_reference_profile`` below).  It is written as plain Python floating-point
   operations with an explicit 2x2 inverse — no numpy linear algebra and no
   helper imported from :mod:`data.silverquest` — so it is what a second person
   reading the R script would type.  A wrong formula in the module cannot satisfy
   it.
2. **Geometric invariants with exact answers.**  With 204Pb normalisation the
   fractionation ray through an ore at ``(0, 0, z0)`` is the ``z`` axis, so R's
   perpendicular basis comes out as ``i1 = (1, 0, 0)`` and ``i2 = (0, 1, 0)``
   exactly.  An artefact offset parallel to the ray therefore has ``dist = 0``
   exactly, and an artefact equal to the ore has ``dist = 0`` exactly — neither
   depends on any constant.  (A ``z0 = 0`` ore is *not* usable as a fixture: R's
   ``i11 <- c(1, 1, -(i3[1] + i3[2]) / i3[3])`` divides by ``i3[3]``, so such an
   ore yields ``Inf``/``NaN`` rather than a plane.  Real galena analyses always
   have ``208Pb/204Pb ~ 38``, so the branch is never taken in practice.)
3. **Closed forms for the axes case, derived in the comments** and evaluated
   here.  They are *not* ``dx**2 / W[i][i]``: ``A = Aperp^T W Aperp`` inherits
   the correlation structure of ``romatrix``, so the perpendicular distance is
   ``dx**2 * Ainv[0][0]`` with ``Ainv`` the inverse of the ``(x, y)`` block of
   ``W``.  That is the whole point of the method (R line 327 cites "Wichern and
   Johnson 5A.2"), so the off-diagonal terms must not be dropped.

The R source (``reference/r_packages/SilverQuest_v1/SilverQuest_R_v1.R``) is
named line by line in :mod:`data.silverquest`.  The R package folder ships no
reference output to diff against, and R is not installed on the porting machine
(``Get-Command Rscript`` finds nothing), so no R-vs-Python comparison was run —
the expectations here are the hand-derived ones above.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from data.silverquest import (
    COLOUR_RAMP,
    CORRELATION_MATRIX,
    DEFAULT_DMAX,
    DEFAULT_JITTER_RADIUS,
    FRACTIONATION_FACTOR,
    NORMALIZATIONS,
    SIGMA_MATRIX_DIAGONAL,
    SIGMA_PCT,
    SILVERQUEST_DB_ENV_VAR,
    SILVERQUEST_DB_RELATIVE_PATH,
    SilverQuestArtifact,
    SilverQuestArtifactResult,
    SilverQuestConfig,
    SilverQuestDatabase,
    _build_weight_matrix,
    _colour_ramp,
    _distance_colour_index,
    _r_round,
    artifacts_from_records,
    default_database_path,
    load_silverquest_database,
    resolve_database_path,
    run_silverquest,
    silverquest_profile,
)

# ── fixtures and the independent transcription ───────────────────────────

#: Ore whose fractionation ray is the z axis: cosdir0 = (0, 0, 4 * z0).
_Z_ORE: tuple[float, float, float] = (0.0, 0.0, 1.0)

#: Offsets used by the hand-computed tests.  5 % of a ratio is large for real
#: data but keeps the printed numbers short.
_DX = 0.05
_DY = 0.05

_SMATRIX_204 = (
    FRACTIONATION_FACTOR * 2.0 * SIGMA_PCT[0],
    FRACTIONATION_FACTOR * 3.0 * SIGMA_PCT[1],
    FRACTIONATION_FACTOR * 4.0 * SIGMA_PCT[2],
)

#: ``(x, y)`` block of ``W`` and its inverse, used by the closed forms below.
_A_XY = (
    (
        _SMATRIX_204[0] ** 2,
        _SMATRIX_204[0] * CORRELATION_MATRIX["204Pb"][0][1] * _SMATRIX_204[1],
    ),
    (
        _SMATRIX_204[0] * CORRELATION_MATRIX["204Pb"][0][1] * _SMATRIX_204[1],
        _SMATRIX_204[1] ** 2,
    ),
)
_A_XY_DET = _A_XY[0][0] * _A_XY[1][1] - _A_XY[0][1] * _A_XY[1][0]
_AINV_00 = _A_XY[1][1] / _A_XY_DET
_AINV_11 = _A_XY[0][0] / _A_XY_DET
_AINV_01 = -_A_XY[0][1] / _A_XY_DET

#: Perpendicular distance of an offset (dx, 0, 0) from the z-axis ray.
_DIST_X = _DX**2 * _AINV_00
#: Perpendicular distance of an offset (0, dy, 0) — with a cross term, because
#: Ainv[0][1] != 0.
_DIST_Y = _DY**2 * _AINV_11
#: ... and the two together include the off-diagonal contribution.
_DIST_XY = _DX**2 * _AINV_00 + 2 * _DX * _DY * _AINV_01 + _DY**2 * _AINV_11


def _database(rows: list[tuple[float, float, float]]) -> SilverQuestDatabase:
    """Build a database from ``(x, y, z)`` 204Pb-normalised ore triples."""
    array = np.array(rows, dtype=float)
    return SilverQuestDatabase(
        country=np.array([f"Ore{index}" for index in range(len(rows))], dtype=object),
        latitude=np.linspace(40.0, 41.0, len(rows)),
        longitude=np.linspace(20.0, 21.0, len(rows)),
        pb206_204=array[:, 0],
        pb207_204=array[:, 1],
        pb208_204=array[:, 2],
    )


def _reference_profile(
    artifact: tuple[float, float, float],
    ore: tuple[float, float, float],
    normalization: str = "204Pb",
) -> dict[str, float]:
    """Independent scalar transcription of R lines 297-342.

    Plain floats and tuple algebra only; the 2x2 weighted system is inverted by
    hand.  Imports nothing from :mod:`data.silverquest`.
    """
    x, y, z = artifact
    x0, y0, z0 = ore
    if normalization == "204Pb":
        cosdir0 = (2.0 * x0, 3.0 * y0, 4.0 * z0)
        smatrix = (
            FRACTIONATION_FACTOR * 2.0 * SIGMA_PCT[0],
            FRACTIONATION_FACTOR * 3.0 * SIGMA_PCT[1],
            FRACTIONATION_FACTOR * 4.0 * SIGMA_PCT[2],
        )
    else:
        x, y, z = 1.0 / x, y / x, z / x
        x0, y0, z0 = 1.0 / x0, y0 / x0, z0 / x0
        cosdir0 = (-2.0 * x0, y0, 2.0 * z0)
        smatrix = (
            FRACTIONATION_FACTOR * (-2.0 / SIGMA_PCT[0]),
            FRACTIONATION_FACTOR * (SIGMA_PCT[1] / SIGMA_PCT[0]),
            FRACTIONATION_FACTOR * (2.0 * SIGMA_PCT[2] / SIGMA_PCT[0]),
        )
    romatrix = CORRELATION_MATRIX[normalization].tolist()
    weight = [
        [smatrix[row] * romatrix[row][column] * smatrix[column] for column in range(3)]
        for row in range(3)
    ]

    norm = math.sqrt(sum(component * component for component in cosdir0))
    i3 = tuple(component / norm for component in cosdir0)

    i11 = (1.0, 1.0, -(i3[0] + i3[1]) / i3[2])
    norm_i11 = math.sqrt(sum(component * component for component in i11))
    i1 = tuple(component / norm_i11 for component in i11)

    i2_raw = (
        i1[1] * i3[2] - i1[2] * i3[1],
        i1[2] * i3[0] - i1[0] * i3[2],
        i1[0] * i3[1] - i1[1] * i3[0],
    )
    norm_i2 = math.sqrt(sum(component * component for component in i2_raw))
    i2 = tuple(component / norm_i2 for component in i2_raw)

    ap = (x0 - x, y0 - y, z0 - z)

    # A = Aperp^T W Aperp with Aperp = [i1 | i2], written out.
    a_matrix = [[0.0, 0.0], [0.0, 0.0]]
    for row in (0, 1):
        basis_row = i1 if row == 0 else i2
        for column in (0, 1):
            basis_column = i1 if column == 0 else i2
            total = 0.0
            for p in range(3):
                for q in range(3):
                    total += basis_row[p] * weight[p][q] * basis_column[q]
            a_matrix[row][column] = total

    aproj = (
        sum(i1[index] * ap[index] for index in range(3)),
        sum(i2[index] * ap[index] for index in range(3)),
    )

    determinant = a_matrix[0][0] * a_matrix[1][1] - a_matrix[0][1] * a_matrix[1][0]
    inverse = (
        (a_matrix[1][1] / determinant, -a_matrix[0][1] / determinant),
        (-a_matrix[1][0] / determinant, a_matrix[0][0] / determinant),
    )
    dist = (
        aproj[0] * (inverse[0][0] * aproj[0] + inverse[0][1] * aproj[1])
        + aproj[1] * (inverse[1][0] * aproj[0] + inverse[1][1] * aproj[1])
    )

    dotp = sum(ap[index] * i3[index] for index in range(3))
    cros = (
        ap[1] * cosdir0[2] - ap[2] * cosdir0[1],
        ap[2] * cosdir0[0] - ap[0] * cosdir0[2],
        ap[0] * cosdir0[1] - ap[1] * cosdir0[0],
    )
    normcros = math.sqrt(sum(component * component for component in cros))
    # R line 336: sg <- sign(normcros / dotp); sign(NaN) is NaN, sign(x/0) is +-1.
    if dotp == 0.0:
        sg = float("nan")
    else:
        sg = math.copysign(1.0, normcros / dotp)

    denominator = sum(component * component for component in cosdir0)
    u = sum(cosdir0[index] * ap[index] for index in range(3)) / denominator
    return {"dist": dist, "fract": cosdir0[0] * u, "sg": sg, "dotp": dotp}


def _single_ore_setup():
    """One z-axis ore, artefact offset in x, y and z.

    ``dist = _DIST_XY = 2.396030167416821`` — under the default ``dmax = 3``.
    The z offset is what makes ``dotp`` non-zero, so ``sg`` is defined.
    """
    artifact = SilverQuestArtifact(
        no="G107", pb206_204=_DX, pb207_204=_DY, pb208_204=1.05
    )
    return _database([_Z_ORE]), artifact


# ── constants transcribed from the R script ──────────────────────────────


def test_normalizations_match_the_r_choices() -> None:
    assert NORMALIZATIONS == ("204Pb", "206Pb")


def test_sigma_matrix_diagonal_matches_r_expression() -> None:
    # R line 289: f * diag(c(2 * 18.7, 3 * 15.65, 4 * 39))
    assert SIGMA_MATRIX_DIAGONAL["204Pb"] == pytest.approx(
        (0.001 * 37.4, 0.001 * 46.95, 0.001 * 156.0), rel=0, abs=0
    )
    # R line 291: f * diag(c(-2 / 18.7, 15.65 / 18.7, 2 * 39 / 18.7))
    assert SIGMA_MATRIX_DIAGONAL["206Pb"] == pytest.approx(
        (
            0.001 * (-2.0 / 18.7),
            0.001 * (15.65 / 18.7),
            0.001 * (2.0 * 39.0 / 18.7),
        ),
        rel=0,
        abs=0,
    )
    # The module's smatrix must be the same numbers my closed forms use.
    assert SIGMA_PCT == (18.7, 15.65, 39.0)
    np.testing.assert_allclose(
        _SMATRIX_204, SIGMA_MATRIX_DIAGONAL["204Pb"], rtol=1e-15, atol=0
    )
    for predicted, actual in zip(_SMATRIX_204, SIGMA_MATRIX_DIAGONAL["204Pb"]):
        assert predicted == pytest.approx(actual, rel=1e-15)


def test_weight_matrix_is_smatrix_romatrix_smatrix() -> None:
    weight = _build_weight_matrix("204Pb")
    smatrix = np.diag(SIGMA_MATRIX_DIAGONAL["204Pb"])
    predicted = smatrix @ CORRELATION_MATRIX["204Pb"] @ smatrix
    np.testing.assert_allclose(weight, predicted, rtol=0, atol=0)
    # Off-diagonal entry: f^2 * 2*18.7 * 0.96 * 3*15.65
    assert weight[0, 1] == pytest.approx(
        FRACTIONATION_FACTOR**2 * 2 * 18.7 * 0.96 * 3 * 15.65, rel=1e-12
    )
    assert weight[0, 1] == pytest.approx(0.0016856928, rel=1e-9)
    # 206Pb carries the negative 1/206 term (R line 291); squared, so positive
    # but tiny — 1.14387e-08 by hand.
    weight_206 = _build_weight_matrix("206Pb")
    assert weight_206[0, 0] == pytest.approx(
        FRACTIONATION_FACTOR**2 * (2.0 / 18.7) ** 2, rel=1e-12
    )
    assert weight_206[0, 0] == pytest.approx(1.14387028510966e-08, rel=1e-9)
    assert weight_206[0, 0] < weight[0, 0]


# ── the numeric core ─────────────────────────────────────────────────────


def test_profile_zero_distance_when_artifact_is_the_ore() -> None:
    profile = silverquest_profile(_Z_ORE, _Z_ORE)
    assert profile["dist"] == pytest.approx(0.0, abs=0.0)
    assert profile["fract"] == pytest.approx(0.0, abs=0.0)
    assert profile["dotp"] == pytest.approx(0.0, abs=0.0)
    # R line 336: sign(NaN) is NaN, so the port reports NaN.
    assert math.isnan(profile["sg"])


def test_profile_is_zero_along_the_whole_fractionation_line() -> None:
    """An offset parallel to cosdir0 = (2x0, 3y0, 4z0) has no perpendicular part.

    For ore ``(0.2, 0.3, 1.0)``: ``cosdir0 = (0.4, 0.9, 4.0)``,
    ``|cosdir0| = 4.119464044526446`` and ``i3 = (0.0971001, 0.2184752,
    0.9709996)``.  The R code builds ``AP <- ore - artefact``, so an artefact
    displaced by ``-scale * cosdir0`` gives ``AP = +scale * cosdir0`` and
    ``dotp = AP . i3 = scale * |cosdir0|``.
    """
    ore = (0.2, 0.3, 1.0)
    norm_squared = 0.4**2 + 0.9**2 + 4.0**2
    norm = math.sqrt(norm_squared)
    assert norm_squared == pytest.approx(16.97, rel=1e-12)
    assert norm == pytest.approx(4.119465984809196, rel=1e-12)
    for scale in (0.001, 0.05, -0.05):
        artifact = (
            ore[0] - scale * 0.4,
            ore[1] - scale * 0.9,
            ore[2] - scale * 4.0,
        )
        profile = silverquest_profile(artifact, ore)
        # Exactly zero up to floating-point cancellation in Aperp^T W Aperp.
        assert profile["dist"] == pytest.approx(0.0, abs=1e-27)
        assert profile["dotp"] == pytest.approx(scale * norm, rel=1e-9)
        assert profile["sg"] == pytest.approx(math.copysign(1.0, scale))
        # u = dot(cosdir0, AP) / |cosdir0|^2 = scale, and R takes
        # fract = cosdir0[1] * u = 0.4 * scale.
        assert profile["fract"] == pytest.approx(scale * 0.4, rel=1e-9)


def test_profile_along_ray_offset_has_zero_perpendicular_component() -> None:
    """``normcros`` is exactly 0 along the ray, so R's ``sign`` returns 0.

    R line 336 computes ``sign(normcros / dotp)``; with ``cros == 0`` that is
    ``sign(0) == 0``, not ``+1``.  A non-zero ``sg`` therefore only appears when
    the artefact is genuinely off the ore's ray — an ambiguity of the R code
    worth knowing before the column is used as a classification.
    """
    # Exactly along the z-axis ray through (0, 0, 1): cross product is zero.
    on_ray = silverquest_profile((0.0, 0.0, 1.05), _Z_ORE)
    assert on_ray["dist"] == pytest.approx(0.0, abs=0.0)
    assert on_ray["dotp"] == pytest.approx(-0.05, rel=1e-12)
    assert on_ray["sg"] == pytest.approx(0.0)

    # A tiny perpendicular component is enough to make the sign meaningful.
    nearly = silverquest_profile((1e-9, 0.0, 1.0), _Z_ORE)
    assert nearly["dotp"] == pytest.approx(0.0, abs=0.0)
    assert math.isnan(nearly["sg"])


def test_profile_pure_x_offset_matches_hand_computation() -> None:
    """Ore (0, 0, 1) → ray (0, 0, 4), so i1 = (1, 0, 0) and i2 = (0, 1, 0).

    ``A`` is therefore the ``(x, y)`` block of ``W`` — *not* diagonal, because
    ``romatrix[0][1] = 0.96`` — and the perpendicular offset (0.05, 0, 0) has
    ``dist = 0.05**2 * Ainv[0][0]``.
    """
    profile = silverquest_profile((_DX, 0.0, 1.0), _Z_ORE)
    # Ainv[0][0] = W[1][1] / det = 0.0022043025 / 3.083642e-06
    assert _AINV_00 == pytest.approx(9118.863880019651, rel=1e-9)  # by hand
    assert _DIST_X == pytest.approx(22.797159700049114, rel=1e-9)  # by hand
    assert profile["dist"] == pytest.approx(_DIST_X, rel=1e-12)
    # fract = cosdir0[1] * u with cosdir0[1] = 2 * x0 = 0 for this ore.
    assert profile["fract"] == pytest.approx(0.0, abs=0.0)
    # AP = (-0.05, 0, 0) lies exactly across the ray, so R's sign() is NaN.
    assert profile["dotp"] == pytest.approx(0.0, abs=0.0)
    assert math.isnan(profile["sg"])


def test_profile_pure_y_offset_matches_hand_computation() -> None:
    """Same ore, offset +0.05 in 207Pb/204Pb only → ``0.05**2 * Ainv[1][1]``."""
    profile = silverquest_profile((0.0, _DY, 1.0), _Z_ORE)
    assert _AINV_11 == pytest.approx(5786.457185806525, rel=1e-9)  # by hand
    assert _DIST_Y == pytest.approx(14.46614296451631, rel=1e-9)  # by hand
    assert profile["dist"] == pytest.approx(_DIST_Y, rel=1e-12)
    assert profile["fract"] == pytest.approx(0.0, abs=0.0)
    assert math.isnan(profile["sg"])


def test_profile_pure_z_offset_is_along_the_ray() -> None:
    """Offset along the z-axis ray: no perpendicular part, so dist is 0.

    ``i3 = (0, 0, 1)``, so ``dotp`` is the *normalised* z offset, not the raw one,
    and ``sg`` is 0 rather than ±1 because the perpendicular part vanishes — see
    :func:`test_profile_along_ray_offset_has_zero_perpendicular_component`.
    """
    profile = silverquest_profile((0.0, 0.0, 1.05), _Z_ORE)
    assert profile["dist"] == pytest.approx(0.0, abs=0.0)
    # fract = cosdir0[1] * u = 0 because cosdir0[1] = 2 * x0 = 0.
    assert profile["fract"] == pytest.approx(0.0, abs=0.0)
    # AP = (0, 0, -0.05) and i3 = (0, 0, 1), so dotp = -0.05.
    assert profile["dotp"] == pytest.approx(-0.05, rel=1e-12)
    assert profile["sg"] == pytest.approx(0.0)

    # The other direction along the same ray differs only in the sign of dotp.
    ahead = silverquest_profile((0.0, 0.0, 0.95), _Z_ORE)
    assert ahead["dist"] == pytest.approx(0.0, abs=0.0)
    assert ahead["dotp"] == pytest.approx(0.05, rel=1e-12)
    assert ahead["sg"] == pytest.approx(0.0)


def test_profile_sg_sign_needs_both_parts_non_zero() -> None:
    """``sg`` is ±1 only when ``dotp != 0`` *and* the perpendicular part is non-zero."""
    cases = [
        ((0.05, 0.05, 1.05), _Z_ORE, -1.0),          # AP_z < 0
        ((0.05, 0.05, 0.95), _Z_ORE, 1.0),           # AP_z > 0
        ((0.2, 0.3, 1.05), (0.2, 0.3, 1.0), -1.0),   # oblique ray, AP_z < 0
        ((0.2, 0.3, 0.95), (0.2, 0.3, 1.0), 1.0),    # oblique ray, AP_z > 0
        ((0.05, 0.05, 1.05), (0.2, 0.3, 1.0), 1.0),  # oblique ray, far off it
    ]
    for artifact, ore, expected in cases:
        profile = silverquest_profile(artifact, ore)
        assert profile["dotp"] != 0.0
        assert profile["dist"] > 0.0
        assert profile["sg"] == pytest.approx(expected), (artifact, ore)


def test_profile_x_and_y_offsets_include_the_correlation_cross_term() -> None:
    """``dist = dx**2*Ainv00 + 2*dx*dy*Ainv01 + dy**2*Ainv11``.

    Dropping ``Ainv[0][1]`` — i.e. treating the errors as uncorrelated — would
    give 37.26 instead of 2.396, so this is the test that pins the method.
    """
    profile = silverquest_profile((_DX, _DY, 1.0), _Z_ORE)
    uncorrelated = _DX**2 * _AINV_00 + _DY**2 * _AINV_11
    assert _DIST_XY == pytest.approx(2.396030167416815, rel=1e-9)  # by hand
    assert uncorrelated == pytest.approx(37.26330266456543, rel=1e-9)
    assert profile["dist"] == pytest.approx(_DIST_XY, rel=1e-12)
    assert profile["dist"] != pytest.approx(uncorrelated, rel=1e-3)


def test_profile_ignores_offsets_along_the_ray() -> None:
    """The 208Pb/204Pb component does not move the point off this ore's ray."""
    base = silverquest_profile((_DX, _DY, 1.0), _Z_ORE)
    shifted = silverquest_profile((_DX, _DY, 1.05), _Z_ORE)
    assert shifted["dist"] == pytest.approx(base["dist"], rel=1e-12)
    # ... but it does change the orientation sign (dotp flips with the offset).
    assert base["sg"] != shifted["sg"]


def test_profile_matches_independent_scalar_transcription() -> None:
    """Cross-check on 204Pb and 206Pb, axis-aligned and oblique rays."""
    cases = [
        ((_DX, _DY, 1.0), _Z_ORE, "204Pb"),
        ((0.3, -0.4, 0.8), (1.5, 0.9, 1.1), "204Pb"),
        ((2.05, 1.03, 1.02), (2.0, 1.0, 1.0), "204Pb"),
        ((0.1, 0.1, 1.1), (0.2, 0.3, 1.0), "204Pb"),
        ((18.5764, 15.6597, 38.589), (18.85, 15.70, 38.90), "204Pb"),
        ((18.5764, 15.6597, 38.589), (18.85, 15.70, 38.90), "206Pb"),
        ((3.0, 0.6, 1.1), (2.0, 1.0, 1.0), "206Pb"),
        ((2.0, 0.55, 0.5), (2.0, 1.0, 1.0), "206Pb"),
    ]
    for artifact, ore, normalization in cases:
        got = silverquest_profile(artifact, ore, normalization)
        expected = _reference_profile(artifact, ore, normalization)
        assert got["dist"] == pytest.approx(expected["dist"], rel=1e-12, abs=1e-15), (
            artifact,
            ore,
            normalization,
        )
        assert got["fract"] == pytest.approx(expected["fract"], rel=1e-12, abs=1e-15)
        assert got["dotp"] == pytest.approx(expected["dotp"], rel=1e-12, abs=1e-15)
        if math.isnan(expected["sg"]):
            assert math.isnan(got["sg"])
        else:
            assert got["sg"] == pytest.approx(expected["sg"])


def test_profile_sign_is_positive_along_and_negative_across_the_ray() -> None:
    """R line 336: sg = sign(normcros / dotp) — orientation, not classification.

    ``normcros`` is ``|AP x cosdir0|``, so it is zero when the artefact lies on
    the ore's ray, and ``dotp = AP . i3`` is zero when it lies exactly across it.
    ``sg`` is only ±1 when neither happens.
    """
    # For the z-axis ore the ray points along +z, so a lower z means AP_z > 0.
    below = silverquest_profile((_DX, _DY, 1.05), _Z_ORE)
    above = silverquest_profile((_DX, _DY, 0.95), _Z_ORE)
    assert below["dotp"] < 0.0 and below["sg"] == pytest.approx(-1.0)
    assert above["dotp"] > 0.0 and above["sg"] == pytest.approx(1.0)
    # The distance is unchanged by the sign of the along-ray offset.
    assert below["dist"] == pytest.approx(above["dist"], rel=1e-12)

    # Exactly across the ray: dotp = 0, where R's sign(NaN) is NaN.
    across = silverquest_profile((_DX, 0.0, 1.0), _Z_ORE)
    assert across["dotp"] == pytest.approx(0.0, abs=0.0)
    assert math.isnan(across["sg"])

    # The oblique ray through ore (0.2, 0.3, 1.0): same rule, both directions.
    oblique_ore = (0.2, 0.3, 1.0)
    oblique_below = silverquest_profile((0.2, 0.3, 1.05), oblique_ore)
    oblique_above = silverquest_profile((0.2, 0.3, 0.95), oblique_ore)
    assert oblique_below["sg"] == pytest.approx(-1.0)
    assert oblique_above["sg"] == pytest.approx(1.0)
    assert oblique_below["dist"] == pytest.approx(oblique_above["dist"], rel=1e-12)
    assert oblique_below["fract"] == pytest.approx(-oblique_above["fract"], rel=1e-12)


def test_profile_rejects_unknown_normalization() -> None:
    with pytest.raises(ValueError, match="Invalid normalization"):
        silverquest_profile((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), "207Pb")


def test_profile_normalises_internally() -> None:
    """Artefact == ore is on the ray in either normalisation → zero distance."""
    triple = (18.0, 15.6, 38.4)
    for normalization in NORMALIZATIONS:
        profile = silverquest_profile(triple, triple, normalization)
        assert profile["dist"] == pytest.approx(0.0, abs=1e-15)


# ── run_silverquest ──────────────────────────────────────────────────────


def test_run_single_hit_matches_hand_computed_numbers() -> None:
    database, artifact = _single_ore_setup()
    result = run_silverquest([artifact], database, SilverQuestConfig(jittered=False))

    assert result.database_rows == 1
    assert result.total_hits == 1
    hit_result = result.artifacts[0]
    assert hit_result.no == "G107"
    assert hit_result.n_hits == 1

    hit = hit_result.hits[0]
    assert hit["dist"] == pytest.approx(_DIST_XY, rel=1e-12)
    assert hit["dist"] == pytest.approx(2.396030167416815, rel=1e-9)
    assert hit["Country"] == "Ore0"
    assert hit["no"] == 1
    assert hit["Latitude"] == pytest.approx(40.0)
    # fract = cosdir0[1] * u = 0 for a z-axis ray (cosdir0[1] = 2 * x0 = 0).
    assert hit["fract"] == pytest.approx(0.0, abs=0.0)
    # AP = (-0.05, -0.05, -0.05), cosdir0 = (0, 0, 4) → dotp = -0.2 → sg = -1.
    assert hit["sg"] == pytest.approx(-1.0)
    # nprox = 1 → single colour-ramp entry, index 1 (R lines 396/418).
    assert hit["nocol"] == 1
    assert hit["point_color"] == "#000000"
    assert hit_result.colour_indices == (1,)
    assert hit_result.colour_index_clamped is False


def test_run_hits_are_sorted_closest_last() -> None:
    """R lines 360/372: order(dist) then order(dist, decreasing = TRUE).

    The three ores are placed on the artefact's own fractionation ray (same
    ``x`` and ``y``, differing only in ``z``), so their distances come out
    ``0`` / ``0.10450`` / ``0.17275`` — the nearest is the artefact's own triple.
    """
    database = _database([(0.05, 0.05, 1.90), (_DX, _DY, 1.05), (0.05, 0.05, 1.60)])
    artifact = SilverQuestArtifact(
        no="A", pb206_204=_DX, pb207_204=_DY, pb208_204=1.05
    )
    labels = [(0.05, 0.05, 1.90), (_DX, _DY, 1.05), (0.05, 0.05, 1.60)]
    distances = {ore: _reference_profile((_DX, _DY, 1.05), ore)["dist"] for ore in labels}
    assert distances[(_DX, _DY, 1.05)] == pytest.approx(0.0, abs=0.0)
    assert distances[(0.05, 0.05, 1.60)] == pytest.approx(0.10450437457461986, rel=1e-9)
    assert distances[(0.05, 0.05, 1.90)] == pytest.approx(0.172745494051819, rel=1e-9)

    # dmax must exceed the largest hit distance, otherwise that hit is dropped.
    result = run_silverquest(
        [artifact], database, SilverQuestConfig(dmax=0.4, jittered=False)
    )
    hit_result = result.artifacts[0]
    assert hit_result.n_hits == 3
    assert [hit["Country"] for hit in hit_result.table] == ["Ore1", "Ore2", "Ore0"]
    assert [hit["Country"] for hit in hit_result.hits] == ["Ore0", "Ore2", "Ore1"]
    # R line 418 with dmax = 0.4: 0.1727 → 1.36 → 1, 0.1045 → 1.02 → 1,
    # 0 → 0.5 → 1 (ties away from zero).  All three land on the first entry.
    # Widening dmax past the hit range does not change that — see the quirk test.
    assert [hit["nocol"] for hit in hit_result.hits] == [1, 1, 1]
    assert [hit["point_color"] for hit in hit_result.hits] == [
        "#000000",
        "#000000",
        "#000000",
    ]


def test_run_hits_are_sorted_by_distance_ascending_then_reversed() -> None:
    """The hit *table* is ascending; only the hit list is reversed."""
    database = _database([(0.05, 0.05, 1.90), (_DX, _DY, 1.05), (0.05, 0.05, 1.60)])
    artifact = SilverQuestArtifact(
        no="A", pb206_204=_DX, pb207_204=_DY, pb208_204=1.05
    )
    result = run_silverquest(
        [artifact], database, SilverQuestConfig(dmax=1.0, jittered=False)
    )
    table_distances = [hit["dist"] for hit in result.artifacts[0].table]
    hit_distances = [hit["dist"] for hit in result.artifacts[0].hits]
    assert table_distances == sorted(table_distances)
    assert hit_distances == sorted(hit_distances, reverse=True)
    # The hit list is exactly the first nprox rows of the table, reversed.
    assert hit_distances == list(reversed(table_distances[: result.artifacts[0].n_hits]))


def test_run_colour_index_follows_the_dmax_parameter_not_the_hit_range() -> None:
    """R-QUIRK: ``nocol`` divides by the user parameter ``dmax``, not the max hit.

    With hits spanning 0 … 0.17 and ``dmax = 3`` the ramp index collapses to 1
    for every hit, so the grey/coloured maps lose their gradient — that is what
    the R script does.
    """
    database = _database([(0.05, 0.05, 1.90), (_DX, _DY, 1.05), (0.05, 0.05, 1.60)])
    artifact = SilverQuestArtifact(
        no="A", pb206_204=_DX, pb207_204=_DY, pb208_204=1.05
    )
    result = run_silverquest(
        [artifact], database, SilverQuestConfig(dmax=3.0, jittered=False)
    )
    assert [hit["nocol"] for hit in result.artifacts[0].hits] == [1, 1, 1]
    assert {hit["point_color"] for hit in result.artifacts[0].hits} == {"#000000"}


def test_run_dmax_threshold_is_strict_and_uses_squared_distance() -> None:
    """R line 364 compares the *squared* distance with the linear parameter."""
    database, artifact = _single_ore_setup()
    distance = silverquest_profile(
        (artifact.pb206_204, artifact.pb207_204, artifact.pb208_204), _Z_ORE
    )["dist"]
    assert distance == pytest.approx(_DIST_XY, rel=1e-12)

    def hits(dmax: float) -> int:
        return run_silverquest(
            [artifact], database, SilverQuestConfig(dmax=dmax, jittered=False)
        ).artifacts[0].n_hits

    assert hits(distance * 1.000001) == 1
    assert hits(distance * 0.999999) == 0
    # strict `<`: equality is not a hit
    assert hits(distance) == 0
    # the full table is still reported for a miss
    missed = run_silverquest(
        [artifact], database, SilverQuestConfig(dmax=distance, jittered=False)
    )
    assert missed.artifacts[0].hits == ()
    assert len(missed.artifacts[0].table) == 1


def test_run_default_dmax_and_jitter_radius_match_the_shiny_inputs() -> None:
    config = SilverQuestConfig()
    assert config.dmax == pytest.approx(DEFAULT_DMAX)
    assert config.dmax == pytest.approx(3.0)
    assert config.jitter_radius == pytest.approx(DEFAULT_JITTER_RADIUS)
    assert config.jitter_radius == pytest.approx(0.01)
    assert config.jittered is True
    assert config.normalization == "204Pb"


def test_run_config_rejects_values_outside_the_r_choices() -> None:
    with pytest.raises(ValueError, match="Invalid normalization"):
        SilverQuestConfig(normalization="208Pb")
    with pytest.raises(ValueError, match="jitter_radius"):
        SilverQuestConfig(jitter_radius=-0.1)


def test_run_without_jitter_keeps_exact_coordinates() -> None:
    database, artifact = _single_ore_setup()
    result = run_silverquest(
        [artifact], database, SilverQuestConfig(jittered=False, jitter_radius=0.5)
    )
    hit = result.artifacts[0].hits[0]
    assert hit["Latitude"] == pytest.approx(40.0)
    assert hit["Longitude"] == pytest.approx(20.0)


def test_run_jitter_stays_inside_r0_over_5() -> None:
    """R line 382: r <- (r0 / 5) * sqrt(runif(nprox)); line 390 adds it."""
    database, artifact = _single_ore_setup()
    radius = 2.5
    limit = radius / 5.0
    displacements = []
    for seed in range(25):
        result = run_silverquest(
            [artifact],
            database,
            SilverQuestConfig(jittered=True, jitter_radius=radius),
            seed=seed,
        )
        hit = result.artifacts[0].hits[0]
        displacement = math.hypot(hit["Latitude"] - 40.0, hit["Longitude"] - 20.0)
        assert displacement <= limit + 1e-12
        displacements.append(displacement)
    # Not satisfied by not jittering at all.
    assert max(displacements) > limit / 4.0


def test_run_jitter_is_reproducible_with_a_seed() -> None:
    database, artifact = _single_ore_setup()
    first = run_silverquest([artifact], database, seed=7)
    second = run_silverquest([artifact], database, seed=7)
    assert first.artifacts[0].hits[0]["Latitude"] == second.artifacts[0].hits[0]["Latitude"]
    assert first.artifacts[0].hits[0]["Longitude"] == second.artifacts[0].hits[0]["Longitude"]
    # Without a seed the draw differs (the R script uses the global RNG).
    third = run_silverquest([artifact], database)
    assert third.artifacts[0].hits[0]["Latitude"] != first.artifacts[0].hits[0]["Latitude"]


def test_run_sg_column_repeats_the_last_ore_row() -> None:
    """R-QUIRK: R's length-1 ``sg`` is overwritten per ore, keeping the last.

    Two real galena analyses bracket the artefact: the near one (18.5764,
    15.6597, 38.589) has a true sign of -1, the far one (18.85, 15.70, 38.90) has
    +1.  R writes the length-1 ``sg`` inside the ore loop, so every row of the
    hit table reports the *last* ore's value.
    """
    artifact_triple = (18.60, 15.68, 38.70)
    ore_first = (18.5764, 15.6597, 38.589)
    ore_last = (18.85, 15.70, 38.90)
    database = _database([ore_first, ore_last])
    artifact = SilverQuestArtifact(
        no="G107",
        pb206_204=artifact_triple[0],
        pb207_204=artifact_triple[1],
        pb208_204=artifact_triple[2],
    )
    table = run_silverquest(
        [artifact], database, SilverQuestConfig(dmax=1e9, jittered=False)
    ).artifacts[0].table

    assert len(table) == 2
    assert _reference_profile(artifact_triple, ore_first)["sg"] == pytest.approx(-1.0)
    assert _reference_profile(artifact_triple, ore_last)["sg"] == pytest.approx(1.0)
    # Every row carries the last ore's value, not its own.
    assert {hit["sg"] for hit in table} == {1.0}
    # ... and the near ore's own sign really is the opposite.
    assert table[0]["dist"] < table[1]["dist"]


def test_run_sg_column_is_not_per_row() -> None:
    """Same quirk with the ores swapped, so it cannot be coincidence."""
    artifact_triple = (18.60, 15.68, 38.70)
    ore_first = (18.85, 15.70, 38.90)   # true sign +1
    ore_last = (18.5764, 15.6597, 38.589)  # true sign -1
    database = _database([ore_first, ore_last])
    artifact = SilverQuestArtifact(
        no="G107",
        pb206_204=artifact_triple[0],
        pb207_204=artifact_triple[1],
        pb208_204=artifact_triple[2],
    )
    table = run_silverquest(
        [artifact], database, SilverQuestConfig(dmax=1e9, jittered=False)
    ).artifacts[0].table

    assert _reference_profile(artifact_triple, ore_first)["sg"] == pytest.approx(1.0)
    assert _reference_profile(artifact_triple, ore_last)["sg"] == pytest.approx(-1.0)
    assert {hit["sg"] for hit in table} == {-1.0}


def test_run_handles_multiple_artifacts_independently() -> None:
    database = _database([_Z_ORE])
    first = SilverQuestArtifact(no="A", pb206_204=_DX, pb207_204=_DY, pb208_204=1.05)
    second = SilverQuestArtifact(no="B", pb206_204=0.0, pb207_204=0.0, pb208_204=1.0)
    result = run_silverquest(
        [first, second], database, SilverQuestConfig(jittered=False)
    )
    assert [item.no for item in result.artifacts] == ["A", "B"]
    # B is the ore's own triple → exactly zero distance.
    assert result.artifacts[1].table[0]["dist"] == pytest.approx(0.0, abs=0.0)
    assert result.artifacts[0].table[0]["dist"] == pytest.approx(_DIST_XY, rel=1e-12)


def test_run_rejects_empty_database() -> None:
    empty = SilverQuestDatabase(
        country=np.array([], dtype=object),
        latitude=np.array([]),
        longitude=np.array([]),
        pb206_204=np.array([]),
        pb207_204=np.array([]),
        pb208_204=np.array([]),
    )
    artifact = SilverQuestArtifact(no="A", pb206_204=_DX, pb207_204=_DY, pb208_204=1.05)
    with pytest.raises(ValueError, match="database is empty"):
        run_silverquest([artifact], empty)


def test_run_206pb_normalization_round_trips_through_the_profile() -> None:
    """The batch path and the scalar path must agree under 206Pb as well.

    The ore is chosen so that R's basis construction stays well conditioned:
    ``(Pb206204, Pb207204, Pb208204) = (2, 1, 1)`` normalises to
    ``(0.5, 0.5, 0.5)``, giving ``cosdir0 = (-1, 0.5, 0.5)`` and ``i3[3] = 0.5``.
    """
    ore = (2.0, 1.0, 1.0)
    artifact = SilverQuestArtifact(no="A", pb206_204=3.0, pb207_204=0.6, pb208_204=1.1)
    database = _database([ore])
    batch = run_silverquest(
        [artifact], database, SilverQuestConfig(normalization="206Pb", jittered=False)
    )
    scalar = silverquest_profile(
        (artifact.pb206_204, artifact.pb207_204, artifact.pb208_204), ore, "206Pb"
    )
    expected = _reference_profile((3.0, 0.6, 1.1), ore, "206Pb")
    assert batch.artifacts[0].table[0]["dist"] == pytest.approx(scalar["dist"], rel=1e-12)
    assert batch.artifacts[0].table[0]["dist"] == pytest.approx(
        expected["dist"], rel=1e-12
    )
    assert batch.artifacts[0].table[0]["fract"] == pytest.approx(
        scalar["fract"], rel=1e-12
    )
    # By hand: normalised artefact (1/3, 0.2, 11/30) against ore (0.5, 0.5, 0.5).
    # cosdir0 = (-2*x0, y0, 2*z0) = (-1, 0.5, 1) — note the 2*z0, which is what
    # differs from the 204Pb branch — so |cosdir0|^2 = 2.25 and
    # AP = (1/6, 0.3, 2/15).  dot = -1/6 + 0.15 + 2/15 = 0.1166667, and
    # u = dot / 2.25 = 0.0518519.  R takes cosdir0[1] — the *first* element,
    # here -1 — so fract = -1 * 0.0518519 = -0.0518519.
    assert batch.artifacts[0].table[0]["fract"] == pytest.approx(
        -0.05185185185185184, rel=1e-9
    )
    assert batch.artifacts[0].table[0]["dist"] == pytest.approx(
        264576.33724574314, rel=1e-9
    )


def test_run_206pb_matches_the_closed_form_for_the_y_axis_ray() -> None:
    """Under 206Pb the ray through ore (2, 1, 1) is ``cosdir0 = (-1, 0.5, 0.5)``.

    Normalised, the ore's ``y`` is 0.5 and ``x`` is 0.5; moving the artefact's
    ``y`` alone leaves the offset in the plane, and the independent transcription
    gives its distance.
    """
    ore = (2.0, 1.0, 1.0)
    artifact = SilverQuestArtifact(no="B", pb206_204=2.0, pb207_204=0.55, pb208_204=0.5)
    database = _database([ore])
    result = run_silverquest(
        [artifact], database, SilverQuestConfig(normalization="206Pb", jittered=False)
    )
    expected = _reference_profile((2.0, 0.55, 0.5), ore, "206Pb")
    assert result.artifacts[0].table[0]["dist"] == pytest.approx(
        expected["dist"], rel=1e-12
    )
    # 0.05 offset in the normalised y on a ray whose y component is +0.5:
    # the offset is neither along nor exactly across, so it has a real distance.
    assert result.artifacts[0].table[0]["dist"] > 0.0


def test_result_summary_mentions_the_run_configuration() -> None:
    database, artifact = _single_ore_setup()
    summary = run_silverquest(
        [artifact], database, SilverQuestConfig(jittered=False)
    ).summary()
    assert "204Pb" in summary
    assert "1 artefact(s)" in summary
    assert "1 hit(s)" in summary


# ── R semantics helpers ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value, expected",
    [(0.5, 1.0), (1.5, 2.0), (2.5, 3.0), (-0.5, -1.0), (0.4, 0.0), (0.6, 1.0)],
)
def test_r_round_breaks_ties_away_from_zero(value: float, expected: float) -> None:
    """R's round() differs from numpy's banker's rounding at .5."""
    assert _r_round(value) == expected
    if value == 0.5:
        assert float(np.round(value)) == 0.0  # numpy rounds to even


def test_distance_colour_index_matches_r_line_418() -> None:
    """round((dist / dmax) * (nprox - 1) + 0.5), floored at 1."""
    distances = np.array([0.25, 0.5, 1.0])
    indices, clamped = _distance_colour_index(distances, dmax=2.0, n_hits=3)
    # (0.25/2)*2 + 0.5 = 0.75 → 1 ; (0.5/2)*2 + 0.5 = 1.0 → 1 ; (1/2)*2+0.5 = 1.5 → 2
    assert list(indices) == [1, 1, 2]
    assert clamped is False


def test_distance_colour_index_clamps_beyond_the_ramp() -> None:
    """R-QUIRK: nocol is scaled by the parameter dmax, so it can pass nprox."""
    distances = np.array([0.9, 5.0])
    indices, clamped = _distance_colour_index(distances, dmax=1.0, n_hits=2)
    # (5.0/1)*1 + 0.5 = 5.5 → 6, far past the two-entry ramp.
    assert clamped is True
    assert list(indices) == [1, 2]


def test_distance_colour_index_uses_r_rounding_at_the_tie() -> None:
    """A tie must round *up* (R), not to even (numpy)."""
    # dist = 0, nprox = 2, dmax = 1 → round(0.5) = 1 in R, 0 in numpy.
    indices, _ = _distance_colour_index(np.array([0.0]), dmax=1.0, n_hits=2)
    assert list(indices) == [1]


def test_distance_colour_index_never_returns_zero() -> None:
    indices, _ = _distance_colour_index(np.array([0.0]), dmax=3.0, n_hits=4)
    assert list(indices) == [1]  # pmax(nocol, 1), R line 419


def test_colour_ramp_matches_grdevices_endpoints() -> None:
    ramp = _colour_ramp(5)
    assert ramp == [
        "#000000",
        "#ff0000",
        "#ffa500",
        "#ffff00",
        "#ffffff",
    ]
    # R's own colour names for the same five anchors (R lines 396/462).
    assert COLOUR_RAMP == ("black", "red", "orange", "yellow", "white")
    assert _colour_ramp(1) == ["#000000"]
    assert _colour_ramp(0) == []


def test_colour_for_distance_reads_the_precomputed_index() -> None:
    database, artifact = _single_ore_setup()
    hit_result = run_silverquest(
        [artifact], database, SilverQuestConfig(jittered=False)
    ).artifacts[0]
    assert hit_result.n_hits == 1
    assert hit_result.colour_for_distance(0, hit_result.n_hits) == "#000000"
    with pytest.raises(IndexError):
        hit_result.colour_for_distance(5, hit_result.n_hits)


def test_artifact_result_colour_lookup_rejects_a_missing_result() -> None:
    empty = SilverQuestArtifactResult(no="A", n_hits=0, hits=(), table=())
    with pytest.raises(IndexError):
        empty.colour_for_distance(0, 4)


# ── database loading / path contract ─────────────────────────────────────


def test_database_path_is_resolved_relative_to_the_repository() -> None:
    path = default_database_path()
    assert path.is_absolute()
    assert path.name == "Pb_DB_20240310AllGalenas.xlsx"
    assert "SilverQuest_v1" in str(path)
    assert path == default_database_path()
    assert SILVERQUEST_DB_RELATIVE_PATH.endswith("Pb_DB_20240310AllGalenas.xlsx")


def test_database_path_honours_an_explicit_override(tmp_path) -> None:
    explicit = tmp_path / "custom.xlsx"
    assert resolve_database_path(explicit) == explicit


def test_database_path_prefers_the_env_override_when_default_is_absent(
    tmp_path, monkeypatch
) -> None:
    target = tmp_path / "from_env.xlsx"
    monkeypatch.setenv(SILVERQUEST_DB_ENV_VAR, str(target))
    monkeypatch.setattr(
        "data.silverquest.default_database_path", lambda: tmp_path / "absent.xlsx"
    )
    assert resolve_database_path(None) == target


def test_load_database_reports_a_missing_workbook(tmp_path) -> None:
    with pytest.raises(FileNotFoundError) as excinfo:
        load_silverquest_database(tmp_path / "nope.xlsx")
    message = str(excinfo.value)
    assert "Pb_DB_20240310AllGalenas.xlsx" in message
    assert SILVERQUEST_DB_ENV_VAR in message


def test_load_database_from_a_synthetic_workbook(tmp_path) -> None:
    """Round-trip a tiny workbook, including the non-numeric row R trips on."""
    pandas = pytest.importorskip("pandas")
    frame = pandas.DataFrame(
        {
            "Country": ["Algeria", "Peru", "Broken"],
            "Latitude": [36.6, -12.0, "Mountains"],
            "Longitude": [8.1, -75.0, "Deh"],
            "Pb206204": [18.86, 18.5, "Hosein"],
            "Pb207204": [15.694, 15.6, 15.7],
            "Pb208204": [38.946, 38.4, 38.5],
        }
    )
    workbook = tmp_path / "tiny.xlsx"
    frame.to_excel(workbook, index=False)

    database = load_silverquest_database(workbook)
    assert database.n_rows == 2
    assert database.dropped_rows == (2,)
    assert list(database.country) == ["Algeria", "Peru"]
    assert database.pb206_204[0] == pytest.approx(18.86)
    assert database.latitude[1] == pytest.approx(-12.0)


def test_load_database_rejects_a_workbook_without_the_r_columns(tmp_path) -> None:
    pandas = pytest.importorskip("pandas")
    workbook = tmp_path / "wrong.xlsx"
    pandas.DataFrame({"Country": ["A"], "Latitude": [1.0]}).to_excel(workbook, index=False)
    with pytest.raises(ValueError, match="missing column"):
        load_silverquest_database(workbook)


# ── record adapter ───────────────────────────────────────────────────────


def test_artifacts_from_records_accepts_both_column_spellings() -> None:
    from_r = artifacts_from_records(
        [
            {
                "no": "G107",
                "group": 1,
                "Pb206204": 18.5764,
                "Pb207204": 15.6597,
                "Pb208204": 38.589,
            }
        ]
    )
    from_app = artifacts_from_records(
        [
            {
                "no": "G107",
                "group": "1",
                "Pb206_204": 18.5764,
                "Pb207_204": 15.6597,
                "Pb208_204": 38.589,
            }
        ]
    )
    assert from_r == from_app
    assert from_r[0].no == "G107"


def test_artifacts_from_records_reports_a_missing_ratio_column() -> None:
    with pytest.raises(KeyError, match="Pb207204"):
        artifacts_from_records([{"no": "A", "Pb206204": 1.0, "Pb208204": 1.0}])


def test_artifacts_from_records_defaults_group() -> None:
    artifacts = artifacts_from_records(
        [{"no": "A", "Pb206204": 1.0, "Pb207204": 0.5, "Pb208204": 0.5}]
    )
    assert artifacts[0].group == "1"


def test_artifacts_from_records_carry_the_r_input_order() -> None:
    """The R readme's worked example (Readme.pdf, "Input Example")."""
    records = [
        {"no": "G107", "group": 1, "Pb206204": 18.5764,
         "Pb207204": 15.6597, "Pb208204": 38.589},
        {"no": "G089", "group": 1, "Pb206204": 18.5649,
         "Pb207204": 15.6561, "Pb208204": 38.572},
    ]
    artifacts = artifacts_from_records(records)
    database = _database(
        [(a.pb206_204, a.pb207_204, a.pb208_204) for a in artifacts]
    )
    result = run_silverquest(artifacts, database, SilverQuestConfig(jittered=False))
    assert result.database_rows == 2
    # Each artefact finds its own analysis at distance exactly 0.
    for index, hit_result in enumerate(result.artifacts):
        assert hit_result.table[0]["dist"] == pytest.approx(0.0, abs=0.0)
        assert hit_result.table[0]["no"] == index + 1
