"""
Legend Tab - Interactive legend management
"""
import tkinter as tk
from tkinter import ttk, colorchooser

from core import app_state


class LegendTabMixin:
    """Mixin providing the Legend tab builder and legend management"""

    def _build_legend_tab(self, parent):
        """Build the interactive legend tab"""
        frame = self._build_scrollable_frame(parent)
        self.legend_container = frame
        
        # Legend Settings Section
        settings_frame = ttk.Frame(frame, style='ControlPanel.TFrame')
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Legend Columns Slider
        self._add_slider(
            settings_frame,
            key='legend_cols',
            label_text="Columns",
            minimum=0,
            maximum=10,
            initial=getattr(app_state, 'legend_columns', 0),
            formatter=lambda v: "Auto" if int(float(v)) == 0 else str(int(float(v))),
            step=1
        )

        # Add a refresh button
        refresh_btn = ttk.Button(
            frame,
            text=self._translate("Refresh Legend"),
            style='Secondary.TButton',
            command=self._refresh_legend_tab
        )
        refresh_btn.pack(anchor=tk.W, pady=(0, 10))
        self._register_translation(refresh_btn, "Refresh Legend")
        
        self.legend_items_frame = ttk.Frame(frame, style='ControlPanel.TFrame')
        self.legend_items_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initial population
        self._refresh_legend_tab()

    def _refresh_legend_tab(self):
        """
        Populate the legend tab with current groups and colors.
        
        Features:
        - Lists all groups (up to a limit) with checkboxes for visibility.
        - Shows a color swatch for each group (clickable to change color).
        - Provides a 'Top' button to bring a group's points to the front (z-order).
        - Includes a 'Select All' toggle.
        """
        if not hasattr(self, 'legend_items_frame'):
            return
            
        # Clear existing
        for child in self.legend_items_frame.winfo_children():
            child.destroy()
            
        if not app_state.current_groups:
            lbl = ttk.Label(self.legend_items_frame, text=self._translate("No legend data available."), style='BodyMuted.TLabel')
            lbl.pack(anchor=tk.W, pady=10)
            self._register_translation(lbl, "No legend data available.")
            return

        # Checkbox var for "Select All"
        self.select_all_var = tk.BooleanVar(value=True)
        
        def toggle_all():
            state = self.select_all_var.get()
            for var in self.legend_vars.values():
                var.set(state)
            self._apply_legend_filter()

        select_all_cb = ttk.Checkbutton(
            self.legend_items_frame,
            text=self._translate("Select all"),
            variable=self.select_all_var,
            command=toggle_all,
            style='Option.TRadiobutton'
        )
        select_all_cb.pack(anchor=tk.W, pady=(0, 5))
        self._register_translation(select_all_cb, "Select all")
        
        self.legend_vars = {}
        
        visible = set(app_state.visible_groups) if app_state.visible_groups else set(app_state.current_groups)

        # Limit the number of items to prevent UI freeze
        max_items = 100
        groups_to_show = app_state.current_groups[:max_items]
        
        if len(app_state.current_groups) > max_items:
            warning_lbl = ttk.Label(
                self.legend_items_frame, 
                text=self._translate("Showing first {max} groups only.", max=max_items),
                style='BodyMuted.TLabel'
            )
            warning_lbl.pack(anchor=tk.W, pady=(0, 5))
            self._register_translation(warning_lbl, "Showing first {max} groups only.", formatter=lambda: {'max': max_items})

        for group in groups_to_show:
            row = ttk.Frame(self.legend_items_frame, style='ControlPanel.TFrame')
            row.pack(fill=tk.X, pady=2)
            
            # Color swatch (Clickable)
            color = app_state.current_palette.get(group, '#cccccc')
            swatch = tk.Canvas(row, width=16, height=16, bg=color, highlightthickness=0, cursor="hand2")
            swatch.pack(side=tk.LEFT, padx=(0, 8))
            swatch.bind("<Button-1>", lambda e, g=group, s=swatch: self._pick_color(g, s))
            
            # Checkbox
            is_visible = group in visible
            var = tk.BooleanVar(value=is_visible)
            self.legend_vars[group] = var
            
            cb = ttk.Checkbutton(
                row,
                text=str(group),
                variable=var,
                command=self._apply_legend_filter,
                style='Option.TRadiobutton'
            )
            cb.pack(side=tk.LEFT, fill=tk.X, expand=True)
            
            # Top Button (Bring to front)
            top_btn = ttk.Button(
                row,
                text=self._translate("Top"),
                width=4,
                style='Secondary.TButton',
                command=lambda g=group: self._bring_to_front(g)
            )
            top_btn.pack(side=tk.RIGHT, padx=(4, 0))
            self._register_translation(top_btn, "Top")

    def sync_legend_ui(self):
        """Update legend checkboxes to match app_state.visible_groups without rebuilding."""
        if not hasattr(self, 'legend_vars'):
            return
            
        visible = set(app_state.visible_groups) if app_state.visible_groups else set(app_state.current_groups)
        
        for group, var in self.legend_vars.items():
            var.set(group in visible)
            
        # Update Select All checkbox state
        if hasattr(self, 'select_all_var'):
            # If visible_groups is None, it means all are visible
            all_visible = (app_state.visible_groups is None) or (len(visible) == len(app_state.current_groups))
            self.select_all_var.set(all_visible)

    def _pick_color(self, group, swatch):
        """
        Open a color picker dialog for a specific group.
        
        Updates the global palette and immediately redraws the scatter plot
        if the group is currently displayed.
        
        Args:
            group: The group identifier (e.g., name).
            swatch: The canvas widget displaying the current color (to be updated).
        """
        current_color = app_state.current_palette.get(group, '#cccccc')
        color = colorchooser.askcolor(initialcolor=current_color, title=f"Color for {group}")
        
        if color[1]:  # color is ((r,g,b), hex)
            new_hex = color[1]
            app_state.current_palette[group] = new_hex
            swatch.configure(bg=new_hex)
            
            # Update plot immediately
            if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
                sc = app_state.group_to_scatter[group]
                try:
                    sc.set_color(new_hex)
                    # Restore edge color which set_color might overwrite
                    sc.set_edgecolor("#1e293b") 
                    if app_state.fig:
                        app_state.fig.canvas.draw_idle()
                except Exception as e:
                    print(f"[WARN] Failed to update color for {group}: {e}")

    def _bring_to_front(self, group):
        """
        Bring a group's scatter points to the front of the plot.
        
        Adjusts the z-order of the scatter collection corresponding to the group
        to be higher than all other collections.
        
        Args:
            group: The group identifier.
        """
        if hasattr(app_state, 'group_to_scatter') and group in app_state.group_to_scatter:
            sc = app_state.group_to_scatter[group]
            try:
                # Find max zorder
                max_z = 2  # Default base zorder
                if hasattr(app_state, 'scatter_collections'):
                    for c in app_state.scatter_collections:
                        max_z = max(max_z, c.get_zorder())
                
                sc.set_zorder(max_z + 1)
                if app_state.fig:
                    app_state.fig.canvas.draw_idle()
            except Exception as e:
                print(f"[WARN] Failed to bring {group} to front: {e}")

    def _apply_legend_filter(self):
        """
        Apply the visibility filter from the legend tab.
        
        Updates `app_state.visible_groups` based on the checked state of each group
        in the legend list, then triggers a plot refresh via the callback.
        """
        selected = [g for g, var in self.legend_vars.items() if var.get()]
        
        if not selected:
            # Don't allow empty selection
            pass
            
        if len(selected) == len(app_state.current_groups):
            app_state.visible_groups = None
        else:
            app_state.visible_groups = selected
            
        if self.callback:
            self.callback()

    def _open_legend_filter(self):
        """Launch legend filter dialog to hide/show groups."""
        from tkinter import messagebox
        
        if not app_state.available_groups:
            messagebox.showinfo(
                self._translate("Legend Filter"),
                self._translate("No legend entries are available yet."),
                parent=self.root
            )
            return

        try:
            from ui.dialogs.legend_dialog import select_visible_groups
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
