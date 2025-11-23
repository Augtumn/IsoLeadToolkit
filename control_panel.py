"""
Control Panel - Interactive Parameter Adjustment
Tkinter-based control panel for UMAP/t-SNE parameters and visualization settings
"""
import os
import re
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, simpledialog, filedialog

import pandas as pd

from state import app_state
import state as state_module
from events import toggle_selection_mode


class ControlPanel:
    """Interactive control panel for algorithm parameters"""
    
    def __init__(self, callback):
        """
        Initialize control panel
        
        Args:
            callback: function to call when parameters change
        """
        self.callback = callback

        # Reuse Matplotlib's Tk root when available so the panel shares the
        # same event loop and remains responsive while plt.show() runs.
        master = tk._default_root
        self._owns_master = False
        if master is None:
            master = tk.Tk()
            master.withdraw()
            self._owns_master = True

        self.master = master
        self.root = tk.Toplevel(master)
        self.root.title("Control Panel")
        self.root.geometry("520x820")
        self.root.minsize(420, 620)
        self.root.resizable(True, True)
        self.root.configure(bg="#edf2f7")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.is_visible = True

        self.primary_bg = "#edf2f7"
        self.card_bg = "#ffffff"
        self.style = None
        self._setup_styles()
        
        # Store slider references
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self._slider_after = {}
        self._slider_steps = {}
        self._slider_delay_ms = 350

        self.selection_button = None
        self.selection_status = None
        self.export_csv_button = None
        self.export_excel_button = None
        
        self._create_widgets()

        # Try to raise the panel so it is not hidden behind the figure window.
        try:
            if master is not None:
                self.root.transient(master)
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass
    
    def _create_widgets(self):
        """Create GUI widgets with improved styling"""
        self.root.columnconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding=(18, 18, 18, 14), style='ControlPanel.TFrame')
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(container, text="Visualization Controls", style='Header.TLabel')
        header.pack(anchor=tk.W)

        subtitle = ttk.Label(
            container,
            text="Fine-tune algorithm settings and instantly preview the updated embedding.",
            style='Subheader.TLabel',
            wraplength=440,
            justify=tk.LEFT
        )
        subtitle.pack(anchor=tk.W, pady=(4, 14))

        canvas_frame = ttk.Frame(container, style='ControlPanel.TFrame')
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6))

        main_canvas = tk.Canvas(
            canvas_frame,
            highlightthickness=0,
            bd=0,
            background=self.primary_bg
        )
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollable_frame = ttk.Frame(main_canvas, style='ControlPanel.TFrame')
        canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        main_canvas.bind(
            "<Configure>",
            lambda e: main_canvas.itemconfigure(canvas_window, width=e.width)
        )

        main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.config(command=main_canvas.yview)

        # ========== Algorithm & Dimensionality Selection ==========
        if not getattr(app_state, 'render_mode', None):
            app_state.render_mode = getattr(app_state, 'algorithm', 'UMAP')
        self.radio_vars['render_mode'] = tk.StringVar(value=app_state.render_mode)

        algo_section = self._create_section(
            scrollable_frame,
            "Projection Mode",
            "Select between UMAP or t-SNE embeddings, or display raw measurements in either 2D or 3D space."
        )

        selection_grid = ttk.Frame(algo_section, style='CardBody.TFrame')
        selection_grid.pack(fill=tk.X, pady=(4, 0))

        options = [
            ("UMAP Embedding", "UMAP"),
            ("t-SNE Embedding", "tSNE"),
            ("2D Scatter (raw)", "2D"),
            ("3D Scatter (raw)", "3D"),
        ]

        for idx, (label, value) in enumerate(options):
            column = idx // 2
            row = idx % 2
            cell = ttk.Frame(selection_grid, style='CardBody.TFrame')
            cell.grid(row=row, column=column, sticky=tk.W, padx=(0 if column == 0 else 16, 0), pady=2)
            ttk.Radiobutton(
                cell,
                text=label,
                variable=self.radio_vars['render_mode'],
                value=value,
                command=self._on_change,
                style='Option.TRadiobutton'
            ).pack(anchor=tk.W)

        for col in range(2):
            selection_grid.columnconfigure(col, weight=1)

        # ========== UMAP Parameters ==========
        umap_section = self._create_section(
            scrollable_frame,
            "UMAP Parameters",
            "Control neighbourhood size and how tightly points cluster."
        )

        self._add_slider(
            umap_section,
            key='umap_n',
            label_text="n_neighbors",
            minimum=2,
            maximum=50,
            initial=app_state.umap_params['n_neighbors'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            umap_section,
            key='umap_d',
            label_text="min_dist",
            minimum=0.0,
            maximum=1.0,
            initial=app_state.umap_params['min_dist'],
            formatter=lambda v: f"{float(v):.2f}",
            step=0.01
        )

        self._add_slider(
            umap_section,
            key='umap_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.umap_params['random_state'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        # ========== t-SNE Parameters ==========
        tsne_section = self._create_section(
            scrollable_frame,
            "t-SNE Parameters",
            "Adjust perplexity and learning rate to refine t-SNE embeddings."
        )

        self._add_slider(
            tsne_section,
            key='tsne_p',
            label_text="perplexity",
            minimum=5,
            maximum=100,
            initial=app_state.tsne_params['perplexity'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            tsne_section,
            key='tsne_lr',
            label_text="learning_rate",
            minimum=10,
            maximum=1000,
            initial=app_state.tsne_params['learning_rate'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        # ========== Common Parameters ==========
        common_section = self._create_section(
            scrollable_frame,
            "Common Settings",
            "Options shared by both algorithms, including point styling and grouping."
        )

        self._add_slider(
            common_section,
            key='size',
            label_text="Point size",
            minimum=10,
            maximum=200,
            initial=app_state.point_size,
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        group_label = ttk.Label(
            common_section,
            text="Group column",
            style='FieldLabel.TLabel'
        )
        group_label.pack(anchor=tk.W, pady=(12, 4))

        self.radio_vars['group'] = tk.StringVar(value=app_state.last_group_col or '')

        group_container = ttk.Frame(common_section, style='CardBody.TFrame')
        group_container.pack(fill=tk.X)
        self.group_container = group_container
        self.group_placeholder = None

        if app_state.group_cols:
            for col in app_state.group_cols:
                ttk.Radiobutton(
                    group_container,
                    text=col,
                    variable=self.radio_vars['group'],
                    value=col,
                    command=self._on_change,
                    style='Option.TRadiobutton'
                ).pack(anchor=tk.W, pady=2)
        else:
            placeholder = ttk.Label(
                group_container,
                text="Load data to unlock grouping options.",
                style='BodyMuted.TLabel',
                wraplength=400,
                justify=tk.LEFT
            )
            placeholder.pack(anchor=tk.W, pady=4)
            self.group_placeholder = placeholder

        legend_tools = ttk.Frame(common_section, style='CardBody.TFrame')
        legend_tools.pack(fill=tk.X, pady=(12, 0))

        ttk.Button(
            legend_tools,
            text="Filter legend...",
            style='Secondary.TButton',
            command=self._open_legend_filter
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(
            legend_tools,
            text="Reload data...",
            style='Secondary.TButton',
            command=self._reload_data
        ).pack(side=tk.LEFT)

        selection_section = self._create_section(
            scrollable_frame,
            "数据选择",
            "开启数据选择模式后，在二维或嵌入视图中双击或框选样本，然后在此导出结果。"
        )

        selection_row = ttk.Frame(selection_section, style='CardBody.TFrame')
        selection_row.pack(fill=tk.X, pady=(0, 6))

        self.selection_button = ttk.Button(
            selection_row,
            text="进入数据选择",
            style='Secondary.TButton',
            command=self._on_toggle_selection
        )
        self.selection_button.pack(side=tk.LEFT)

        self.selection_status = ttk.Label(
            selection_row,
            text="当前选中: 0",
            style='BodyMuted.TLabel'
        )
        self.selection_status.pack(side=tk.LEFT, padx=(12, 0))

        export_row = ttk.Frame(selection_section, style='CardBody.TFrame')
        export_row.pack(fill=tk.X)

        self.export_csv_button = ttk.Button(
            export_row,
            text="导出 CSV...",
            style='Secondary.TButton',
            command=self._export_selected_csv
        )
        self.export_csv_button.pack(side=tk.LEFT, padx=(0, 12))

        self.export_excel_button = ttk.Button(
            export_row,
            text="追加 Excel Sheet...",
            style='Secondary.TButton',
            command=self._export_selected_excel
        )
        self.export_excel_button.pack(side=tk.LEFT)

        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL, style='SectionSeparator.TSeparator').pack(fill=tk.X, pady=12)

        footer_note = ttk.Label(
            container,
            text="Adjust sliders to refresh the plot automatically. Close the panel to reclaim screen space.",
            style='Footer.TLabel',
            wraplength=440,
            justify=tk.LEFT
        )
        footer_note.pack(anchor=tk.W, pady=(12, 8))

        action_frame = ttk.Frame(container, style='ControlPanel.TFrame')
        action_frame.pack(fill=tk.X)

        ttk.Button(
            action_frame,
            text="Close Panel",
            style='Accent.TButton',
            command=self._on_close
        ).pack(side=tk.RIGHT, padx=(0, 4))

        self.update_selection_controls()

    def _setup_styles(self):
        """Configure ttk styles for a polished appearance"""
        self.style = ttk.Style(self.master)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

        primary = self.primary_bg
        card = self.card_bg

        self.style.configure('ControlPanel.TFrame', background=primary)
        self.style.configure('Header.TLabel', background=primary, foreground='#1a202c', font=('Segoe UI', 16, 'bold'))
        self.style.configure('Subheader.TLabel', background=primary, foreground='#4a5568', font=('Segoe UI', 10))
        self.style.configure('Footer.TLabel', background=primary, foreground='#4a5568', font=('Segoe UI', 9))
        self.style.configure('SectionSeparator.TSeparator', background='#cbd5f5', lightcolor='#cbd5f5', darkcolor='#cbd5f5')

        self.style.configure('Card.TLabelframe', background=card, borderwidth=1, relief='solid')
        self.style.configure('Card.TLabelframe.Label', background=card, foreground='#1a202c', font=('Segoe UI', 12, 'bold'))
        self.style.configure('CardBody.TFrame', background=card)
        self.style.configure('Body.TLabel', background=card, foreground='#4a5568', font=('Segoe UI', 10))
        self.style.configure('BodyMuted.TLabel', background=card, foreground='#94a3b8', font=('Segoe UI', 10))
        self.style.configure('FieldLabel.TLabel', background=card, foreground='#1a202c', font=('Segoe UI', 10, 'bold'))
        self.style.configure('ValueLabel.TLabel', background=card, foreground='#2d3748', font=('Segoe UI', 10, 'bold'))

        self.style.configure('Option.TRadiobutton', background=card, foreground='#1a202c', padding=4, font=('Segoe UI', 10))
        self.style.map('Option.TRadiobutton', background=[('active', card)], foreground=[('active', '#1a202c')])

        self.style.configure('Accent.TButton', background='#2563eb', foreground='#ffffff', font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')], foreground=[('disabled', '#d1d5db'), ('active', '#ffffff'), ('pressed', '#ffffff')])
        self.style.configure('Secondary.TButton', background='#ffffff', foreground='#2563eb', font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('Secondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])

    def _create_section(self, parent, title, description=None):
        """Create a styled section container"""
        section = ttk.LabelFrame(parent, text=title, padding=14, style='Card.TLabelframe')
        section.pack(fill=tk.X, padx=6, pady=6)

        if description:
            desc = ttk.Label(section, text=description, style='Body.TLabel', wraplength=430, justify=tk.LEFT)
            desc.pack(anchor=tk.W, pady=(0, 10))

        return section

    def _add_slider(self, parent, key, label_text, minimum, maximum, initial, formatter, step=1):
        """Add a labeled slider with value indicator and micro-adjust controls."""
        row = ttk.Frame(parent, style='CardBody.TFrame')
        row.pack(fill=tk.X, pady=6)

        ttk.Label(row, text=label_text, style='FieldLabel.TLabel').pack(anchor=tk.W)

        slider_container = ttk.Frame(row, style='CardBody.TFrame')
        slider_container.pack(fill=tk.X, pady=(4, 0))

        value_label = ttk.Label(slider_container, text=formatter(initial), style='ValueLabel.TLabel')
        value_label.pack(side=tk.RIGHT)

        control_frame = ttk.Frame(slider_container, style='CardBody.TFrame')
        control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        decrement = ttk.Button(
            control_frame,
            text="<",
            width=3,
            style='Secondary.TButton',
            command=lambda k=key: self._nudge_slider(k, -step)
        )
        decrement.pack(side=tk.LEFT, padx=(0, 6))

        slider = ttk.Scale(
            control_frame,
            from_=minimum,
            to=maximum,
            orient=tk.HORIZONTAL
        )
        slider.set(initial)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        increment = ttk.Button(
            control_frame,
            text=">",
            width=3,
            style='Secondary.TButton',
            command=lambda k=key: self._nudge_slider(k, step)
        )
        increment.pack(side=tk.LEFT)

        def _handle_slider(value, slider_key=key):
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                numeric_value = value
            else:
                step_value = self._slider_steps.get(slider_key, 0) or 0
                if step_value:
                    snapped = round(numeric_value / step_value) * step_value
                    if step_value < 1:
                        step_str = f"{step_value:.6f}".rstrip('0').rstrip('.')
                        if '.' in step_str:
                            decimals = len(step_str.split('.')[1])
                            snapped = round(snapped, decimals)
                    if abs(snapped - numeric_value) > 1e-9:
                        numeric_value = snapped
                        slider_widget = self.sliders.get(slider_key)
                        if slider_widget is not None:
                            slider_widget.set(numeric_value)
            try:
                value_label.config(text=formatter(numeric_value))
            except Exception:
                pass
            self._schedule_slider_callback(slider_key)

        slider.configure(command=_handle_slider)
        slider.bind("<ButtonRelease-1>", lambda _e, k=key: self._apply_slider_change(k))
        slider.bind("<FocusOut>", lambda _e, k=key: self._apply_slider_change(k))
        slider.bind("<KeyRelease>", lambda _e, k=key: self._apply_slider_change(k))

        self.sliders[key] = slider
        self.labels[key] = value_label
        self._slider_steps[key] = float(step)

        return slider

    def _schedule_slider_callback(self, key):
        """Debounce expensive recomputation while the slider is moving."""
        existing = self._slider_after.get(key)
        if existing is not None:
            try:
                self.root.after_cancel(existing)
            except Exception:
                pass

        self._slider_after[key] = self.root.after(
            self._slider_delay_ms,
            lambda k=key: self._apply_slider_change(k)
        )

    def _apply_slider_change(self, key):
        """Commit the slider value and trigger downstream updates."""
        pending = self._slider_after.pop(key, None)
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except Exception:
                pass

        self._on_change()

    def _nudge_slider(self, key, delta):
        """Micro-adjust the slider value using the auxiliary buttons."""
        slider = self.sliders.get(key)
        if slider is None:
            return

        step = self._slider_steps.get(key, 1.0)
        try:
            current = float(slider.get())
            minimum = float(slider.cget('from'))
            maximum = float(slider.cget('to'))
        except (TypeError, ValueError):
            return

        new_value = current + delta
        if step:
            new_value = round(new_value / step) * step

        new_value = max(minimum, min(maximum, new_value))

        # Limit floating-point noise to six decimal places at most.
        if step < 1:
            step_str = f"{step:.6f}".rstrip('0').rstrip('.')
            if '.' in step_str:
                decimals = len(step_str.split('.')[1])
                new_value = round(new_value, decimals)

        slider.set(new_value)
        self._apply_slider_change(key)

    def _refresh_group_options(self):
        """Rebuild group radio buttons to match the latest dataset."""
        if not hasattr(self, 'group_container') or self.group_container is None:
            return

        for child in list(self.group_container.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        self.group_placeholder = None

        if app_state.group_cols:
            for col in app_state.group_cols:
                ttk.Radiobutton(
                    self.group_container,
                    text=col,
                    variable=self.radio_vars['group'],
                    value=col,
                    command=self._on_change,
                    style='Option.TRadiobutton'
                ).pack(anchor=tk.W, pady=2)
        else:
            placeholder = ttk.Label(
                self.group_container,
                text="Load data to unlock grouping options.",
                style='BodyMuted.TLabel',
                wraplength=400,
                justify=tk.LEFT
            )
            placeholder.pack(anchor=tk.W, pady=4)
            self.group_placeholder = placeholder

    def _open_legend_filter(self):
        """Launch legend filter dialog to hide/show groups."""
        if not app_state.available_groups:
            messagebox.showinfo("Legend Filter", "No legend entries are available yet.", parent=self.root)
            return

        try:
            from legend_dialog import select_visible_groups
        except Exception as exc:
            messagebox.showerror("Legend Filter", f"Unable to open filter dialog: {exc}", parent=self.root)
            return

        current = app_state.visible_groups or app_state.available_groups
        selection = select_visible_groups(app_state.available_groups, selected=current)
        if selection is None:
            return

        if len(selection) == len(app_state.available_groups):
            app_state.visible_groups = None
        else:
            app_state.visible_groups = selection

        if self.callback:
            self.callback()

    def update_selection_controls(self):
        """Refresh selection-related widgets to reflect current state."""
        if not hasattr(self, 'selection_button'):
            return

        count = len(getattr(app_state, 'selected_indices', []))

        if getattr(self, 'selection_status', None) is not None:
            try:
                self.selection_status.config(text=f"当前选中: {count}")
            except Exception:
                pass

        for button_attr in ('export_csv_button', 'export_excel_button'):
            btn = getattr(self, button_attr, None)
            if btn is None:
                continue
            try:
                if count == 0:
                    btn.state(['disabled'])
                else:
                    btn.state(['!disabled'])
            except Exception:
                pass

        toggle_btn = getattr(self, 'selection_button', None)
        if toggle_btn is None:
            return

        try:
            if app_state.selection_mode:
                toggle_btn.config(text="退出数据选择", style='Accent.TButton')
            else:
                toggle_btn.config(text="进入数据选择", style='Secondary.TButton')

            if app_state.render_mode == '3D':
                toggle_btn.state(['disabled'])
            else:
                toggle_btn.state(['!disabled'])
        except Exception:
            pass

    def _get_selected_dataframe(self):
        """Return a DataFrame with the currently selected samples."""
        if not app_state.selected_indices:
            messagebox.showinfo("导出选中数据", "请先在可视化中选择至少一个样本。", parent=self.root)
            return None

        if app_state.df_global is None or app_state.df_global.empty:
            messagebox.showwarning("导出选中数据", "当前没有可导出的数据。", parent=self.root)
            return None

        try:
            indices = sorted(app_state.selected_indices)
            df = app_state.df_global.iloc[indices].copy()
        except Exception as exc:
            messagebox.showerror("导出选中数据", f"无法提取选中样本：{exc}", parent=self.root)
            return None
        return df

    def _sanitize_filename(self, value):
        """Sanitize user-provided filename fragments for safe saving."""
        sanitized = re.sub(r'[\/\\:*?"<>|]+', '_', value)
        sanitized = sanitized.strip().strip('.')
        return sanitized

    def _on_toggle_selection(self):
        """Toggle selection mode from the control panel."""
        if app_state.render_mode == '3D':
            messagebox.showinfo(
                "数据选择",
                "三维模式暂不支持数据选择，请先切换到二维或嵌入视图。",
                parent=self.root
            )
            return

        toggle_selection_mode()
        self.update_selection_controls()

    def _export_selected_csv(self):
        """Export selected samples to a CSV file."""
        df = self._get_selected_dataframe()
        if df is None:
            return

        default_name = f"selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        name = simpledialog.askstring(
            "导出为 CSV",
            "请输入导出文件名（无需扩展名）：",
            initialvalue=default_name,
            parent=self.root
        )
        if name is None:
            return

        name = name.strip()
        sanitized = self._sanitize_filename(name)
        if not sanitized:
            messagebox.showerror("导出为 CSV", "文件名不能为空或仅包含非法字符。", parent=self.root)
            return

        target_dir = os.path.dirname(app_state.file_path) if app_state.file_path else os.getcwd()
        if not target_dir:
            target_dir = os.getcwd()
        target_path = os.path.join(target_dir, f"{sanitized}.csv")

        if os.path.exists(target_path):
            overwrite = messagebox.askyesno(
                "导出为 CSV",
                f"文件已存在：\n{target_path}\n是否覆盖？",
                parent=self.root
            )
            if not overwrite:
                return

        try:
            df.to_csv(target_path, index=False, encoding='utf-8-sig')
        except Exception as exc:
            messagebox.showerror("导出为 CSV", f"导出失败：{exc}", parent=self.root)
            return

        messagebox.showinfo(
            "导出为 CSV",
            f"已导出 {len(df)} 条记录到：\n{target_path}",
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
                title="选择目标工作簿",
                defaultextension=".xlsx",
                filetypes=[("Excel 工作簿", "*.xlsx")],
                initialfile="selected_data.xlsx"
            )
            if not workbook_path:
                return

        if not workbook_path.lower().endswith('.xlsx'):
            workbook_path = f"{workbook_path}.xlsx"

        sheet_default = f"Selected_{datetime.now().strftime('%Y%m%d_%H%M')}"
        sheet_name = simpledialog.askstring(
            "追加至 Excel",
            "请输入新工作表名称：",
            initialvalue=sheet_default,
            parent=self.root
        )
        if sheet_name is None:
            return

        sheet_name = sheet_name.strip()
        if not sheet_name:
            messagebox.showerror("追加至 Excel", "工作表名称不能为空。", parent=self.root)
            return
        if len(sheet_name) > 31:
            messagebox.showerror("追加至 Excel", "工作表名称不能超过 31 个字符。", parent=self.root)
            return
        if any(ch in sheet_name for ch in '[]:*?/\\'):
            messagebox.showerror("追加至 Excel", "工作表名称包含非法字符：[]:*?/\\", parent=self.root)
            return

        try:
            import openpyxl
        except ImportError:
            messagebox.showerror(
                "追加至 Excel",
                "需要安装 openpyxl 库才能写入 Excel。请先安装 openpyxl。",
                parent=self.root
            )
            return

        exists = os.path.exists(workbook_path)
        if exists:
            try:
                wb = openpyxl.load_workbook(workbook_path)
            except Exception as exc:
                messagebox.showerror("追加至 Excel", f"无法打开目标工作簿：{exc}", parent=self.root)
                return
            if sheet_name in wb.sheetnames:
                wb.close()
                messagebox.showerror("追加至 Excel", "指定的工作表已存在，请使用其他名称。", parent=self.root)
                return
            wb.close()

        try:
            if exists:
                with pd.ExcelWriter(workbook_path, mode='a', engine='openpyxl', if_sheet_exists='new') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                with pd.ExcelWriter(workbook_path, mode='w', engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as exc:
            messagebox.showerror("追加至 Excel", f"写入失败：{exc}", parent=self.root)
            return

        messagebox.showinfo(
            "追加至 Excel",
            f"已将 {len(df)} 条记录写入工作表 '{sheet_name}'。\n路径：{workbook_path}",
            parent=self.root
        )

    def _reload_data(self):
        """Allow the user to pick a new dataset and refresh the UI."""
        try:
            from data import load_data
        except Exception as exc:
            messagebox.showerror("Reload Data", f"Unable to reload data: {exc}", parent=self.root)
            return

        success = load_data(show_file_dialog=True, show_config_dialog=True)
        if not success:
            messagebox.showinfo("Reload Data", "Data reload cancelled.", parent=self.root)
            return

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

        messagebox.showinfo("Reload Data", "Dataset reloaded successfully.", parent=self.root)
    
    def _on_change(self):
        """Handle any parameter change - with safety checks"""
        try:
            print(f"[DEBUG] _on_change called", flush=True)
            
            # Verify all dictionaries are initialized
            if not self.sliders or not self.labels or not self.radio_vars:
                print("[DEBUG] Dictionaries not fully initialized yet", flush=True)
                return
            
            algorithm_changed = False

            if 'render_mode' in self.radio_vars:
                requested_mode = self.radio_vars['render_mode'].get()
                previous_mode = app_state.render_mode

                if requested_mode == '3D' and len(app_state.data_cols) < 3:
                    print("[WARN] Need at least three numeric columns for 3D view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != '3D' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)
                elif requested_mode == '2D' and len(app_state.data_cols) < 2:
                    print("[WARN] Need at least two numeric columns for 2D view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != '2D' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)

                if requested_mode in ('UMAP', 'tSNE'):
                    old_algo = app_state.algorithm
                    app_state.algorithm = 'UMAP' if requested_mode == 'UMAP' else 'tSNE'
                    algorithm_changed = (old_algo != app_state.algorithm)
                    if algorithm_changed:
                        print(f"[DEBUG] Algorithm changed: {old_algo} -> {app_state.algorithm}", flush=True)
                        app_state.embedding_cache.clear()

                if requested_mode != previous_mode:
                    print(f"[DEBUG] Render mode changed: {previous_mode} -> {requested_mode}", flush=True)
                    app_state.render_mode = requested_mode
                    if requested_mode == '2D':
                        app_state.selected_2d_confirmed = False
                    elif requested_mode == '3D':
                        app_state.selected_3d_confirmed = False

            if app_state.render_mode in ('UMAP', 'tSNE'):
                app_state.algorithm = 'UMAP' if app_state.render_mode == 'UMAP' else 'tSNE'
            
            # Update UMAP parameters - only if keys exist
            umap_changed = False
            if 'umap_n' in self.sliders and 'umap_n' in self.labels:
                new_val = int(self.sliders['umap_n'].get())
                if app_state.umap_params['n_neighbors'] != new_val:
                    umap_changed = True
                app_state.umap_params['n_neighbors'] = new_val
                self.labels['umap_n'].config(text=f"{new_val}")
            
            if 'umap_d' in self.sliders and 'umap_d' in self.labels:
                new_val = float(self.sliders['umap_d'].get())
                if app_state.umap_params['min_dist'] != new_val:
                    umap_changed = True
                app_state.umap_params['min_dist'] = new_val
                self.labels['umap_d'].config(text=f"{new_val:.2f}")
            
            if 'umap_r' in self.sliders and 'umap_r' in self.labels:
                new_val = int(self.sliders['umap_r'].get())
                if app_state.umap_params['random_state'] != new_val:
                    umap_changed = True
                app_state.umap_params['random_state'] = new_val
                self.labels['umap_r'].config(text=f"{new_val}")
            
            # Clear UMAP cache if parameters changed
            if umap_changed:
                print(f"[DEBUG] UMAP parameters changed, clearing UMAP cache", flush=True)
                # Remove UMAP entries from cache
                keys_to_remove = [k for k in app_state.embedding_cache.keys() if k[0] == 'umap']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update t-SNE parameters
            tsne_changed = False
            if 'tsne_p' in self.sliders and 'tsne_p' in self.labels:
                p = int(self.sliders['tsne_p'].get())
                if app_state.df_global is not None and p >= app_state.df_global.shape[0]:
                    p = app_state.df_global.shape[0] - 1
                    self.sliders['tsne_p'].set(p)
                if app_state.tsne_params['perplexity'] != p:
                    tsne_changed = True
                app_state.tsne_params['perplexity'] = p
                self.labels['tsne_p'].config(text=f"{p}")
            
            if 'tsne_lr' in self.sliders and 'tsne_lr' in self.labels:
                new_val = int(self.sliders['tsne_lr'].get())
                if app_state.tsne_params['learning_rate'] != new_val:
                    tsne_changed = True
                app_state.tsne_params['learning_rate'] = new_val
                self.labels['tsne_lr'].config(text=f"{new_val}")
            
            # Clear t-SNE cache if parameters changed
            if tsne_changed:
                print(f"[DEBUG] t-SNE parameters changed, clearing t-SNE cache", flush=True)
                # Remove t-SNE entries from cache
                keys_to_remove = [k for k in app_state.embedding_cache.keys() if k[0] == 'tsne']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update common parameters
            if 'size' in self.sliders and 'size' in self.labels:
                app_state.point_size = int(self.sliders['size'].get())
                self.labels['size'].config(text=f"{int(self.sliders['size'].get())}")
            
            # Update group column if available
            if 'group' in self.radio_vars:
                old_group = app_state.last_group_col
                app_state.last_group_col = self.radio_vars['group'].get()
                print(f"[DEBUG] Group column changed: {old_group} -> {app_state.last_group_col}", flush=True)
            
            # Call the callback
            print(f"[DEBUG] Calling callback", flush=True)
            if self.callback:
                self.callback()
            print(f"[DEBUG] Callback completed", flush=True)
        
        except KeyError as e:
            print(f"[DEBUG] KeyError in _on_change (expected during init): {e}", flush=True)
        except Exception as e:
            print(f"[ERROR] _on_change: {e}", flush=True)
    
    def show(self):
        """Show the control panel"""
        print("[INFO] Control panel displayed", flush=True)
        self.root.mainloop()

    def destroy(self):
        """Destroy the control panel and master if owned"""
        try:
            for pending in list(self._slider_after.values()):
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
            self._slider_after.clear()
            self.root.destroy()
        finally:
            if getattr(self, "_owns_master", False) and getattr(self, "master", None) is not None:
                try:
                    self.master.destroy()
                except Exception:
                    pass

    def open(self):
        """Bring the control panel window back if it was hidden"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_visible = True
        except Exception as exc:
            print(f"[WARN] Unable to reopen control panel: {exc}", flush=True)

    def _on_close(self):
        """Handle window close without tearing down shared Tk root"""
        try:
            self.root.withdraw()
            self.is_visible = False
        except Exception:
            pass


def create_control_panel(callback):
    """
    Create and return a control panel instance
    
    Args:
        callback: function to call when parameters change
    
    Returns:
        ControlPanel instance
    """
    return ControlPanel(callback)
