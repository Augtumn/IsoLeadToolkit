"""
Panel Export - Data export and management functionality
"""
import os
import re
from datetime import datetime
from tkinter import messagebox, simpledialog, filedialog

import pandas as pd
import numpy as np

from core import app_state, CONFIG

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

    def _export_plotnine_image(self):
        """Open an interactive plot export dialog (plotnine)."""
        try:
            from ui.dialogs.plot_export_dialog import PlotExportDialog
            PlotExportDialog(self.root)
        except Exception as exc:
            messagebox.showerror(
                self._translate("Export Plot"),
                self._translate("Unable to open export dialog: {error}", error=exc),
                parent=self.root
            )

    def _build_plotnine_export_data(self):
        """Prepare a DataFrame and column names for plotnine export."""
        df_source = app_state.df_global
        if df_source is None or df_source.empty:
            messagebox.showwarning(
                self._translate("Export Plot"),
                self._translate("No data is available to export."),
                parent=self.root
            )
            return None, None, None, None

        # Apply subset if active
        if app_state.active_subset_indices is not None:
            indices = sorted(list(app_state.active_subset_indices))
            df_plot = df_source.iloc[indices].copy()
        else:
            df_plot = df_source.copy()
            indices = None

        # Apply visible group filtering
        group_col = app_state.last_group_col if app_state.last_group_col in df_plot.columns else None
        if group_col and app_state.visible_groups:
            allowed = set(app_state.visible_groups)
            df_plot = df_plot[df_plot[group_col].isin(allowed)].copy()

        # Use embedding when available
        embedding = getattr(app_state, 'last_embedding', None)
        embedding_indices = None
        if embedding is not None and getattr(embedding, "shape", (0, 0))[1] >= 2:
            embed_rows = embedding.shape[0]
            if indices is not None:
                if embed_rows == len(indices):
                    embedding_indices = None
                elif embed_rows == len(df_source):
                    embedding_indices = np.asarray(indices)
                else:
                    messagebox.showwarning(
                        self._translate("Export Plot"),
                        self._translate("Embedding size does not match current data selection."),
                        parent=self.root
                    )
                    embedding = None
            else:
                if embed_rows == len(df_source):
                    embedding_indices = df_plot.index.to_numpy()
                elif embed_rows == len(df_plot):
                    embedding_indices = None
                else:
                    messagebox.showwarning(
                        self._translate("Export Plot"),
                        self._translate("Embedding size does not match current data selection."),
                        parent=self.root
                    )
                    embedding = None

        if embedding is not None and embedding.shape[1] >= 2:
            if embedding_indices is not None:
                try:
                    embedding = embedding[embedding_indices]
                except Exception:
                    messagebox.showwarning(
                        self._translate("Export Plot"),
                        self._translate("Embedding size does not match current data selection."),
                        parent=self.root
                    )
                    embedding = None

        if embedding is not None and embedding.shape[1] >= 2:
            df_plot["_plotnine_x"] = embedding[:, 0]
            df_plot["_plotnine_y"] = embedding[:, 1]
            x_col = "_plotnine_x"
            y_col = "_plotnine_y"
            plot_title = getattr(app_state, 'last_embedding_type', 'Embedding')

            if plot_title in ("PCA", "RobustPCA"):
                plot_title = "PCA"
            elif plot_title == "UMAP":
                plot_title = "UMAP"
            elif plot_title == "tSNE":
                plot_title = "t-SNE"
            elif plot_title == "V1V2":
                plot_title = "V1-V2"
            return df_plot, x_col, y_col, plot_title

        # Fallback: 2D scatter for selected columns
        if app_state.render_mode == '2D':
            cols = list(getattr(app_state, 'selected_2d_cols', []))
            if len(cols) == 2 and all(c in df_plot.columns for c in cols):
                return df_plot, cols[0], cols[1], "2D Scatter"

        # Fallback: Pb evolution axes if available
        pb206 = "206Pb/204Pb"
        if app_state.render_mode == 'PB_EVOL_76' and pb206 in df_plot.columns and "207Pb/204Pb" in df_plot.columns:
            return df_plot, pb206, "207Pb/204Pb", "Pb Evolution 206-207"
        if app_state.render_mode == 'PB_EVOL_86' and pb206 in df_plot.columns and "208Pb/204Pb" in df_plot.columns:
            return df_plot, pb206, "208Pb/204Pb", "Pb Evolution 206-208"

        messagebox.showwarning(
            self._translate("Export Plot"),
            self._translate("No compatible plot data found for export."),
            parent=self.root
        )
        return None, None, None, None

    def _get_plotnine_font_family(self):
        """Choose a font family that supports CJK if possible."""
        preferred = []
        cjk_font = getattr(app_state, 'custom_cjk_font', '').strip()
        primary_font = getattr(app_state, 'custom_primary_font', '').strip()
        if cjk_font:
            preferred.append(cjk_font)
        if primary_font:
            preferred.append(primary_font)
        preferred.extend(CONFIG.get('preferred_plot_fonts', []))

        try:
            from matplotlib import font_manager
            available = {f.name for f in font_manager.fontManager.ttflist}
            for name in preferred:
                if name in available:
                    return name
        except Exception:
            pass
        return 'sans-serif'

    def _plotnine_axis_labels(self, x_col, y_col):
        """Return axis labels based on current render mode."""
        mode = getattr(app_state, 'render_mode', '')
        embed_type = getattr(app_state, 'last_embedding_type', '')

        if embed_type in ('PCA', 'RobustPCA'):
            return "PC1", "PC2"
        if embed_type == 'UMAP':
            return "UMAP1", "UMAP2"
        if embed_type == 'tSNE':
            return "t-SNE1", "t-SNE2"
        if embed_type == 'V1V2':
            return "V1", "V2"

        if mode == 'PB_EVOL_76':
            return "206Pb/204Pb", "207Pb/204Pb"
        if mode == 'PB_EVOL_86':
            return "206Pb/204Pb", "208Pb/204Pb"

        return x_col, y_col

    def _add_plotnine_overlays(self, plot, df_plot, x_col, y_col):
        """Add overlay lines to plotnine export to match the UI plot."""
        mode = getattr(app_state, 'render_mode', '')
        if mode not in ('PB_EVOL_76', 'PB_EVOL_86'):
            return plot

        try:
            from data import geochemistry
            params = geochemistry.engine.get_parameters()
        except Exception:
            return plot

        try:
            import plotnine as p9
        except Exception:
            return plot

        # Determine x-range for overlays
        x_min = float(pd.to_numeric(df_plot[x_col], errors='coerce').min())
        x_max = float(pd.to_numeric(df_plot[x_col], errors='coerce').max())
        if not np.isfinite(x_min) or not np.isfinite(x_max):
            return plot
        x_vals = np.linspace(x_min, x_max, 200)

        l238 = params['lambda_238']
        l235 = params['lambda_235']
        l232 = params['lambda_232']
        T1 = params.get('Tsec', 0.0)
        if T1 <= 0:
            T1 = params.get('T2', params.get('T1', T1))
        X1 = params['a1']
        Y1 = params['b1']
        Z1 = params['c1']
        u_ratio = params['U_ratio']
        U8U5 = 1.0 / u_ratio if u_ratio else 137.88
        kappa = params.get('omega_M', 36.84) / params.get('mu_M', 9.74)

        # Model curves
        if getattr(app_state, 'show_model_curves', True):
            try:
                tsec = params.get('Tsec', 0.0)
                if tsec and tsec > 0:
                    t_max = tsec / 1e6
                    t1_override = tsec
                else:
                    t_max = params.get('T2', params.get('T1', 0.0)) / 1e6
                    t1_override = params.get('T2', params.get('T1', 0.0))
                t_vals = np.linspace(0, t_max, 200)
                curve = geochemistry.calculate_modelcurve(t_vals, params=params, T1=t1_override / 1e6 if t1_override else None)
                if mode == 'PB_EVOL_76':
                    y_vals = curve['Pb207_204']
                else:
                    y_vals = curve['Pb208_204']
                curve_df = pd.DataFrame({"x": curve['Pb206_204'], "y": y_vals})
                plot += p9.geom_path(
                    data=curve_df,
                    mapping=p9.aes(x="x", y="y"),
                    color="#1f2937",
                    size=float(getattr(app_state, 'model_curve_width', 1.2))
                )
            except Exception:
                pass

        # Paleoisochrons
        if getattr(app_state, 'show_paleoisochrons', True):
            ages = getattr(app_state, 'paleoisochron_ages', [3000, 2000, 1000, 0])
            line_rows = []
            label_rows = []
            for age in ages:
                t = float(age) * 1e6
                e8T = np.exp(l238 * T1)
                e8t = np.exp(l238 * t)
                if mode == 'PB_EVOL_76':
                    e5T = np.exp(l235 * T1)
                    e5t = np.exp(l235 * t)
                    slope = (e5T - e5t) / (U8U5 * (e8T - e8t))
                    intercept = Y1 - slope * X1
                else:
                    e2T = np.exp(l232 * T1)
                    e2t = np.exp(l232 * t)
                    slope = kappa * (e2T - e2t) / (e8T - e8t)
                    intercept = Z1 - slope * X1

                y_vals = slope * x_vals + intercept
                line_id = f"age_{int(age)}"
                for xv, yv in zip(x_vals, y_vals):
                    line_rows.append({"x": xv, "y": yv, "line_id": line_id})
                label_rows.append({
                    "x": x_vals[-1],
                    "y": y_vals[-1],
                    "label": f"{age:.0f} Ma"
                })

            line_df = pd.DataFrame(line_rows)
            label_df = pd.DataFrame(label_rows)

            if not line_df.empty:
                plot += p9.geom_path(
                    data=line_df,
                    mapping=p9.aes(x="x", y="y", group="line_id"),
                    linetype="dashed",
                    color="#94a3b8",
                    size=float(getattr(app_state, 'paleoisochron_width', 0.9))
                )
            if not label_df.empty:
                plot += p9.geom_text(
                    data=label_df,
                    mapping=p9.aes(x="x", y="y", label="label"),
                    color="#94a3b8",
                    size=7
                )

        # Model age lines
        if getattr(app_state, 'show_model_age_lines', True):
            try:
                col_206 = "206Pb/204Pb"
                col_207 = "207Pb/204Pb"
                col_208 = "208Pb/204Pb"
                pb206 = pd.to_numeric(df_plot[col_206], errors='coerce').values if col_206 in df_plot.columns else None
                pb207 = pd.to_numeric(df_plot[col_207], errors='coerce').values if col_207 in df_plot.columns else None
                pb208 = pd.to_numeric(df_plot[col_208], errors='coerce').values if col_208 in df_plot.columns else None

                if pb206 is None or pb207 is None:
                    return plot

                t_sk = geochemistry.calculate_two_stage_age(pb206, pb207, params=params)
                t_cdt = geochemistry.calculate_single_stage_age(pb206, pb207, params=params)
                if params.get('Tsec', 0.0) <= 0:
                    t_model = t_cdt
                    t1_override = params.get('T2', params.get('T1', None))
                else:
                    t_model = np.where(np.isfinite(t_sk), t_sk, t_cdt)
                    t1_override = params.get('Tsec', None)
                curve = geochemistry.calculate_modelcurve(t_model, params=params, T1=t1_override / 1e6 if t1_override else None)

                x_curve = np.asarray(curve['Pb206_204'])
                if mode == 'PB_EVOL_76':
                    y_curve = np.asarray(curve['Pb207_204'])
                    y_data = pb207
                else:
                    y_curve = np.asarray(curve['Pb208_204'])
                    y_data = pb208

                max_lines = 200
                idxs = np.arange(len(pb206))
                if len(idxs) > max_lines:
                    idxs = np.random.choice(idxs, size=max_lines, replace=False)

                seg_rows = []
                pt_rows = []
                for i in idxs:
                    if np.isnan(pb206[i]) or np.isnan(y_data[i]) or np.isnan(x_curve[i]) or np.isnan(y_curve[i]):
                        continue
                    seg_rows.append({"x": x_curve[i], "y": y_curve[i], "xend": pb206[i], "yend": y_data[i]})
                    pt_rows.append({"x": x_curve[i], "y": y_curve[i]})

                seg_df = pd.DataFrame(seg_rows)
                pt_df = pd.DataFrame(pt_rows)
                if not seg_df.empty:
                    plot += p9.geom_segment(
                        data=seg_df,
                        mapping=p9.aes(x="x", y="y", xend="xend", yend="yend"),
                        color="#cbd5f5",
                        size=float(getattr(app_state, 'model_age_line_width', 0.7)),
                        alpha=0.7
                    )
                if not pt_df.empty:
                    plot += p9.geom_point(
                        data=pt_df,
                        mapping=p9.aes(x="x", y="y"),
                        color="#475569",
                        size=1.2,
                        alpha=0.6
                    )
            except Exception:
                pass

        return plot

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
