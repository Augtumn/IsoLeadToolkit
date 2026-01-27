"""
Data Configuration Dialog
Allows users to select grouping columns and data columns from loaded data
"""
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd

from core.localization import translate


class DataConfigDialog:
    """Dialog for selecting data and grouping columns"""
    
    def __init__(self, df, default_group_cols=None, default_data_cols=None):
        """
        Initialize data configuration dialog
        
        Args:
            df: pandas DataFrame with all columns
        """
        self.df = df
        self.result = None
        
        # Get available columns
        self.all_columns = list(df.columns)
        
        # Create main window
        self.root = tk.Tk()
        self.root.title(translate("Configure Data Columns"))
        self.root.geometry("980x700")
        self.root.minsize(900, 620)
        self.root.configure(bg="#edf2f7")
        self.root.resizable(True, True)

        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

        # Initialize with defaults (if provided) and filter to available columns
        available_cols = set(self.all_columns)
        self.selected_group_cols = set(default_group_cols or []).intersection(available_cols)
        self.selected_data_cols = set(default_data_cols or []).intersection(available_cols)
        self.group_checkbuttons = {}
        self.data_checkbuttons = {}
        self.group_widgets = []
        self.data_widgets = []
        self.group_search_var = tk.StringVar(master=self.root)
        self.data_search_var = tk.StringVar(master=self.root)

        self._setup_styles()
        self._create_widgets_with_scroll()

    def _create_widgets_with_scroll(self):
        """Create GUI widgets wrapped in a scrollable container"""
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        outer = ttk.Frame(self.root, style='DataConfig.TFrame')
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0, bd=0, background="#edf2f7")
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        container = ttk.Frame(canvas, padding=(10, 10, 10, 10), style='DataConfig.TFrame')
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
            text=translate("Select Columns"),
            style='DataConfig.Header.TLabel'
        )
        title_label.grid(row=0, column=0, sticky=tk.W)

        info_label = ttk.Label(
            container,
            text=translate("Choose grouping columns (used for coloring and filtering) and numeric data columns for embedding."),
            style='DataConfig.Subheader.TLabel',
            wraplength=760,
            justify=tk.LEFT
        )
        info_label.grid(row=1, column=0, sticky=tk.W, pady=(6, 18))

        content = ttk.Frame(container, style='DataConfig.TFrame')
        content.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)

        self._build_column_card(
            parent=content,
            column_index=0,
            title=translate("Grouping Columns"),
            description=translate("Pick one or more categorical columns to color and organize the scatter plot."),
            selection_type='group'
        )

        self._build_column_card(
            parent=content,
            column_index=1,
            title=translate("Data Columns"),
            description=translate("Choose numeric measurements that feed into UMAP or t-SNE embeddings."),
            selection_type='data'
        )

        tips_label = ttk.Label(
            container,
            text=translate("Hint: Data columns must be numeric. Grouping columns can be any categorical field."),
            style='DataConfig.Footer.TLabel'
        )
        tips_label.grid(row=3, column=0, sticky=tk.W, pady=(18, 10))

        footer = ttk.Frame(container, style='DataConfig.TFrame')
        footer.grid(row=4, column=0, sticky=(tk.W, tk.E))
        footer.columnconfigure(0, weight=1)

        button_container = ttk.Frame(footer, style='DataConfig.TFrame')
        button_container.grid(row=0, column=0, sticky=tk.E)

        ttk.Button(
            button_container,
            text=translate("Cancel"),
            style='DataConfig.Secondary.TButton',
            command=self._cancel_clicked
        ).grid(row=0, column=0, padx=(0, 12))
        ttk.Button(
            button_container,
            text=translate("Apply"),
            style='DataConfig.Accent.TButton',
            command=self._ok_clicked
        ).grid(row=0, column=1)

    def _setup_styles(self):
        """Configure ttk styles for the dialog"""
        self.style.configure('DataConfig.TFrame', background="#edf2f7")
        self.style.configure('DataConfig.Card.TFrame', background="#ffffff", borderwidth=1, relief='solid')
        self.style.configure('DataConfig.CardBody.TFrame', background="#ffffff")
        self.style.configure('DataConfig.Header.TLabel', background="#edf2f7", foreground="#1a202c", font=('Segoe UI', 20, 'bold'))
        self.style.configure('DataConfig.Subheader.TLabel', background="#edf2f7", foreground="#4a5568", font=('Segoe UI', 11))
        self.style.configure('DataConfig.SectionHeader.TLabel', background="#ffffff", foreground="#1a202c", font=('Segoe UI', 13, 'bold'))
        self.style.configure('DataConfig.Body.TLabel', background="#ffffff", foreground="#475569", font=('Segoe UI', 10))
        self.style.configure('DataConfig.Footer.TLabel', background="#edf2f7", foreground="#475569", font=('Segoe UI', 10))
        self.style.configure('DataConfig.Accent.TButton', background="#2563eb", foreground="#ffffff", font=('Segoe UI', 11, 'bold'), padding=(14, 6))
        self.style.map('DataConfig.Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')], foreground=[('disabled', '#d1d5db'), ('active', '#ffffff')])
        self.style.configure('DataConfig.Secondary.TButton', background="#ffffff", foreground="#2563eb", font=('Segoe UI', 10, 'bold'), padding=(12, 5))
        self.style.map('DataConfig.Secondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])
        self.style.configure('DataConfig.Toolbar.TButton', background="#f1f5f9", foreground="#1f2937", font=('Segoe UI', 9, 'bold'), padding=(8, 4))
        self.style.map('DataConfig.Toolbar.TButton', background=[('active', '#e2e8f0')])
        self.style.configure('DataConfig.Checkbutton.TCheckbutton', background="#ffffff", foreground="#1f2937", font=('Segoe UI', 10))
        self.style.map('DataConfig.Checkbutton.TCheckbutton', background=[('active', '#ffffff')], foreground=[('active', '#1f2937')])

    def _build_column_card(self, parent, column_index, title, description, selection_type):
        """Create a card containing selectable column checkboxes"""
        card = ttk.Frame(parent, padding=10, style='DataConfig.Card.TFrame')
        card.grid(row=0, column=column_index, sticky=(tk.N, tk.S, tk.E, tk.W), padx=(0, 10) if column_index == 0 else (10, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(4, weight=1)

        header = ttk.Label(card, text=title, style='DataConfig.SectionHeader.TLabel')
        header.grid(row=0, column=0, sticky=tk.W)

        desc = ttk.Label(card, text=description, style='DataConfig.Body.TLabel', wraplength=480, justify=tk.LEFT)
        desc.grid(row=1, column=0, sticky=tk.W, pady=(4, 12))

        toolbar = ttk.Frame(card, style='DataConfig.CardBody.TFrame')
        toolbar.grid(row=2, column=0, sticky=tk.W, pady=(0, 10))

        if selection_type == 'group':
            ttk.Button(
                toolbar,
                text=translate("Select all"),
                style='DataConfig.Toolbar.TButton',
                command=self._select_all_groups
            ).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(
                toolbar,
                text=translate("Clear"),
                style='DataConfig.Toolbar.TButton',
                command=self._clear_groups
            ).pack(side=tk.LEFT)
            ttk.Button(
                toolbar,
                text=translate("Recommend"),
                style='DataConfig.Toolbar.TButton',
                command=self._recommend_groups
            ).pack(side=tk.LEFT, padx=(8, 0))
        else:
            ttk.Button(
                toolbar,
                text=translate("Select all"),
                style='DataConfig.Toolbar.TButton',
                command=self._select_all_data
            ).pack(side=tk.LEFT, padx=(0, 8))
            ttk.Button(
                toolbar,
                text=translate("Clear"),
                style='DataConfig.Toolbar.TButton',
                command=self._clear_data
            ).pack(side=tk.LEFT)
            ttk.Button(
                toolbar,
                text=translate("Recommend"),
                style='DataConfig.Toolbar.TButton',
                command=self._recommend_data
            ).pack(side=tk.LEFT, padx=(8, 0))

        # Search field
        search_frame = ttk.Frame(card, style='DataConfig.CardBody.TFrame')
        search_frame.grid(row=3, column=0, sticky=tk.EW, pady=(6, 10))
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text=translate("Search"), style='DataConfig.Body.TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 6))
        search_var = self.group_search_var if selection_type == 'group' else self.data_search_var
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.grid(row=0, column=1, sticky=tk.EW)
        search_entry.bind('<KeyRelease>', lambda e, s=selection_type: self._filter_columns(s))

        canvas = tk.Canvas(card, highlightthickness=0, bd=0, background="#ffffff")
        canvas.grid(row=4, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        scrollbar = ttk.Scrollbar(card, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.grid(row=4, column=1, sticky=(tk.N, tk.S))

        scrollable_frame = ttk.Frame(canvas, style='DataConfig.CardBody.TFrame')
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def _sync_scrollregion(event, target_canvas=canvas):
            try:
                target_canvas.configure(scrollregion=target_canvas.bbox("all"))
            except tk.TclError:
                pass

        def _resize_canvas(event, target_canvas=canvas, window_id=canvas_window):
            try:
                target_canvas.itemconfigure(window_id, width=event.width)
            except tk.TclError:
                pass

        scrollable_frame.bind("<Configure>", _sync_scrollregion)
        canvas.bind("<Configure>", _resize_canvas)

        # Enable mousewheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            return "break"

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        # Bind enter/leave events to the card to enable/disable scrolling
        card.bind("<Enter>", _bind_mousewheel)
        card.bind("<Leave>", _unbind_mousewheel)

        for col in self.all_columns:
            is_numeric = pd.api.types.is_numeric_dtype(self.df[col])
            
            # Filter for Data Columns: only show numeric
            if selection_type == 'data' and not is_numeric:
                continue

            var = tk.BooleanVar(value=(col in self.selected_group_cols if selection_type == 'group' else col in self.selected_data_cols))
            dtype_label = translate("numeric") if is_numeric else translate("text")
            display_text = translate("{column} ({dtype})", column=col, dtype=dtype_label)
            cb = ttk.Checkbutton(
                scrollable_frame,
                text=display_text,
                variable=var,
                style='DataConfig.Checkbutton.TCheckbutton'
            )
            cb.pack(anchor=tk.W, pady=3)

            if selection_type == 'group':
                cb.configure(command=lambda c=col, v=var: self._on_group_check(c, v))
                self.group_checkbuttons[col] = var
                self.group_widgets.append({'col': col, 'widget': cb, 'text': display_text})
            else:
                cb.configure(command=lambda c=col, v=var: self._on_data_check(c, v))
                self.data_checkbuttons[col] = var
                self.data_widgets.append({'col': col, 'widget': cb, 'text': display_text})

        return card
    
    def _on_group_check(self, col, var):
        """Handle grouping column checkbox change"""
        if var.get():
            self.selected_group_cols.add(col)
        else:
            self.selected_group_cols.discard(col)
    
    def _on_data_check(self, col, var):
        """Handle data column checkbox change"""
        if var.get():
            self.selected_data_cols.add(col)
        else:
            self.selected_data_cols.discard(col)
    
    def _select_all_groups(self):
        """Select all grouping columns"""
        for col, var in self.group_checkbuttons.items():
            var.set(True)
            self.selected_group_cols.add(col)
    
    def _clear_groups(self):
        """Clear grouping column selection"""
        for col, var in self.group_checkbuttons.items():
            var.set(False)
            self.selected_group_cols.discard(col)
    
    def _select_all_data(self):
        """Select all data columns"""
        for col, var in self.data_checkbuttons.items():
            var.set(True)
            self.selected_data_cols.add(col)
    
    def _clear_data(self):
        """Clear data column selection"""
        for col, var in self.data_checkbuttons.items():
            var.set(False)
            self.selected_data_cols.discard(col)

    def _filter_columns(self, selection_type):
        query = (self.group_search_var.get() if selection_type == 'group' else self.data_search_var.get()).strip().lower()
        widgets = self.group_widgets if selection_type == 'group' else self.data_widgets
        for item in widgets:
            widget = item['widget']
            text = item['text'].lower()
            if not query or query in text:
                if not widget.winfo_ismapped():
                    widget.pack(anchor=tk.W, pady=3)
            else:
                if widget.winfo_ismapped():
                    widget.pack_forget()

    def _recommend_groups(self):
        """Recommend grouping columns based on common names"""
        preferred = ['序号', '样品', '样品编号', 'Sample', 'Sample ID', 'ID', 'Group', '组']
        # Clear current
        self._clear_groups()
        # Pick preferred if present
        for name in preferred:
            if name in self.group_checkbuttons:
                self.group_checkbuttons[name].set(True)
                self.selected_group_cols.add(name)
                return
        # Fallback: first non-numeric column
        for col in self.all_columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]) and col in self.group_checkbuttons:
                self.group_checkbuttons[col].set(True)
                self.selected_group_cols.add(col)
                return

    def _recommend_data(self):
        """Recommend data columns for isotope plotting"""
        preferred = ['206Pb/204Pb', '207Pb/204Pb', '208Pb/204Pb']
        self._clear_data()
        found = [c for c in preferred if c in self.data_checkbuttons]
        if found:
            for col in found:
                self.data_checkbuttons[col].set(True)
                self.selected_data_cols.add(col)
            return
        # Fallback: select all numeric columns
        for col, var in self.data_checkbuttons.items():
            var.set(True)
            self.selected_data_cols.add(col)
    
    def _ok_clicked(self):
        """Handle OK button click"""
        # Get selected columns from checkbuttons
        selected_groups = list(self.selected_group_cols)
        selected_data = list(self.selected_data_cols)
        
        # Validation
        if not selected_groups:
            messagebox.showwarning(
                translate("Validation Error"),
                translate("Please select at least one grouping column.")
            )
            return
        
        if not selected_data:
            messagebox.showwarning(
                translate("Validation Error"),
                translate("Please select at least one data column.")
            )
            return
        
        # Check that data columns are numeric
        try:
            for col in selected_data:
                if not pd.api.types.is_numeric_dtype(self.df[col]):
                    messagebox.showwarning(
                        translate("Validation Error"),
                        translate("Data column '{column}' is not numeric. Please select only numeric columns for data.", column=col)
                    )
                    return
        except Exception as e:
            messagebox.showerror(
                translate("Error"),
                translate("Error validating columns: {error}", error=e)
            )
            return
        
        # Store result
        self.result = {
            'group_cols': selected_groups,
            'data_cols': selected_data
        }
        
        self.root.destroy()
    
    def _cancel_clicked(self):
        """Handle Cancel button click"""
        self.result = None
        self.root.destroy()
    
    def show(self):
        """Show dialog and return result"""
        self.root.mainloop()
        return self.result


def get_data_configuration(df, default_group_cols=None, default_data_cols=None):
    """
    Show data configuration dialog
    
    Args:
        df: pandas DataFrame
    
    Returns:
        dict with keys 'group_cols' and 'data_cols', or None if cancelled
    """
    dialog = DataConfigDialog(
        df,
        default_group_cols=default_group_cols,
        default_data_cols=default_data_cols
    )
    return dialog.show()
