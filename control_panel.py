"""
Control Panel - Interactive Parameter Adjustment
Tkinter-based control panel for UMAP/t-SNE parameters and visualization settings
"""
import os
import re
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox, simpledialog, filedialog

import pandas as pd

from localization import translate, available_languages, set_language
from state import app_state
import state as state_module
from events import toggle_selection_mode


class ControlPanel:
    """Interactive control panel for algorithm parameters"""
    
    def __init__(self, callback):
        """
        Initialize control panel
        
        Args:
            callback: function to call when parameters change
        """
        self.callback = callback
        self._translations = []

        # Reuse Matplotlib's Tk root when available so the panel shares the
        # same event loop and remains responsive while plt.show() runs.
        master = tk._default_root
        self._owns_master = False
        if master is None:
            master = tk.Tk()
            master.withdraw()
            self._owns_master = True

        self.master = master
        self.root = tk.Toplevel(master)
        self.root.title(self._translate("Control Panel"))
        self._register_translation(self.root, "Control Panel", attr='title')
        self.root.geometry("520x820")
        self.root.minsize(420, 620)
        self.root.resizable(True, True)
        self.root.configure(bg="#edf2f7")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.is_visible = True

        self.primary_bg = "#edf2f7"
        self.card_bg = "#ffffff"
        self.style = None
        self._language_labels = dict(available_languages())
        self.language_choice = None
        self.language_combobox = None
        self._setup_styles()
        
        # Store slider references
        self.sliders = {}
        self.labels = {}
        self.radio_vars = {}
        self.check_vars = {}  # For checkboxes
        self._slider_after = {}
        self._slider_steps = {}
        self._slider_delay_ms = 350

        self.selection_button = None
        self.selection_status = None
        self.export_csv_button = None
        self.export_excel_button = None
        
        self._create_widgets()
        self._refresh_language()
        self.update_selection_controls()
        app_state.register_language_listener(self.refresh_language)

        # Try to raise the panel so it is not hidden behind the figure window.
        try:
            if master is not None:
                self.root.transient(master)
            self.root.lift()
            self.root.focus_force()
        except Exception:
            pass
    
    def _create_widgets(self):
        """Create GUI widgets with improved styling"""
        self.root.columnconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding=(18, 18, 18, 14), style='ControlPanel.TFrame')
        container.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(container, text=self._translate("Visualization Controls"), style='Header.TLabel')
        header.pack(anchor=tk.W)
        self._register_translation(header, "Visualization Controls")

        subtitle = ttk.Label(
            container,
            text=self._translate("Fine-tune algorithm settings and instantly preview the updated embedding."),
            style='Subheader.TLabel',
            wraplength=440,
            justify=tk.LEFT
        )
        subtitle.pack(anchor=tk.W, pady=(4, 14))
        self._register_translation(subtitle, "Fine-tune algorithm settings and instantly preview the updated embedding.")

        canvas_frame = ttk.Frame(container, style='ControlPanel.TFrame')
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(0, 6))

        main_canvas = tk.Canvas(
            canvas_frame,
            highlightthickness=0,
            bd=0,
            background=self.primary_bg
        )
        main_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollable_frame = ttk.Frame(main_canvas, style='ControlPanel.TFrame')
        canvas_window = main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        main_canvas.bind(
            "<Configure>",
            lambda e: main_canvas.itemconfigure(canvas_window, width=e.width)
        )

        main_canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.config(command=main_canvas.yview)

        self._create_language_controls(scrollable_frame)

        # ========== Algorithm & Dimensionality Selection ==========
        if not getattr(app_state, 'render_mode', None):
            app_state.render_mode = getattr(app_state, 'algorithm', 'UMAP')
        self.radio_vars['render_mode'] = tk.StringVar(value=app_state.render_mode)

        algo_section = self._create_section(
            scrollable_frame,
            "Projection Mode",
            "Select between UMAP or t-SNE embeddings, or display raw measurements in either 2D or 3D space."
        )

        selection_grid = ttk.Frame(algo_section, style='CardBody.TFrame')
        selection_grid.pack(fill=tk.X, pady=(4, 0))

        options = [
            ("UMAP Embedding", "UMAP"),
            ("t-SNE Embedding", "tSNE"),
            ("PCA Embedding", "PCA"),
            ("2D Scatter (raw)", "2D"),
            ("3D Scatter (raw)", "3D"),
        ]

        for idx, (label_key, value) in enumerate(options):
            column = idx // 2
            row = idx % 2
            cell = ttk.Frame(selection_grid, style='CardBody.TFrame')
            cell.grid(row=row, column=column, sticky=tk.W, padx=(0 if column == 0 else 16, 0), pady=2)
            radio = ttk.Radiobutton(
                cell,
                text=self._translate(label_key),
                variable=self.radio_vars['render_mode'],
                value=value,
                command=self._on_change,
                style='Option.TRadiobutton'
            )
            radio.pack(anchor=tk.W)
            self._register_translation(radio, label_key)

        for col in range(2):
            selection_grid.columnconfigure(col, weight=1)

        # ========== UMAP Parameters ==========
        umap_section = self._create_section(
            scrollable_frame,
            "UMAP Parameters",
            "Control neighbourhood size and how tightly points cluster."
        )

        self._add_slider(
            umap_section,
            key='umap_n',
            label_text="n_neighbors",
            minimum=2,
            maximum=50,
            initial=app_state.umap_params['n_neighbors'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            umap_section,
            key='umap_d',
            label_text="min_dist",
            minimum=0.0,
            maximum=1.0,
            initial=app_state.umap_params['min_dist'],
            formatter=lambda v: f"{float(v):.2f}",
            step=0.01
        )

        self._add_slider(
            umap_section,
            key='umap_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.umap_params['random_state'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        # ========== t-SNE Parameters ==========
        tsne_section = self._create_section(
            scrollable_frame,
            "t-SNE Parameters",
            "Adjust perplexity and learning rate to refine t-SNE embeddings."
        )

        self._add_slider(
            tsne_section,
            key='tsne_p',
            label_text="perplexity",
            minimum=5,
            maximum=100,
            initial=app_state.tsne_params['perplexity'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            tsne_section,
            key='tsne_lr',
            label_text="learning_rate",
            minimum=10,
            maximum=1000,
            initial=app_state.tsne_params['learning_rate'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        # ========== Common Parameters ==========
        common_section = self._create_section(
            scrollable_frame,
            "Common Settings",
            "Options shared by both algorithms, including point styling and grouping."
        )

        self._add_slider(
            common_section,
            key='size',
            label_text="Point size",
            minimum=10,
            maximum=200,
            initial=app_state.point_size,
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        # Ellipse Checkbox
        self.check_vars['ellipses'] = tk.BooleanVar(value=app_state.show_ellipses)
        ellipse_check = ttk.Checkbutton(
            common_section,
            text=self._translate("Show Confidence Ellipses"),
            variable=self.check_vars['ellipses'],
            command=self._on_change,
            style='Option.TRadiobutton'  # Reusing radio style for consistency
        )
        ellipse_check.pack(anchor=tk.W, pady=(4, 8))
        self._register_translation(ellipse_check, "Show Confidence Ellipses")

        group_label = ttk.Label(
            common_section,
            text=self._translate("Group column"),
            style='FieldLabel.TLabel'
        )
        group_label.pack(anchor=tk.W, pady=(12, 4))
        self._register_translation(group_label, "Group column")

        self.radio_vars['group'] = tk.StringVar(value=app_state.last_group_col or '')

        group_container = ttk.Frame(common_section, style='CardBody.TFrame')
        group_container.pack(fill=tk.X)
        self.group_container = group_container
        self.group_placeholder = None

        if app_state.group_cols:
            for col in app_state.group_cols:
                ttk.Radiobutton(
                    group_container,
                    text=col,
                    variable=self.radio_vars['group'],
                    value=col,
                    command=self._on_change,
                    style='Option.TRadiobutton'
                ).pack(anchor=tk.W, pady=2)
        else:
            placeholder = ttk.Label(
                group_container,
                text=self._translate("Load data to unlock grouping options."),
                style='BodyMuted.TLabel',
                wraplength=400,
                justify=tk.LEFT
            )
            placeholder.pack(anchor=tk.W, pady=4)
            self.group_placeholder = placeholder
            self._register_translation(placeholder, "Load data to unlock grouping options.")

        legend_tools = ttk.Frame(common_section, style='CardBody.TFrame')
        legend_tools.pack(fill=tk.X, pady=(12, 0))

        filter_button = ttk.Button(
            legend_tools,
            text=self._translate("Filter legend..."),
            style='Secondary.TButton',
            command=self._open_legend_filter
        )
        filter_button.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(filter_button, "Filter legend...")

        reload_button = ttk.Button(
            legend_tools,
            text=self._translate("Reload data..."),
            style='Secondary.TButton',
            command=self._reload_data
        )
        reload_button.pack(side=tk.LEFT)
        self._register_translation(reload_button, "Reload data...")

        selection_section = self._create_section(
            scrollable_frame,
            "Selection Tools",
            "Enable selection mode to pick samples in 2D or embedding views, then export the results."
        )

        selection_row = ttk.Frame(selection_section, style='CardBody.TFrame')
        selection_row.pack(fill=tk.X, pady=(0, 6))

        self.selection_button = ttk.Button(
            selection_row,
            text=self._translate("Enable Selection"),
            style='Secondary.TButton',
            command=self._on_toggle_selection
        )
        self.selection_button.pack(side=tk.LEFT)

        self.selection_status = ttk.Label(
            selection_row,
            text=self._translate("Selected Samples: {count}", count=0),
            style='BodyMuted.TLabel'
        )
        self.selection_status.pack(side=tk.LEFT, padx=(12, 0))
        self._register_translation(
            self.selection_status,
            "Selected Samples: {count}",
            formatter=lambda: {'count': len(getattr(app_state, 'selected_indices', []))}
        )

        export_row = ttk.Frame(selection_section, style='CardBody.TFrame')
        export_row.pack(fill=tk.X)

        self.export_csv_button = ttk.Button(
            export_row,
            text=self._translate("Export CSV"),
            style='Secondary.TButton',
            command=self._export_selected_csv
        )
        self.export_csv_button.pack(side=tk.LEFT, padx=(0, 12))
        self._register_translation(self.export_csv_button, "Export CSV")

        self.export_excel_button = ttk.Button(
            export_row,
            text=self._translate("Export Excel"),
            style='Secondary.TButton',
            command=self._export_selected_excel
        )
        self.export_excel_button.pack(side=tk.LEFT)
        self._register_translation(self.export_excel_button, "Export Excel")

        ttk.Separator(scrollable_frame, orient=tk.HORIZONTAL, style='SectionSeparator.TSeparator').pack(fill=tk.X, pady=12)

        footer_note = ttk.Label(
            container,
            text=self._translate("Adjust sliders to refresh the plot automatically. Close the panel to reclaim screen space."),
            style='Footer.TLabel',
            wraplength=440,
            justify=tk.LEFT
        )
        footer_note.pack(anchor=tk.W, pady=(12, 8))
        self._register_translation(footer_note, "Adjust sliders to refresh the plot automatically. Close the panel to reclaim screen space.")

        action_frame = ttk.Frame(container, style='ControlPanel.TFrame')
        action_frame.pack(fill=tk.X)

        close_button = ttk.Button(
            action_frame,
            text=self._translate("Close Panel"),
            style='Accent.TButton',
            command=self._on_close
        )
        close_button.pack(side=tk.RIGHT, padx=(0, 4))
        self._register_translation(close_button, "Close Panel")

        self.update_selection_controls()

    def _setup_styles(self):
        """Configure ttk styles for a polished appearance"""
        self.style = ttk.Style(self.master)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            pass

        primary = self.primary_bg
        card = self.card_bg

        self.style.configure('ControlPanel.TFrame', background=primary)
        self.style.configure('Header.TLabel', background=primary, foreground='#1a202c', font=('Segoe UI', 16, 'bold'))
        self.style.configure('Subheader.TLabel', background=primary, foreground='#4a5568', font=('Segoe UI', 10))
        self.style.configure('Footer.TLabel', background=primary, foreground='#4a5568', font=('Segoe UI', 9))
        self.style.configure('SectionSeparator.TSeparator', background='#cbd5f5', lightcolor='#cbd5f5', darkcolor='#cbd5f5')

        self.style.configure('Card.TLabelframe', background=card, borderwidth=1, relief='solid')
        self.style.configure('Card.TLabelframe.Label', background=card, foreground='#1a202c', font=('Segoe UI', 12, 'bold'))
        self.style.configure('CardBody.TFrame', background=card)
        self.style.configure('Body.TLabel', background=card, foreground='#4a5568', font=('Segoe UI', 10))
        self.style.configure('BodyMuted.TLabel', background=card, foreground='#94a3b8', font=('Segoe UI', 10))
        self.style.configure('FieldLabel.TLabel', background=card, foreground='#1a202c', font=('Segoe UI', 10, 'bold'))
        self.style.configure('ValueLabel.TLabel', background=card, foreground='#2d3748', font=('Segoe UI', 10, 'bold'))

        self.style.configure('Option.TRadiobutton', background=card, foreground='#1a202c', padding=4, font=('Segoe UI', 10))
        self.style.map('Option.TRadiobutton', background=[('active', card)], foreground=[('active', '#1a202c')])

        self.style.configure('Accent.TButton', background='#2563eb', foreground='#ffffff', font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('Accent.TButton', background=[('active', '#1d4ed8'), ('pressed', '#1d4ed8')], foreground=[('disabled', '#d1d5db'), ('active', '#ffffff'), ('pressed', '#ffffff')])
        self.style.configure('Secondary.TButton', background='#ffffff', foreground='#2563eb', font=('Segoe UI', 10, 'bold'), padding=(12, 6))
        self.style.map('Secondary.TButton', background=[('active', '#e2e8f0')], foreground=[('active', '#1d4ed8')])

    def _translate(self, key, **kwargs):
        """Translate helper bound to the current app language."""
        language = getattr(app_state, 'language', None)
        return translate(key, language=language, **kwargs)

    def _register_translation(self, widget, key, attr='text', formatter=None):
        """Track a widget attribute for future language refreshes."""
        if widget is None:
            return
        self._translations.append({
            'widget': widget,
            'key': key,
            'attr': attr,
            'formatter': formatter,
        })

    def _apply_translation(self, widget, attr, value):
        """Apply translated text to a widget attribute."""
        if widget is None or value is None:
            return
        try:
            if attr == 'title' and hasattr(widget, 'title'):
                widget.title(value)
            else:
                widget.configure(**{attr: value})
        except Exception:
            pass

    def _refresh_language(self):
        """Reapply translations for all registered widgets."""
        for entry in self._translations:
            kwargs = {}
            if entry.get('formatter') is not None:
                result = entry['formatter']()
                if isinstance(result, dict):
                    kwargs = result
                elif isinstance(result, str):
                    self._apply_translation(entry['widget'], entry['attr'], result)
                    continue
            translated = self._translate(entry['key'], **kwargs)
            self._apply_translation(entry['widget'], entry['attr'], translated)

    def _language_label(self, code):
        """Return the human-readable label for a language code."""
        return self._language_labels.get(code, code)

    def _create_section(self, parent, title, description=None):
        """Create a styled section container"""
        section = ttk.LabelFrame(parent, text=self._translate(title), padding=14, style='Card.TLabelframe')
        section.pack(fill=tk.X, padx=6, pady=6)
        self._register_translation(section, title)

        if description:
            desc = ttk.Label(section, text=self._translate(description), style='Body.TLabel', wraplength=430, justify=tk.LEFT)
            desc.pack(anchor=tk.W, pady=(0, 10))
            self._register_translation(desc, description)

        return section

    def _add_slider(self, parent, key, label_text, minimum, maximum, initial, formatter, step=1):
        """Add a labeled slider with value indicator and micro-adjust controls."""
        row = ttk.Frame(parent, style='CardBody.TFrame')
        row.pack(fill=tk.X, pady=6)

        label_widget = ttk.Label(row, text=self._translate(label_text), style='FieldLabel.TLabel')
        label_widget.pack(anchor=tk.W)
        self._register_translation(label_widget, label_text)

        slider_container = ttk.Frame(row, style='CardBody.TFrame')
        slider_container.pack(fill=tk.X, pady=(4, 0))

        value_label = ttk.Label(slider_container, text=formatter(initial), style='ValueLabel.TLabel')
        value_label.pack(side=tk.RIGHT)

        control_frame = ttk.Frame(slider_container, style='CardBody.TFrame')
        control_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        decrement = ttk.Button(
            control_frame,
            text="<",
            width=3,
            style='Secondary.TButton',
            command=lambda k=key: self._nudge_slider(k, -step)
        )
        decrement.pack(side=tk.LEFT, padx=(0, 6))

        slider = ttk.Scale(
            control_frame,
            from_=minimum,
            to=maximum,
            orient=tk.HORIZONTAL
        )
        slider.set(initial)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        increment = ttk.Button(
            control_frame,
            text=">",
            width=3,
            style='Secondary.TButton',
            command=lambda k=key: self._nudge_slider(k, step)
        )
        increment.pack(side=tk.LEFT)

        def _handle_slider(value, slider_key=key):
            try:
                numeric_value = float(value)
            except (TypeError, ValueError):
                numeric_value = value
            else:
                step_value = self._slider_steps.get(slider_key, 0) or 0
                if step_value:
                    snapped = round(numeric_value / step_value) * step_value
                    if step_value < 1:
                        step_str = f"{step_value:.6f}".rstrip('0').rstrip('.')
                        if '.' in step_str:
                            decimals = len(step_str.split('.')[1])
                            snapped = round(snapped, decimals)
                    if abs(snapped - numeric_value) > 1e-9:
                        numeric_value = snapped
                        slider_widget = self.sliders.get(slider_key)
                        if slider_widget is not None:
                            slider_widget.set(numeric_value)
            try:
                value_label.config(text=formatter(numeric_value))
            except Exception:
                pass
            self._schedule_slider_callback(slider_key)

        slider.configure(command=_handle_slider)
        slider.bind("<ButtonRelease-1>", lambda _e, k=key: self._apply_slider_change(k))
        slider.bind("<FocusOut>", lambda _e, k=key: self._apply_slider_change(k))
        slider.bind("<KeyRelease>", lambda _e, k=key: self._apply_slider_change(k))

        self.sliders[key] = slider
        self.labels[key] = value_label
        self._slider_steps[key] = float(step)

        return slider

    def _create_language_controls(self, parent):
        """Add language selection controls."""
        section = self._create_section(parent, "Language", "Choose the interface language.")

        values = dict(available_languages()) or self._language_labels or {'en': 'English'}
        self._language_labels = values
        current_label = self._language_label(app_state.language)
        if current_label not in values.values():
            current_label = next(iter(values.values()))

        label = ttk.Label(section, text=self._translate("Select Language"), style='FieldLabel.TLabel')
        label.pack(anchor=tk.W, pady=(0, 6))
        self._register_translation(label, "Select Language")

        self.language_choice = tk.StringVar(value=current_label)
        combo = ttk.Combobox(
            section,
            textvariable=self.language_choice,
            values=list(values.values()),
            state='readonly'
        )
        combo.pack(fill=tk.X)
        combo.bind('<<ComboboxSelected>>', self._on_language_change)
        self.language_combobox = combo

    def _on_language_change(self, _event=None):
        """Handle selection of a new interface language."""
        if self.language_choice is None:
            return

        selection = self.language_choice.get()
        target_code = None
        for code, label in self._language_labels.items():
            if label == selection:
                target_code = code
                break

        if target_code is None:
            return

        if target_code == getattr(app_state, 'language', None):
            return

        if not set_language(target_code):
            messagebox.showerror(
                self._translate("Language"),
                self._translate("Language switch failed. Please try again."),
                parent=self.root
            )
            self.language_choice.set(self._language_label(app_state.language))
            return

        self.language_choice.set(self._language_label(target_code))
        self._refresh_language()
        self.update_selection_controls()

        messagebox.showinfo(
            self._translate("Language"),
            self._translate("Language updated to {language}", language=self._language_label(target_code)),
            parent=self.root
        )

    def _schedule_slider_callback(self, key):
        """Debounce expensive recomputation while the slider is moving."""
        existing = self._slider_after.get(key)
        if existing is not None:
            try:
                self.root.after_cancel(existing)
            except Exception:
                pass

        self._slider_after[key] = self.root.after(
            self._slider_delay_ms,
            lambda k=key: self._apply_slider_change(k)
        )

    def _apply_slider_change(self, key):
        """Commit the slider value and trigger downstream updates."""
        pending = self._slider_after.pop(key, None)
        if pending is not None:
            try:
                self.root.after_cancel(pending)
            except Exception:
                pass

        self._on_change()

    def _nudge_slider(self, key, delta):
        """Micro-adjust the slider value using the auxiliary buttons."""
        slider = self.sliders.get(key)
        if slider is None:
            return

        step = self._slider_steps.get(key, 1.0)
        try:
            current = float(slider.get())
            minimum = float(slider.cget('from'))
            maximum = float(slider.cget('to'))
        except (TypeError, ValueError):
            return

        new_value = current + delta
        if step:
            new_value = round(new_value / step) * step

        new_value = max(minimum, min(maximum, new_value))

        # Limit floating-point noise to six decimal places at most.
        if step < 1:
            step_str = f"{step:.6f}".rstrip('0').rstrip('.')
            if '.' in step_str:
                decimals = len(step_str.split('.')[1])
                new_value = round(new_value, decimals)

        slider.set(new_value)
        self._apply_slider_change(key)

    def _refresh_group_options(self):
        """Rebuild group radio buttons to match the latest dataset."""
        if not hasattr(self, 'group_container') or self.group_container is None:
            return

        for child in list(self.group_container.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass

        self.group_placeholder = None

        if app_state.group_cols:
            for col in app_state.group_cols:
                ttk.Radiobutton(
                    self.group_container,
                    text=col,
                    variable=self.radio_vars['group'],
                    value=col,
                    command=self._on_change,
                    style='Option.TRadiobutton'
                ).pack(anchor=tk.W, pady=2)
        else:
            placeholder = ttk.Label(
                self.group_container,
                text=self._translate("Load data to unlock grouping options."),
                style='BodyMuted.TLabel',
                wraplength=400,
                justify=tk.LEFT
            )
            placeholder.pack(anchor=tk.W, pady=4)
            self.group_placeholder = placeholder
            self._register_translation(placeholder, "Load data to unlock grouping options.")

    def _open_legend_filter(self):
        """Launch legend filter dialog to hide/show groups."""
        if not app_state.available_groups:
            messagebox.showinfo(
                self._translate("Legend Filter"),
                self._translate("No legend entries are available yet."),
                parent=self.root
            )
            return

        try:
            from legend_dialog import select_visible_groups
        except Exception as exc:
            messagebox.showerror(
                self._translate("Legend Filter"),
                self._translate("Unable to open filter dialog: {error}", error=exc),
                parent=self.root
            )
            return

        current = app_state.visible_groups or app_state.available_groups
        selection = select_visible_groups(app_state.available_groups, selected=current)
        if selection is None:
            return

        if len(selection) == len(app_state.available_groups):
            app_state.visible_groups = None
        else:
            app_state.visible_groups = selection

        if self.callback:
            self.callback()

    def update_selection_controls(self):
        """Refresh selection-related widgets to reflect current state."""
        if not hasattr(self, 'selection_button'):
            return

        count = len(getattr(app_state, 'selected_indices', []))

        if getattr(self, 'selection_status', None) is not None:
            try:
                self.selection_status.config(
                    text=self._translate("Selected Samples: {count}", count=count)
                )
            except Exception:
                pass

        for button_attr in ('export_csv_button', 'export_excel_button'):
            btn = getattr(self, button_attr, None)
            if btn is None:
                continue
            try:
                if count == 0:
                    btn.state(['disabled'])
                else:
                    btn.state(['!disabled'])
            except Exception:
                pass

        toggle_btn = getattr(self, 'selection_button', None)
        if toggle_btn is None:
            return

        try:
            if app_state.selection_mode:
                toggle_btn.config(
                    text=self._translate("Disable Selection"),
                    style='Accent.TButton'
                )
            else:
                toggle_btn.config(
                    text=self._translate("Enable Selection"),
                    style='Secondary.TButton'
                )

            if app_state.render_mode == '3D':
                toggle_btn.state(['disabled'])
            else:
                toggle_btn.state(['!disabled'])
        except Exception:
            pass

    def refresh_language(self):
        """Public entry point for reapplying translations."""
        self._refresh_language()
        self.update_selection_controls()

    def _get_selected_dataframe(self):
        """Return a DataFrame with the currently selected samples."""
        if not app_state.selected_indices:
            messagebox.showinfo(
                self._translate("Export Selected Data"),
                self._translate("Please select at least one sample before exporting."),
                parent=self.root
            )
            return None

        if app_state.df_global is None or app_state.df_global.empty:
            messagebox.showwarning(
                self._translate("Export Selected Data"),
                self._translate("No data is available to export."),
                parent=self.root
            )
            return None

        try:
            indices = sorted(app_state.selected_indices)
            df = app_state.df_global.iloc[indices].copy()
        except Exception as exc:
            messagebox.showerror(
                self._translate("Export Selected Data"),
                self._translate("Unable to extract selected samples: {error}", error=exc),
                parent=self.root
            )
            return None
        return df

    def _sanitize_filename(self, value):
        """Sanitize user-provided filename fragments for safe saving."""
        sanitized = re.sub(r'[\/\\:*?"<>|]+', '_', value)
        sanitized = sanitized.strip().strip('.')
        return sanitized

    def _on_toggle_selection(self):
        """Toggle selection mode from the control panel."""
        if app_state.render_mode == '3D':
            messagebox.showinfo(
                self._translate("Selection Mode"),
                self._translate("Selection mode is only available in 2D views"),
                parent=self.root
            )
            return

        toggle_selection_mode()
        self.update_selection_controls()

    def _export_selected_csv(self):
        """Export selected samples to a CSV file."""
        df = self._get_selected_dataframe()
        if df is None:
            return

        default_name = f"selected_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        name = simpledialog.askstring(
            self._translate("Export to CSV"),
            self._translate("Enter a file name (without extension):"),
            initialvalue=default_name,
            parent=self.root
        )
        if name is None:
            return

        name = name.strip()
        sanitized = self._sanitize_filename(name)
        if not sanitized:
            messagebox.showerror(
                self._translate("Export to CSV"),
                self._translate("File name cannot be empty or only invalid characters."),
                parent=self.root
            )
            return

        target_dir = os.path.dirname(app_state.file_path) if app_state.file_path else os.getcwd()
        if not target_dir:
            target_dir = os.getcwd()
        target_path = os.path.join(target_dir, f"{sanitized}.csv")

        if os.path.exists(target_path):
            overwrite = messagebox.askyesno(
                self._translate("Export to CSV"),
                self._translate("File already exists:\n{path}\nOverwrite?", path=target_path),
                parent=self.root
            )
            if not overwrite:
                return

        try:
            df.to_csv(target_path, index=False, encoding='utf-8-sig')
        except Exception as exc:
            messagebox.showerror(
                self._translate("Export to CSV"),
                self._translate("Export failed: {error}", error=exc),
                parent=self.root
            )
            return

        messagebox.showinfo(
            self._translate("Export to CSV"),
            self._translate("Exported {count} records to:\n{path}", count=len(df), path=target_path),
            parent=self.root
        )

    def _export_selected_excel(self):
        """Append selected samples to an Excel sheet."""
        df = self._get_selected_dataframe()
        if df is None:
            return

        if app_state.file_path and app_state.file_path.lower().endswith(('.xlsx', '.xlsm')):
            workbook_path = app_state.file_path
        else:
            workbook_path = filedialog.asksaveasfilename(
                parent=self.root,
                title=self._translate("Select target workbook"),
                defaultextension=".xlsx",
                filetypes=[(self._translate("Excel Workbook"), "*.xlsx")],
                initialfile="selected_data.xlsx"
            )
            if not workbook_path:
                return

        if not workbook_path.lower().endswith('.xlsx'):
            workbook_path = f"{workbook_path}.xlsx"

        sheet_default = f"Selected_{datetime.now().strftime('%Y%m%d_%H%M')}"
        sheet_name = simpledialog.askstring(
            self._translate("Append to Excel"),
            self._translate("Enter a new worksheet name:"),
            initialvalue=sheet_default,
            parent=self.root
        )
        if sheet_name is None:
            return

        sheet_name = sheet_name.strip()
        if not sheet_name:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name cannot be empty."),
                parent=self.root
            )
            return
        if len(sheet_name) > 31:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name cannot exceed 31 characters."),
                parent=self.root
            )
            return
        if any(ch in sheet_name for ch in '[]:*?/\\'):
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Worksheet name contains invalid characters: []:*?/\\"),
                parent=self.root
            )
            return

        try:
            import openpyxl
        except ImportError:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("openpyxl is required to write Excel files. Please install openpyxl."),
                parent=self.root
            )
            return

        exists = os.path.exists(workbook_path)
        if exists:
            try:
                wb = openpyxl.load_workbook(workbook_path)
            except Exception as exc:
                messagebox.showerror(
                    self._translate("Append to Excel"),
                    self._translate("Unable to open target workbook: {error}", error=exc),
                    parent=self.root
                )
                return
            if sheet_name in wb.sheetnames:
                wb.close()
                messagebox.showerror(
                    self._translate("Append to Excel"),
                    self._translate("Worksheet already exists. Please choose another name."),
                    parent=self.root
                )
                return
            wb.close()

        try:
            if exists:
                with pd.ExcelWriter(workbook_path, mode='a', engine='openpyxl', if_sheet_exists='new') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                with pd.ExcelWriter(workbook_path, mode='w', engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as exc:
            messagebox.showerror(
                self._translate("Append to Excel"),
                self._translate("Failed to write Excel file: {error}", error=exc),
                parent=self.root
            )
            return

        messagebox.showinfo(
            self._translate("Append to Excel"),
            self._translate(
                "Appended {count} records to worksheet '{sheet}'.\nPath: {path}",
                count=len(df),
                sheet=sheet_name,
                path=workbook_path
            ),
            parent=self.root
        )

    def _reload_data(self):
        """Allow the user to pick a new dataset and refresh the UI."""
        try:
            from data import load_data
        except Exception as exc:
            messagebox.showerror(
                self._translate("Reload Data"),
                self._translate("Unable to reload data: {error}", error=exc),
                parent=self.root
            )
            return

        success = load_data(show_file_dialog=True, show_config_dialog=True)
        if not success:
            messagebox.showinfo(
                self._translate("Reload Data"),
                self._translate("Data reload cancelled."),
                parent=self.root
            )
            return

        if app_state.group_cols:
            if app_state.last_group_col not in app_state.group_cols:
                app_state.last_group_col = app_state.group_cols[0]
        else:
            app_state.last_group_col = None

        if 'group' in self.radio_vars:
            self.radio_vars['group'].set(app_state.last_group_col or '')

        app_state.visible_groups = None
        app_state.available_groups = []
        app_state.selected_2d_cols = []
        app_state.selected_3d_cols = []
        app_state.selected_2d_confirmed = False
        app_state.selected_3d_confirmed = False
        app_state.initial_render_done = False

        self._refresh_group_options()

        if self.callback:
            self.callback()

        self.update_selection_controls()

        messagebox.showinfo(
            self._translate("Reload Data"),
            self._translate("Dataset reloaded successfully."),
            parent=self.root
        )
    
    def _on_change(self):
        """Handle any parameter change - with safety checks"""
        try:
            print(f"[DEBUG] _on_change called", flush=True)
            
            # Verify all dictionaries are initialized
            if not self.sliders or not self.labels or not self.radio_vars:
                print("[DEBUG] Dictionaries not fully initialized yet", flush=True)
                return
            
            algorithm_changed = False

            if 'render_mode' in self.radio_vars:
                requested_mode = self.radio_vars['render_mode'].get()
                previous_mode = app_state.render_mode

                if requested_mode == '3D' and len(app_state.data_cols) < 3:
                    print("[WARN] Need at least three numeric columns for 3D view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != '3D' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)
                elif requested_mode == '2D' and len(app_state.data_cols) < 2:
                    print("[WARN] Need at least two numeric columns for 2D view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != '2D' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)

                if requested_mode in ('UMAP', 'tSNE', 'PCA'):
                    old_algo = app_state.algorithm
                    if requested_mode == 'UMAP':
                        app_state.algorithm = 'UMAP'
                    elif requested_mode == 'tSNE':
                        app_state.algorithm = 'tSNE'
                    else:
                        app_state.algorithm = 'PCA'
                    
                    algorithm_changed = (old_algo != app_state.algorithm)
                    if algorithm_changed:
                        print(f"[DEBUG] Algorithm changed: {old_algo} -> {app_state.algorithm}", flush=True)
                        app_state.embedding_cache.clear()

                if requested_mode != previous_mode:
                    print(f"[DEBUG] Render mode changed: {previous_mode} -> {requested_mode}", flush=True)
                    app_state.render_mode = requested_mode
                    if requested_mode == '2D':
                        app_state.selected_2d_confirmed = False
                    elif requested_mode == '3D':
                        app_state.selected_3d_confirmed = False

            if app_state.render_mode in ('UMAP', 'tSNE', 'PCA'):
                if app_state.render_mode == 'UMAP':
                    app_state.algorithm = 'UMAP'
                elif app_state.render_mode == 'tSNE':
                    app_state.algorithm = 'tSNE'
                else:
                    app_state.algorithm = 'PCA'
            
            # Update Ellipse setting
            if 'ellipses' in self.check_vars:
                app_state.show_ellipses = self.check_vars['ellipses'].get()

            # Update UMAP parameters - only if keys exist
            umap_changed = False
            if 'umap_n' in self.sliders and 'umap_n' in self.labels:
                new_val = int(self.sliders['umap_n'].get())
                if app_state.umap_params['n_neighbors'] != new_val:
                    umap_changed = True
                app_state.umap_params['n_neighbors'] = new_val
                self.labels['umap_n'].config(text=f"{new_val}")
            
            if 'umap_d' in self.sliders and 'umap_d' in self.labels:
                new_val = float(self.sliders['umap_d'].get())
                if app_state.umap_params['min_dist'] != new_val:
                    umap_changed = True
                app_state.umap_params['min_dist'] = new_val
                self.labels['umap_d'].config(text=f"{new_val:.2f}")
            
            if 'umap_r' in self.sliders and 'umap_r' in self.labels:
                new_val = int(self.sliders['umap_r'].get())
                if app_state.umap_params['random_state'] != new_val:
                    umap_changed = True
                app_state.umap_params['random_state'] = new_val
                self.labels['umap_r'].config(text=f"{new_val}")
            
            # Clear UMAP cache if parameters changed
            if umap_changed:
                print(f"[DEBUG] UMAP parameters changed, clearing UMAP cache", flush=True)
                # Remove UMAP entries from cache
                keys_to_remove = [k for k in app_state.embedding_cache.keys() if k[0] == 'umap']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update t-SNE parameters
            tsne_changed = False
            if 'tsne_p' in self.sliders and 'tsne_p' in self.labels:
                p = int(self.sliders['tsne_p'].get())
                if app_state.df_global is not None and p >= app_state.df_global.shape[0]:
                    p = app_state.df_global.shape[0] - 1
                    self.sliders['tsne_p'].set(p)
                if app_state.tsne_params['perplexity'] != p:
                    tsne_changed = True
                app_state.tsne_params['perplexity'] = p
                self.labels['tsne_p'].config(text=f"{p}")
            
            if 'tsne_lr' in self.sliders and 'tsne_lr' in self.labels:
                new_val = int(self.sliders['tsne_lr'].get())
                if app_state.tsne_params['learning_rate'] != new_val:
                    tsne_changed = True
                app_state.tsne_params['learning_rate'] = new_val
                self.labels['tsne_lr'].config(text=f"{new_val}")
            
            # Clear t-SNE cache if parameters changed
            if tsne_changed:
                print(f"[DEBUG] t-SNE parameters changed, clearing t-SNE cache", flush=True)
                # Remove t-SNE entries from cache
                keys_to_remove = [k for k in app_state.embedding_cache.keys() if k[0] == 'tsne']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update common parameters
            if 'size' in self.sliders and 'size' in self.labels:
                app_state.point_size = int(self.sliders['size'].get())
                self.labels['size'].config(text=f"{int(self.sliders['size'].get())}")
            
            # Update group column if available
            if 'group' in self.radio_vars:
                old_group = app_state.last_group_col
                app_state.last_group_col = self.radio_vars['group'].get()
                print(f"[DEBUG] Group column changed: {old_group} -> {app_state.last_group_col}", flush=True)
            
            # Call the callback
            print(f"[DEBUG] Calling callback", flush=True)
            if self.callback:
                self.callback()
            print(f"[DEBUG] Callback completed", flush=True)
        
        except KeyError as e:
            print(f"[DEBUG] KeyError in _on_change (expected during init): {e}", flush=True)
        except Exception as e:
            print(f"[ERROR] _on_change: {e}", flush=True)
    
    def show(self):
        """Show the control panel"""
        print("[INFO] Control panel displayed", flush=True)
        self.root.mainloop()

    def destroy(self):
        """Destroy the control panel and master if owned"""
        try:
            for pending in list(self._slider_after.values()):
                try:
                    self.root.after_cancel(pending)
                except Exception:
                    pass
            self._slider_after.clear()
            self.root.destroy()
        finally:
            try:
                if self.refresh_language in getattr(app_state, 'language_listeners', []):
                    app_state.language_listeners.remove(self.refresh_language)
            except Exception:
                pass
            if getattr(self, "_owns_master", False) and getattr(self, "master", None) is not None:
                try:
                    self.master.destroy()
                except Exception:
                    pass

    def open(self):
        """Bring the control panel window back if it was hidden"""
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self.is_visible = True
        except Exception as exc:
            print(f"[WARN] Unable to reopen control panel: {exc}", flush=True)

    def _on_close(self):
        """Handle window close without tearing down shared Tk root"""
        try:
            self.root.withdraw()
            self.is_visible = False
        except Exception:
            pass


def create_control_panel(callback):
    """
    Create and return a control panel instance
    
    Args:
        callback: function to call when parameters change
    
    Returns:
        ControlPanel instance
    """
    return ControlPanel(callback)
