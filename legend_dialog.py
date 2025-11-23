"""Legend Filter Dialog"""
import tkinter as tk
from tkinter import ttk, messagebox

from localization import translate


class LegendFilterDialog:
    """Simple checkbox dialog for selecting which groups remain visible."""

    def __init__(self, groups, selected=None):
        self.groups = list(groups)
        self.selected = set(selected or groups)
        self.result = None

        master = tk._default_root
        self._owns_master = False
        if master is None:
            master = tk.Tk()
            master.withdraw()
            self._owns_master = True

        self.master = master
        self.root = tk.Toplevel(master)
        self.root.title(translate("Legend Filter"))
        self.root.configure(bg="#edf2f7")
        self.root.geometry("420x360")
        self.root.minsize(420, 320)
        self.root.resizable(False, False)

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

    def _setup_styles(self):
        self.style.configure('LegendDialog.TFrame', background="#edf2f7")
        self.style.configure('LegendCard.TFrame', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('LegendHeader.TLabel', background="#edf2f7", foreground="#1a202c", font=('Segoe UI', 14, 'bold'))
        self.style.configure('LegendBody.TLabel', background="#ffffff", foreground="#475569", font=('Segoe UI', 10))
        self.style.configure('LegendCheck.TCheckbutton', background="#ffffff", foreground="#1a202c", font=('Segoe UI', 10))
        self.style.configure('LegendAccent.TButton', background="#2563eb", foreground="#ffffff", font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('LegendAccent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')])
        self.style.configure('LegendSecondary.TButton', background="#ffffff", foreground="#2563eb", font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('LegendSecondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])

    def _build_ui(self):
        outer = ttk.Frame(self.root, style='LegendDialog.TFrame')
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, bd=0, background="#edf2f7")
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        dialog_scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        dialog_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        container = ttk.Frame(canvas, padding=(18, 18, 18, 14), style='LegendDialog.TFrame')
        window_id = canvas.create_window((0, 0), window=container, anchor='nw')
        canvas.configure(yscrollcommand=dialog_scrollbar.set)

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
            text=translate("Choose which groups stay visible"),
            style='LegendHeader.TLabel',
            wraplength=360,
            justify=tk.LEFT
        )
        title.pack(anchor=tk.W)

        card = ttk.Frame(container, padding=14, style='LegendCard.TFrame')
        card.pack(fill=tk.BOTH, expand=True, pady=(12, 16))

        ttk.Label(
            card,
            text=translate("Uncheck any legend entries you want to hide from the plot."),
            style='LegendBody.TLabel',
            wraplength=340,
            justify=tk.LEFT
        ).pack(anchor=tk.W, pady=(0, 12))

        toolbar = ttk.Frame(card, style='LegendCard.TFrame')
        toolbar.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(
            toolbar,
            text=translate("Select all"),
            style='LegendSecondary.TButton',
            command=self._select_all
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(
            toolbar,
            text=translate("Clear"),
            style='LegendSecondary.TButton',
            command=self._clear_all
        ).pack(side=tk.LEFT)

        self.vars = {}

        list_canvas = tk.Canvas(card, highlightthickness=0, bd=0, background="#ffffff")
        list_canvas.pack(fill=tk.BOTH, expand=True)

        list_scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=list_canvas.yview)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        list_canvas.configure(yscrollcommand=list_scrollbar.set)

        list_frame = ttk.Frame(list_canvas, style='LegendCard.TFrame')
        list_window_id = list_canvas.create_window((0, 0), window=list_frame, anchor='nw')

        def _sync_list_scroll(event, target_canvas=list_canvas):
            try:
                target_canvas.configure(scrollregion=target_canvas.bbox("all"))
            except tk.TclError:
                pass

        def _resize_list_canvas(event, target_canvas=list_canvas, item=list_window_id):
            try:
                target_canvas.itemconfigure(item, width=event.width)
            except tk.TclError:
                pass

        list_frame.bind("<Configure>", _sync_list_scroll)
        list_canvas.bind("<Configure>", _resize_list_canvas)

        for group in self.groups:
            var = tk.BooleanVar(value=(group in self.selected))
            cb = ttk.Checkbutton(
                list_frame,
                text=str(group),
                variable=var,
                style='LegendCheck.TCheckbutton'
            )
            cb.pack(anchor=tk.W, pady=4)
            self.vars[group] = var

        button_row = ttk.Frame(container, style='LegendDialog.TFrame')
        button_row.pack(fill=tk.X)

        ttk.Button(
            button_row,
            text=translate("Cancel"),
            style='LegendSecondary.TButton',
            command=self._on_cancel
        ).pack(side=tk.RIGHT, padx=(0, 10))
        ttk.Button(
            button_row,
            text=translate("Apply"),
            style='LegendAccent.TButton',
            command=self._on_ok
        ).pack(side=tk.RIGHT)

    def _select_all(self):
        for var in self.vars.values():
            var.set(True)

    def _clear_all(self):
        for var in self.vars.values():
            var.set(False)

    def _on_ok(self):
        selection = [group for group, var in self.vars.items() if var.get()]
        if not selection:
            messagebox.showwarning(
                translate("Legend Filter"),
                translate("Please keep at least one group visible."),
                parent=self.root
            )
            return
        self.result = selection
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


def select_visible_groups(groups, selected=None):
    """Show the legend filter dialog and return the chosen subset."""
    dialog = LegendFilterDialog(groups, selected=selected)
    return dialog.show()
