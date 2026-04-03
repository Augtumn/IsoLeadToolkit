"""Data loading and execution workflow for provenance ML dialog."""

import logging
import os

import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from core import app_state, state_gateway, translate

logger = logging.getLogger(__name__)


class ProvenanceMLWorkflowMixin:
    """Workflow and result actions for provenance ML dialog."""

    def _browse_training_file(self):
        file_types = ";;".join(
            [
                f"{translate('Excel files')} (*.xlsx *.xls)",
                f"{translate('CSV files')} (*.csv)",
                f"{translate('All files')} (*.*)",
            ]
        )

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            translate("Select Data File"),
            self.train_file_edit.text() or "",
            file_types,
        )

        if file_path:
            self.train_file_edit.setText(file_path)
            self._populate_training_sheets(file_path)
            self._load_training_data()

    def _populate_training_sheets(self, file_path: str):
        self.train_sheet_combo.blockSignals(True)
        self.train_sheet_combo.clear()

        if not file_path or not os.path.exists(file_path):
            self.train_sheet_combo.addItem(translate("No sheet"))
            self.train_sheet_combo.setEnabled(False)
            self.train_sheet_combo.blockSignals(False)
            return

        if file_path.lower().endswith(('.xlsx', '.xls', '.xlsm')):
            try:
                xls = pd.ExcelFile(file_path, engine='calamine')
            except Exception:
                xls = pd.ExcelFile(file_path)

            sheet_names = xls.sheet_names
            self.train_sheet_combo.addItems(sheet_names)
            self.train_sheet_combo.setEnabled(True)
            if 'Directly usable data' in sheet_names:
                self.train_sheet_combo.setCurrentText('Directly usable data')
        else:
            self.train_sheet_combo.addItem(translate("No sheet"))
            self.train_sheet_combo.setEnabled(False)

        self.train_sheet_combo.blockSignals(False)

    def _on_training_sheet_change(self, _index):
        if self.train_sheet_combo.isEnabled():
            self._load_training_data()

    def _read_training_file(self, file_path: str, sheet_name: str | None):
        if file_path.lower().endswith(('.xlsx', '.xls', '.xlsm')):
            try:
                return pd.read_excel(file_path, sheet_name=sheet_name, engine='calamine')
            except Exception:
                return pd.read_excel(file_path, sheet_name=sheet_name)
        return pd.read_csv(file_path)

    def _load_training_data(self):
        file_path = self.train_file_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, translate("Warning"), translate("Please select a file."))
            return
        if not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                translate("Warning"),
                translate("File not found: {path}").format(path=file_path),
            )
            return

        sheet_name = None
        if self.train_sheet_combo.isEnabled():
            sheet_name = self.train_sheet_combo.currentText()

        try:
            df = self._read_training_file(file_path, sheet_name)
            self._training_df = df
            self._update_training_columns(df)
            self.train_status_label.setText(
                translate("Training data loaded: {rows} rows, {cols} columns.").format(
                    rows=len(df), cols=len(df.columns)
                )
            )
        except Exception as exc:
            logger.error("Failed to load training data: %s", exc)
            self._training_df = None
            self.train_status_label.setText("")
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Training data load failed: {error}").format(error=str(exc)),
            )

    def _update_training_columns(self, df: pd.DataFrame):
        columns = df.columns.astype(str).tolist()

        self.train_region_combo.clear()
        self.train_region_combo.addItems(columns)

        self.train_206_combo.clear()
        self.train_206_combo.addItems(columns)

        self.train_207_combo.clear()
        self.train_207_combo.addItems(columns)

        self.train_208_combo.clear()
        self.train_208_combo.addItems(columns)

        self._auto_detect_region_column(columns)
        self._auto_detect_pb_columns(columns, self.train_206_combo, self.train_207_combo, self.train_208_combo)

    def _on_run_ml(self):
        if app_state.df_global is None:
            QMessageBox.warning(self, translate("Warning"), translate("Please load data first."))
            return

        if self._training_df is None:
            QMessageBox.warning(self, translate("Warning"), translate("Please load training data first."))
            return

        region_col = self.train_region_combo.currentText()
        train_cols = [
            self.train_206_combo.currentText(),
            self.train_207_combo.currentText(),
            self.train_208_combo.currentText(),
        ]

        if not region_col or not all(train_cols) or len(set(train_cols)) < 3:
            QMessageBox.warning(self, translate("Warning"), translate("Please select training columns."))
            return

        pred_cols = [
            self.pred_206_combo.currentText(),
            self.pred_207_combo.currentText(),
            self.pred_208_combo.currentText(),
        ]

        if not all(pred_cols) or len(set(pred_cols)) < 3:
            QMessageBox.warning(self, translate("Warning"), translate("Please select Pb columns for prediction."))
            return

        if self.radio_selected.isChecked() and app_state.selected_indices:
            selected = sorted(list(app_state.selected_indices))
            df_pred = app_state.df_global.iloc[selected].reset_index(drop=True)
            self._selected_original_indices = selected
        else:
            df_pred = app_state.df_global
            self._selected_original_indices = None

        params = state_gateway.get_ml_params() or self._ml_params
        xgb_params = params.get('xgb_params', {})
        smote_sampling_strategy = params.get('smote_sampling_strategy', 1.0)

        try:
            from ui.dialogs.progress_dialog import ProgressDialog

            progress = ProgressDialog(translate("Provenance ML"), translate("Loading Data"))
        except Exception:
            progress = None

        try:
            if progress:
                progress.update_message(translate("Preparing data..."))

            from data.provenance_ml import ProvenanceMLError, run_provenance_pipeline

            result = run_provenance_pipeline(
                training_df=self._training_df,
                region_col=region_col,
                feature_cols=train_cols,
                target_df=df_pred,
                target_feature_cols=pred_cols,
                min_region_samples=int(self.min_region_spin.value()),
                dbscan_min_region_samples=int(self.dbscan_min_region_spin.value()),
                dbscan_eps=float(self.eps_spin.value()),
                dbscan_min_samples_ratio=float(self.min_samples_ratio_spin.value()),
                standardize=bool(self.standardize_check.isChecked()),
                smote_enabled=bool(self.smote_check.isChecked()),
                smote_k_neighbors=int(self.smote_k_spin.value()),
                smote_sampling_strategy=smote_sampling_strategy,
                xgb_params=xgb_params,
                predict_threshold=float(self.threshold_spin.value()),
            )

            pred = result['predictions']
            valid_mask = pred['valid_mask']
            full_labels = np.full(len(df_pred), 'Unknown', dtype=object)
            full_probs = np.full(len(df_pred), np.nan, dtype=float)

            if pred['labels']:
                full_labels[valid_mask] = np.array(pred['labels'], dtype=object)
                full_probs[valid_mask] = np.array(pred['max_prob'], dtype=float)

            indices = (
                self._selected_original_indices
                if self._selected_original_indices is not None
                else list(range(len(df_pred)))
            )

            pred_df = pd.DataFrame(
                {
                    'Index': indices,
                    translate("Predicted Region"): full_labels,
                    translate("Predicted Probability"): full_probs,
                }
            )

            proba = pred.get('proba')
            label_order = pred.get('label_order', [])
            if proba is not None and len(label_order) > 0:
                for i, label in enumerate(label_order):
                    col = f"P({label})"
                    values = np.full(len(df_pred), np.nan, dtype=float)
                    if proba.size > 0:
                        values[valid_mask] = proba[:, i]
                    pred_df[col] = values

            result['prediction_df'] = pred_df
            result['full_labels'] = full_labels
            result['full_probs'] = full_probs
            result['prediction_count'] = int(len(df_pred))

            self._result = result
            state_gateway.set_ml_last_result(result)
            state_gateway.set_ml_last_model_meta(result.get('model_info'))

            self._display_results()
        except ProvenanceMLError as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("ML training failed: {error}").format(error=str(exc)),
            )
        except Exception as exc:
            logger.error("Provenance ML failed: %s", exc)
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("ML training failed: {error}").format(error=str(exc)),
            )
        finally:
            if progress:
                progress.close()

    def _display_results(self):
        if self._result is None:
            return

        stats = self._result['training']['stats']
        pred_count = self._result.get('prediction_count', 0)
        labels = self._result.get('full_labels', [])
        unique_labels = sorted(set(labels) - {'Unknown', 'None'}) if len(labels) else []

        summary = [
            translate("Training samples: {count}").format(count=stats.get('rows_final', 0)),
            translate("Training labels: {count}").format(count=stats.get('labels_final', 0)),
            translate("Outliers removed: {count}").format(count=stats.get('outliers_removed', 0)),
            translate("Regions dropped: {count}").format(count=len(stats.get('regions_dropped_small', []))),
            translate("Prediction samples: {count}").format(count=pred_count),
            translate("Predicted regions: {count}").format(count=len(unique_labels)),
        ]

        self.result_text.setPlainText("\n".join(summary))
        self.result_group.setVisible(True)
        self.apply_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

    def _on_apply_group_column(self):
        if self._result is None:
            QMessageBox.warning(self, translate("Warning"), translate("No ML results available."))
            return

        if app_state.df_global is None:
            QMessageBox.warning(self, translate("Warning"), translate("Please load data first."))
            return

        col_label = '_ML_Predicted_Region'
        col_prob = '_ML_Predicted_Prob'

        full_labels = np.full(len(app_state.df_global), 'Unknown', dtype=object)
        full_probs = np.full(len(app_state.df_global), np.nan, dtype=float)

        if self._selected_original_indices is not None:
            for i, orig_idx in enumerate(self._selected_original_indices):
                full_labels[orig_idx] = self._result['full_labels'][i]
                full_probs[orig_idx] = self._result['full_probs'][i]
        else:
            full_labels[:] = self._result['full_labels']
            full_probs[:] = self._result['full_probs']

        app_state.df_global[col_label] = full_labels
        app_state.df_global[col_prob] = full_probs

        if col_label not in app_state.group_cols:
            app_state.group_cols.append(col_label)

        state_gateway.set_last_group_col(col_label)
        state_gateway.set_visible_groups(None)

        if hasattr(app_state, '_notify_listeners'):
            app_state._notify_listeners()

        QMessageBox.information(
            self,
            translate("Success"),
            translate("Provenance results applied successfully."),
        )

    def _on_export_results(self):
        if self._result is None:
            QMessageBox.warning(self, translate("Warning"), translate("No ML results available."))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            translate("Export Results"),
            "",
            ";;".join(
                [
                    f"{translate('CSV files')} (*.csv)",
                    f"{translate('Excel files')} (*.xlsx)",
                    f"{translate('All files')} (*.*)",
                ]
            ),
        )

        if not file_path:
            return

        try:
            df = self._result.get('prediction_df')
            if df is None:
                raise ValueError("No prediction data to export.")

            if file_path.endswith('.xlsx'):
                df.to_excel(file_path, index=False)
            else:
                df.to_csv(file_path, index=False)

            QMessageBox.information(
                self,
                translate("Success"),
                translate("Results exported successfully to {file}").format(file=file_path),
            )
        except Exception as exc:
            QMessageBox.warning(
                self,
                translate("Error"),
                translate("Failed to export results: {error}").format(error=str(exc)),
            )
