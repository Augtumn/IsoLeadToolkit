"""2D Column Selection Dialog"""
import tkinter as tk
from tkinter import ttk, messagebox


class _Select2DColumnsDialog:
    """Modal dialog that lets the user pick two distinct columns for 2D plotting."""

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
        self.root.title("Select 2D Axes")
        self.root.configure(bg="#edf2f7")
        self.root.resizable(False, False)
        self.root.geometry("420x320")
        self.root.minsize(420, 320)

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
        self.style.configure('Dialog.TFrame', background="#edf2f7")
        self.style.configure('Card.TFrame', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('Header.TLabel', background="#edf2f7", foreground="#1a202c", font=('Segoe UI', 14, 'bold'))
        self.style.configure('Body.TLabel', background="#ffffff", foreground="#475569", font=('Segoe UI', 10))
        self.style.configure('Field.TLabel', background="#ffffff", foreground="#1a202c", font=('Segoe UI', 10, 'bold'))
        self.style.configure('Accent.TButton', background="#2563eb", foreground="#ffffff", font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')])
        self.style.configure('Secondary.TButton', background="#ffffff", foreground="#2563eb", font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('Secondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])

    def _build_ui(self):
        container = ttk.Frame(self.root, padding=(18, 18, 18, 14), style='Dialog.TFrame')
        container.pack(fill=tk.BOTH, expand=True)

        title = ttk.Label(container, text="Choose axes for the 2D scatter", style='Header.TLabel', wraplength=340, justify=tk.LEFT)
        title.pack(anchor=tk.W)

        card = ttk.Frame(container, padding=14, style='Card.TFrame')
        card.pack(fill=tk.BOTH, expand=True, pady=(12, 16))

        ttk.Label(card, text="Select one column for each axis. Columns must be unique.", style='Body.TLabel', wraplength=320, justify=tk.LEFT).pack(anchor=tk.W, pady=(0, 12))

        self.vars = {
            'x': tk.StringVar(value=self._prefill(0)),
            'y': tk.StringVar(value=self._prefill(1)),
        }

        for idx, axis in enumerate(('x', 'y')):
            row = ttk.Frame(card, style='Card.TFrame')
            row.pack(fill=tk.X, pady=6)

            ttk.Label(row, text=f"Axis {axis.upper()}", style='Field.TLabel').pack(anchor=tk.W)

            combo = ttk.Combobox(row, textvariable=self.vars[axis], values=self.columns, state='readonly', font=('Segoe UI', 10))
            combo.pack(fill=tk.X, pady=(4, 0))
            if not self.vars[axis].get() and self.columns:
                combo.current(0)

        button_row = ttk.Frame(container, style='Dialog.TFrame')
        button_row.pack(fill=tk.X)

        ttk.Button(button_row, text="Cancel", style='Secondary.TButton', command=self._on_cancel).pack(side=tk.RIGHT, padx=(0, 10))
        ttk.Button(button_row, text="Apply", style='Accent.TButton', command=self._on_ok).pack(side=tk.RIGHT)

    def _prefill(self, index):
        if len(self.preselected) > index and self.preselected[index] in self.columns:
            return self.preselected[index]
        if len(self.columns) > index:
            return self.columns[index]
        return ''

    def _on_ok(self):
        selections = [self.vars['x'].get(), self.vars['y'].get()]
        if '' in selections:
            messagebox.showwarning("Selection Required", "Please choose a column for each axis.", parent=self.root)
            return
        if len(set(selections)) != 2:
            messagebox.showwarning("Fields Must Differ", "Each axis must use a different data column.", parent=self.root)
            return
        try:
            print(f"[DEBUG] 2D dialog confirmed selection: {selections}", flush=True)
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


def select_2d_columns(columns, preselected=None):
    """Show the 2D column picker dialog and return the chosen axes."""
    dialog = _Select2DColumnsDialog(columns, preselected=preselected)
    return dialog.show()
