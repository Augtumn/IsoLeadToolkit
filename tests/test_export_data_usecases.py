"""Smoke tests for tabular export use cases."""

from pathlib import Path

import pandas as pd

from application.use_cases.export_data import build_export_dataframe, export_dataframe_to_file


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
        algorithm="UMAP",
        embedding=embedding,
        embedding_type="UMAP",
        active_subset_indices=None,
        pca_component_indices=None,
        algorithm_params={"n_neighbors": 15},
    )

    assert list(export_df["sample"]) == ["A", "C"]
    assert list(export_df["UMAP 1"]) == [0.1, 0.5]
    assert list(export_df["UMAP 2"]) == [0.2, 0.6]
    assert list(export_df["param_n_neighbors"]) == [15, 15]


def test_export_dataframe_to_csv_with_preferred_suffix(tmp_path: Path) -> None:
    data = pd.DataFrame({"x": [1, 2], "y": [3, 4]})

    target = export_dataframe_to_file(
        dataframe=data,
        file_path=str(tmp_path / "export_result"),
        preferred_format="csv",
    )

    assert target.endswith(".csv")
    assert (tmp_path / "export_result.csv").exists()
