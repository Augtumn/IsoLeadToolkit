"""
File Selection Dialog
For selecting CSV or Excel files
"""
import tkinter as tk
from tkinter import ttk, filedialog
import os

from localization import translate as t, available_languages, set_language
from state import app_state


class FileSelectionDialog:
    """Dialog for selecting data files"""
    
    def __init__(self):
        """Initialize file selection dialog"""
        self.result = None
        self.selected_file = None
        self._translations = []

        self.root = tk.Tk()
        self.root.title(t("Select Data File"))
        self.root.geometry("780x480")
        self.root.minsize(640, 400)
        self.root.configure(bg="#edf2f7")
        self.root.resizable(True, True)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

        self._setup_styles()
        self._create_widgets()
        self._refresh_language()

    def _register_translation(self, widget, key, attr='text'):
        """Register a widget for translation updates"""
        self._translations.append({'widget': widget, 'key': key, 'attr': attr})

    def _refresh_language(self):
        """Update all registered widgets with current language"""
        current_lang = app_state.language
        
        for item in self._translations:
            try:
                widget = item['widget']
                key = item['key']
                attr = item['attr']
                
                # Special handling for file_label to avoid overwriting selected path
                if widget == getattr(self, 'file_label', None) and self.selected_file:
                    continue

                if widget.winfo_exists():
                    # Explicitly pass language to translate to ensure correct lookup
                    translated = t(key, language=current_lang)
                    
                    if attr == 'title':
                        widget.title(translated)
                    else:
                        # Force update for some widgets if needed
                        widget.configure(**{attr: translated})
                        
                        # For Comboboxes or other complex widgets, we might need more
                        if isinstance(widget, ttk.Button):
                            # Sometimes style changes need a redraw?
                            pass
            except Exception:
                pass
        
        # Force UI update
        self.root.update_idletasks()

    def _on_language_change(self, event=None):
        """Handle language selection change"""
        selected_label = self.language_combobox.get()
        
        # Find code from label "code - label"
        code = next((k for k, v in self._language_labels.items() if f"{k} - {v}" == selected_label), None)
        
        if code is None:
            # Fallback if format doesn't match
            code = selected_label.split(' - ')[0]
        
        if code:
            success = set_language(code)
            
            if success:
                app_state.language = code
                self._refresh_language()
            
            # Update combobox values to reflect new language (if labels were translated)
            # But here labels are static names like "English", "中文"
            pass

    def _setup_styles(self):
        """Configure ttk styles for a cohesive dialog appearance"""
        ui_font = 'Microsoft YaHei UI'
        
        self.style.configure('FileDialog.TFrame', background="#edf2f7")
        self.style.configure('Card.TFrame', background="#ffffff", relief='flat', borderwidth=1)
        self.style.configure('Card.TLabelframe', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('Card.TLabelframe.Label', background="#ffffff", foreground="#1a202c", font=(ui_font, 12, 'bold'))
        self.style.configure('Header.TLabel', background="#edf2f7", foreground="#1a202c", font=(ui_font, 18, 'bold'))
        self.style.configure('Subheader.TLabel', background="#edf2f7", foreground="#4a5568", font=(ui_font, 10))
        self.style.configure('Body.TLabel', background="#ffffff", foreground="#4a5568", font=(ui_font, 10))
        self.style.configure('Path.TLabel', background="#ffffff", foreground="#1a202c", font=(ui_font, 11, 'bold'))
        self.style.configure('Muted.TLabel', background="#ffffff", foreground="#94a3b8", font=(ui_font, 10))
        self.style.configure('Accent.TButton', background="#2563eb", foreground="#ffffff", font=(ui_font, 11, 'bold'), padding=(12, 6))
        self.style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')], foreground=[('disabled', '#d1d5db'), ('active', '#ffffff')])
        self.style.configure('Secondary.TButton', background="#ffffff", foreground="#2563eb", font=(ui_font, 10, 'bold'), padding=(10, 5))
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

        # Header Row with Language Selector
        header_frame = ttk.Frame(container, style='FileDialog.TFrame')
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        header = ttk.Label(header_frame, text=t("Select Data File"), style='Header.TLabel')
        header.pack(side=tk.LEFT)
        self._register_translation(header, "Select Data File")
        self._register_translation(self.root, "Select Data File", attr='title')

        # Language Selector
        self._language_labels = dict(available_languages())
        lang_frame = ttk.Frame(header_frame, style='FileDialog.TFrame')
        lang_frame.pack(side=tk.RIGHT)
        
        ttk.Label(lang_frame, text="Language:", style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        
        current_lang = app_state.language or 'en'
        lang_values = [f"{k} - {v}" for k, v in self._language_labels.items()]
        self.language_combobox = ttk.Combobox(
            lang_frame, 
            values=lang_values,
            state="readonly",
            width=15
        )
        current_label = f"{current_lang} - {self._language_labels.get(current_lang, current_lang)}"
        if current_label in lang_values:
            self.language_combobox.set(current_label)
        elif lang_values:
            self.language_combobox.current(0)
            
        self.language_combobox.pack(side=tk.LEFT)
        self.language_combobox.bind("<<ComboboxSelected>>", self._on_language_change)

        subtitle = ttk.Label(
            container,
            text=t("Choose a CSV or Excel file (.csv, .xlsx, .xls) that contains the isotope dataset you want to explore."),
            style='Subheader.TLabel',
            wraplength=640,
            justify=tk.LEFT
        )
        subtitle.grid(row=1, column=0, sticky=tk.W, pady=(6, 18))
        self._register_translation(subtitle, "Choose a CSV or Excel file (.csv, .xlsx, .xls) that contains the isotope dataset you want to explore.")

        card = ttk.Frame(container, padding=18, style='Card.TFrame')
        card.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        card.columnconfigure(0, weight=1)

        card_header = ttk.Label(card, text=t("Current selection"), style='Body.TLabel')
        card_header.grid(row=0, column=0, sticky=tk.W)
        self._register_translation(card_header, "Current selection")

        self.file_label = ttk.Label(card, text=t("No file selected"), style='Muted.TLabel', wraplength=640, justify=tk.LEFT)
        self.file_label.grid(row=1, column=0, sticky=tk.W, pady=(6, 10))
        self._register_translation(self.file_label, "No file selected")

        helper_text = ttk.Label(
            card,
            text=t("Tip: For Excel workbooks, you can pick the sheet in the next step."),
            style='Body.TLabel'
        )
        helper_text.grid(row=2, column=0, sticky=tk.W)
        self._register_translation(helper_text, "Tip: For Excel workbooks, you can pick the sheet in the next step.")

        button_row = ttk.Frame(container, style='FileDialog.TFrame')
        button_row.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(18, 12))
        button_row.columnconfigure(0, weight=1)

        button_group = ttk.Frame(button_row, style='FileDialog.TFrame')
        button_group.grid(row=0, column=0, sticky=tk.W)

        browse_btn = ttk.Button(button_group, text=t("Browse..."), style='Accent.TButton', command=self._browse_file)
        browse_btn.grid(row=0, column=0, padx=(0, 10))
        self._register_translation(browse_btn, "Browse...")
        
        clear_btn = ttk.Button(button_group, text=t("Clear Selection"), style='Secondary.TButton', command=self._clear_file)
        clear_btn.grid(row=0, column=1)
        self._register_translation(clear_btn, "Clear Selection")

        separator = ttk.Separator(container, orient=tk.HORIZONTAL)
        separator.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=12)

        footer = ttk.Frame(container, style='FileDialog.TFrame')
        footer.grid(row=5, column=0, sticky=(tk.W, tk.E))
        footer.columnconfigure(0, weight=1)

        button_container = ttk.Frame(footer, style='FileDialog.TFrame')
        button_container.grid(row=0, column=0, sticky=tk.E)

        cancel_btn = ttk.Button(button_container, text=t("Cancel"), style='Secondary.TButton', command=self._cancel_clicked)
        cancel_btn.grid(row=0, column=0, padx=(0, 12))
        self._register_translation(cancel_btn, "Cancel")
        
        continue_btn = ttk.Button(button_container, text=t("Continue"), style='Accent.TButton', command=self._ok_clicked)
        continue_btn.grid(row=0, column=1)
        self._register_translation(continue_btn, "Continue")
    
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
