"""
File Selection Dialog
For selecting CSV or Excel files
"""
import tkinter as tk
from tkinter import ttk, filedialog
import os

from localization import translate as t


class FileSelectionDialog:
    """Dialog for selecting data files"""
    
    def __init__(self):
        """Initialize file selection dialog"""
        self.result = None
        self.selected_file = None

        self.root = tk.Tk()
        self.root.title(t("Select Data File"))
        self.root.geometry("780x420")
        self.root.minsize(640, 340)
        self.root.configure(bg="#edf2f7")
        self.root.resizable(True, True)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

        self._setup_styles()
        self._create_widgets()

    def _setup_styles(self):
        """Configure ttk styles for a cohesive dialog appearance"""
        self.style.configure('FileDialog.TFrame', background="#edf2f7")
        self.style.configure('Card.TFrame', background="#ffffff", relief='flat', borderwidth=1)
        self.style.configure('Card.TLabelframe', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('Card.TLabelframe.Label', background="#ffffff", foreground="#1a202c", font=('Segoe UI', 12, 'bold'))
        self.style.configure('Header.TLabel', background="#edf2f7", foreground="#1a202c", font=('Segoe UI', 18, 'bold'))
        self.style.configure('Subheader.TLabel', background="#edf2f7", foreground="#4a5568", font=('Segoe UI', 10))
        self.style.configure('Body.TLabel', background="#ffffff", foreground="#4a5568", font=('Segoe UI', 10))
        self.style.configure('Path.TLabel', background="#ffffff", foreground="#1a202c", font=('Segoe UI', 11, 'bold'))
        self.style.configure('Muted.TLabel', background="#ffffff", foreground="#94a3b8", font=('Segoe UI', 10))
        self.style.configure('Accent.TButton', background="#2563eb", foreground="#ffffff", font=('Segoe UI', 11, 'bold'), padding=(12, 6))
        self.style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')], foreground=[('disabled', '#d1d5db'), ('active', '#ffffff')])
        self.style.configure('Secondary.TButton', background="#ffffff", foreground="#2563eb", font=('Segoe UI', 10, 'bold'), padding=(10, 5))
        self.style.map('Secondary.TButton', background=[('active', '#e2e8f0')])

    def _create_widgets(self):
        """Create GUI widgets"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, style='FileDialog.TFrame')
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, bd=0, background="#edf2f7")
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        container = ttk.Frame(canvas, padding=(24, 20, 24, 20), style='FileDialog.TFrame')
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

        header = ttk.Label(container, text=t("Select Data File"), style='Header.TLabel')
        header.grid(row=0, column=0, sticky=tk.W)

        subtitle = ttk.Label(
            container,
            text=t("Choose a CSV or Excel file (.csv, .xlsx, .xls) that contains the isotope dataset you want to explore."),
            style='Subheader.TLabel',
            wraplength=640,
            justify=tk.LEFT
        )
        subtitle.grid(row=1, column=0, sticky=tk.W, pady=(6, 18))

        card = ttk.Frame(container, padding=18, style='Card.TFrame')
        card.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        card.columnconfigure(0, weight=1)

        card_header = ttk.Label(card, text=t("Current selection"), style='Body.TLabel')
        card_header.grid(row=0, column=0, sticky=tk.W)

        self.file_label = ttk.Label(card, text=t("No file selected"), style='Muted.TLabel', wraplength=640, justify=tk.LEFT)
        self.file_label.grid(row=1, column=0, sticky=tk.W, pady=(6, 10))

        helper_text = ttk.Label(
            card,
            text=t("Tip: For Excel workbooks, you can pick the sheet in the next step."),
            style='Body.TLabel'
        )
        helper_text.grid(row=2, column=0, sticky=tk.W)

        button_row = ttk.Frame(container, style='FileDialog.TFrame')
        button_row.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(18, 12))
        button_row.columnconfigure(0, weight=1)

        button_group = ttk.Frame(button_row, style='FileDialog.TFrame')
        button_group.grid(row=0, column=0, sticky=tk.W)

        ttk.Button(button_group, text=t("Browse..."), style='Accent.TButton', command=self._browse_file).grid(row=0, column=0, padx=(0, 10))
        ttk.Button(button_group, text=t("Clear Selection"), style='Secondary.TButton', command=self._clear_file).grid(row=0, column=1)

        separator = ttk.Separator(container, orient=tk.HORIZONTAL)
        separator.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=12)

        footer = ttk.Frame(container, style='FileDialog.TFrame')
        footer.grid(row=5, column=0, sticky=(tk.W, tk.E))
        footer.columnconfigure(0, weight=1)

        button_container = ttk.Frame(footer, style='FileDialog.TFrame')
        button_container.grid(row=0, column=0, sticky=tk.E)

        ttk.Button(button_container, text=t("Cancel"), style='Secondary.TButton', command=self._cancel_clicked).grid(row=0, column=0, padx=(0, 12))
        ttk.Button(button_container, text=t("Continue"), style='Accent.TButton', command=self._ok_clicked).grid(row=0, column=1)
    
    def _browse_file(self):
        """Open file browser"""
        print("[DEBUG] File browser opening...", flush=True)
        
        file_types = [
            (t("Excel files"), "*.xlsx *.xls"),
            (t("CSV files"), "*.csv"),
            (t("All files"), "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title=t("Select Data File"),
            filetypes=file_types,
            defaultextension=".xlsx"
        )
        
        if file_path:
            print(f"[DEBUG] File selected: {file_path}", flush=True)
            self.selected_file = file_path
            display_path = os.path.basename(file_path)
            directory = os.path.dirname(file_path)
            self.file_label.config(text=f"{display_path}\n{directory}", style='Path.TLabel')
    
    def _clear_file(self):
        """Clear selected file"""
        self.selected_file = None
        self.file_label.config(text=t("No file selected"), style='Muted.TLabel')
    
    def _ok_clicked(self):
        """Handle OK button click"""
        if not self.selected_file:
            print("[WARNING] No file selected", flush=True)
            return
        
        self.result = {'file': self.selected_file}
        print(f"[DEBUG] FileSelectionDialog result: {self.result}", flush=True)
        self.root.destroy()
    
    def _cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.root.destroy()
    
    def show(self):
        """Show dialog and return selected file"""
        print("[DEBUG] FileSelectionDialog showing...", flush=True)
        self.root.mainloop()
        return self.result


def get_file_sheet_selection():
    """
    Show file selection dialog
    
    Returns:
        dict with 'file' key, or None if cancelled
    """
    dialog = FileSelectionDialog()
    return dialog.show()
