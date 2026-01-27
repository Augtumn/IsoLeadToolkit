"""
Sheet Selection Dialog
Simple dialog for selecting a sheet from an Excel file
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import os

from core.localization import translate


class SheetSelectionDialog:
    """Simple dialog for selecting a sheet"""
    
    def __init__(self, file_path, default_sheet=None):
        """
        Initialize sheet selection dialog
        
        Args:
            file_path: str, path to Excel file
        """
        self.file_path = file_path
        self.result = None
        self.default_sheet = default_sheet
        self.sheets = []
        
        # Load sheets
        try:
            self.sheets = list(pd.ExcelFile(file_path).sheet_names)
        except Exception as e:
            print(f"[ERROR] Could not load sheets: {e}", flush=True)
            return
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(translate("Select Sheet"))
        self.root.geometry("620x460")
        self.root.minsize(560, 420)
        self.root.configure(bg="#edf2f7")
        self.root.resizable(True, True)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

        self._setup_styles()
        self._create_widgets_with_scroll()

    def _create_widgets_with_scroll(self):
        """Create GUI widgets wrapped in a scrollable container"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, style='SheetDialog.TFrame')
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, bd=0, background="#edf2f7")
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        container = ttk.Frame(canvas, padding=(24, 20, 24, 20), style='SheetDialog.TFrame')
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
        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        title_label = ttk.Label(
            container,
            text=translate("Choose a Sheet"),
            style='SheetDialog.Header.TLabel'
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        info_label = ttk.Label(
            container,
            text=translate("Select the worksheet that contains the measurements you want to analyze."),
            style='SheetDialog.Subheader.TLabel',
            wraplength=460,
            justify=tk.LEFT
        )
        info_label.grid(row=1, column=0, sticky=tk.W, pady=(6, 16))

        card = ttk.Frame(container, padding=18, style='SheetDialog.Card.TFrame')
        card.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        workbook_name = os.path.basename(self.file_path)
        list_header = ttk.Label(
            card,
            text=translate("Sheets in {workbook}", workbook=workbook_name),
            style='SheetDialog.Body.TLabel'
        )
        list_header.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))

        list_frame = ttk.Frame(card, style='SheetDialog.CardBody.TFrame')
        list_frame.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        self.sheet_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            height=8,
            activestyle='dotbox',
            selectbackground='#2563eb',
            selectforeground='#ffffff',
            bd=0,
            highlightthickness=0,
            relief=tk.FLAT,
            font=('Microsoft YaHei UI', 11)
        )
        self.sheet_listbox.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        scrollbar.config(command=self.sheet_listbox.yview)

        for sheet in self.sheets:
            self.sheet_listbox.insert(tk.END, sheet)

        if self.sheets:
            if self.default_sheet in self.sheets:
                idx = self.sheets.index(self.default_sheet)
                self.sheet_listbox.selection_set(idx)
                self.sheet_listbox.see(idx)
            else:
                self.sheet_listbox.selection_set(0)
                self.sheet_listbox.see(0)

        self.sheet_listbox.bind('<Double-Button-1>', lambda e: self._ok_clicked())

        footer = ttk.Frame(container, style='SheetDialog.TFrame')
        footer.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(18, 0))
        footer.columnconfigure(0, weight=1)

        button_container = ttk.Frame(footer, style='SheetDialog.TFrame')
        button_container.grid(row=0, column=0, sticky=tk.E)

        ttk.Button(
            button_container,
            text=translate("Cancel"),
            style='SheetDialog.Secondary.TButton',
            command=self._cancel_clicked
        ).grid(row=0, column=0, padx=(0, 12))
        ttk.Button(
            button_container,
            text=translate("Continue"),
            style='SheetDialog.Accent.TButton',
            command=self._ok_clicked
        ).grid(row=0, column=1)

    def _setup_styles(self):
        """Configure ttk styles for the sheet dialog"""
        ui_font = 'Microsoft YaHei UI'
        self.style.configure('SheetDialog.TFrame', background="#edf2f7")
        self.style.configure('SheetDialog.Card.TFrame', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('SheetDialog.CardBody.TFrame', background="#ffffff")
        self.style.configure('SheetDialog.Header.TLabel', background="#edf2f7", foreground="#1a202c", font=(ui_font, 18, 'bold'))
        self.style.configure('SheetDialog.Subheader.TLabel', background="#edf2f7", foreground="#4a5568", font=(ui_font, 10))
        self.style.configure('SheetDialog.Body.TLabel', background="#ffffff", foreground="#475569", font=(ui_font, 11, 'bold'))
        self.style.configure('SheetDialog.Secondary.TButton', background="#ffffff", foreground="#2563eb", font=(ui_font, 10, 'bold'), padding=(10, 6))
        self.style.map('SheetDialog.Secondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])
        self.style.configure('SheetDialog.Accent.TButton', background="#2563eb", foreground="#ffffff", font=(ui_font, 11, 'bold'), padding=(12, 6))
        self.style.map('SheetDialog.Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')], foreground=[('disabled', '#d1d5db'), ('active', '#ffffff')])
    
    def _ok_clicked(self):
        """Handle OK button click"""
        selection = self.sheet_listbox.curselection()
        if not selection:
            messagebox.showwarning(
                translate("Error"),
                translate("Please select a sheet."),
            )
            return
        
        self.result = self.sheets[selection[0]]
        self.root.destroy()
    
    def _cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.root.destroy()
    
    def show(self):
        """Show dialog and return selected sheet"""
        print("[DEBUG] SheetSelectionDialog showing...", flush=True)
        self.root.mainloop()
        print(f"[DEBUG] Selected sheet: {self.result}", flush=True)
        return self.result


def get_sheet_selection(file_path, default_sheet=None):
    """
    Show sheet selection dialog
    
    Args:
        file_path: str, path to Excel file
    
    Returns:
        str, selected sheet name, or None if cancelled
    """
    dialog = SheetSelectionDialog(file_path, default_sheet=default_sheet)
    return dialog.show()
