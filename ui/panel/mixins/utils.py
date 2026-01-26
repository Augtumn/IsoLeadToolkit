"""
Panel Utils - Utility methods for the Control Panel

Contains helper methods for UI creation, translation, and common utilities.
"""
import tkinter as tk
from tkinter import ttk

from core import translate, app_state


class PanelUtilsMixin:
    """Mixin providing utility methods for the ControlPanel"""

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

    def _language_label(self, code):
        """Return the human-readable label for a language code."""
        return self._language_labels.get(code, code)

    def _apply_translation(self, widget, attr, value):
        """Apply translated text to a widget attribute."""
        if widget is None or value is None:
            return
        try:
            if attr == 'title' and hasattr(widget, 'title'):
                widget.title(value)
            elif attr == 'tab':
                # Special handling for notebook tabs
                tab_id = value.get('tab_id')
                text = self._translate(self._translations[tab_id + 3]['key'])
                self.notebook.tab(tab_id, text=text)
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
            
            # Special handling for tabs
            if entry.get('attr') == 'tab':
                tab_id = kwargs.get('tab_id')
                text = self._translate(entry['key'])
                self.notebook.tab(tab_id, text=text)
                continue

            translated = self._translate(entry['key'], **kwargs)
            self._apply_translation(entry['widget'], entry['attr'], translated)
            
        # Refresh legend tab text
        if hasattr(self, '_refresh_legend_tab'):
            self._refresh_legend_tab()

    def _build_scrollable_frame(self, parent):
        """
        Helper to create a scrollable frame inside a tab.
        
        Creates a Canvas and Scrollbar. The Scrollbar is packed to the right,
        and the Canvas fills the remaining space to the left.
        A frame is placed inside the canvas window.
        
        Args:
            parent: The parent widget (usually a tab frame)
            
        Returns:
            ttk.Frame: The inner scrollable frame where widgets should be added.
        """
        canvas = tk.Canvas(parent, highlightthickness=0, bd=0, background=self.primary_bg)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='ControlPanel.TFrame')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind canvas configure to update frame width
        def _on_canvas_configure(event):
            canvas.itemconfig(window_id, width=event.width)
        
        canvas.bind("<Configure>", _on_canvas_configure)
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to canvas and its children
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        return scrollable_frame

    def _create_section(self, parent, title, description=None):
        """Create a styled section container"""
        section = ttk.LabelFrame(parent, text=self._translate(title), padding=14, style='Card.TLabelframe')
        section.pack(fill=tk.X, padx=6, pady=6)
        self._register_translation(section, title)

        if description:
            desc = ttk.Label(section, text=self._translate(description), style='Body.TLabel', wraplength=340, justify=tk.LEFT)
            desc.pack(fill=tk.X, pady=(0, 10))
            
            # Bind configure event to update wraplength dynamically
            def _update_wraplength(event):
                if event.width > 20:
                    desc.configure(wraplength=event.width - 20)
            
            desc.bind('<Configure>', _update_wraplength)
            
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

    def _update_data_count_label(self):
        """Update the label showing the number of loaded data rows."""
        if app_state.df_global is not None:
            count = len(app_state.df_global)
            text = self._translate("Loaded Data: {count} rows", count=count)
            self.data_count_label.config(text=text)
        else:
            self.data_count_label.config(text="")
