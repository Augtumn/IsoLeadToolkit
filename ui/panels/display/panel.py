"""Display panel mixin composition."""

from .build import DisplayBuildMixin
from .themes import DisplayThemeMixin


class DisplayPanelMixin(DisplayBuildMixin, DisplayThemeMixin):
    """显示标签页"""

