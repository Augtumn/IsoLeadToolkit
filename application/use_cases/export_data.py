"""Application use cases for tabular data export."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import pandas as pd

logger = logging.getLogger(__name__)


def build_export_dataframe(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    algorithm: str | None,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    axis_labels: Mapping[str, str] | None = None,
) -> pd.DataFrame:
    """Create export DataFrame and append coordinate columns for every mode.

    Column names are taken from the current plot's axis labels so they
    reflect exactly what is shown on screen (e.g. "UMAP 1" / "UMAP 2",
    "206Pb/204Pb" / "207Pb/204Pb" for Pb evolution, etc.).
    """
    selected_list = list(selected_indices)
    selected_df = df_global.iloc[selected_list].copy()

    if embedding is None or len(embedding) == 0:
        return selected_df

    if active_subset_indices is not None:
        data_indices = sorted(list(active_subset_indices))
    else:
        data_indices = list(range(len(df_global)))

    axis_lbl = dict(axis_labels or {})

    index_map = {orig: i for i, orig in enumerate(data_indices)}
    n_dims = len(embedding[0]) if len(embedding) > 0 else 0

    for dim_idx in range(min(n_dims, 3)):
        col_values: list[float | None] = []
        for idx in selected_list:
            mapped_idx = index_map.get(idx)
            if mapped_idx is None or mapped_idx >= len(embedding):
                col_values.append(None)
                continue
            row = embedding[mapped_idx]
            col_values.append(
                float(row[dim_idx]) if dim_idx < len(row) else None
            )

        if dim_idx == 0:
            col_name = axis_lbl.get("x") or _dimension_label(embedding_type, 0, pca_component_indices)
        elif dim_idx == 1:
            col_name = axis_lbl.get("y") or _dimension_label(embedding_type, 1, pca_component_indices)
        else:
            col_name = axis_lbl.get("z") or _dimension_label(embedding_type, 2, pca_component_indices)

        selected_df[col_name] = col_values

    for key, value in (algorithm_params or {}).items():
        selected_df[f"param_{key}"] = value

    return selected_df


def _dimension_label(
    embedding_type: str | None,
    dim_idx: int,
    pca_component_indices: Sequence[int] | None,
) -> str:
    """Build a fallback column name for a dimension index."""
    if embedding_type in ("PCA", "RobustPCA"):
        pca_idx = list(pca_component_indices or [0, 1])
        pc = pca_idx[dim_idx] + 1 if dim_idx < len(pca_idx) else dim_idx + 1
        return f"PC{pc}"
    prefix = embedding_type or "Dim"
    return f"{prefix} {dim_idx + 1}"


def export_dataframe_to_file(
    *,
    dataframe: pd.DataFrame,
    file_path: str,
    preferred_format: str | None = None,
) -> str:
    """Export DataFrame to CSV or Excel and return the normalized target path."""
    target = Path(file_path)
    normalized_preferred = str(preferred_format or "").strip().lower().lstrip(".")
    suffix = target.suffix.lower().lstrip(".")

    if suffix in {"xlsx", "xls"}:
        dataframe.to_excel(str(target), index=False)
        return str(target)

    if suffix == "csv":
        dataframe.to_csv(str(target), index=False)
        return str(target)

    if normalized_preferred in {"xlsx", "xls"}:
        target = target.with_suffix(".xlsx") if target.suffix else Path(f"{file_path}.xlsx")
        dataframe.to_excel(str(target), index=False)
        return str(target)

    target = target.with_suffix(".csv") if target.suffix else Path(f"{file_path}.csv")
    dataframe.to_csv(str(target), index=False)
    return str(target)


def export_selected_data_to_file(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    algorithm: str | None,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    file_path: str,
    preferred_format: str | None = None,
) -> str:
    """Build and export selected data to target file."""
    export_df = build_export_dataframe(
        selected_indices=selected_indices,
        df_global=df_global,
        algorithm=algorithm,
        embedding=embedding,
        embedding_type=embedding_type,
        active_subset_indices=active_subset_indices,
        pca_component_indices=pca_component_indices,
        algorithm_params=algorithm_params,
    )
    return export_dataframe_to_file(
        dataframe=export_df,
        file_path=file_path,
        preferred_format=preferred_format,
    )


def append_selected_data_to_excel(
    *,
    selected_indices: Iterable[int],
    df_global: pd.DataFrame,
    algorithm: str | None,
    embedding: Sequence[Sequence[float]] | None,
    embedding_type: str | None,
    active_subset_indices: Iterable[int] | None,
    pca_component_indices: Sequence[int] | None,
    algorithm_params: Mapping[str, object] | None,
    file_path: str,
    sheet_name: str,
) -> str:
    """Append selected data to an Excel sheet and return normalized path."""
    export_df = build_export_dataframe(
        selected_indices=selected_indices,
        df_global=df_global,
        algorithm=algorithm,
        embedding=embedding,
        embedding_type=embedding_type,
        active_subset_indices=active_subset_indices,
        pca_component_indices=pca_component_indices,
        algorithm_params=algorithm_params,
    )

    target = Path(file_path)
    if target.suffix.lower().lstrip(".") not in {"xlsx", "xls"}:
        target = target.with_suffix(".xlsx") if target.suffix else Path(f"{file_path}.xlsx")

    # Ensures openpyxl is available and surfaces a clear dependency error to UI layer.
    import openpyxl  # noqa: F401

    if target.exists():
        with pd.ExcelWriter(str(target), engine="openpyxl", mode="a", if_sheet_exists="new") as writer:
            export_df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        export_df.to_excel(str(target), sheet_name=sheet_name, index=False)

    return str(target)
