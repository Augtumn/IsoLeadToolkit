import tkinter as tk
from tkinter import ttk, messagebox, filedialog

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from core import app_state, CONFIG
from core.localization import translate


class PlotExportDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title(translate("Export Plot Settings"))
        self.top.geometry("980x720")
        self.top.minsize(900, 640)

        try:
            import plotnine as _p9
            self._p9 = _p9
        except Exception as exc:
            message = ttk.Label(
                self.top,
                text=translate("Plotnine is not available: {error}", error=exc),
                style='Body.TLabel'
            )
            message.pack(expand=True, padx=20, pady=20)
            return

        self.df_source = app_state.df_global
        if self.df_source is None or self.df_source.empty:
            message = ttk.Label(
                self.top,
                text=translate("No data is available to export."),
                style='Body.TLabel'
            )
            message.pack(expand=True, padx=20, pady=20)
            return

        self.current_plot = None
        self.current_fig = None
        self.canvas = None

        self._init_vars()
        self._build_layout()

    def _init_vars(self):
        default_title = getattr(app_state, 'last_embedding_type', 'Plot')
        x_default, y_default = self._plotnine_axis_labels("", "")
        self._default_axis_labels = (x_default or "", y_default or "")

        self.title_var = tk.StringVar(value=default_title)
        self.x_label_var = tk.StringVar(value=self._default_axis_labels[0])
        self.y_label_var = tk.StringVar(value=self._default_axis_labels[1])

        self.point_size_var = tk.DoubleVar(value=1.6)
        self.point_alpha_var = tk.DoubleVar(value=0.85)

        fig_w, fig_h = getattr(app_state, 'plot_figsize', (7, 5))
        self.fig_w_var = tk.DoubleVar(value=float(fig_w))
        self.fig_h_var = tk.DoubleVar(value=float(fig_h))
        self.dpi_var = tk.IntVar(value=int(getattr(app_state, 'plot_dpi', 130)))

        font_sizes = getattr(app_state, 'plot_font_sizes', {})
        self.font_title_var = tk.IntVar(value=int(font_sizes.get('title', 14)))
        self.font_label_var = tk.IntVar(value=int(font_sizes.get('label', 12)))
        self.font_tick_var = tk.IntVar(value=int(font_sizes.get('tick', 10)))
        self.font_legend_var = tk.IntVar(value=int(font_sizes.get('legend', 10)))

        self.palette_var = tk.StringVar(value="Default")

        self.show_model_curves_var = tk.BooleanVar(value=getattr(app_state, 'show_model_curves', True))
        self.show_paleoisochrons_var = tk.BooleanVar(value=getattr(app_state, 'show_paleoisochrons', True))
        self.show_model_age_lines_var = tk.BooleanVar(value=getattr(app_state, 'show_model_age_lines', True))
        self.show_isochron_fits_var = tk.BooleanVar(value=getattr(app_state, 'show_isochrons', True))

    def _build_layout(self):
        outer = ttk.Frame(self.top, padding=12)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        controls = ttk.LabelFrame(outer, text=translate("Plot Controls"), padding=12)
        controls.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 10))
        controls.columnconfigure(5, weight=1)

        ttk.Label(controls, text=translate("Title")).grid(row=0, column=0, sticky="w")
        ttk.Entry(controls, textvariable=self.title_var, width=28).grid(row=0, column=1, sticky="w", padx=(6, 16))

        ttk.Label(controls, text=translate("X Label")).grid(row=0, column=2, sticky="w")
        ttk.Entry(controls, textvariable=self.x_label_var, width=20).grid(row=0, column=3, sticky="w", padx=(6, 16))

        ttk.Label(controls, text=translate("Y Label")).grid(row=0, column=4, sticky="w")
        ttk.Entry(controls, textvariable=self.y_label_var, width=20).grid(row=0, column=5, sticky="w")

        ttk.Label(controls, text=translate("Point Size")).grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=0.5, to=6.0, orient=tk.HORIZONTAL, variable=self.point_size_var).grid(row=1, column=1, sticky="ew", padx=(6, 16), pady=(8, 0))

        ttk.Label(controls, text=translate("Point Alpha")).grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Scale(controls, from_=0.1, to=1.0, orient=tk.HORIZONTAL, variable=self.point_alpha_var).grid(row=1, column=3, sticky="ew", padx=(6, 16), pady=(8, 0))

        ttk.Label(controls, text=translate("Palette")).grid(row=1, column=4, sticky="w", pady=(8, 0))
        palette_combo = ttk.Combobox(
            controls,
            textvariable=self.palette_var,
            values=["Default", "Set2", "Set1", "Set3", "Dark2", "Paired", "Pastel1", "Pastel2"],
            state="readonly",
            width=18
        )
        palette_combo.grid(row=1, column=5, sticky="w", pady=(8, 0))

        ttk.Label(controls, text=translate("Figure Width")).grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.fig_w_var, width=6).grid(row=2, column=1, sticky="w", padx=(6, 16), pady=(8, 0))

        ttk.Label(controls, text=translate("Figure Height")).grid(row=2, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.fig_h_var, width=6).grid(row=2, column=3, sticky="w", padx=(6, 16), pady=(8, 0))

        ttk.Label(controls, text=translate("DPI")).grid(row=2, column=4, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.dpi_var, width=6).grid(row=2, column=5, sticky="w", pady=(8, 0))

        font_section = ttk.LabelFrame(outer, text=translate("Font Sizes"), padding=10)
        font_section.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 10))
        font_section.columnconfigure(7, weight=1)

        ttk.Label(font_section, text=translate("Title Size")).grid(row=0, column=0, sticky="w")
        ttk.Entry(font_section, textvariable=self.font_title_var, width=6).grid(row=0, column=1, sticky="w", padx=(6, 16))

        ttk.Label(font_section, text=translate("Label Size")).grid(row=0, column=2, sticky="w")
        ttk.Entry(font_section, textvariable=self.font_label_var, width=6).grid(row=0, column=3, sticky="w", padx=(6, 16))

        ttk.Label(font_section, text=translate("Tick Size")).grid(row=0, column=4, sticky="w")
        ttk.Entry(font_section, textvariable=self.font_tick_var, width=6).grid(row=0, column=5, sticky="w", padx=(6, 16))

        ttk.Label(font_section, text=translate("Legend Size")).grid(row=0, column=6, sticky="w")
        ttk.Entry(font_section, textvariable=self.font_legend_var, width=6).grid(row=0, column=7, sticky="w")

        overlay_section = ttk.LabelFrame(outer, text=translate("Overlays"), padding=10)
        overlay_section.grid(row=2, column=0, sticky="ew", padx=4, pady=(0, 10))

        ttk.Checkbutton(overlay_section, text=translate("Show Model Curves"), variable=self.show_model_curves_var).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(overlay_section, text=translate("Show Paleoisochrons"), variable=self.show_paleoisochrons_var).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(overlay_section, text=translate("Show Model Age Lines"), variable=self.show_model_age_lines_var).pack(side=tk.LEFT, padx=(0, 16))
        ttk.Checkbutton(overlay_section, text=translate("Show Isochron Fits"), variable=self.show_isochron_fits_var).pack(side=tk.LEFT)

        button_row = ttk.Frame(outer)
        button_row.grid(row=3, column=0, sticky="ew", padx=4, pady=(0, 8))

        ttk.Button(button_row, text=translate("Preview"), style='Secondary.TButton', command=self._render_preview).pack(side=tk.LEFT)
        ttk.Button(button_row, text=translate("Export Plot"), style='Accent.TButton', command=self._export_plot).pack(side=tk.LEFT, padx=(10, 0))

        preview_frame = ttk.Frame(outer)
        preview_frame.grid(row=4, column=0, sticky="nsew")
        outer.rowconfigure(4, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        preview_frame.columnconfigure(0, weight=1)

        self.preview_container = preview_frame

    def _render_preview(self):
        plot = self._build_plot()
        if plot is None:
            return
        fig = plot.draw()

        if self.canvas:
            self.canvas.get_tk_widget().destroy()
        if self.current_fig:
            try:
                plt.close(self.current_fig)
            except Exception:
                pass
        self.current_fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.preview_container)
        self.canvas.draw()
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        self.current_plot = plot

    def _export_plot(self):
        plot = self.current_plot or self._build_plot()
        if plot is None:
            return

        target_path = filedialog.asksaveasfilename(
            parent=self.top,
            title=translate("Export Plot"),
            defaultextension=".png",
            filetypes=[
                (translate("PNG Image"), "*.png"),
                (translate("PDF Document"), "*.pdf"),
                (translate("SVG Image"), "*.svg")
            ],
            initialfile="plotnine_export.png"
        )
        if not target_path:
            return

        try:
            plot.save(target_path, dpi=float(self.dpi_var.get()))
        except Exception as exc:
            messagebox.showerror(translate("Export Plot"), translate("Export failed: {error}", error=exc), parent=self.top)
            return

        messagebox.showinfo(translate("Export Plot"), translate("Plot exported to:\n{path}", path=target_path), parent=self.top)

    def _build_plot(self):
        df_plot, x_col, y_col, plot_title = self._build_plotnine_export_data()
        if df_plot is None:
            return None

        group_col = app_state.last_group_col if app_state.last_group_col in df_plot.columns else None
        self._maybe_update_axis_labels(*self._plotnine_axis_labels(x_col, y_col))
        p9 = self._p9
        mapping = p9.aes(x=x_col, y=y_col)
        if group_col:
            mapping = p9.aes(x=x_col, y=y_col, color=group_col)

        fig_size = (float(self.fig_w_var.get()), float(self.fig_h_var.get()))
        font_family = self._get_plotnine_font_family()

        p = (
            p9.ggplot(df_plot, mapping)
            + p9.geom_point(size=float(self.point_size_var.get()), alpha=float(self.point_alpha_var.get()))
            + p9.theme_bw()
            + p9.theme(
                figure_size=fig_size,
                text=p9.element_text(family=font_family, size=int(self.font_label_var.get())),
                axis_title_x=p9.element_text(size=int(self.font_label_var.get())),
                axis_title_y=p9.element_text(size=int(self.font_label_var.get())),
                axis_text_x=p9.element_text(size=int(self.font_tick_var.get())),
                axis_text_y=p9.element_text(size=int(self.font_tick_var.get())),
                legend_text=p9.element_text(size=int(self.font_legend_var.get())),
                legend_title=p9.element_text(size=int(self.font_legend_var.get())),
                plot_title=p9.element_text(size=int(self.font_title_var.get()))
            )
            + p9.labs(
                x=self.x_label_var.get(),
                y=self.y_label_var.get(),
                title=self.title_var.get() or plot_title
            )
        )

        if group_col and self.palette_var.get() != "Default":
            p += p9.scale_color_brewer(type='qual', palette=self.palette_var.get())

        p = self._add_plotnine_overlays(p, df_plot, x_col, y_col, group_col)
        return p

    def _build_plotnine_export_data(self):
        df_source = self.df_source
        if df_source is None or df_source.empty:
            messagebox.showwarning(translate("Export Plot"), translate("No data is available to export."), parent=self.top)
            return None, None, None, None

        if app_state.active_subset_indices is not None:
            indices = sorted(list(app_state.active_subset_indices))
            df_plot = df_source.iloc[indices].copy()
        else:
            df_plot = df_source.copy()
            indices = None

        group_col = app_state.last_group_col if app_state.last_group_col in df_plot.columns else None
        if group_col and app_state.visible_groups:
            allowed = set(app_state.visible_groups)
            df_plot = df_plot[df_plot[group_col].isin(allowed)].copy()

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
                        translate("Export Plot"),
                        translate("Embedding size does not match current data selection."),
                        parent=self.top
                    )
                    embedding = None
            else:
                if embed_rows == len(df_source):
                    embedding_indices = df_plot.index.to_numpy()
                elif embed_rows == len(df_plot):
                    embedding_indices = None
                else:
                    messagebox.showwarning(
                        translate("Export Plot"),
                        translate("Embedding size does not match current data selection."),
                        parent=self.top
                    )
                    embedding = None

        if embedding is not None and embedding.shape[1] >= 2:
            if embedding_indices is not None:
                try:
                    embedding = embedding[embedding_indices]
                except Exception:
                    messagebox.showwarning(
                        translate("Export Plot"),
                        translate("Embedding size does not match current data selection."),
                        parent=self.top
                    )
                    embedding = None

        if embedding is not None and embedding.shape[1] >= 2:
            df_plot["_plotnine_x"] = embedding[:, 0]
            df_plot["_plotnine_y"] = embedding[:, 1]
            x_col = "_plotnine_x"
            y_col = "_plotnine_y"
            plot_title = getattr(app_state, 'last_embedding_type', 'Embedding')
            return df_plot, x_col, y_col, plot_title

        if app_state.render_mode == '2D':
            cols = list(getattr(app_state, 'selected_2d_cols', []))
            if len(cols) == 2 and all(c in df_plot.columns for c in cols):
                return df_plot, cols[0], cols[1], "2D Scatter"

        pb206 = "206Pb/204Pb"
        if app_state.render_mode == 'PB_EVOL_76' and pb206 in df_plot.columns and "207Pb/204Pb" in df_plot.columns:
            return df_plot, pb206, "207Pb/204Pb", "Pb Evolution 206-207"
        if app_state.render_mode == 'PB_EVOL_86' and pb206 in df_plot.columns and "208Pb/204Pb" in df_plot.columns:
            return df_plot, pb206, "208Pb/204Pb", "Pb Evolution 206-208"

        messagebox.showwarning(translate("Export Plot"), translate("No compatible plot data found for export."), parent=self.top)
        return None, None, None, None

    def _get_plotnine_font_family(self):
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

    def _plotnine_axis_labels(self, _x_col, _y_col):
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

        return _x_col, _y_col

    def _maybe_update_axis_labels(self, x_label, y_label):
        current_x = self.x_label_var.get()
        current_y = self.y_label_var.get()
        default_x, default_y = self._default_axis_labels
        if not current_x or current_x == default_x:
            self.x_label_var.set(x_label or "")
        if not current_y or current_y == default_y:
            self.y_label_var.set(y_label or "")
        self._default_axis_labels = (x_label or "", y_label or "")

    def _add_plotnine_overlays(self, plot, df_plot, x_col, y_col, group_col):
        mode = getattr(app_state, 'render_mode', '')
        if mode not in ('PB_EVOL_76', 'PB_EVOL_86'):
            return plot

        try:
            from data import geochemistry
            params = geochemistry.engine.get_parameters()
        except Exception:
            return plot

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

        p9 = self._p9
        if self.show_model_curves_var.get():
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

        if self.show_paleoisochrons_var.get():
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
                label_rows.append({"x": x_vals[-1], "y": y_vals[-1], "label": f"{age:.0f} Ma"})

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

        if self.show_isochron_fits_var.get():
            if group_col and group_col in df_plot.columns:
                groups = df_plot[group_col].fillna('Unknown').astype(str).unique()
            else:
                groups = ['All Data']
                df_plot['_iso_group'] = 'All Data'
                group_col = '_iso_group'

            line_rows = []
            for grp in groups:
                subset = df_plot[df_plot[group_col] == grp]
                x_vals_g = pd.to_numeric(subset[x_col], errors='coerce').values
                y_vals_g = pd.to_numeric(subset[y_col], errors='coerce').values
                valid = np.isfinite(x_vals_g) & np.isfinite(y_vals_g)
                x_vals_g = x_vals_g[valid]
                y_vals_g = y_vals_g[valid]
                if len(x_vals_g) < 2:
                    continue
                slope, intercept = np.polyfit(x_vals_g, y_vals_g, 1)
                x_line = np.linspace(np.min(x_vals_g), np.max(x_vals_g), 50)
                y_line = slope * x_line + intercept
                for xv, yv in zip(x_line, y_line):
                    line_rows.append({"x": xv, "y": yv, "group": grp})

            line_df = pd.DataFrame(line_rows)
            if not line_df.empty:
                if group_col and group_col in df_plot.columns:
                    plot += p9.geom_line(
                        data=line_df,
                        mapping=p9.aes(x="x", y="y", color="group"),
                        linetype="dotted",
                        size=float(getattr(app_state, 'isochron_line_width', 1.0)),
                        alpha=0.9
                    )
                else:
                    plot += p9.geom_line(
                        data=line_df,
                        mapping=p9.aes(x="x", y="y"),
                        linetype="dotted",
                        color="#475569",
                        size=float(getattr(app_state, 'isochron_line_width', 1.0)),
                        alpha=0.9
                    )

        if self.show_model_age_lines_var.get():
            try:
                pb206 = pd.to_numeric(df_plot["206Pb/204Pb"], errors='coerce').values
                pb207 = pd.to_numeric(df_plot["207Pb/204Pb"], errors='coerce').values
                pb208 = pd.to_numeric(df_plot["208Pb/204Pb"], errors='coerce').values

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
