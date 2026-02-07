"""
Panel Dialogs - Dialog windows for the Control Panel
"""
import tkinter as tk
from tkinter import ttk, messagebox

from core import app_state, save_session_params


class PanelDialogsMixin:
    """Mixin providing dialog methods for the ControlPanel"""

    def _open_tooltip_settings(self):
        """Open a dialog to select columns for the tooltip."""
        if app_state.df_global is None:
            messagebox.showwarning(
                self._translate("No Data"),
                self._translate("Please load data first.")
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self._translate("Tooltip Configuration"))
        dialog.geometry("300x400")
        
        # Make it modal
        dialog.transient(self.root)
        dialog.grab_set()

        lbl = ttk.Label(dialog, text=self._translate("Select columns to display:"))
        lbl.pack(pady=10, padx=10, anchor=tk.W)
        self._register_translation(lbl, "Select columns to display:")

        # Buttons - Pack FIRST at BOTTOM to avoid being hidden
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        def save_tooltip_config():
            selected = [col for col, var in self.tooltip_vars.items() if var.get()]
            app_state.tooltip_columns = selected
            print(f"[DEBUG] Tooltip columns updated to: {selected}", flush=True)
            
            # Trigger immediate save to disk
            try:
                save_session_params(
                    algorithm=app_state.algorithm,
                    umap_params=app_state.umap_params,
                    tsne_params=app_state.tsne_params,
                    point_size=app_state.point_size,
                    group_col=app_state.last_group_col,
                    group_cols=app_state.group_cols,
                    data_cols=app_state.data_cols,
                    file_path=app_state.file_path,
                    sheet_name=app_state.sheet_name,
                    render_mode=app_state.render_mode,
                    selected_2d_cols=getattr(app_state, 'selected_2d_cols', []),
                    selected_3d_cols=app_state.selected_3d_cols,
                    language=app_state.language,
                    tooltip_columns=app_state.tooltip_columns
                )
            except Exception as e:
                print(f"[WARN] Failed to auto-save session: {e}", flush=True)

            dialog.destroy()

        save_btn = ttk.Button(btn_frame, text=self._translate("Save"), command=save_tooltip_config)
        save_btn.pack(side=tk.RIGHT, padx=5)
        self._register_translation(save_btn, "Save")

        cancel_btn = ttk.Button(btn_frame, text=self._translate("Cancel"), command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT)
        self._register_translation(cancel_btn, "Cancel")

        # Scrollable frame for checkboxes
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Ensure frame width matches canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Checkboxes
        self.tooltip_vars = {}
        all_columns = list(app_state.df_global.columns)
        
        # Ensure default columns are in the list if they exist in dataframe
        current_selection = app_state.tooltip_columns
        if current_selection is None:
            current_selection = []

        for col in all_columns:
            var = tk.BooleanVar(value=col in current_selection)
            self.tooltip_vars[col] = var
            cb = ttk.Checkbutton(scrollable_frame, text=col, variable=var)
            cb.pack(anchor=tk.W, pady=2)

    def _open_group_col_settings(self):
        """Open a dialog to select columns for grouping."""
        if app_state.df_global is None:
            messagebox.showwarning(
                self._translate("No Data"),
                self._translate("Please load data first.")
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self._translate("Group Columns Configuration"))
        dialog.geometry("300x400")
        
        dialog.transient(self.root)
        dialog.grab_set()

        lbl = ttk.Label(dialog, text=self._translate("Select columns to use for grouping:"))
        lbl.pack(pady=10, padx=10, anchor=tk.W)
        self._register_translation(lbl, "Select columns to use for grouping:")

        # Buttons - Pack FIRST at BOTTOM
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        def save_group_config():
            selected = [col for col, var in self.group_vars.items() if var.get()]
            if not selected:
                messagebox.showwarning(
                    self._translate("Validation Error"),
                    self._translate("Please select at least one grouping column."),
                    parent=dialog
                )
                return

            app_state.group_cols = selected
            print(f"[DEBUG] Group columns updated to: {selected}", flush=True)
            
            # Refresh UI
            self._refresh_group_list()
            
            # Trigger immediate save to disk
            try:
                save_session_params(
                    algorithm=app_state.algorithm,
                    umap_params=app_state.umap_params,
                    tsne_params=app_state.tsne_params,
                    point_size=app_state.point_size,
                    group_col=app_state.last_group_col,
                    group_cols=app_state.group_cols,
                    data_cols=app_state.data_cols,
                    file_path=app_state.file_path,
                    sheet_name=app_state.sheet_name,
                    render_mode=app_state.render_mode,
                    selected_2d_cols=getattr(app_state, 'selected_2d_cols', []),
                    selected_3d_cols=app_state.selected_3d_cols,
                    language=app_state.language,
                    tooltip_columns=app_state.tooltip_columns
                )
            except Exception as e:
                print(f"[WARN] Failed to auto-save session: {e}", flush=True)

            dialog.destroy()

        save_btn = ttk.Button(btn_frame, text=self._translate("Save"), command=save_group_config)
        save_btn.pack(side=tk.RIGHT, padx=5)
        self._register_translation(save_btn, "Save")

        cancel_btn = ttk.Button(btn_frame, text=self._translate("Cancel"), command=dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT)
        self._register_translation(cancel_btn, "Cancel")

        # Scrollable frame
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Ensure frame width matches canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Checkboxes
        self.group_vars = {}
        all_columns = list(app_state.df_global.columns)
        
        # Identify data columns to exclude
        data_cols = set(app_state.data_cols) if app_state.data_cols else set()
        
        current_selection = app_state.group_cols or []

        for col in all_columns:
            # Skip if it is a data column
            if col in data_cols:
                continue

            var = tk.BooleanVar(value=col in current_selection)
            self.group_vars[col] = var
            cb = ttk.Checkbutton(scrollable_frame, text=col, variable=var)
            cb.pack(anchor=tk.W, pady=2)

    def _open_mixing_calculator(self):
        """Open a dialog to compute mixing proportions."""
        if app_state.df_global is None:
            messagebox.showwarning(
                self._translate("No Data"),
                self._translate("Please load data first.")
            )
            return

        groups = getattr(app_state, 'mixing_groups', {}) or {}
        endmembers = groups.get('endmembers', {})
        mixtures = groups.get('mixtures', {})
        if not endmembers:
            messagebox.showwarning(
                self._translate("Warning"),
                self._translate("Please define endmember groups first.")
            )
            return
        if not mixtures:
            messagebox.showwarning(
                self._translate("Warning"),
                self._translate("Please define mixture groups first.")
            )
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self._translate("Mixing Calculator"))
        dialog.geometry("520x560")
        dialog.transient(self.root)
        dialog.grab_set()

        title_lbl = ttk.Label(
            dialog,
            text=self._translate("Columns for Mixing"),
            style='Body.TLabel'
        )
        title_lbl.pack(pady=(10, 6), padx=10, anchor=tk.W)
        self._register_translation(title_lbl, "Columns for Mixing")

        # Scrollable list of columns
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=False, padx=10)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Column checkboxes
        self.mixing_col_vars = {}
        df = app_state.df_global
        numeric_cols = list(df.select_dtypes(include='number').columns)
        default_cols = list(getattr(app_state, 'mixing_calc_cols', [])) or list(
            getattr(app_state, 'data_cols', [])
        )
        for col in numeric_cols:
            var = tk.BooleanVar(value=col in default_cols)
            self.mixing_col_vars[col] = var
            cb = ttk.Checkbutton(scrollable_frame, text=col, variable=var)
            cb.pack(anchor=tk.W, pady=2)

        results_frame = ttk.Frame(dialog)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(8, 6))

        results_lbl = ttk.Label(
            results_frame,
            text=self._translate("Mixing Results"),
            style='Body.TLabel'
        )
        results_lbl.pack(anchor=tk.W)
        self._register_translation(results_lbl, "Mixing Results")

        columns = ("mixture", "endmember", "weight", "rmse")
        tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=10)
        tree.heading("mixture", text=self._translate("Mixture Group"))
        tree.heading("endmember", text=self._translate("Endmember Group"))
        tree.heading("weight", text=self._translate("Weight"))
        tree.heading("rmse", text=self._translate("RMSE"))
        tree.column("mixture", width=150, anchor=tk.W)
        tree.column("endmember", width=150, anchor=tk.W)
        tree.column("weight", width=80, anchor=tk.E)
        tree.column("rmse", width=80, anchor=tk.E)
        tree.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        def _clear_tree():
            for item in tree.get_children():
                tree.delete(item)

        def _run_calc():
            selected_cols = [col for col, var in self.mixing_col_vars.items() if var.get()]
            if not selected_cols:
                messagebox.showwarning(
                    self._translate("Validation Error"),
                    self._translate("Please select at least one data column."),
                    parent=dialog
                )
                return

            try:
                from data.mixing import calculate_mixing

                results = calculate_mixing(
                    df=df,
                    endmember_groups=endmembers,
                    mixture_groups=mixtures,
                    columns=selected_cols
                )
                app_state.mixing_results = results
                app_state.mixing_calc_cols = list(selected_cols)

                _clear_tree()
                for row in results:
                    tree.insert(
                        "",
                        "end",
                        values=(
                            row.get('mixture', ''),
                            row.get('endmember', ''),
                            f"{row.get('weight', 0.0):.4f}",
                            f"{row.get('rmse', 0.0):.4f}",
                        )
                    )
                if not results:
                    messagebox.showinfo(
                        self._translate("Info"),
                        self._translate("No mixing results were produced."),
                        parent=dialog
                    )
            except Exception as err:
                messagebox.showerror(
                    self._translate("Error"),
                    self._translate("Mixing calculation failed: {error}", error=err),
                    parent=dialog
                )

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        run_btn = ttk.Button(btn_frame, text=self._translate("Calculate"), command=_run_calc)
        run_btn.pack(side=tk.RIGHT, padx=5)
        self._register_translation(run_btn, "Calculate")

        close_btn = ttk.Button(btn_frame, text=self._translate("Close"), command=dialog.destroy)
        close_btn.pack(side=tk.RIGHT)
        self._register_translation(close_btn, "Close")

    def _open_column_selection(self):
        """Open column selection dialog based on current render mode."""
        if app_state.df_global is None:
            messagebox.showwarning(
                self._translate("No Data"),
                self._translate("Please load data first."),
                parent=self.root
            )
            return
            
        if app_state.render_mode == '2D':
            try:
                from ui.dialogs.two_d_dialog import select_2d_columns
                available = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                current = getattr(app_state, 'selected_2d_cols', [])
                selection = select_2d_columns(available, preselected=current)
                if selection and len(selection) == 2:
                    app_state.selected_2d_cols = selection
                    app_state.selected_2d_confirmed = True
                    if self.callback:
                        self.callback()
            except Exception as e:
                print(f"[ERROR] Failed to open 2D column selection: {e}", flush=True)
                messagebox.showerror(self._translate("Error"), str(e))
        elif app_state.render_mode == '3D':
            try:
                from ui.dialogs.three_d_dialog import select_3d_columns
                available = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                current = app_state.selected_3d_cols
                selection = select_3d_columns(available, preselected=current)
                if selection and len(selection) == 3:
                    app_state.selected_3d_cols = selection
                    app_state.selected_3d_confirmed = True
                    if self.callback:
                        self.callback()
            except Exception as e:
                print(f"[ERROR] Failed to open 3D column selection: {e}", flush=True)
                messagebox.showerror(self._translate("Error"), str(e))
        elif app_state.render_mode == 'Ternary':
            try:
                from ui.dialogs.ternary_dialog import ask_ternary_columns
                available = [c for c in app_state.data_cols if c in app_state.df_global.columns]
                current = app_state.selected_ternary_cols
                selection = ask_ternary_columns(available, preselected=current)
                if selection and len(selection) == 3:
                    app_state.selected_ternary_cols = selection
                    app_state.selected_ternary_confirmed = True
                    if hasattr(self, 'update_ternary_sliders_from_data'):
                        self.update_ternary_sliders_from_data(preserve_existing=False)
                    if self.callback:
                        self.callback()
            except Exception as e:
                print(f"[ERROR] Failed to open Ternary column selection: {e}", flush=True)
                messagebox.showerror(self._translate("Error"), str(e))
        else:
            messagebox.showinfo(
                self._translate("Info"), 
                self._translate("Column selection is only available for 2D/3D/Ternary modes.")
            )
