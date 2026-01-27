"""
Panel Export - Data export and management functionality
"""
import os
import re
from datetime import datetime
from tkinter import messagebox, simpledialog, filedialog

import pandas as pd
import numpy as np

from core import app_state

try:
    from data.geochemistry import calculate_all_parameters
except ImportError:
    calculate_all_parameters = None


class PanelExportMixin:
    """Mixin providing data export and management methods for the ControlPanel"""

    def _build_export_parameters(self):
        """Build a flat table of export parameters."""
        rows = []

        def add_row(key, value):
            rows.append({'Parameter': key, 'Value': value})

        try:
            from data import geochemistry
            params = geochemistry.engine.get_parameters()
            for key, value in sorted(params.items()):
                add_row(key, value)
        except Exception:
            pass

        return pd.DataFrame(rows)

    def _get_selected_dataframe(self):
        """Return a DataFrame with the currently selected samples."""
        if not app_state.selected_indices:
            messagebox.showinfo(
                self._translate("Export Selected Data"),
                self._translate("Please select at least one sample before exporting."),
                parent=self.root
            )
            return None

        if app_state.df_global is None or app_state.df_global.empty:
            messagebox.showwarning(
                self._translate("Export Selected Data"),
                self._translate("No data is available to export."),
                parent=self.root
            )
            return None

        try:
            indices = sorted(app_state.selected_indices)
            df = app_state.df_global.iloc[indices].copy()
            
            # Attempt to calculate and append V1V2 parameters
            if calculate_all_parameters:
                all_cols = df.columns.tolist()
                # Exact matching for prescribed headers
                col_206 = "206Pb/204Pb" if "206Pb/204Pb" in all_cols else None
                col_207 = "207Pb/204Pb" if "207Pb/204Pb" in all_cols else None
                col_208 = "208Pb/204Pb" if "208Pb/204Pb" in all_cols else None
                lower_map = {col.lower(): col for col in all_cols}
                age_col = None
                for key in ("age", "age (ma)", "age(ma)", "age_ma", "t", "t (ma)", "t(ma)", "t_ma"):
                    if key in lower_map:
                        age_col = lower_map[key]
                        break
                
                if col_206 and col_207 and col_208:
                    try:
                        pb206 = pd.to_numeric(df[col_206], errors='coerce').values
                        pb207 = pd.to_numeric(df[col_207], errors='coerce').values
                        pb208 = pd.to_numeric(df[col_208], errors='coerce').values
                        t_ma = pd.to_numeric(df[age_col], errors='coerce').values if age_col else None
                        
                        # Get V1V2 parameters from state or engine
                        v1v2_params = getattr(app_state, 'v1v2_params', {})
                        scale = v1v2_params.get('scale', 1.0)
                        a = v1v2_params.get('a')
                        b = v1v2_params.get('b')
                        c = v1v2_params.get('c')

                        results = calculate_all_parameters(
                            pb206, pb207, pb208, 
                            calculate_ages=True,
                            a=a, b=b, c=c, scale=scale,
                            t_Ma=t_ma
                        )
                        
                        # Append new columns (core)
                        df['Delta_alpha'] = results['Delta_alpha']
                        df['Delta_beta'] = results['Delta_beta']
                        df['Delta_gamma'] = results['Delta_gamma']
                        df['V1'] = results['V1']
                        df['V2'] = results['V2']
                        df['tCDT (Ma)'] = results['tCDT (Ma)']
                        df['tSK (Ma)'] = results['tSK (Ma)']

                        # Export only parameters for the active geochemistry model
                        current_model = ""
                        try:
                            from data import geochemistry
                            current_model = getattr(geochemistry.engine, 'current_model_name', '')
                        except Exception:
                            current_model = ""

                        if "1st Stage" in current_model or current_model.endswith("(1st Stage)"):
                            df['mu_SK1'] = results.get('mu_SK', np.nan)
                            df['kappa_SK1'] = results.get('kappa_SK', np.nan)
                            df['omega_SK1'] = results.get('omega_SK', np.nan)
                        elif "2nd Stage" in current_model or current_model.endswith("(2nd Stage)"):
                            df['mu_SK2'] = results.get('mu_SK', np.nan)
                            df['kappa_SK2'] = results.get('kappa_SK', np.nan)
                            df['omega_SK2'] = results.get('omega_SK', np.nan)
                        else:
                            df['mu_singleStage'] = results.get('mu', np.nan)
                            df['nu_singleStage'] = results.get('nu', np.nan)
                            df['omega_singleStage'] = results.get('omega', np.nan)
                        
                        print("[INFO] Appended V1V2 parameters to export data.", flush=True)
                    except Exception as e:
                        print(f"[WARN] Failed to calculate V1V2 parameters for export: {e}", flush=True)

        except Exception as exc:
            messagebox.showerror(
                self._translate("Export Selected Data"),
                self._translate("Unable to extract selected samples: {error}", error=exc),
                parent=self.root
            )
            return None
        return df

    def _sanitize_filename(self, value):
        """Sanitize user-provided filename fragments for safe saving."""
        sanitized = re.sub(r'[\/\\:*?"<>|]+', '_', value)
        sanitized = sanitized.strip().strip('.')
        return sanitized

    def _export_selected_csv(self):
        """Export selected samples to a CSV file."""
        df = self._get_selected_dataframe()
        if df is None:
            return

        default_name = f"selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        name = simpledialog.askstring(
            self._translate("Export to CSV"),
            self._translate("Enter a file name (without extension):"),
            initialvalue=default_name,
            parent=self.root
        )
        if name is None:
            return

        name = name.strip()
        sanitized = self._sanitize_filename(name)
        if not sanitized:
            messagebox.showerror(
                self._translate("Export to CSV"),
                self._translate("File name cannot be empty or only invalid characters."),
                parent=self.root
            )
            return

        target_dir = os.path.dirname(app_state.file_path) if app_state.file_path else os.getcwd()
        if not target_dir:
            target_dir = os.getcwd()
        target_path = os.path.join(target_dir, f"{sanitized}.csv")

        if os.path.exists(target_path):
            overwrite = messagebox.askyesno(
                self._translate("Export to CSV"),
                self._translate("File already exists:\n{path}\nOverwrite?", path=target_path),
                parent=self.root
            )
            if not overwrite:
                return

        try:
            df.to_csv(target_path, index=False, encoding='utf-8-sig')
            params_df = self._build_export_parameters()
            params_path = os.path.join(target_dir, f"{sanitized}_params.csv")
            params_df.to_csv(params_path, index=False, encoding='utf-8-sig')
        except Exception as exc:
            messagebox.showerror(
                self._translate("Export to CSV"),
                self._translate("Export failed: {error}", error=exc),
                parent=self.root
            )
            return

        messagebox.showinfo(
            self._translate("Export to CSV"),
            self._translate("Exported {count} records to:\n{path}", count=len(df), path=target_path),
            parent=self.root
        )

    def _export_selected_excel(self):
        """Append selected samples to an Excel sheet."""
        df = self._get_selected_dataframe()
        if df is None:
            return

        if app_state.file_path and app_state.file_path.lower().endswith(('.xlsx', '.xlsm')):
            workbook_path = app_state.file_path
        else:
            workbook_path = filedialog.asksaveasfilename(
                parent=self.root,
                title=self._translate("Select target workbook"),
                defaultextension=".xlsx",
                filetypes=[(self._translate("Excel Workbook"), "*.xlsx")],
                initialfile="selected_data.xlsx"
            )
            if not workbook_path:
                return

        if not workbook_path.lower().endswith('.xlsx'):
            workbook_path = f"{workbook_path}.xlsx"

        sheet_default = f"Selected_{datetime.now().strftime('%Y%m%d_%H%M')}"
        sheet_name = simpledialog.askstring(
            self._translate("Append to Excel"),
            self._translate("Enter a new worksheet name:"),
            initialvalue=sheet_default,
            parent=self.root
        )
        if sheet_name is None:
            return

        sheet_name = sheet_name.strip()
        if not sheet_name:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name cannot be empty."),
                parent=self.root
            )
            return
        if len(sheet_name) > 31:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name cannot exceed 31 characters."),
                parent=self.root
            )
            return
        if any(ch in sheet_name for ch in '[]:*?/\\'):
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name contains invalid characters: []:*?/\\"),
                parent=self.root
            )
            return

        try:
            import openpyxl
        except ImportError:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("openpyxl is required to write Excel files. Please install openpyxl."),
                parent=self.root
            )
            return

        exists = os.path.exists(workbook_path)
        if exists:
            try:
                wb = openpyxl.load_workbook(workbook_path)
            except Exception as exc:
                messagebox.showerror(
                    self._translate("Append to Excel"),
                    self._translate("Unable to open target workbook: {error}", error=exc),
                    parent=self.root
                )
                return
            if sheet_name in wb.sheetnames:
                wb.close()
                messagebox.showerror(
                    self._translate("Append to Excel"),
                    self._translate("Worksheet already exists. Please choose another name."),
                    parent=self.root
                )
                return
            wb.close()

        try:
            if exists:
                with pd.ExcelWriter(workbook_path, mode='a', engine='openpyxl', if_sheet_exists='new') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    params_df = self._build_export_parameters()
                    params_df.to_excel(writer, sheet_name=f"{sheet_name}_params", index=False)
            else:
                # Try xlsxwriter for faster writing of new files
                try:
                    with pd.ExcelWriter(workbook_path, mode='w', engine='xlsxwriter') as writer:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        params_df = self._build_export_parameters()
                        params_df.to_excel(writer, sheet_name=f"{sheet_name}_params", index=False)
                except Exception:
                    print("[INFO] xlsxwriter not available, falling back to openpyxl", flush=True)
                    with pd.ExcelWriter(workbook_path, mode='w', engine='openpyxl') as writer:
                        df.to_excel(writer, sheet_name=sheet_name, index=False)
                        params_df = self._build_export_parameters()
                        params_df.to_excel(writer, sheet_name=f"{sheet_name}_params", index=False)
        except Exception as exc:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Failed to write Excel file: {error}", error=exc),
                parent=self.root
            )
            return

        messagebox.showinfo(
            self._translate("Append to Excel"),
            self._translate(
                "Appended {count} records to worksheet '{sheet}'.\nPath: {path}",
                count=len(df),
                sheet=sheet_name,
                path=workbook_path
            ),
            parent=self.root
        )

    def _reload_data(self):
        """Allow the user to pick a new dataset and refresh the UI."""
        try:
            from data import load_data
        except Exception as exc:
            messagebox.showerror(
                self._translate("Reload Data"),
                self._translate("Unable to reload data: {error}", error=exc),
                parent=self.root
            )
            return

        success = load_data(show_file_dialog=True, show_config_dialog=True)
        if not success:
            messagebox.showinfo(
                self._translate("Reload Data"),
                self._translate("Data reload cancelled."),
                parent=self.root
            )
            return
            
        self._update_data_count_label()

        if app_state.group_cols:
            if app_state.last_group_col not in app_state.group_cols:
                app_state.last_group_col = app_state.group_cols[0]
        else:
            app_state.last_group_col = None

        if 'group' in self.radio_vars:
            self.radio_vars['group'].set(app_state.last_group_col or '')

        app_state.visible_groups = None
        app_state.available_groups = []
        app_state.selected_2d_cols = []
        app_state.selected_3d_cols = []
        app_state.selected_2d_confirmed = False
        app_state.selected_3d_confirmed = False
        app_state.initial_render_done = False

        self._refresh_group_options()

        if self.callback:
            self.callback()

        self.update_selection_controls()

        messagebox.showinfo(
            self._translate("Reload Data"),
            self._translate("Dataset reloaded successfully."),
            parent=self.root
        )
    
    def _analyze_subset(self):
        """Set the active subset to the currently selected indices and re-run analysis."""
        if not app_state.selected_indices:
            messagebox.showinfo(
                self._translate("Analyze Subset"),
                self._translate("Please select samples first."),
                parent=self.root
            )
            return
        
        # Set the active subset
        app_state.active_subset_indices = sorted(list(app_state.selected_indices))
        
        # Clear cache to force re-calculation
        app_state.embedding_cache.clear()
        
        # Trigger update
        if self.callback:
            self.callback()
            
        messagebox.showinfo(
            self._translate("Analyze Subset"),
            self._translate("Analysis restricted to {count} selected samples.", count=len(app_state.active_subset_indices)),
            parent=self.root
        )

    def _reset_data(self):
        """Reset to full dataset."""
        if app_state.active_subset_indices is None:
            return

        app_state.active_subset_indices = None
        app_state.embedding_cache.clear()
        
        if self.callback:
            self.callback()
            
        messagebox.showinfo(
            self._translate("Reset Data"),
            self._translate("Analysis reset to full dataset."),
            parent=self.root
        )
