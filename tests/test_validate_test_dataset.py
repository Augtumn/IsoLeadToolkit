"""Validate isotope benchmark dataset with group-specific metrics.

Rules:
- zhu/geokit: validate only V1 and V2
- PbIso: validate only tSK and tCDT
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.geochemistry import calculate_all_parameters, engine


MODEL_MAP = {
    "zhu": "V1V2 (Zhu 1993)",
    "geokit": "V1V2 (Geokit)",
    "PbIso": "Stacey & Kramers (2nd Stage)",
}

RULES = {
    "zhu": ["V1", "V2"],
    "geokit": ["V1", "V2"],
    "PbIso": ["tSK", "tCDT"],
}

STD_COLUMN_CANDIDATES = {
    "V1": ["V1_std", "V1standard"],
    "V2": ["V2_std", "V2standard"],
    "tSK": ["tSK_std", "tSKstandard"],
    "tCDT": ["tCDT_std", "tCDTstandard"],
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
    checks: list[bool] = []
    if "V1" in checked_metrics and pd.notna(row["V1_pass_pm1"]):
        checks.append(bool(row["V1_pass_pm1"]))
    if "V2" in checked_metrics and pd.notna(row["V2_pass_pm1"]):
        checks.append(bool(row["V2_pass_pm1"]))
    if "tSK" in checked_metrics and pd.notna(row["tSK_pass_pm1"]):
        checks.append(bool(row["tSK_pass_pm1"]))
    if "tCDT" in checked_metrics and pd.notna(row["tCDT_pass_pm1"]):
        checks.append(bool(row["tCDT_pass_pm1"]))
    return all(checks) if checks else True


def validate_dataset(input_path: Path, output_path: Path, tolerance: float) -> pd.DataFrame:
    df = pd.read_excel(input_path)

    required_base_columns = ["序号", "206Pb/204Pb", "207Pb/204Pb", "208Pb/204Pb"]
    missing_base = [c for c in required_base_columns if c not in df.columns]
    if missing_base:
        raise ValueError(f"Missing required columns: {missing_base}")

    std_cols = {
        metric: _pick_column(df, candidates)
        for metric, candidates in STD_COLUMN_CANDIDATES.items()
    }

    rows: list[dict[str, object]] = []

    for group_name, model_name in MODEL_MAP.items():
        group_df = df[df["序号"].astype(str).str.strip() == group_name].copy()
        if group_df.empty:
            continue

        engine.load_preset(model_name)
        result = calculate_all_parameters(
            group_df["206Pb/204Pb"].to_numpy(float),
            group_df["207Pb/204Pb"].to_numpy(float),
            group_df["208Pb/204Pb"].to_numpy(float),
            calculate_ages=True,
        )

        for i, (idx, src_row) in enumerate(group_df.iterrows()):
            excel_row = int(idx) + 2

            v1_std = _to_float_or_nan(src_row.get(std_cols["V1"])) if std_cols["V1"] else float("nan")
            v2_std = _to_float_or_nan(src_row.get(std_cols["V2"])) if std_cols["V2"] else float("nan")
            tsk_std = _to_float_or_nan(src_row.get(std_cols["tSK"])) if std_cols["tSK"] else float("nan")
            tcdt_std = _to_float_or_nan(src_row.get(std_cols["tCDT"])) if std_cols["tCDT"] else float("nan")

            v1_calc = float(result["V1"][i]) if "V1" in result and np.ndim(result["V1"]) > 0 else float("nan")
            v2_calc = float(result["V2"][i]) if "V2" in result and np.ndim(result["V2"]) > 0 else float("nan")
            tsk_calc = float(result["tSK (Ma)"][i]) if "tSK (Ma)" in result and np.ndim(result["tSK (Ma)"]) > 0 else float("nan")
            tcdt_calc = float(result["tCDT (Ma)"][i]) if "tCDT (Ma)" in result and np.ndim(result["tCDT (Ma)"]) > 0 else float("nan")

            v1_err = _calc_err(v1_calc, v1_std)
            v2_err = _calc_err(v2_calc, v2_std)
            tsk_err = _calc_err(tsk_calc, tsk_std)
            tcdt_err = _calc_err(tcdt_calc, tcdt_std)

            current_rule = RULES.get(group_name, [])
            row_data: dict[str, object] = {
                "excel_row": excel_row,
                "group": group_name,
                "206Pb/204Pb": float(src_row["206Pb/204Pb"]),
                "207Pb/204Pb": float(src_row["207Pb/204Pb"]),
                "208Pb/204Pb": float(src_row["208Pb/204Pb"]),
                "Reference": src_row.get("Reference", ""),
                "V1_calc": v1_calc,
                "V1_std": v1_std,
                "V1_err": v1_err,
                "V1_pass_pm1": (v1_err <= tolerance) if not np.isnan(v1_err) else np.nan,
                "V2_calc": v2_calc,
                "V2_std": v2_std,
                "V2_err": v2_err,
                "V2_pass_pm1": (v2_err <= tolerance) if not np.isnan(v2_err) else np.nan,
                "tSK_calc": tsk_calc,
                "tSK_std": tsk_std,
                "tSK_err": tsk_err,
                "tSK_pass_pm1": (tsk_err <= tolerance) if not np.isnan(tsk_err) else np.nan,
                "tCDT_calc": tcdt_calc,
                "tCDT_std": tcdt_std,
                "tCDT_err": tcdt_err,
                "tCDT_pass_pm1": (tcdt_err <= tolerance) if not np.isnan(tcdt_err) else np.nan,
                "validated_metrics": ",".join(current_rule),
            }
            row_data["row_pass_by_rule"] = _calc_row_pass(row_data, current_rule)
            rows.append(row_data)

    out = pd.DataFrame(rows).sort_values("excel_row").reset_index(drop=True)
    out.to_csv(output_path, index=False, encoding="utf-8-sig")
    return out


def _print_summary(out: pd.DataFrame) -> None:
    print("=== RULE-BASED SUMMARY (±1) ===")
    for group_name in ["zhu", "geokit", "PbIso"]:
        group_df = out[out["group"] == group_name]
        if group_df.empty:
            continue
        passed = int(group_df["row_pass_by_rule"].sum())
        total = len(group_df)
        print(f"{group_name}: {passed}/{total} rows pass by rule")

    print("\n=== FAIL ROWS BY RULE ===")
    fails = out[~out["row_pass_by_rule"]]
    if fails.empty:
        print("None")
        return
    fail_cols = [
        "excel_row",
        "group",
        "validated_metrics",
        "V1_err",
        "V2_err",
        "tSK_err",
        "tCDT_err",
    ]
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

    Reasonable crustal lead isotope ratios are used. Expected V1/V2/tSK/tCDT values
    are pre-computed with the same geochemistry engine so the validation can verify
    the pipeline structure without needing a real benchmark file.
    """
    # --- pre-compute expected values for each group ---
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

    engine.load_preset("Stacey & Kramers (2nd Stage)")
    rp = calculate_all_parameters(
        np.array([17.5]), np.array([15.5]), np.array([38.0]),
        calculate_ages=True,
    )

    data: dict[str, list[object]] = {
        "序号": ["zhu", "geokit", "PbIso"],
        "206Pb/204Pb": [18.5, 19.0, 17.5],
        "207Pb/204Pb": [15.6, 15.7, 15.5],
        "208Pb/204Pb": [38.5, 39.0, 38.0],
        "Reference": ["synthetic", "synthetic", "synthetic"],
        "V1_std": [
            _scalar(rz.get("V1")),
            _scalar(rg.get("V1")),
            float("nan"),
        ],
        "V2_std": [
            _scalar(rz.get("V2")),
            _scalar(rg.get("V2")),
            float("nan"),
        ],
        "tSK_std": [
            float("nan"),
            float("nan"),
            _scalar(rp.get("tSK (Ma)")),
        ],
        "tCDT_std": [
            float("nan"),
            float("nan"),
            _scalar(rp.get("tCDT (Ma)")),
        ],
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

    zhu = out[out["group"] == "zhu"]
    geokit = out[out["group"] == "geokit"]
    pbiso = out[out["group"] == "PbIso"]

    assert not zhu.empty, "Expected zhu group in output"
    assert not geokit.empty, "Expected geokit group in output"
    assert not pbiso.empty, "Expected PbIso group in output"

    assert set(zhu["validated_metrics"].dropna().unique()) == {"V1,V2"}
    assert set(geokit["validated_metrics"].dropna().unique()) == {"V1,V2"}
    assert set(pbiso["validated_metrics"].dropna().unique()) == {"tSK,tCDT"}

    # All synthetic rows should pass (±1 tolerance vs self-computed standard)
    failing = out[~out["row_pass_by_rule"]]
    assert failing.empty, (
        f"Expected all rows to pass, but {len(failing)} fail(ed):\n"
        f"{failing[['group', 'V1_err', 'V2_err', 'tSK_err', 'tCDT_err']].to_string()}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate isotopes benchmark dataset by group rules.")
    parser.add_argument(
        "--input",
        default="test.xlsx",
        help="Input Excel path. Default: test.xlsx",
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
