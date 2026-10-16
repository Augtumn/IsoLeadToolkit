"""The 2D scatter mode, on the shared render sequence.

Only the parts that make a 2D scatter a 2D scatter live here. The axes are ensured, the view is
restored, the plot state is cleared and the style is applied by the pipeline, so this adapter cannot
forget them - which is what the sequence is for.
"""
from __future__ import annotations

import logging
from typing import Any

from ..context import RenderContext
from ..pipeline import Ink
from ..registry import Adapter, register

logger = logging.getLogger(__name__)


class TwoDAdapter(Adapter):
    """A 2D scatter plot of two selected columns."""

    mode = "2D"

    def validate(self, context: RenderContext) -> None:
        from ..raw.plot2d import _df_global, _validate_2d_inputs

        if _validate_2d_inputs(list(context.columns_2d), _df_global()) is None:
            raise ValueError("the 2D columns are not usable")

    def token(self, context: RenderContext) -> tuple[Any, ...]:
        return ("2D", tuple(context.columns_2d))

    def axes_dimensions(self, context: RenderContext) -> Any:
        return 2

    def prepare(self, context: RenderContext) -> Any:
        from ..raw.plot2d import _df_global, _prepare_2d_dataframe

        prepared = _prepare_2d_dataframe(
            context.group_col, list(context.columns_2d), _df_global()
        )
        return prepared if prepared is not None else False

    def groups(self, context: RenderContext, prepared: Any) -> list[Any]:
        return _categories(context, prepared)

    def configure_axes(self, context: RenderContext, prepared: Any) -> None:
        try:
            context.axes.set_aspect("auto")
            context.axes.set_autoscale_on(True)
        except Exception as err:
            logger.warning("Could not configure the 2D axes: %s", err)

    def draw(self, context: RenderContext, prepared: Any) -> Ink:
        from ..raw.plot2d import _render_2d_kde, _render_2d_scatter_groups

        columns = list(context.columns_2d)
        categories = _categories(context, prepared)
        if context.show_kde:
            _render_2d_kde(prepared, context.group_col, columns)
            return Ink.DRAWN

        # The helper registers the collections it creates in the plot state itself.
        scatters = _render_2d_scatter_groups(
            prepared, context.group_col, columns, categories, context.point_size
        )
        if not scatters:
            if len(prepared) == 0:
                # Every group the user keeps visible is absent from this projection: the empty frame
                # stays, and with it the mode and the legend selection.
                return Ink.EMPTY
            logger.error("No points were plotted in 2D")
            return Ink.FAILED
        return Ink.DRAWN

    def marginal(self, context: RenderContext, prepared: Any) -> None:
        from ... import kde as kde_utils
        from ..raw.plot2d import _render_2d_marginal_kde

        kde_utils.clear_marginal_axes()
        if context.show_marginal_kde:
            _render_2d_marginal_kde(
                prepared,
                context.group_col,
                _categories(context, prepared),
                list(context.columns_2d),
            )

    def legend(self, context: RenderContext, prepared: Any) -> None:
        from core import app_state

        from ..raw.plot2d import _render_2d_legend

        # The collections the scatter helper registered in the plot state, as the renderer read them.
        _render_2d_legend(
            context.axes,
            context.group_col,
            _categories(context, prepared),
            list(app_state.scatter_collections),
            context.show_kde,
            context.show_marginal_kde,
        )

    def decorate(self, context: RenderContext, prepared: Any) -> None:
        from ..raw.plot2d import _draw_2d_title_and_labels

        subset_info = " (Subset)" if context.is_subset else ""
        _draw_2d_title_and_labels(context.group_col, list(context.columns_2d), subset_info)

    def finish(self, context: RenderContext, prepared: Any) -> None:
        from ..raw.plot2d import _attach_annotation, _notify_legend_panel

        if len(prepared) == 0:
            # Tell the legend panel anyway: its checkboxes have to match the selection that produced
            # this empty frame.
            _notify_legend_panel(context.group_col, [], [])
            _attach_annotation()
            return
        _attach_annotation()


def _categories(context: RenderContext, prepared: Any) -> list[Any]:
    """The groups present in *prepared*, in the order the legend shows them."""
    try:
        return sorted(prepared[context.group_col].unique())
    except Exception as err:
        logger.warning("Could not read the 2D categories: %s", err)
        return []


def register_two_d() -> TwoDAdapter:
    """Put the 2D adapter in the registry."""
    return register(TwoDAdapter())  # type: ignore[return-value]
