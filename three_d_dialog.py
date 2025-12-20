"""3D Column Selection Dialog"""
import tkinter as tk
from tkinter import ttk, messagebox

from localization import translate


class _Select3DColumnsDialog:
    """Modal dialog that lets the user pick three distinct columns for 3D plotting."""

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
        self.root.title(translate("Select 3D Axes"))
        self.root.configure(bg="#edf2f7")
        self.root.resizable(False, False)
        self.root.geometry("440x360")
        self.root.minsize(440, 360)

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
        """
        Construct the user interface.
        
        Sets up a scrollable canvas containing the selection widgets.
        The layout uses a standard left-aligned canvas and right-aligned scrollbar.
        """
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

        title = ttk.Label(
            container,
            text=translate("Choose axes for the 3D scatter"),
            style='Header.TLabel',
            wraplength=360,
            justify=tk.LEFT
        )
        title.pack(anchor=tk.W)

        card = ttk.Frame(container, padding=14, style='Card.TFrame')
        card.pack(fill=tk.BOTH, expand=True, pady=(12, 16))

        ttk.Label(
            card,
            text=translate("Select one column for each axis. Columns must be unique."),
            style='Body.TLabel',
            wraplength=340,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 12))

        self.vars = {
            'x': tk.StringVar(value=self._prefill(0)),
            'y': tk.StringVar(value=self._prefill(1)),
            'z': tk.StringVar(value=self._prefill(2))
        }

        for idx, axis in enumerate(('x', 'y', 'z')):
            row = ttk.Frame(card, style='Card.TFrame')
            row.pack(fill=tk.X, pady=6)

            ttk.Label(
                row,
                text=translate("Axis {axis}", axis=axis.upper()),
                style='Field.TLabel'
            ).pack(anchor=tk.W)

            combo = ttk.Combobox(row, textvariable=self.vars[axis], values=self.columns, state='readonly', font=('Segoe UI', 10))
            combo.pack(fill=tk.X, pady=(4, 0))
            if not self.vars[axis].get() and self.columns:
                combo.current(0)

        button_row = ttk.Frame(container, style='Dialog.TFrame')
        button_row.pack(fill=tk.X)

        ttk.Button(
            button_row,
            text=translate("Cancel"),
            style='Secondary.TButton',
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=(0, 10))
        ttk.Button(
            button_row,
            text=translate("Apply"),
            style='Accent.TButton',
            command=self._on_ok
        ).pack(side=tk.RIGHT)

    def _prefill(self, index):
        if len(self.preselected) > index and self.preselected[index] in self.columns:
            return self.preselected[index]
        if len(self.columns) > index:
            return self.columns[index]
        return ''

    def _on_ok(self):
        selections = [self.vars['x'].get(), self.vars['y'].get(), self.vars['z'].get()]
        if '' in selections:
            messagebox.showwarning(
                translate("Selection Required"),
                translate("Please choose a column for each axis."),
                parent=self.root
            )
            return
        if len(set(selections)) != 3:
            messagebox.showwarning(
                translate("Fields Must Differ"),
                translate("Each axis must use a different data column."),
                parent=self.root
            )
            return
        try:
            print(f"[DEBUG] 3D dialog confirmed selection: {selections}", flush=True)
        except Exception:
            pass
        self.result = selections
        self._close()

    def _on_cancel(self):
        self.result = None
        self._close()

    def _close(self):
        try:
            self.root.grab_release()
        except Exception:
            pass
        self.root.destroy()
        if self._owns_master and self.master is not None:
            try:
                self.master.destroy()
            except Exception:
                pass

    def show(self):
        self.root.wait_window()
        return self.result


def select_3d_columns(columns, preselected=None):
    """Convenience helper to show the 3D column picker dialog."""
    dialog = _Select3DColumnsDialog(columns, preselected=preselected)
    return dialog.show()
