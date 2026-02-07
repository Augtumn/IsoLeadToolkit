"""
Algorithm Tab - Algorithm parameters and settings
"""
import tkinter as tk
from tkinter import ttk

from core import app_state

try:
    from data import geochemistry
except ImportError:
    geochemistry = None


class AlgorithmTabMixin:
    """Mixin providing the Algorithm tab builder"""

    def _build_algorithm_tab(self, parent):
        """Build the Algorithm tab content"""
        from visualization import show_scree_plot, show_pca_loadings
        
        frame = self._build_scrollable_frame(parent)

        # --- Grouping Controls ---
        self.group_section = self._create_section(
            frame,
            "Coloring / Grouping",
            "Select column for coloring points."
        )
        
        self.radio_vars['group'] = tk.StringVar(value=app_state.last_group_col or '')
        
        self.group_container = ttk.Frame(self.group_section, style='CardBody.TFrame')
        self.group_container.pack(fill=tk.X)
        self.group_placeholder = None

        self._refresh_group_list()

        group_config_btn = ttk.Button(
            self.group_section,
            text=self._translate("Configure Group Columns"),
            command=self._open_group_col_settings,
            style='Secondary.TButton'
        )
        group_config_btn.pack(anchor=tk.W, pady=(4, 0))
        self._register_translation(group_config_btn, "Configure Group Columns")

        # Mode-specific settings container
        self.mode_section = self._create_section(
            frame,
            "Mode-specific Settings",
            "Controls shown here depend on the current projection mode."
        )

        # UMAP Parameters
        self.umap_section = self._create_section(
            self.mode_section,
            "UMAP Parameters",
            "Control neighbourhood size and how tightly points cluster."
        )

        self._add_slider(
            self.umap_section,
            key='umap_n',
            label_text="n_neighbors",
            minimum=2,
            maximum=50,
            initial=app_state.umap_params['n_neighbors'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.umap_section,
            key='umap_d',
            label_text="min_dist",
            minimum=0.0,
            maximum=1.0,
            initial=app_state.umap_params['min_dist'],
            formatter=lambda v: f"{float(v):.2f}",
            step=0.01
        )

        self._add_slider(
            self.umap_section,
            key='umap_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.umap_params['random_state'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )
        
        # t-SNE Parameters
        self.tsne_section = self._create_section(
            self.mode_section,
            "t-SNE Parameters",
            "Adjust perplexity and learning rate to refine t-SNE embeddings."
        )

        self._add_slider(
            self.tsne_section,
            key='tsne_p',
            label_text="perplexity",
            minimum=5,
            maximum=100,
            initial=app_state.tsne_params['perplexity'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.tsne_section,
            key='tsne_lr',
            label_text="learning_rate",
            minimum=10,
            maximum=1000,
            initial=app_state.tsne_params['learning_rate'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.tsne_section,
            key='tsne_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.tsne_params.get('random_state', 42),
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        # PCA Parameters
        self.pca_section = self._create_section(
            self.mode_section,
            "PCA Parameters",
            "Standard Principal Component Analysis settings."
        )

        self._add_slider(
            self.pca_section,
            key='pca_n',
            label_text="n_components",
            minimum=2,
            maximum=10,
            initial=app_state.pca_params['n_components'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.pca_section,
            key='pca_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.pca_params.get('random_state', 42),
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )
        
        # PCA Dimension Selection & Scree Plot
        pca_tools = ttk.Frame(self.pca_section, style='CardBody.TFrame')
        pca_tools.pack(fill=tk.X, pady=(8, 0))
        
        scree_btn = ttk.Button(
            pca_tools,
            text=self._translate("Show Scree Plot"),
            style='Secondary.TButton',
            command=lambda: show_scree_plot(self.root)
        )
        scree_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(scree_btn, "Show Scree Plot")

        loadings_btn = ttk.Button(
            pca_tools,
            text=self._translate("Show Loadings"),
            style='Secondary.TButton',
            command=lambda: show_pca_loadings(self.root)
        )
        loadings_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(loadings_btn, "Show Loadings")
        
        dim_frame = ttk.Frame(pca_tools, style='CardBody.TFrame')
        dim_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(dim_frame, text=self._translate("X:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.pca_x_var = tk.StringVar(value=str(app_state.pca_component_indices[0] + 1))
        self.pca_x_spin = ttk.Spinbox(dim_frame, from_=1, to=10, width=3, textvariable=self.pca_x_var, command=self._on_pca_dim_change)
        self.pca_x_spin.pack(side=tk.LEFT, padx=(0, 8))
        self.pca_x_spin.bind('<Return>', lambda e: self._on_pca_dim_change())
        
        ttk.Label(dim_frame, text=self._translate("Y:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.pca_y_var = tk.StringVar(value=str(app_state.pca_component_indices[1] + 1))
        self.pca_y_spin = ttk.Spinbox(dim_frame, from_=1, to=10, width=3, textvariable=self.pca_y_var, command=self._on_pca_dim_change)
        self.pca_y_spin.pack(side=tk.LEFT)
        self.pca_y_spin.bind('<Return>', lambda e: self._on_pca_dim_change())

        # Robust PCA Parameters
        self.rpca_section = self._create_section(
            self.mode_section,
            "Robust PCA Parameters",
            "Minimum Covariance Determinant (MCD) based PCA. Resistant to outliers."
        )

        self._add_slider(
            self.rpca_section,
            key='rpca_n',
            label_text="n_components",
            minimum=2,
            maximum=10,
            initial=app_state.robust_pca_params['n_components'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.rpca_section,
            key='rpca_r',
            label_text="random_state",
            minimum=0,
            maximum=200,
            initial=app_state.robust_pca_params['random_state'],
            formatter=lambda v: f"{int(float(v))}",
            step=1
        )

        self._add_slider(
            self.rpca_section,
            key='rpca_sf',
            label_text="support_fraction",
            minimum=0.5,
            maximum=0.99,
            initial=app_state.robust_pca_params.get('support_fraction', 0.75),
            formatter=lambda v: f"{float(v):.2f}",
            step=0.01
        )
        
        rpca_tools = ttk.Frame(self.rpca_section, style='CardBody.TFrame')
        rpca_tools.pack(fill=tk.X, pady=(8, 0))
        
        rpca_scree_btn = ttk.Button(
            rpca_tools,
            text=self._translate("Show Scree Plot"),
            style='Secondary.TButton',
            command=lambda: show_scree_plot(self.root)
        )
        rpca_scree_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(rpca_scree_btn, "Show Scree Plot")

        rpca_loadings_btn = ttk.Button(
            rpca_tools,
            text=self._translate("Show Loadings"),
            style='Secondary.TButton',
            command=lambda: show_pca_loadings(self.root)
        )
        rpca_loadings_btn.pack(side=tk.LEFT, padx=(0, 10))
        self._register_translation(rpca_loadings_btn, "Show Loadings")

        # RPCA Dimensions
        r_dim_frame = ttk.Frame(rpca_tools, style='CardBody.TFrame')
        r_dim_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        ttk.Label(r_dim_frame, text=self._translate("X:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.rpca_x_spin = ttk.Spinbox(r_dim_frame, from_=1, to=10, width=3, textvariable=self.pca_x_var, command=self._on_pca_dim_change)
        self.rpca_x_spin.pack(side=tk.LEFT, padx=(0, 8))
        self.rpca_x_spin.bind('<Return>', lambda e: self._on_pca_dim_change())
        
        ttk.Label(r_dim_frame, text=self._translate("Y:"), style='Body.TLabel').pack(side=tk.LEFT, padx=(0, 2))
        self.rpca_y_spin = ttk.Spinbox(r_dim_frame, from_=1, to=10, width=3, textvariable=self.pca_y_var, command=self._on_pca_dim_change)
        self.rpca_y_spin.pack(side=tk.LEFT)
        self.rpca_y_spin.bind('<Return>', lambda e: self._on_pca_dim_change())

        # --- Ternary Parameters ---
        self._build_ternary_section(self.mode_section)

        # Geochemistry Plot Controls
        self.geochem_section = self._create_section(
            self.mode_section,
            "Geochemistry Plot Controls",
            "Toggle model curves, paleoisochrons and age lines."
        )

        # Isochron Line Toggle
        self.check_vars['show_isochrons'] = tk.BooleanVar(value=getattr(app_state, 'show_isochrons', True))
        chk_iso = ttk.Checkbutton(
            self.geochem_section,
            text=self._translate("Show Age Isochrons"),
            variable=self.check_vars['show_isochrons'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        chk_iso.pack(anchor=tk.W, pady=2)
        self._register_translation(chk_iso, "Show Age Isochrons")

        self.check_vars['show_model_curves'] = tk.BooleanVar(
            value=getattr(app_state, 'show_model_curves', True)
        )
        chk_model_curves = ttk.Checkbutton(
            self.geochem_section,
            text=self._translate("Show Model Curves"),
            variable=self.check_vars['show_model_curves'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        chk_model_curves.pack(anchor=tk.W, pady=2)
        self._register_translation(chk_model_curves, "Show Model Curves")

        # Model curve selection removed: curves follow current model only

        self.check_vars['show_paleoisochrons'] = tk.BooleanVar(
            value=getattr(app_state, 'show_paleoisochrons', True)
        )
        chk_paleo = ttk.Checkbutton(
            self.geochem_section,
            text=self._translate("Show Paleoisochrons"),
            variable=self.check_vars['show_paleoisochrons'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        chk_paleo.pack(anchor=tk.W, pady=2)
        self._register_translation(chk_paleo, "Show Paleoisochrons")

        # Paleoisochron density (step in Ma)
        paleo_step_frame = ttk.Frame(self.geochem_section, style='CardBody.TFrame')
        paleo_step_frame.pack(fill=tk.X, pady=(2, 4))
        paleo_step_label = ttk.Label(
            paleo_step_frame,
            text=self._translate("Paleoisochron Step (Ma):"),
            style='Body.TLabel'
        )
        paleo_step_label.pack(side=tk.LEFT)
        self._register_translation(paleo_step_label, "Paleoisochron Step (Ma):")

        self.paleo_step_var = tk.StringVar(value=str(getattr(app_state, 'paleoisochron_step', 1000)))
        paleo_step_spin = ttk.Spinbox(
            paleo_step_frame,
            from_=50,
            to=5000,
            increment=50,
            width=6,
            textvariable=self.paleo_step_var,
            command=self._on_change
        )
        paleo_step_spin.pack(side=tk.LEFT, padx=(8, 0))
        paleo_step_spin.bind('<Return>', lambda e: self._on_change())
        paleo_step_spin.bind('<FocusOut>', lambda e: self._on_change())

        self.check_vars['show_model_age_lines'] = tk.BooleanVar(
            value=getattr(app_state, 'show_model_age_lines', True)
        )
        chk_age = ttk.Checkbutton(
            self.geochem_section,
            text=self._translate("Show Model Age Lines"),
            variable=self.check_vars['show_model_age_lines'],
            command=self._on_change,
            style='Option.TCheckbutton'
        )
        chk_age.pack(anchor=tk.W, pady=2)
        self._register_translation(chk_age, "Show Model Age Lines")
        
        # 2D Scatter Parameters
        self.twod_section = self._create_section(
            self.mode_section,
            "2D Scatter Parameters",
            "Select axes for 2D scatter plot."
        )
        
        twod_grid = ttk.Frame(self.twod_section, style='CardBody.TFrame')
        twod_grid.pack(fill=tk.X, pady=(4, 0))
        
        # X Axis
        lbl_x = ttk.Label(twod_grid, text=self._translate("X Axis:"), style='Body.TLabel')
        lbl_x.pack(anchor=tk.W)
        self._register_translation(lbl_x, "X Axis:")
        
        self.xaxis_var = tk.StringVar()
        self.xaxis_combo = ttk.Combobox(twod_grid, textvariable=self.xaxis_var, state="readonly")
        self.xaxis_combo.pack(fill=tk.X, pady=(0, 8))
        self.xaxis_combo.bind("<<ComboboxSelected>>", self._on_2d_axis_change)
        
        # Y Axis
        lbl_y = ttk.Label(twod_grid, text=self._translate("Y Axis:"), style='Body.TLabel')
        lbl_y.pack(anchor=tk.W)
        self._register_translation(lbl_y, "Y Axis:")
        
        self.yaxis_var = tk.StringVar()
        self.yaxis_combo = ttk.Combobox(twod_grid, textvariable=self.yaxis_var, state="readonly")
        self.yaxis_combo.pack(fill=tk.X)
        self.yaxis_combo.bind("<<ComboboxSelected>>", self._on_2d_axis_change)

        # Initial visibility update
        self._update_algorithm_visibility()

    def _build_ternary_section(self, parent):
        """Build the Ternary Plot controls."""

        self.ternary_section = self._create_section(
            parent,
            "Ternary Plot",
            "Standard Ternary Diagram (mpltern)"
        )
        
        info_label = ttk.Label(
            self.ternary_section, 
            text=self._translate("Using Standard Ternary Plot.\nData is plotted as relative proportions."),
            style='BodyMuted.TLabel',
            wraplength=250
        )
        info_label.pack(anchor=tk.W, pady=8)
        self._register_translation(info_label, "Using Standard Ternary Plot.\nData is plotted as relative proportions.")

        # Auto Zoom Checkbox
        self.ternary_auto_zoom_var = tk.BooleanVar(value=False)
        self.ternary_auto_zoom_chk = ttk.Checkbutton(
            self.ternary_section,
            text=self._translate("Auto-Zoom to Data"),
            variable=self.ternary_auto_zoom_var,
            command=self._on_ternary_zoom_change,
            style='Option.TCheckbutton'
        )
        self.ternary_auto_zoom_chk.pack(anchor=tk.W, pady=5)
        self._register_translation(self.ternary_auto_zoom_chk, "Auto-Zoom to Data")

        # Stretch Mode Control (slider with 3 modes)
        scale_frame = ttk.Frame(self.ternary_section)
        scale_frame.pack(fill=tk.X, pady=8)
        
        # Header with Label and Value
        header_frame = ttk.Frame(scale_frame)
        header_frame.pack(fill=tk.X, pady=(0, 2))
        
        lbl_scale = ttk.Label(header_frame, text=self._translate("Stretch Mode"), style='Body.TLabel')
        lbl_scale.pack(side=tk.LEFT)
        self._register_translation(lbl_scale, "Stretch Mode")
        
        self._stretch_modes = ['power', 'minmax', 'hybrid']
        mode_label_map = {
            'power': self._translate("Power"),
            'minmax': self._translate("Min-Max"),
            'hybrid': self._translate("Hybrid")
        }
        current_mode = getattr(app_state, 'ternary_stretch_mode', 'power')
        current_idx = self._stretch_modes.index(current_mode) if current_mode in self._stretch_modes else 0
        self.lbl_ternary_scale_val = ttk.Label(header_frame, text=mode_label_map[self._stretch_modes[current_idx]])
        self.lbl_ternary_scale_val.pack(side=tk.RIGHT)

        self.ternary_scale_var = tk.DoubleVar(value=current_idx)
        
        # Debounced Slider
        self.ternary_scale_slider = ttk.Scale(
            scale_frame,
            from_=0,
            to=2,
            variable=self.ternary_scale_var,
            orient=tk.HORIZONTAL,
            command=self._on_ternary_scale_slide
        )
        self.ternary_scale_slider.pack(fill=tk.X)

        # Update label when language changes
        def _refresh_mode_label():
            mode = getattr(app_state, 'ternary_stretch_mode', 'power')
            if mode not in self._stretch_modes:
                mode = 'power'
            self.lbl_ternary_scale_val.configure(text=mode_label_map[mode])
        self._register_translation(self.lbl_ternary_scale_val, "Stretch Mode", formatter=lambda: _refresh_mode_label() or "Stretch Mode")

        # Stretch Checkbox
        self.ternary_stretch_var = tk.BooleanVar(value=getattr(app_state, 'ternary_stretch', False))
        chk_stretch = ttk.Checkbutton(
            self.ternary_section, 
            text=self._translate("Stretch to Fill"), 
            variable=self.ternary_stretch_var,
            command=self._on_stretch_change
        )
        chk_stretch.pack(fill=tk.X, pady=8)
        self._register_translation(chk_stretch, "Stretch to Fill")

    def _on_stretch_change(self):
        """Handle stretch toggle."""
        app_state.ternary_stretch = self.ternary_stretch_var.get()
        if self.callback:
            self.callback('alg_params')

    def _on_ternary_scale_slide(self, val):
        """Handle slider movement with debounce."""
        try:
            val = float(val)
            # Update label immediately for feedback
            self.lbl_ternary_scale_val.configure(text=f"{val:.2f}")
            
            # Cancel previous timer
            if self._ternary_update_job:
                self.root.after_cancel(self._ternary_update_job)
            
            # Schedule new update in 150ms
            self._ternary_update_job = self.root.after(150, lambda v=val: self._trigger_ternary_update(v))
            
        except ValueError:
            pass

    def _trigger_ternary_update(self, val):
        """Execute the actual update."""
        # Snap to discrete modes
        idx = int(round(val))
        idx = max(0, min(2, idx))
        mode = self._stretch_modes[idx]
        app_state.ternary_stretch_mode = mode
        # Update label
        mode_label_map = {
            'power': self._translate("Power"),
            'minmax': self._translate("Min-Max"),
            'hybrid': self._translate("Hybrid")
        }
        self.lbl_ternary_scale_val.configure(text=mode_label_map.get(mode, mode))
        # Ensure stretch is enabled when adjusting strength
        app_state.ternary_stretch = True
        if hasattr(self, 'ternary_stretch_var'):
            self.ternary_stretch_var.set(True)
        self._on_change()
        self._ternary_update_job = None

    def _on_ternary_zoom_change(self):
        """Handle Auto Zoom toggle."""
        app_state.ternary_auto_zoom = self.ternary_auto_zoom_var.get()
        if self.callback:
            self.callback()

    # Model curve selection handler removed

    def _refresh_2d_combos(self):
        """Update 2D scatter axis comboboxes with available columns."""
        if not hasattr(self, 'xaxis_combo') or not hasattr(self, 'yaxis_combo'):
            return

        cols = [c for c in app_state.data_cols if c in app_state.df_global.columns]
        self.xaxis_combo['values'] = cols
        self.yaxis_combo['values'] = cols
        
        current = getattr(app_state, 'selected_2d_cols', [])
        
        # If no current selection (or invalid), try to pick first two
        if (not current or len(current) != 2) and len(cols) >= 2:
            current = [cols[0], cols[1]]
            app_state.selected_2d_cols = current
            app_state.selected_2d_confirmed = True
        
        if len(current) == 2:
            if current[0] in cols:
                self.xaxis_var.set(current[0])
            if current[1] in cols:
                self.yaxis_var.set(current[1])

    def _on_2d_axis_change(self, event=None):
        """Handle 2D axis selection change."""
        x_col = self.xaxis_var.get()
        y_col = self.yaxis_var.get()
        
        if x_col and y_col:
            app_state.selected_2d_cols = [x_col, y_col]
            app_state.selected_2d_confirmed = True
            print(f"[DEBUG] 2D Axes Changed: X={x_col}, Y={y_col}", flush=True)
            self._on_change()  # Trigger update

    def _on_pca_dim_change(self):
        """Handle changes to PCA dimension selection spinners"""
        try:
            # Get values from string vars
            try:
                x_dim = int(self.pca_x_var.get())
                y_dim = int(self.pca_y_var.get())
            except ValueError:
                return  # Invalid input
            
            # Convert to 0-based indices
            x_idx = max(0, x_dim - 1)
            y_idx = max(0, y_dim - 1)
            
            current_indices = app_state.pca_component_indices
            if current_indices[0] != x_idx or current_indices[1] != y_idx:
                print(f"[DEBUG] PCA dimensions changed: {current_indices} -> [{x_idx}, {y_idx}]", flush=True)
                app_state.pca_component_indices = [x_idx, y_idx]
                
                # Trigger update if we are in PCA or RobustPCA mode
                if app_state.render_mode in ('PCA', 'RobustPCA'):
                    if self.callback:
                        self.callback()
        except Exception as e:
            print(f"[ERROR] _on_pca_dim_change error: {e}", flush=True)

    def _refresh_group_list(self):
        """Refresh the list of group column radio buttons"""
        if not hasattr(self, 'group_container'):
            return
            
        for widget in self.group_container.winfo_children():
            widget.destroy()

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

    def _update_algorithm_visibility(self):
        """Show or hide algorithm controls based on current mode."""
        mode = app_state.render_mode
        if mode in ('PB_MODELS_76', 'PB_MODELS_86'):
            mode = 'PB_EVOL_76' if mode.endswith('_76') else 'PB_EVOL_86'
        
        # Hide all sections first
        for section in ['umap_section', 'tsne_section', 'pca_section', 'rpca_section', 
                        'ternary_section', 'geochem_section', 'twod_section']:
            if hasattr(self, section):
                getattr(self, section).pack_forget()

        # Show relevant section
        if mode == 'UMAP' and hasattr(self, 'umap_section'):
            self.umap_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'tSNE' and hasattr(self, 'tsne_section'):
            self.tsne_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'PCA' and hasattr(self, 'pca_section'):
            self.pca_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'RobustPCA' and hasattr(self, 'rpca_section'):
            self.rpca_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == 'Ternary' and hasattr(self, 'ternary_section'):
            self.ternary_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode in ('PB_EVOL_76', 'PB_EVOL_86'):
            if hasattr(self, 'geochem_section'):
                self.geochem_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode in ('PB_MU_AGE', 'PB_KAPPA_AGE') and hasattr(self, 'geochem_section'):
            self.geochem_section.pack(fill=tk.X, padx=6, pady=6)
        elif mode == '2D' and hasattr(self, 'twod_section'):
            self.twod_section.pack(fill=tk.X, padx=6, pady=6)
            self._refresh_2d_combos()
