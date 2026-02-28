"""Overlay and geochemistry visualization state."""
from __future__ import annotations


class OverlayState:
    """Groups all overlay toggle, style, and label tracking fields."""

    def __init__(self):
        # Visibility toggles
        self.show_model_curves = True
        self.show_paleoisochrons = True
        self.show_plumbotectonics_curves = True
        self.show_model_age_lines = True
        self.show_isochrons = False
        self.show_growth_curves = True
        self.show_equation_overlays = False

        # Mu/Kappa age
        self.use_real_age_for_mu_kappa = False
        self.mu_kappa_age_col = None

        # Isochron label display options
        self.isochron_label_options = {
            'show_age': True,
            'show_mswd': False,
            'show_r_squared': False,
            'show_slope': False,
            'show_intercept': False,
            'show_n_points': True,
        }

        # Geochemistry model
        self.geo_model_name = "Stacey & Kramers (2nd Stage)"

        # Equation overlays
        self.equation_overlays: list[dict] = [
            {
                'id': 'eq_206_208',
                'label': 'y=1.0049x+20.259',
                'latex': r"y=1.0049x+20.259",
                'expression': '1.0049*x+20.259',
                'slope': 1.0049,
                'intercept': 20.259,
                'enabled': True,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85
            },
            {
                'id': 'eq_identity',
                'label': 'y=x',
                'latex': r"y=x",
                'expression': 'x',
                'slope': 1.0,
                'intercept': 0.0,
                'enabled': True,
                'color': '#ef4444',
                'linewidth': 1.0,
                'linestyle': '--',
                'alpha': 0.85
            }
        ]

        # Line styles for all overlay types
        self.line_styles: dict[str, dict] = {
            'model_curve': {
                'color': None,
                'linewidth': 1.2,
                'linestyle': '-',
                'alpha': 0.8
            },
            'plumbotectonics_curve': {
                'color': None,
                'linewidth': 1.2,
                'linestyle': '-',
                'alpha': 0.85
            },
            'growth_curve': {
                'color': None,
                'linewidth': 1.2,
                'linestyle': ':',
                'alpha': 0.6
            },
            'paleoisochron': {
                'color': '#94a3b8',
                'linewidth': 0.9,
                'linestyle': '--',
                'alpha': 0.85
            },
            'model_age_line': {
                'color': '#cbd5f5',
                'linewidth': 0.7,
                'linestyle': '-',
                'alpha': 0.7
            },
            'isochron': {
                'color': None,
                'linewidth': 1.5,
                'linestyle': '-',
                'alpha': 0.8
            },
            'selected_isochron': {
                'color': '#ef4444',
                'linewidth': 2.0,
                'linestyle': '-',
                'alpha': 0.9
            },
            'kde_curve': {
                'color': None,
                'linewidth': 1.0,
                'linestyle': '-',
                'alpha': 0.6,
                'fill': True,
                'levels': 10,
            },
            'marginal_kde_curve': {
                'color': None,
                'linewidth': 1.0,
                'linestyle': '-',
                'alpha': 0.25,
                'fill': True,
            }
        }

        # Paleoisochron configuration
        self.paleoisochron_min_age = 0
        self.paleoisochron_max_age = 3000
        self.paleoisochron_step = 1000
        self.paleoisochron_ages: list[int] = list(
            range(self.paleoisochron_max_age, self.paleoisochron_min_age - 1, -self.paleoisochron_step)
        )

        # Plumbotectonics
        self.plumbotectonics_variant = '0'
        self.model_curve_models = None  # None means all preset models

        # Isochron regression error configuration
        self.isochron_error_mode = 'fixed'  # 'fixed' or 'columns'
        self.isochron_sx_col = ''
        self.isochron_sy_col = ''
        self.isochron_rxy_col = ''
        self.isochron_sx_value = 0.001
        self.isochron_sy_value = 0.001
        self.isochron_rxy_value = 0.0
        self.selected_isochron_data = None
        self.isochron_results: dict = {}

        # Line width shortcuts (kept for backward compat with display panel)
        self.model_curve_width = 1.2
        self.plumbotectonics_curve_width = 1.2
        self.paleoisochron_width = 0.9
        self.model_age_line_width = 0.7
        self.isochron_line_width = 1.5

        # Runtime artist tracking (not persisted)
        self.overlay_artists: dict[str, list] = {}
        self.overlay_curve_label_data: list[dict] = []
        self.paleoisochron_label_data: list[dict] = []
        self.plumbotectonics_label_data: list[dict] = []
        self.plumbotectonics_isoage_label_data: list[dict] = []

    def _init_equation_styles(self):
        """Ensure each equation overlay has a style entry in line_styles."""
        for overlay in self.equation_overlays:
            style_key = overlay.get('style_key')
            if not style_key:
                overlay_id = (overlay.get('id') or overlay.get('expression')
                              or overlay.get('label') or 'equation')
                style_key = f"equation:{overlay_id}"
                overlay['style_key'] = style_key
            self.line_styles.setdefault(style_key, {
                'color': overlay.get('color', '#ef4444'),
                'linewidth': overlay.get('linewidth', 1.0),
                'linestyle': overlay.get('linestyle', '--'),
                'alpha': overlay.get('alpha', 0.85),
            })

    def clear_artists(self):
        """Reset runtime artist tracking state."""
        self.overlay_artists = {}
        self.overlay_curve_label_data = []
        self.paleoisochron_label_data = []
        self.plumbotectonics_label_data = []
        self.plumbotectonics_isoage_label_data = []
