"""What one render needs, gathered once and read-only.

A renderer used to read the application's globals field by field, from wherever in its body the value
happened to be needed, and so did the helpers it called. That made "what does this render depend on?"
unanswerable without reading the whole call tree, and it made the same value get read twice with two
different answers.

A :class:`RenderContext` is built once, before a render starts, and handed to the mode's adapter. It
holds only what a render needs and nothing that can be written. The fields are passed in rather than
read here, on purpose: the pipeline is the one place that reads the application's state, so the count
of places that poke at a single global figure or axes goes down as adapters replace renderers, never up.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.render_modes import ModeCapabilities, capabilities_for


@dataclass(frozen=True)
class RenderContext:
    """Everything one render needs, and nothing it may change."""

    #: The mode being drawn, as the state spells it.
    mode: str
    #: The column the samples are grouped by.
    group_col: str
    #: The figure and axes this render draws into.
    figure: Any
    axes: Any

    #: What this mode needs, from the one table in ``core.render_modes``.
    capabilities: ModeCapabilities = field(default_factory=ModeCapabilities)

    #: The columns the user selected, per plot family.
    columns_2d: tuple[str, ...] = ()
    columns_3d: tuple[str, ...] = ()
    columns_ternary: tuple[str, ...] = ()

    #: Values the renderers read while drawing.
    point_size: int = 60
    show_kde: bool = False
    show_marginal_kde: bool = False
    legend_columns: int = 1

    #: The parameters the embedding algorithms are computed with, and a precomputed embedding when a
    #: worker has already produced one.
    umap_params: Any = None
    tsne_params: Any = None
    pca_params: Any = None
    robust_pca_params: Any = None
    precomputed_embedding: Any = None
    precomputed_meta: Any = None

    #: Set when the user is looking at a subset of the data.
    subset_indices: Any = None

    def __post_init__(self) -> None:
        # The capabilities of a context are the capabilities of its mode; a caller that passes them
        # cannot pass the wrong ones.
        if self.capabilities != capabilities_for(self.mode):
            object.__setattr__(self, "capabilities", capabilities_for(self.mode))

    @property
    def projection(self) -> str:
        """Which axes this render needs."""
        return self.capabilities.projection

    def with_axes(self, axes: Any) -> RenderContext:
        """The same context drawing into *axes*.

        The sequence ensures the axes before it draws, and ensuring them may create one; the render
        then draws into the axes that exists, not the one that was there when it started.
        """
        if axes is self.axes:
            return self
        from dataclasses import replace

        return replace(self, axes=axes)

    @property
    def is_subset(self) -> bool:
        return self.subset_indices is not None

    def token(self, *extra: Any) -> tuple[Any, ...]:
        """What identifies the content of this render, for deciding whether a view still applies.

        The mode, what this render's plot is made of (*extra*, which the adapter supplies), the
        columns the user selected, and whether it is a subset - a different one of those is a
        different picture, and the user's zoom belongs to the picture they zoomed.
        """
        return (
            str(self.mode),
            tuple(str(value) for value in extra),
            tuple(self.columns_2d),
            tuple(self.columns_3d),
            tuple(self.columns_ternary),
            str(self.subset_indices) if self.is_subset else "",
        )


def build_context(
    mode: str,
    *,
    group_col: str,
    figure: Any,
    axes: Any,
    columns_2d: Any = (),
    columns_3d: Any = (),
    columns_ternary: Any = (),
    point_size: int = 60,
    show_kde: bool = False,
    show_marginal_kde: bool = False,
    legend_columns: int = 1,
    umap_params: Any = None,
    tsne_params: Any = None,
    pca_params: Any = None,
    robust_pca_params: Any = None,
    precomputed_embedding: Any = None,
    precomputed_meta: Any = None,
    subset_indices: Any = None,
) -> RenderContext:
    """Assemble the context for one render of *mode*."""
    return RenderContext(
        mode=str(mode),
        group_col=str(group_col or ""),
        figure=figure,
        axes=axes,
        capabilities=capabilities_for(mode),
        columns_2d=tuple(str(column) for column in (columns_2d or ())),
        columns_3d=tuple(str(column) for column in (columns_3d or ())),
        columns_ternary=tuple(str(column) for column in (columns_ternary or ())),
        point_size=int(point_size),
        show_kde=bool(show_kde),
        show_marginal_kde=bool(show_marginal_kde),
        legend_columns=int(legend_columns),
        umap_params=umap_params,
        tsne_params=tsne_params,
        pca_params=pca_params,
        robust_pca_params=robust_pca_params,
        precomputed_embedding=precomputed_embedding,
        precomputed_meta=precomputed_meta,
        subset_indices=subset_indices,
    )
