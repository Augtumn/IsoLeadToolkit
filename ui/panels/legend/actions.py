"""Legend panel action handlers and auto style logic."""

from core import app_state, state_gateway


class LegendActionsMixin:
    """Behavior methods for legend panel."""

    def _on_auto_palette_change(self, value):
        if self.auto_palette_combo is None:
            return
        palette_name = self.auto_palette_combo.currentData()
        if not palette_name:
            return
        if palette_name == "__custom__":
            new_name = self._prompt_custom_palette()
            if new_name:
                index = self.auto_palette_combo.findData(new_name)
                if index >= 0:
                    self.auto_palette_combo.blockSignals(True)
                    self.auto_palette_combo.setCurrentIndex(index)
                    self.auto_palette_combo.blockSignals(False)
                palette_name = new_name
            else:
                index = self.auto_palette_combo.findData(self._last_palette_name)
                if index >= 0:
                    self.auto_palette_combo.blockSignals(True)
                    self.auto_palette_combo.setCurrentIndex(index)
                    self.auto_palette_combo.blockSignals(False)
                return
        state_gateway.set_attr('color_scheme', palette_name)
        self._last_palette_name = palette_name
        try:
            from visualization import refresh_plot_style
            refresh_plot_style()
        except Exception:
            self._on_change()

    def _on_shape_set_change(self, _index):
        if self.auto_shape_set_combo is None:
            return
        if self.auto_shape_set_combo.currentData() != "__custom__":
            return
        new_name, shapes = self._prompt_custom_shape_set()
        if not new_name or not shapes:
            index = self.auto_shape_set_combo.findData("all")
            if index >= 0:
                self.auto_shape_set_combo.blockSignals(True)
                self.auto_shape_set_combo.setCurrentIndex(index)
                self.auto_shape_set_combo.blockSignals(False)
            return
        self.auto_shape_set_combo.blockSignals(True)
        self.auto_shape_set_combo.addItem(new_name, shapes)
        self.auto_shape_set_combo.setCurrentIndex(self.auto_shape_set_combo.count() - 1)
        self.auto_shape_set_combo.blockSignals(False)

    def _on_legend_inside_position_change(self, position):
        current = getattr(app_state, 'legend_position', None)
        if current == position:
            state_gateway.set_attr('legend_position', None)
            self._set_legend_inside_position_button(None)
        else:
            state_gateway.set_attr('legend_position', position)
            self._set_legend_inside_position_button(position)
        self._on_change()

    def _on_legend_outside_position_change(self, position):
        current = getattr(app_state, 'legend_location', None)
        if current == position:
            state_gateway.set_attr('legend_location', None)
            self._set_legend_outside_position_button(None)
        else:
            state_gateway.set_attr('legend_location', position)
            self._set_legend_outside_position_button(position)
        self._on_change()

    def _on_legend_columns_change(self, columns):
        state_gateway.set_attr('legend_columns', columns)
        self._on_change()

    def _on_nudge_step_change(self, value):
        try:
            step = float(value)
        except Exception:
            return
        self.legend_nudge_step = step
        state_gateway.set_attr('legend_nudge_step', step)

    def _nudge_legend(self, dx, dy):
        current = getattr(app_state, 'legend_offset', (0.0, 0.0))
        try:
            new_offset = (float(current[0]) + float(dx), float(current[1]) + float(dy))
        except Exception:
            new_offset = (0.0, 0.0)
        state_gateway.set_attr('legend_offset', new_offset)
        try:
            from visualization import refresh_plot_style
            refresh_plot_style()
        except Exception:
            self._on_change()

    def _auto_assign_styles(self):
        if not app_state.last_group_col or app_state.df_global is None:
            return
        groups = list(app_state.available_groups or app_state.df_global[app_state.last_group_col].unique())
        if not groups:
            return

        palette_name = None
        if self.auto_palette_combo is not None:
            palette_name = self.auto_palette_combo.currentData()
        if palette_name:
            if palette_name == "__custom__":
                palette_name = getattr(app_state, 'color_scheme', None)
            state_gateway.set_attr('color_scheme', palette_name)

        color_pool = []
        try:
            from visualization.style_manager import style_manager_instance
            if palette_name and palette_name in style_manager_instance.palettes:
                color_pool = list(style_manager_instance.palettes[palette_name])
        except Exception:
            color_pool = []

        if not color_pool:
            palette = getattr(app_state, 'current_palette', {}) or {}
            for group in groups:
                color = palette.get(group)
                if color and color not in color_pool:
                    color_pool.append(color)

        if not color_pool:
            try:
                import matplotlib.pyplot as plt
                prop_cycle = plt.rcParams.get('axes.prop_cycle', None)
                colors = prop_cycle.by_key().get('color', []) if prop_cycle is not None else []
                for color in colors:
                    if color not in color_pool:
                        color_pool.append(color)
            except Exception:
                pass

        if not color_pool:
            color_pool = ['#333333']

        self._ensure_marker_shape_map()
        shape_values = list(self._marker_shape_map.values())
        basic_shapes = [s for s in ['o', 's', '^', 'v', 'D'] if s in shape_values]
        shape_set = shape_values
        if self.auto_shape_set_combo is not None:
            shape_data = self.auto_shape_set_combo.currentData()
            if shape_data == "basic" and basic_shapes:
                shape_set = basic_shapes
            elif isinstance(shape_data, (list, tuple)):
                shape_set = list(shape_data)

        base_shape = getattr(app_state, 'plot_marker_shape', 'o')
        if self.auto_base_shape_combo is not None:
            marker = self.auto_base_shape_combo.currentData()
            if marker:
                base_shape = marker
        if base_shape not in shape_set and shape_set:
            base_shape = shape_set[0]

        shapes_extra = [s for s in shape_set if s != base_shape] or shape_set

        total_colors = len(color_pool)
        for idx, group in enumerate(groups):
            if idx < total_colors:
                app_state.current_palette[group] = color_pool[idx]
                app_state.group_marker_map[group] = base_shape
            else:
                extra = idx - total_colors
                color = color_pool[extra % total_colors]
                shape = shapes_extra[(extra // total_colors) % len(shapes_extra)]
                app_state.current_palette[group] = color
                app_state.group_marker_map[group] = shape

        self._on_change()
