"""Smoke tests for tabular export use cases."""

from pathlib import Path

import pandas as pd

from application.use_cases.export_data import (
    _parse_linear_expression,
    _unique_sheet_name,
    append_selected_data_to_excel,
    build_export_dataframe,
    export_dataframe_to_file,
    export_selected_data_to_file,
)


def test_build_export_dataframe_with_umap_dimensions() -> None:
    df_global = pd.DataFrame(
        {
            "sample": ["A", "B", "C"],
            "value": [10, 20, 30],
        }
    )
    embedding = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    export_df = build_export_dataframe(
        selected_indices=[0, 2],
        df_global=df_global,
        embedding=embedding,
        embedding_type="UMAP",
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params={"n_neighbors": 15},
        render_mode="UMAP",
    )

    assert list(export_df["sample"]) == ["A", "C"]
    assert list(export_df["UMAP 1"]) == [0.1, 0.5]
    assert list(export_df["UMAP 2"]) == [0.2, 0.6]
    assert list(export_df["param_n_neighbors"]) == [15, 15]


def test_build_export_dataframe_2d_ignores_stale_embedding() -> None:
    """2D/3D exports must not append stale embedding coordinates."""
    df_global = pd.DataFrame(
        {
            "sample": ["A", "B", "C"],
            "X": [1.0, 2.0, 3.0],
            "Y": [4.0, 5.0, 6.0],
        }
    )
    stale_embedding = [[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]]

    export_df = build_export_dataframe(
        selected_indices=[0, 1, 2],
        df_global=df_global,
        embedding=stale_embedding,
        embedding_type="UMAP",
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        axis_labels={"x": "X", "y": "Y"},
        render_mode="2D",
    )

    assert list(export_df.columns) == ["sample", "X", "Y"]


def test_build_export_dataframe_geochem_appends_kappa_model() -> None:
    """PB_EVOL_86 must export kappa_model (the actual result key), not 'kappa'."""
    df_global = pd.DataFrame(
        {
            "sample": ["A", "B"],
            "206Pb/204Pb": [18.0, 19.0],
            "207Pb/204Pb": [15.6, 15.7],
            "208Pb/204Pb": [38.5, 39.0],
        }
    )

    export_df = build_export_dataframe(
        selected_indices=[0, 1],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        render_mode="PB_EVOL_86",
    )

    assert "kappa_model" in export_df.columns
    assert "kappa" not in export_df.columns
    assert "mu_model" in export_df.columns
    assert "t_Model (Ma)" in export_df.columns
    # Values are finite (engine parameters are initialized).
    assert export_df["kappa_model"].notna().all()


def test_export_selected_data_to_file_csv_has_bom(tmp_path: Path) -> None:
    """CSV exports use utf-8-sig so Excel renders CJK names correctly."""
    df_global = pd.DataFrame({"样品": ["甲", "乙"], "值": [1.0, 2.0]})

    target = export_selected_data_to_file(
        selected_indices=[0, 1],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        file_path=str(tmp_path / "out.csv"),
        preferred_format="csv",
        render_mode="UMAP",
    )

    raw = Path(target).read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf"), "CSV must start with a UTF-8 BOM"
    assert "样品".encode("utf-8") in raw


def test_append_selected_data_to_excel_renames_duplicate_sheet(tmp_path: Path) -> None:
    df_global = pd.DataFrame({"x": [1, 2], "y": [3, 4]})
    target = str(tmp_path / "out.xlsx")

    first = append_selected_data_to_excel(
        selected_indices=[0, 1],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        file_path=target,
        sheet_name="Data",
        render_mode="UMAP",
    )
    assert Path(first).exists()

    # Second append with the same sheet name must not silently overwrite.
    second = append_selected_data_to_excel(
        selected_indices=[0],
        df_global=df_global,
        embedding=None,
        embedding_type=None,
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params=None,
        file_path=target,
        sheet_name="Data",
        render_mode="UMAP",
    )
    import openpyxl

    wb = openpyxl.load_workbook(second)
    try:
        assert wb.sheetnames == ["Data", "Data1"]
    finally:
        wb.close()


def test_parse_linear_expression() -> None:
    assert _parse_linear_expression("y = 1.0049*x + 20.259") == (1.0049, 20.259)
    assert _parse_linear_expression("y = -0.5 x - 3") == (-0.5, -3.0)
    assert _parse_linear_expression("y = 2e-3*x + 1.5") == (0.002, 1.5)
    assert _parse_linear_expression("not linear") == (None, None)
    assert _parse_linear_expression("") == (None, None)


def test_unique_sheet_name() -> None:
    assert _unique_sheet_name("Data", set()) == "Data"
    assert _unique_sheet_name("Data", {"Data"}) == "Data1"
    assert _unique_sheet_name("Data", {"Data", "Data1"}) == "Data2"


def test_export_dataframe_to_csv_with_preferred_suffix(tmp_path: Path) -> None:
    data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})

    target = export_dataframe_to_file(
        dataframe=data,
        file_path=str(tmp_path / "export_result"),
        preferred_format="csv",
    )

    assert target.endswith(".csv")
    assert (tmp_path / "export_result.csv").exists()
