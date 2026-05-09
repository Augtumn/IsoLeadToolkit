"""Analysis panel build mixin."""
from __future__ import annotations

from PyQt5.QtCore import Qt

_CONFIDENCE_LEVEL_1SIGMA: float = 0.68
_CONFIDENCE_LEVEL_2SIGMA: float = 0.95
_CONFIDENCE_LEVEL_3SIGMA: float = 0.99
_CONFIDENCE_EPSILON: float = 0.01
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QToolBox,
    QVBoxLayout,
    QWidget,
)

from core import app_state, translate
from ui.icons import apply_color_swatch


class AnalysisPanelBuildMixin:
    """Build UI widgets for the analysis tab."""

    def reset_state(self):
        super().reset_state()
        self.tools_kde_check = None
        self.tools_marginal_kde_check = None
        self.tools_equation_overlays_check = None
        self.equation_overlays_container = None
        self.equation_overlays_layout = None
        self.selection_button = None
        self.ellipse_selection_button = None
        self.lasso_selection_button = None
        self.selection_status_label = None
        self.mixing_group_name_edit = None
        self.mixing_status_label = None
        self.confidence_68_radio = None
        self.confidence_95_radio = None
        self.confidence_99_radio = None
        self.tooltip_check = None

    def build(self) -> QWidget:
        widget = self._build_analysis_section()
        self._is_initialized = True
        return widget

    def _update_status_panel(self):
        """Status panel is owned by the main control panel; no-op here."""
        return

    def _sync_toggle_widgets(self, checked, *widgets):
        """Sync toggle widgets to the same checked state."""
        for widget in widgets:
            if widget is None:
                continue
            if widget.isChecked() != checked:
                widget.blockSignals(True)
                widget.setChecked(checked)
                widget.blockSignals(False)

    def _build_analysis_section(self):
        """Build analysis section widgets."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        section_toolbox = QToolBox()
        section_toolbox.setObjectName('analysis_section_toolbox')

        def _add_group_page(group_widget: QGroupBox, title_key: str) -> None:
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.setContentsMargins(6, 6, 6, 6)
            page_layout.setSpacing(8)
            page_layout.addWidget(group_widget)
            page_layout.addStretch()
            section_toolbox.addItem(page, translate(title_key))

        kde_group = QGroupBox(translate("Kernel Density"))
        kde_group.setProperty('translate_key', 'Kernel Density')
        kde_layout = QVBoxLayout()

        kde_row = QHBoxLayout()
        self.tools_kde_check = QCheckBox(translate("Show Kernel Density"))
        self.tools_kde_check.setProperty('translate_key', 'Show Kernel Density')
        self.tools_kde_check.setChecked(getattr(app_state, 'show_kde', False))
        self.tools_kde_check.stateChanged.connect(self._on_kde_change)
        kde_row.addWidget(self.tools_kde_check)

        kde_swatch = QLabel()
        kde_swatch.setFixedSize(16, 16)
        apply_color_swatch(kde_swatch, '#e2e8f0')
        kde_swatch.setProperty("keepStyle", True)
        kde_swatch.mousePressEvent = lambda event, s=kde_swatch: self._open_kde_style_dialog('kde', s)
        kde_row.addWidget(kde_swatch)
        kde_row.addStretch()
        kde_layout.addLayout(kde_row)

        mkde_row = QHBoxLayout()
        self.tools_marginal_kde_check = QCheckBox(translate("Show Marginal KDE"))
        self.tools_marginal_kde_check.setProperty('translate_key', 'Show Marginal KDE')
        self.tools_marginal_kde_check.setChecked(getattr(app_state, 'show_marginal_kde', False))
        self.tools_marginal_kde_check.stateChanged.connect(self._on_marginal_kde_change)
        mkde_row.addWidget(self.tools_marginal_kde_check)

        mkde_swatch = QLabel()
        mkde_swatch.setFixedSize(16, 16)
        apply_color_swatch(mkde_swatch, '#e2e8f0')
        mkde_swatch.setProperty("keepStyle", True)
        mkde_swatch.mousePressEvent = lambda event, s=mkde_swatch: self._open_kde_style_dialog('marginal_kde', s)
        mkde_row.addWidget(mkde_swatch)
        mkde_row.addStretch()
        kde_layout.addLayout(mkde_row)

        kde_group.setLayout(kde_layout)
        _add_group_page(kde_group, 'Kernel Density')

        equation_group = QGroupBox(translate("Equation Overlays"))
        equation_group.setProperty('translate_key', 'Equation Overlays')
        equation_layout = QVBoxLayout()

        equation_hint = QLabel(translate("Manage equations and visibility."))
        equation_hint.setProperty('translate_key', 'Manage equations and visibility.')
        equation_hint.setWordWrap(True)
        equation_layout.addWidget(equation_hint)

        add_eq_btn = QPushButton(translate("Add Equation"))
        add_eq_btn.setProperty('translate_key', 'Add Equation')
        add_eq_btn.clicked.connect(self._open_add_equation_dialog)
        equation_layout.addWidget(add_eq_btn)

        equation_group.setLayout(equation_layout)
        _add_group_page(equation_group, 'Equation Overlays')

        selection_group = QGroupBox(translate("Selection Tools"))
        selection_group.setProperty('translate_key', 'Selection Tools')
        selection_layout = QVBoxLayout()

        self.selection_button = QPushButton(translate("Enable Selection"))
        self.selection_button.setProperty('translate_key', 'Enable Selection')
        self.selection_button.setCheckable(True)
        self.selection_button.setFixedWidth(200)
        self.selection_button.clicked.connect(self._on_toggle_selection)
        selection_layout.addWidget(self.selection_button, 0, Qt.AlignHCenter)

        self.lasso_selection_button = QPushButton(translate("Custom Shape"))
        self.lasso_selection_button.setProperty('translate_key', 'Custom Shape')
        self.lasso_selection_button.setCheckable(True)
        self.lasso_selection_button.setFixedWidth(200)
        self.lasso_selection_button.clicked.connect(self._on_toggle_lasso_selection)
        selection_layout.addWidget(self.lasso_selection_button, 0, Qt.AlignHCenter)

        self.selection_status_label = QLabel(translate("Selected Samples: {count}").format(count=0))
        selection_layout.addWidget(self.selection_status_label)

        selection_group.setLayout(selection_layout)
        _add_group_page(selection_group, 'Selection Tools')

        analysis_group = QGroupBox(translate("Data Analysis"))
        analysis_group.setProperty('translate_key', 'Data Analysis')
        analysis_layout = QVBoxLayout()

        corr_btn = QPushButton(translate("Correlation Heatmap"))
        corr_btn.setProperty('translate_key', 'Correlation Heatmap')
        corr_btn.setFixedWidth(200)
        corr_btn.clicked.connect(self._on_show_correlation_heatmap)
        analysis_layout.addWidget(corr_btn, 0, Qt.AlignHCenter)

        axis_corr_btn = QPushButton(translate("Show Axis Corr."))
        axis_corr_btn.setProperty('translate_key', 'Show Axis Corr.')
        axis_corr_btn.setFixedWidth(200)
        axis_corr_btn.clicked.connect(self._on_show_axis_correlation)
        analysis_layout.addWidget(axis_corr_btn, 0, Qt.AlignHCenter)

        shepard_btn = QPushButton(translate("Show Shepard Plot"))
        shepard_btn.setProperty('translate_key', 'Show Shepard Plot')
        shepard_btn.setFixedWidth(200)
        shepard_btn.clicked.connect(self._on_show_shepard_diagram)
        analysis_layout.addWidget(shepard_btn, 0, Qt.AlignHCenter)

        analysis_group.setLayout(analysis_layout)
        _add_group_page(analysis_group, 'Data Analysis')

        subset_group = QGroupBox(translate("Subset Analysis"))
        subset_group.setProperty('translate_key', 'Subset Analysis')
        subset_layout = QVBoxLayout()

        analyze_btn = QPushButton(translate("Analyze Subset"))
        analyze_btn.setProperty('translate_key', 'Analyze Subset')
        analyze_btn.setFixedWidth(200)
        analyze_btn.clicked.connect(self._on_analyze_subset)
        subset_layout.addWidget(analyze_btn, 0, Qt.AlignHCenter)

        reset_btn = QPushButton(translate("Reset Data"))
        reset_btn.setProperty('translate_key', 'Reset Data')
        reset_btn.setFixedWidth(200)
        reset_btn.clicked.connect(self._on_reset_data)
        subset_layout.addWidget(reset_btn, 0, Qt.AlignHCenter)

        subset_group.setLayout(subset_layout)
        _add_group_page(subset_group, 'Subset Analysis')

        mixing_group = QGroupBox(translate("Mixing Groups"))
        mixing_group.setProperty('translate_key', 'Mixing Groups')
        mixing_layout = QVBoxLayout()

        group_name_layout = QHBoxLayout()
        group_name_label = QLabel(translate("Group Name:"))
        group_name_label.setProperty('translate_key', 'Group Name:')
        group_name_layout.addWidget(group_name_label)
        self.mixing_group_name_edit = QLineEdit()
        self.mixing_group_name_edit.setPlaceholderText(translate("Enter group name"))
        group_name_layout.addWidget(self.mixing_group_name_edit)
        mixing_layout.addLayout(group_name_layout)

        mixing_btn_layout = QHBoxLayout()

        endmember_btn = QPushButton(translate("Set as Endmember"))
        endmember_btn.setProperty('translate_key', 'Set as Endmember')
        endmember_btn.setFixedWidth(170)
        endmember_btn.clicked.connect(self._on_set_endmember)
        mixing_btn_layout.addWidget(endmember_btn)

        mixture_btn = QPushButton(translate("Set as Mixture"))
        mixture_btn.setProperty('translate_key', 'Set as Mixture')
        mixture_btn.setFixedWidth(170)
        mixture_btn.clicked.connect(self._on_set_mixture)
        mixing_btn_layout.addWidget(mixture_btn)

        mixing_layout.addLayout(mixing_btn_layout)

        self.mixing_status_label = QLabel(translate("No mixing groups defined"))
        self.mixing_status_label.setWordWrap(True)
        mixing_layout.addWidget(self.mixing_status_label)

        mixing_action_layout = QHBoxLayout()

        clear_mixing_btn = QPushButton(translate("Clear Mixing Groups"))
        clear_mixing_btn.setProperty('translate_key', 'Clear Mixing Groups')
        clear_mixing_btn.setFixedWidth(170)
        clear_mixing_btn.clicked.connect(self._on_clear_mixing_groups)
        mixing_action_layout.addWidget(clear_mixing_btn)

        compute_mixing_btn = QPushButton(translate("Compute Mixing"))
        compute_mixing_btn.setProperty('translate_key', 'Compute Mixing')
        compute_mixing_btn.setFixedWidth(170)
        compute_mixing_btn.clicked.connect(self._on_compute_mixing)
        mixing_action_layout.addWidget(compute_mixing_btn)

        mixing_layout.addLayout(mixing_action_layout)

        mixing_group.setLayout(mixing_layout)
        _add_group_page(mixing_group, 'Mixing Groups')

        endmember_group = QGroupBox(translate("Endmember Identification"))
        endmember_group.setProperty('translate_key', 'Endmember Identification')
        endmember_layout = QVBoxLayout()

        endmember_hint = QLabel(translate("Identify lead isotope endmembers using PCA."))
        endmember_hint.setProperty('translate_key', 'Identify lead isotope endmembers using PCA.')
        endmember_hint.setWordWrap(True)
        endmember_layout.addWidget(endmember_hint)

        endmember_btn = QPushButton(translate("Run Endmember Analysis"))
        endmember_btn.setProperty('translate_key', 'Run Endmember Analysis')
        endmember_btn.setFixedWidth(200)
        endmember_btn.clicked.connect(self._on_run_endmember_analysis)
        endmember_layout.addWidget(endmember_btn, 0, Qt.AlignHCenter)

        endmember_group.setLayout(endmember_layout)
        _add_group_page(endmember_group, 'Endmember Identification')

        clustering_group = QGroupBox(translate("HDBSCAN Clustering"))
        clustering_group.setProperty('translate_key', 'HDBSCAN Clustering')
        clustering_layout = QVBoxLayout()

        cluster_hint = QLabel(
            translate("Cluster the current embedding (UMAP, t-SNE, PCA, etc.) using HDBSCAN.")
        )
        cluster_hint.setProperty(
            'translate_key',
            'Cluster the current embedding (UMAP, t-SNE, PCA, etc.) using HDBSCAN.',
        )
        cluster_hint.setWordWrap(True)
        clustering_layout.addWidget(cluster_hint)

        cluster_btn = QPushButton(translate("Run HDBSCAN Clustering"))
        cluster_btn.setProperty('translate_key', 'Run HDBSCAN Clustering')
        cluster_btn.setFixedWidth(200)
        cluster_btn.clicked.connect(self._on_run_clustering)
        clustering_layout.addWidget(cluster_btn, 0, Qt.AlignHCenter)

        clustering_group.setLayout(clustering_layout)
        _add_group_page(clustering_group, 'HDBSCAN Clustering')

        provenance_group = QGroupBox(translate("Provenance ML"))
        provenance_group.setProperty('translate_key', 'Provenance ML')
        provenance_layout = QVBoxLayout()

        provenance_hint = QLabel(translate("Run ML provenance classification using DBSCAN, SMOTE and XGBoost."))
        provenance_hint.setProperty('translate_key', 'Run ML provenance classification using DBSCAN, SMOTE and XGBoost.')
        provenance_hint.setWordWrap(True)
        provenance_layout.addWidget(provenance_hint)

        provenance_btn = QPushButton(translate("Run Provenance ML"))
        provenance_btn.setProperty('translate_key', 'Run Provenance ML')
        provenance_btn.setFixedWidth(200)
        provenance_btn.clicked.connect(self._on_run_provenance_ml)
        provenance_layout.addWidget(provenance_btn, 0, Qt.AlignHCenter)

        provenance_group.setLayout(provenance_layout)
        _add_group_page(provenance_group, 'Provenance ML')

        confidence_group = QGroupBox(translate("Confidence Ellipse"))
        confidence_group.setProperty('translate_key', 'Confidence Ellipse')
        confidence_layout = QVBoxLayout()

        self.ellipse_selection_button = QPushButton(translate("Draw Ellipse"))
        self.ellipse_selection_button.setProperty('translate_key', 'Draw Ellipse')
        self.ellipse_selection_button.setCheckable(True)
        self.ellipse_selection_button.setFixedWidth(200)
        self.ellipse_selection_button.clicked.connect(self._on_toggle_ellipse_selection)
        confidence_layout.addWidget(self.ellipse_selection_button, 0, Qt.AlignHCenter)

        self.confidence_68_radio = QRadioButton(translate("68% (1σ)"))
        self.confidence_68_radio.setProperty('translate_key', '68% (1σ)')
        self.confidence_95_radio = QRadioButton(translate("95% (2σ)"))
        self.confidence_95_radio.setProperty('translate_key', '95% (2σ)')
        self.confidence_99_radio = QRadioButton(translate("99% (3σ)"))
        self.confidence_99_radio.setProperty('translate_key', '99% (3σ)')

        current_level = getattr(app_state, 'confidence_level', _CONFIDENCE_LEVEL_2SIGMA)
        if abs(current_level - _CONFIDENCE_LEVEL_1SIGMA) < _CONFIDENCE_EPSILON:
            self.confidence_68_radio.setChecked(True)
        elif abs(current_level - _CONFIDENCE_LEVEL_3SIGMA) < _CONFIDENCE_EPSILON:
            self.confidence_99_radio.setChecked(True)
        else:
            self.confidence_95_radio.setChecked(True)

        self.confidence_68_radio.toggled.connect(lambda: self._on_confidence_change(_CONFIDENCE_LEVEL_1SIGMA))
        self.confidence_95_radio.toggled.connect(lambda: self._on_confidence_change(_CONFIDENCE_LEVEL_2SIGMA))
        self.confidence_99_radio.toggled.connect(lambda: self._on_confidence_change(_CONFIDENCE_LEVEL_3SIGMA))

        confidence_layout.addWidget(self.confidence_68_radio)
        confidence_layout.addWidget(self.confidence_95_radio)
        confidence_layout.addWidget(self.confidence_99_radio)

        confidence_group.setLayout(confidence_layout)
        _add_group_page(confidence_group, 'Confidence Ellipse')

        layout.addWidget(section_toolbox)
        layout.addStretch()
        return widget