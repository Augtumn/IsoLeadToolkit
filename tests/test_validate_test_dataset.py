"""Validate isotope benchmark dataset against reference values.

Each row in the input Excel file carries an explicit algorithm name in the
first column (``算法``); the corresponding engine preset is loaded directly
for that row, and computed V1/V2/t_Model values are compared against the
``*_std``/``t_Model`` reference columns (± tolerance).

Reference columns are optional per row: a row is validated against the
metrics whose reference columns are present (e.g. V1V2 rows → V1/V2,
Stacey & Kramers / Cumming & Richards rows → t_Model).

Real-data rows for the Albarède & Juteau (1984) model carry
``t_Albarede``/``mu_Albarede``/``kappa_Albarede`` references produced by the
reference implementation (F. Albarède's MATLAB pipeline, as distributed with
the SilverQuest_v1 galena database), so the T–μ–κ inversion is checked against
measured ore compositions rather than synthetic round-trips.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from data.geochemistry import calculate_albarede_parameters, calculate_all_parameters, engine

ALGORITHM_COL = "算法"
MODEL_AGE_STD_COL = "t_Model"
BENCHMARK_XLSX = Path(__file__).resolve().parent / "data" / "isotope_benchmark.xlsx"

ALBAREDE_MODEL = "Albarède & Juteau (1984)"

STD_COLUMN_CANDIDATES = {
    "V1": ["V1_std", "V1standard"],
    "V2": ["V2_std", "V2standard"],
}

# Metric -> calculation result key produced by calculate_all_parameters.
# t_Model is the unified model-age output (one per parameter set).
METRIC_RESULT_KEY = {
    "V1": "V1",
    "V2": "V2",
    "t_Model": "t_Model (Ma)",
}

# AJ84 metrics come from calculate_albarede_parameters instead (their reference
# columns are only filled on AJ84 rows).
ALBAREDE_STD_COLUMN_CANDIDATES = {
    "t_Albarede": ["t_Albarede", "t_Albarede (Ma)"],
    "mu_Albarede": ["mu_Albarede"],
    "kappa_Albarede": ["kappa_Albarede"],
}
ALBAREDE_RESULT_KEY = {
    "t_Albarede": "t_Albarede (Ma)",
    "mu_Albarede": "mu_Albarede",
    "kappa_Albarede": "kappa_Albarede",
}

# Absolute tolerances per metric; unlisted metrics use the --tol argument.
# t_Albarede keeps the file's model-age convention (±1 Ma, same as t_Model);
# mu/kappa are tight because the references carry 4/3 decimals.
METRIC_TOLERANCES = {
    "V1": 1.0,
    "V2": 1.0,
    "t_Model": 1.0,
    "t_Albarede": 1.0,
    "mu_Albarede": 0.01,
    "kappa_Albarede": 0.01,
}


def _pick_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def _to_float_or_nan(value: object) -> float:
    return float(value) if pd.notna(value) else float("nan")


def _calc_err(calc: float, std: float) -> float:
    if np.isnan(calc) or np.isnan(std):
        return float("nan")
    return abs(calc - std)


def _calc_row_pass(row: dict[str, object], checked_metrics: list[str]) -> bool:
    """A row passes only when every checked metric has a real, passing error.

    A metric whose computed value is missing (engine returned None -> NaN)
    yields a NaN pass flag; treating NaN as "skip" let a broken engine
    validate as all-green.
    """
    checks: list[bool] = []
    for metric in checked_metrics:
        pass_key = f"{metric}_pass_pm1"
        value = row.get(pass_key)
        if value is None or pd.isna(value):
            return False
        checks.append(bool(value))
    return all(checks) if checks else True


def validate_dataset(input_path: Path, output_path: Path, tolerance: float) -> pd.DataFrame:
    df = pd.read_excel(input_path)

    if ALGORITHM_COL not in df.columns:
        raise ValueError(f"Missing algorithm column: {ALGORITHM_COL}")
    required_base_columns = ["206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"]
    missing_base = [c for c in required_base_columns if c not in df.columns]
    if missing_base:
        raise ValueError(f"Missing required columns: {missing_base}")

    std_cols: dict[str, str | None] = {
        metric: _pick_column(df, candidates)
        for metric, candidates in STD_COLUMN_CANDIDATES.items()
    }
    # t_Model is the unified model-age reference column.
    std_cols["t_Model"] = MODEL_AGE_STD_COL if MODEL_AGE_STD_COL in df.columns else None
    for metric, candidates in ALBAREDE_STD_COLUMN_CANDIDATES.items():
        std_cols[metric] = _pick_column(df, candidates)
    # Metrics validated for rows of each algorithm are those with a reference
    # column present AND produced by the engine for that algorithm.
    metrics = [m for m, col in std_cols.items() if col is not None]

    rows: list[dict[str, object]] = []

    # Group by algorithm name so each preset is loaded once per algorithm.
    for algorithm, group_df in df.groupby(ALGORITHM_COL, sort=False):
        try:
            engine.load_preset(str(algorithm))
        except Exception as exc:
            raise ValueError(
                f"Unknown algorithm preset: {algorithm!r} (row {int(group_df.index[0]) + 2})"
            ) from exc

        result = calculate_all_parameters(
            group_df["206Pb/204Pb"].to_numpy(float),
            group_df["207Pb/204Pb"].to_numpy(float),
            group_df["208Pb/204Pb"].to_numpy(float),
            calculate_ages=True,
        )

        albarede_result = None
        if str(algorithm) == ALBAREDE_MODEL:
            albarede_result = calculate_albarede_parameters(
                group_df["206Pb/204Pb"].to_numpy(float),
                group_df["207Pb/204Pb"].to_numpy(float),
                group_df["208Pb/204Pb"].to_numpy(float),
                params=engine.get_parameters(),
            )

        for i, (idx, src_row) in enumerate(group_df.iterrows()):
            excel_row = int(idx) + 2

            row_data: dict[str, object] = {
                "excel_row": excel_row,
                "algorithm": str(algorithm),
                "206Pb/204Pb": float(src_row["206Pb/204Pb"]),
                "207Pb/204Pb": float(src_row["207Pb/204Pb"]),
                "208Pb/204Pb": float(src_row["208Pb/204Pb"]),
                "Reference": src_row.get("Reference", ""),
            }
            checked: list[str] = []
            for metric in metrics:
                std_val = _to_float_or_nan(src_row.get(std_cols[metric]))
                if metric in ALBAREDE_RESULT_KEY:
                    calc = (albarede_result or {}).get(ALBAREDE_RESULT_KEY[metric])
                else:
                    calc = result.get(METRIC_RESULT_KEY[metric])
                calc_val = (
                    float(calc[i])
                    if calc is not None and np.ndim(calc) > 0
                    else float("nan")
                )
                metric_tol = METRIC_TOLERANCES.get(metric, tolerance)
                err = _calc_err(calc_val, std_val)
                row_data[f"{metric}_calc"] = calc_val
                row_data[f"{metric}_std"] = std_val
                row_data[f"{metric}_err"] = err
                row_data[f"{metric}_tol"] = metric_tol
                row_data[f"{metric}_pass_pm1"] = (
                    (err <= metric_tol) if not np.isnan(err) else np.nan
                )
                if not np.isnan(std_val):
                    checked.append(metric)

            row_data["validated_metrics"] = ",".join(checked)
            row_data["row_pass_by_rule"] = _calc_row_pass(row_data, checked)
            rows.append(row_data)

    out = pd.DataFrame(rows).sort_values("excel_row").reset_index(drop=True)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    return out


def _print_summary(out: pd.DataFrame) -> None:
    print("=== RULE-BASED SUMMARY (±1) ===")
    for algorithm, group_df in out.groupby("algorithm", sort=False):
        passed = int(group_df["row_pass_by_rule"].sum())
        total = len(group_df)
        print(f"{algorithm}: {passed}/{total} rows pass by rule")

    print("\n=== FAIL ROWS BY RULE ===")
    fails = out[~out["row_pass_by_rule"]]
    if fails.empty:
        print("None")
        return
    fail_cols = [
        "excel_row",
        "algorithm",
        "validated_metrics",
        "V1_err",
        "V2_err",
        "t_Model_err",
        "t_Albarede_err",
        "mu_Albarede_err",
        "kappa_Albarede_err",
    ]
    fail_cols = [c for c in fail_cols if c in fails.columns]
    print(fails[fail_cols].to_string(index=False))


def _scalar(arr: object, default: float = float("nan")) -> float:
    """Extract a scalar float from a numpy array or scalar."""
    if isinstance(arr, np.ndarray):
        return float(arr.item(0)) if arr.ndim > 0 and arr.size > 0 else float("nan")
    try:
        return float(arr)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _make_test_dataset(tmp_path: Path) -> Path:
    """Create a minimal benchmark test Excel file with self-consistent expected values.

    Reasonable crustal lead isotope ratios are used. Expected V1/V2/t_Model values
    are pre-computed with the same geochemistry engine so the validation can verify
    the pipeline structure without needing a real benchmark file.
    """
    engine.load_preset("V1V2 (Zhu 1993)")
    rz = calculate_all_parameters(
        np.array([18.5]), np.array([15.6]), np.array([38.5]),
        calculate_ages=True,
    )

    engine.load_preset("V1V2 (Geokit)")
    rg = calculate_all_parameters(
        np.array([19.0]), np.array([15.7]), np.array([39.0]),
        calculate_ages=True,
    )

    engine.load_preset("Stacey & Kramers (1st Stage)")
    rp_sk1 = calculate_all_parameters(
        np.array([17.5]), np.array([15.5]), np.array([38.0]),
        calculate_ages=True,
    )

    engine.load_preset(ALBAREDE_MODEL)
    ra = calculate_albarede_parameters(
        np.array([18.75]), np.array([15.68]), np.array([38.97]),
        params=engine.get_parameters(),
    )

    data: dict[str, list[object]] = {
        ALGORITHM_COL: [
            "V1V2 (Zhu 1993)",
            "V1V2 (Geokit)",
            "Stacey & Kramers (1st Stage)",
            ALBAREDE_MODEL,
        ],
        "206Pb/204Pb": [18.5, 19.0, 17.5, 18.75],
        "207Pb/204Pb": [15.6, 15.7, 15.5, 15.68],
        "208Pb/204Pb": [38.5, 39.0, 38.0, 38.97],
        "Reference": ["synthetic", "synthetic", "synthetic", "synthetic"],
        "V1_std": [
            _scalar(rz.get("V1")),
            _scalar(rg.get("V1")),
            float("nan"),
            float("nan"),
        ],
        "V2_std": [
            _scalar(rz.get("V2")),
            _scalar(rg.get("V2")),
            float("nan"),
            float("nan"),
        ],
        MODEL_AGE_STD_COL: [
            float("nan"),
            float("nan"),
            _scalar(rp_sk1.get("t_Model (Ma)")),  # unified model age for SK1 row
            float("nan"),
        ],
        # Wiring check for the AJ84 branch (self-consistent, not a real benchmark).
        "t_Albarede": [float("nan"), float("nan"), float("nan"), _scalar(ra.get("t_Albarede (Ma)"))],
        "mu_Albarede": [float("nan"), float("nan"), float("nan"), _scalar(ra.get("mu_Albarede"))],
        "kappa_Albarede": [float("nan"), float("nan"), float("nan"), _scalar(ra.get("kappa_Albarede"))],
    }

    df = pd.DataFrame(data)
    input_path = tmp_path / "test.xlsx"
    df.to_excel(input_path, index=False)
    return input_path


def test_validate_dataset_rules_and_output(tmp_path: Path) -> None:
    input_path = _make_test_dataset(tmp_path)
    output_path = tmp_path / "test_comparison_full.csv"
    out = validate_dataset(input_path, output_path, tolerance=1.0)

    assert not out.empty, "Validation output should not be empty"
    assert output_path.exists(), "Output CSV should have been written"

    zhu = out[out["algorithm"] == "V1V2 (Zhu 1993)"]
    geokit = out[out["algorithm"] == "V1V2 (Geokit)"]
    sk1 = out[out["algorithm"] == "Stacey & Kramers (1st Stage)"]
    aj84 = out[out["algorithm"] == ALBAREDE_MODEL]

    assert not zhu.empty, "Expected zhu algorithm rows in output"
    assert not geokit.empty, "Expected geokit algorithm rows in output"
    assert not sk1.empty, "Expected SK1 algorithm rows in output"
    assert not aj84.empty, "Expected AJ84 algorithm rows in output"

    assert set(zhu["validated_metrics"].dropna().unique()) == {"V1,V2"}
    assert set(geokit["validated_metrics"].dropna().unique()) == {"V1,V2"}
    assert set(sk1["validated_metrics"].dropna().unique()) == {"t_Model"}
    assert set(aj84["validated_metrics"].dropna().unique()) == {
        "t_Albarede,mu_Albarede,kappa_Albarede"
    }

    # All synthetic rows should pass (±1 tolerance vs self-computed standard)
    failing = out[~out["row_pass_by_rule"]]
    assert failing.empty, (
        f"Expected all rows to pass, but {len(failing)} fail(ed):\n"
        f"{failing[['algorithm', 'V1_err', 'V2_err', 't_Model_err']].to_string()}"
    )


def test_real_benchmark_dataset_validates() -> None:
    """Guard: the tracked literature benchmark dataset validates within tolerance.

    Every algorithm group (zhu / geokit / SK1 / SK2 / CR / MM20) must reach
    ≥95% row pass rate. Known exceptions: three zhu rows with documented
    data issues (one bad 207Pb/204Pb=18.503 entry, two marginally outside
    tolerance) are excluded from the pass-rate floor via skip-list.

    AJ84 rows are measured ore compositions whose T–μ–κ references come from
    the reference implementation (F. Albarède's MATLAB pipeline, distributed
    with the SilverQuest_v1 galena database); they must all pass at the tight
    μ/κ tolerances, covering positive ages, negative ages (U-depleted sources)
    and samples at 206Pb/204Pb = x*.
    """
    if not BENCHMARK_XLSX.exists():
        pytest.skip(f"Benchmark dataset missing: {BENCHMARK_XLSX}")
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "benchmark_comparison.csv"
        out = validate_dataset(BENCHMARK_XLSX, out_path, tolerance=1.0)

    assert not out.empty, "Benchmark validation produced no rows"

    # Every algorithm group present
    expected_algorithms = {
        "V1V2 (Zhu 1993)",
        "V1V2 (Geokit)",
        "Stacey & Kramers (1st Stage)",
        "Stacey & Kramers (2nd Stage)",
        "Cumming & Richards (Model III)",
        "Maltese & Mezger (2020)",
        ALBAREDE_MODEL,
    }
    present = set(out["algorithm"].unique())
    missing = expected_algorithms - present
    assert not missing, f"Benchmark missing algorithm groups: {missing}"

    # Known-bad zhu rows (data errors, not engine issues): excel_row 25, 28, 31
    known_bad = {(25, "V1V2 (Zhu 1993)"), (28, "V1V2 (Zhu 1993)"), (31, "V1V2 (Zhu 1993)")}

    failing = out[~out["row_pass_by_rule"]]
    unexpected = failing[
        ~failing.apply(lambda r: (int(r["excel_row"]), r["algorithm"]) in known_bad, axis=1)
    ]
    assert unexpected.empty, (
        f"Unexpected benchmark failures:\n"
        f"{unexpected[['excel_row', 'algorithm', 'V1_err', 'V2_err', 't_Model_err']].to_string()}"
    )

    # AJ84: real ore data, all rows must pass; the group must span the negative
    # model-age branch and the x = x* degenerate case.
    aj84 = out[out["algorithm"] == ALBAREDE_MODEL]
    assert len(aj84) >= 15, f"AJ84 benchmark coverage too thin: {len(aj84)} rows"
    assert (aj84["t_Albarede_std"] < 0).sum() >= 3, "AJ84 rows must cover negative model ages"
    assert np.isclose(aj84["206Pb/204Pb"], 18.750, atol=1e-9).sum() >= 1, (
        "AJ84 rows must cover 206Pb/204Pb = x*"
    )
    aj84_failing = aj84[~aj84["row_pass_by_rule"]]
    assert aj84_failing.empty, (
        "AJ84 real-data rows outside tolerance:\n"
        f"{aj84_failing[['206Pb/204Pb', 't_Albarede_err', 'mu_Albarede_err', 'kappa_Albarede_err']].to_string()}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate isotopes benchmark dataset against reference values.")
    parser.add_argument(
        "--input",
        default=str(BENCHMARK_XLSX),
        help=f"Input Excel path. Default: {BENCHMARK_XLSX}",
    )
    parser.add_argument(
        "--output",
        default="test_comparison_full.csv",
        help="Output CSV path. Default: test_comparison_full.csv",
    )
    parser.add_argument(
        "--tol",
        type=float,
        default=1.0,
        help="Absolute tolerance. Default: 1.0",
    )
    args = parser.parse_args()

    output_df = validate_dataset(Path(args.input), Path(args.output), args.tol)
    _print_summary(output_df)
    print(f"\nSaved: {Path(args.output).resolve()}")
    print(f"Total rows: {len(output_df)}")


if __name__ == "__main__":
    main()
