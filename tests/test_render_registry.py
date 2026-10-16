"""The registry that says which adapter draws which mode."""
from __future__ import annotations

import pytest

from core.render_modes import RENDER_MODE_VALUES, asynchronous_modes
from visualization.plotting.rendering import registry
from visualization.plotting.rendering.context import build_context


class _Adapter:
    """A minimal adapter, enough for the registry to hold and for the protocol to accept."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.drawn: list[object] = []

    def validate(self, context) -> None:
        pass

    def token(self, context):
        return (self.mode,)

    def axes_dimensions(self, context):
        return 2

    def prepare(self, context):
        return {}

    def groups(self, context, prepared):
        return []

    def configure_axes(self, context, prepared) -> None:
        pass

    def draw(self, context, prepared):
        self.drawn.append(context)
        return None

    def marginal(self, context, prepared) -> None:
        pass

    def legend(self, context, prepared) -> None:
        pass

    def decorate(self, context, prepared) -> None:
        pass

    def finish(self, context, prepared) -> None:
        pass


@pytest.fixture(autouse=True)
def empty_registry():
    registry.clear()
    yield
    registry.clear()


def test_a_registered_adapter_is_found_by_its_mode() -> None:
    adapter = registry.register(_Adapter("2D"))
    assert registry.adapter_for("2D") is adapter
    assert registry.registered_modes() == ("2D",)
    assert isinstance(adapter, registry.ModeAdapter)


def test_a_mode_without_an_adapter_is_an_error_not_a_guess() -> None:
    """The dispatch used to hand anything it did not recognise to the embedding renderer."""
    with pytest.raises(registry.UnknownRenderMode) as raised:
        registry.adapter_for("2D")
    assert "2D" in str(raised.value)


def test_two_adapters_cannot_claim_the_same_mode() -> None:
    registry.register(_Adapter("2D"))
    with pytest.raises(registry.DuplicateAdapter):
        registry.register(_Adapter("2D"))


def test_an_adapter_cannot_claim_a_mode_that_is_not_offered() -> None:
    with pytest.raises(registry.NotARenderMode):
        registry.register(_Adapter("GHOST"))


def test_the_modes_still_to_move_are_the_ones_without_an_adapter() -> None:
    registry.register(_Adapter("2D"))
    registry.register(_Adapter("Ternary"))
    assert registry.unregistered_modes() == tuple(
        mode for mode in RENDER_MODE_VALUES if mode not in ("2D", "Ternary")
    )
    assert "UMAP" in registry.unregistered_modes()


def test_the_table_keeps_the_order_the_application_offers() -> None:
    for mode in reversed(RENDER_MODE_VALUES):
        registry.register(_Adapter(mode))
    assert registry.registered_modes() == RENDER_MODE_VALUES
    assert registry.unregistered_modes() == ()


def test_an_adapter_is_drawn_with_the_context_it_is_given() -> None:
    adapter = registry.register(_Adapter("2D"))
    context = build_context(
        "2D", group_col="Site", figure=object(), axes=object(), columns_2d=("x1", "x2")
    )
    registry.adapter_for("2D").draw(context, {})
    assert adapter.drawn == [context]
    assert context.capabilities.needs_columns == 2


def test_the_asynchronous_modes_are_not_special_cased_here() -> None:
    """Which modes compute in the background is a capability, not something the registry decides."""
    for mode in asynchronous_modes():
        registry.register(_Adapter(mode))
    assert set(registry.registered_modes()) == set(asynchronous_modes())
