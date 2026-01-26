"""Ternary Plot Column Selection Dialog"""
import tkinter as tk
from tkinter import ttk, messagebox

from core.localization import translate


class _SelectTernaryColumnsDialog:
    """Modal dialog that lets the user pick three distinct columns for Ternary plotting."""

    def __init__(self, columns, preselected=None):
        self.columns = list(columns)
        self.columns.sort()
        self.preselected = preselected or []
        self.result = None

        master = tk._default_root
        self._owns_master = False
        if master is None:
            master = tk.Tk()
            master.withdraw()
            self._owns_master = True

        self.master = master
        self.root = tk.Toplevel(master)
        self.root.title(translate("Select Ternary Axes"))
        self.root.configure(bg="#edf2f7")
        self.root.resizable(True, True)
        self.root.geometry("450x420")
        self.root.minsize(450, 420)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

        self._setup_styles()
        self._build_ui()

        self.root.transient(master)
        self.root.grab_set()
        self.root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.root.lift()
        self.root.focus_force()
        try:
            self.root.attributes('-topmost', True)
            self.root.after(200, lambda: self.root.attributes('-topmost', False))
        except Exception:
            pass

        try:
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            pass

    def _setup_styles(self):
        ui_font = 'Microsoft YaHei UI'
        self.style.configure('Dialog.TFrame', background="#edf2f7")
        self.style.configure('Card.TFrame', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('Header.TLabel', background="#edf2f7", foreground="#1a202c", font=(ui_font, 14, 'bold'))
        self.style.configure('Body.TLabel', background="#ffffff", foreground="#475569", font=(ui_font, 10))
        self.style.configure('Field.TLabel', background="#ffffff", foreground="#1a202c", font=(ui_font, 10, 'bold'))
        self.style.configure('Accent.TButton', background="#2563eb", foreground="#ffffff", font=(ui_font, 10, 'bold'), padding=(12, 6))
        self.style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')])
        self.style.configure('Secondary.TButton', background="#ffffff", foreground="#2563eb", font=(ui_font, 10, 'bold'), padding=(12, 6))
        self.style.map('Secondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])

    def _build_ui(self):
        outer = ttk.Frame(self.root, style='Dialog.TFrame')
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, bd=0, background="#edf2f7")
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        container = ttk.Frame(canvas, padding=(18, 18, 18, 14), style='Dialog.TFrame')
        window_id = canvas.create_window((0, 0), window=container, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        def _sync_scrollregion(event, target_canvas=canvas):
            try:
                target_canvas.configure(scrollregion=target_canvas.bbox("all"))
            except tk.TclError:
                pass

        def _resize_canvas(event, target_canvas=canvas, item=window_id):
            try:
                target_canvas.itemconfigure(item, width=event.width)
            except tk.TclError:
                pass

        container.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _resize_canvas)

        # Header
        header = ttk.Label(container, text=translate("Configure Ternary Axes"), style='Header.TLabel')
        header.pack(fill=tk.X, pady=(0, 16))

        # Card
        card = ttk.Frame(container, style='Card.TFrame', padding=16)
        card.pack(fill=tk.BOTH, expand=True)

        info_text = translate("Select three columns to map to the vertices of the ternary plot (Top, Right, Left).")
        info_lbl = ttk.Label(card, text=info_text, style='Body.TLabel', wraplength=350)
        info_lbl.pack(fill=tk.X, pady=(0, 12))

        # Defaults
        def_top = ''
        def_right = ''
        def_left = ''
        if len(self.preselected) >= 1: def_top = self.preselected[0]
        if len(self.preselected) >= 2: def_right = self.preselected[1]
        if len(self.preselected) >= 3: def_left = self.preselected[2]

        # Top Axis
        lbl_top = ttk.Label(card, text=translate("Top Vertex (A)"), style='Field.TLabel')
        lbl_top.pack(anchor=tk.W, pady=(4, 2))
        self.combo_top = ttk.Combobox(card, values=self.columns, state="readonly")
        self.combo_top.pack(fill=tk.X, pady=(0, 10))
        if def_top in self.columns:
            self.combo_top.set(def_top)

        # Right Axis
        lbl_right = ttk.Label(card, text=translate("Right Vertex (B)"), style='Field.TLabel')
        lbl_right.pack(anchor=tk.W, pady=(4, 2))
        self.combo_right = ttk.Combobox(card, values=self.columns, state="readonly")
        self.combo_right.pack(fill=tk.X, pady=(0, 10))
        if def_right in self.columns:
            self.combo_right.set(def_right)

        # Left Axis
        lbl_left = ttk.Label(card, text=translate("Left Vertex (C)"), style='Field.TLabel')
        lbl_left.pack(anchor=tk.W, pady=(4, 2))
        self.combo_left = ttk.Combobox(card, values=self.columns, state="readonly")
        self.combo_left.pack(fill=tk.X, pady=(0, 10))
        if def_left in self.columns:
            self.combo_left.set(def_left)

        # Actions
        btn_frame = ttk.Frame(container, style='Dialog.TFrame')
        btn_frame.pack(fill=tk.X, pady=(16, 0))

        ok_btn = ttk.Button(
            btn_frame,
            text=translate("Confirm"),
            style='Accent.TButton',
            command=self._on_ok
        )
        ok_btn.pack(side=tk.RIGHT)

        cancel_btn = ttk.Button(
            btn_frame,
            text=translate("Cancel"),
            style='Secondary.TButton',
            command=self._on_cancel
        )
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 8))

    def _on_ok(self):
        c_top = self.combo_top.get()
        c_right = self.combo_right.get()
        c_left = self.combo_left.get()

        if not c_top or not c_right or not c_left:
            messagebox.showwarning(
                translate("Incomplete Selection"),
                translate("Please select columns for all three axes."),
                parent=self.root
            )
            return

        if len({c_top, c_right, c_left}) < 3:
            messagebox.showwarning(
                translate("Duplicate Columns"),
                translate("Please select three distinct columns."),
                parent=self.root
            )
            return

        self.result = [c_top, c_right, c_left]
        self.root.destroy()
        if self._owns_master:
            self.master.destroy()

    def _on_cancel(self):
        self.result = None
        self.root.destroy()
        if self._owns_master:
            self.master.destroy()


def ask_ternary_columns(columns, preselected=None):
    """
    Open the dialog to select 3 columns.
    Returns [col_top, col_right, col_left] or None.
    """
    dlg = _SelectTernaryColumnsDialog(columns, preselected)
    dlg.root.wait_window()
    return dlg.result
