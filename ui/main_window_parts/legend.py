"""Legend interaction and rendering mixin for main window."""

from .legend_actions import MainWindowLegendActionsMixin
from .legend_core import MainWindowLegendCoreMixin


class MainWindowLegendMixin(MainWindowLegendCoreMixin, MainWindowLegendActionsMixin):
    """Composed legend mixin for main window."""
    pass
