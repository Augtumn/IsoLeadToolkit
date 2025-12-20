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
        self.root.resizable(True, True)

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

    def _bind_mousewheel(self, widget, target_canvas):
        """Enable mouse wheel scrolling for the given widget/canvas pair."""

        def _on_mousewheel(event):
            delta = 0
            if hasattr(event, 'delta') and event.delta:
                delta = event.delta
            elif getattr(event, 'num', None) == 4:
                delta = 120
            elif getattr(event, 'num', None) == 5:
                delta = -120

            if delta == 0:
                return

            target_canvas.yview_scroll(int(-delta / 120), "units")
            return "break"

        widget.bind("<MouseWheel>", _on_mousewheel)
        widget.bind("<Shift-MouseWheel>", _on_mousewheel)
        widget.bind("<Button-4>", _on_mousewheel)
        widget.bind("<Button-5>", _on_mousewheel)

    def _setup_styles(self):
        ui_font = 'Microsoft YaHei UI'
        self.style.configure('LegendDialog.TFrame', background="#edf2f7")
        self.style.configure('LegendCard.TFrame', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('LegendHeader.TLabel', background="#edf2f7", foreground="#1a202c", font=(ui_font, 14, 'bold'))
        self.style.configure('LegendBody.TLabel', background="#ffffff", foreground="#475569", font=(ui_font, 10))
        self.style.configure('LegendCheck.TCheckbutton', background="#ffffff", foreground="#1a202c", font=(ui_font, 10))
        self.style.configure('LegendAccent.TButton', background="#2563eb", foreground="#ffffff", font=(ui_font, 10, 'bold'), padding=(12, 6))
        self.style.map('LegendAccent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')])
        self.style.configure('LegendSecondary.TButton', background="#ffffff", foreground="#2563eb", font=(ui_font, 10, 'bold'), padding=(12, 6))
        self.style.map('LegendSecondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])

    def _build_ui(self):
        outer = ttk.Frame(self.root, padding=(18, 18, 18, 14), style='LegendDialog.TFrame')
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        title = ttk.Label(
            outer,
            text=translate("Choose which groups stay visible"),
            style='LegendHeader.TLabel',
            wraplength=360,
            justify=tk.LEFT
        )
        title.grid(row=0, column=0, sticky=tk.W)

        card = ttk.Frame(outer, padding=14, style='LegendCard.TFrame')
        card.grid(row=1, column=0, sticky=tk.NSEW, pady=(12, 16))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        ttk.Label(
            card,
            text=translate("Uncheck any legend entries you want to hide from the plot."),
            style='LegendBody.TLabel',
            wraplength=340,
            justify=tk.LEFT
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 12))

        search_row = ttk.Frame(card, style='LegendCard.TFrame')
        search_row.grid(row=1, column=0, sticky=tk.EW, pady=(0, 10))
        search_row.columnconfigure(0, weight=1)

        ttk.Label(
            search_row,
            text=translate("Search groups"),
            style='LegendBody.TLabel'
        ).grid(row=0, column=0, sticky=tk.W)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        search_entry.grid(row=1, column=0, sticky=tk.EW, pady=(4, 0))
        search_entry.bind('<KeyRelease>', self._on_search_change)

        toolbar = ttk.Frame(card, style='LegendCard.TFrame')
        toolbar.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))

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
        self._group_widgets = {}

        list_container = ttk.Frame(card, style='LegendCard.TFrame')
        list_container.grid(row=3, column=0, sticky=tk.NSEW)
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        list_canvas = tk.Canvas(list_container, highlightthickness=0, bd=0, background="#ffffff")
        list_canvas.grid(row=0, column=0, sticky=tk.NSEW)

        list_scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=list_canvas.yview)
        list_scrollbar.grid(row=0, column=1, sticky=tk.NS)

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
            self._group_widgets[group] = cb
            self._bind_mousewheel(cb, list_canvas)

        self._bind_mousewheel(list_canvas, list_canvas)
        self._bind_mousewheel(list_frame, list_canvas)

        self.empty_label = ttk.Label(
            list_frame,
            text=translate("No legend entries match your search."),
            style='LegendBody.TLabel'
        )
        self.empty_label.pack(anchor=tk.W, pady=8)
        self.empty_label.pack_forget()

        self._filter_groups()

        button_row = ttk.Frame(outer, style='LegendDialog.TFrame')
        button_row.grid(row=2, column=0, sticky=tk.EW, pady=(0, 4))

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

    def _filter_groups(self):
        """Show only groups that match the current search query."""
        query = (self.search_var.get() or '').strip().lower()
        any_visible = False

        for group, widget in self._group_widgets.items():
            text = str(group).lower()
            if not query or query in text:
                if not widget.winfo_ismapped():
                    widget.pack(anchor=tk.W, pady=4)
                any_visible = True
            else:
                widget.pack_forget()

        if any_visible:
            self.empty_label.pack_forget()
        else:
            self.empty_label.pack(anchor=tk.W, pady=8)

    def _on_search_change(self, event=None):
        self._filter_groups()

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
