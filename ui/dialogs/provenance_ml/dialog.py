"""Provenance ML dialog base state and initialization."""

from pathlib import Path

from core import CONFIG, state_gateway


class ProvenanceMLDialogBaseMixin:
    """Base initialization helpers for provenance ML dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self._tr("Provenance ML"))
        self.setMinimumWidth(760)
        self.setMinimumHeight(700)

        self._training_df = None
        self._result = None
        self._selected_original_indices = None
        self._ml_params = state_gateway.get_ml_params() or CONFIG.get('ml_params', {}).copy()
        self._default_training_file = self._resolve_default_training_file()

        self._setup_ui()
        self._refresh_prediction_columns()

        if self._default_training_file:
            self.train_file_edit.setText(self._default_training_file)
            self._populate_training_sheets(self._default_training_file)
            self._load_training_data()

    def _resolve_default_training_file(self):
        base_dir = Path(__file__).resolve().parents[3]
        default_path = base_dir / 'reference' / '18343221' / 'Database - ore lead signatures.xlsx'
        return str(default_path) if default_path.exists() else ''

    def _tr(self, text: str) -> str:
        """Small indirection to keep base mixin UI-framework agnostic."""
        from core import translate

        return translate(text)
