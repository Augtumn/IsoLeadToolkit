"""Legend panel mixin composition."""

from .actions import LegendActionsMixin
from .build import LegendBuildMixin


class LegendPanelMixin(LegendBuildMixin, LegendActionsMixin):
    """图例标签页"""

