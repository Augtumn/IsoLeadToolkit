"""
Panel Handlers - Core event handlers for the Control Panel
"""
import tkinter as tk
from tkinter import ttk, messagebox

from state import app_state
from localization import translate, available_languages, set_language


class PanelHandlersMixin:
    """Mixin providing core event handlers for the ControlPanel"""

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
                elif requested_mode == 'Ternary' and len(app_state.data_cols) < 3:
                    print("[WARN] Need at least three numeric columns for Ternary view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != 'Ternary' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)
                elif requested_mode == '2D' and len(app_state.data_cols) < 2:
                    print("[WARN] Need at least two numeric columns for 2D view; reverting to previous mode.", flush=True)
                    requested_mode = previous_mode if previous_mode != '2D' else 'UMAP'
                    self.radio_vars['render_mode'].set(requested_mode)

                if requested_mode in ('UMAP', 'tSNE', 'PCA', 'RobustPCA'):
                    old_algo = app_state.algorithm
                    if requested_mode == 'UMAP':
                        app_state.algorithm = 'UMAP'
                    elif requested_mode == 'tSNE':
                        app_state.algorithm = 'tSNE'
                    elif requested_mode == 'PCA':
                        app_state.algorithm = 'PCA'
                    else:
                        app_state.algorithm = 'RobustPCA'
                    
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
                    elif requested_mode == 'Ternary':
                        app_state.selected_ternary_confirmed = False
                    
                    self._update_algorithm_visibility()
                    # Ensure sliders reflect current data/state when switching to Ternary
                    if requested_mode == 'Ternary' and hasattr(self, 'update_ternary_sliders_from_data'):
                        self.update_ternary_sliders_from_data(preserve_existing=True)

            if app_state.render_mode in ('UMAP', 'tSNE', 'PCA', 'RobustPCA'):
                if app_state.render_mode == 'UMAP':
                    app_state.algorithm = 'UMAP'
                elif app_state.render_mode == 'tSNE':
                    app_state.algorithm = 'tSNE'
                elif app_state.render_mode == 'PCA':
                    app_state.algorithm = 'PCA'
                else:
                    app_state.algorithm = 'RobustPCA'
            
            # Update Ellipse setting
            if 'ellipses' in self.check_vars:
                app_state.show_ellipses = self.check_vars['ellipses'].get()
            
            # Update KDE setting
            if 'show_kde' in self.check_vars:
                app_state.show_kde = self.check_vars['show_kde'].get()
                
            # Update Isochron settings
            if 'show_isochrons' in self.check_vars:
                app_state.show_isochrons = self.check_vars['show_isochrons'].get()
            if 'show_growth_curves' in self.check_vars:
                app_state.show_growth_curves = self.check_vars['show_growth_curves'].get()

            if 'confidence' in self.radio_vars:
                app_state.ellipse_confidence = self.radio_vars['confidence'].get()

            # Update UMAP parameters
            umap_changed = False
            if 'umap_n' in self.sliders and 'umap_n' in self.labels:
                new_val = int(self.sliders['umap_n'].get())
                if app_state.umap_params['n_neighbors'] != new_val:
                    print(f"[DEBUG] UMAP n_neighbors changed: {app_state.umap_params['n_neighbors']} -> {new_val}", flush=True)
                    umap_changed = True
                app_state.umap_params['n_neighbors'] = new_val
                self.labels['umap_n'].config(text=f"{new_val}")
            
            if 'umap_d' in self.sliders and 'umap_d' in self.labels:
                new_val = float(self.sliders['umap_d'].get())
                if app_state.umap_params['min_dist'] != new_val:
                    print(f"[DEBUG] UMAP min_dist changed: {app_state.umap_params['min_dist']} -> {new_val}", flush=True)
                    umap_changed = True
                app_state.umap_params['min_dist'] = new_val
                self.labels['umap_d'].config(text=f"{new_val:.2f}")
            
            if 'umap_r' in self.sliders and 'umap_r' in self.labels:
                new_val = int(self.sliders['umap_r'].get())
                if app_state.umap_params['random_state'] != new_val:
                    print(f"[DEBUG] UMAP random_state changed: {app_state.umap_params['random_state']} -> {new_val}", flush=True)
                    umap_changed = True
                app_state.umap_params['random_state'] = new_val
                self.labels['umap_r'].config(text=f"{new_val}")
            
            # Clear UMAP cache if parameters changed
            if umap_changed:
                print(f"[DEBUG] UMAP parameters changed, clearing UMAP cache", flush=True)
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
                    print(f"[DEBUG] t-SNE perplexity changed: {app_state.tsne_params['perplexity']} -> {p}", flush=True)
                    tsne_changed = True
                app_state.tsne_params['perplexity'] = p
                self.labels['tsne_p'].config(text=f"{p}")
            
            if 'tsne_lr' in self.sliders and 'tsne_lr' in self.labels:
                new_val = int(self.sliders['tsne_lr'].get())
                if app_state.tsne_params['learning_rate'] != new_val:
                    print(f"[DEBUG] t-SNE learning_rate changed: {app_state.tsne_params['learning_rate']} -> {new_val}", flush=True)
                    tsne_changed = True
                app_state.tsne_params['learning_rate'] = new_val
                self.labels['tsne_lr'].config(text=f"{new_val}")

            if 'tsne_r' in self.sliders and 'tsne_r' in self.labels:
                new_val = int(self.sliders['tsne_r'].get())
                if app_state.tsne_params.get('random_state') != new_val:
                    print(f"[DEBUG] t-SNE random_state changed: {app_state.tsne_params.get('random_state')} -> {new_val}", flush=True)
                    tsne_changed = True
                app_state.tsne_params['random_state'] = new_val
                self.labels['tsne_r'].config(text=f"{new_val}")
            
            # Clear t-SNE cache if parameters changed
            if tsne_changed:
                print(f"[DEBUG] t-SNE parameters changed, clearing t-SNE cache", flush=True)
                keys_to_remove = [k for k in app_state.embedding_cache.keys() if k[0] == 'tsne']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]

            # Update PCA parameters
            pca_changed = False
            if 'pca_n' in self.sliders and 'pca_n' in self.labels:
                new_val = int(self.sliders['pca_n'].get())
                if app_state.pca_params.get('n_components') != new_val:
                    print(f"[DEBUG] PCA n_components changed: {app_state.pca_params.get('n_components')} -> {new_val}", flush=True)
                    pca_changed = True
                    app_state.pca_params['n_components'] = new_val
                    self.labels['pca_n'].config(text=f"{new_val}")

            if 'pca_r' in self.sliders and 'pca_r' in self.labels:
                new_val = int(self.sliders['pca_r'].get())
                if app_state.pca_params.get('random_state') != new_val:
                    print(f"[DEBUG] PCA random_state changed: {app_state.pca_params.get('random_state')} -> {new_val}", flush=True)
                    pca_changed = True
                    app_state.pca_params['random_state'] = new_val
                    self.labels['pca_r'].config(text=f"{new_val}")

            if pca_changed:
                print(f"[DEBUG] PCA parameters changed, clearing PCA cache", flush=True)
                keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'pca']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]

            # Update Robust PCA parameters
            rpca_changed = False
            if 'rpca_n' in self.sliders and 'rpca_n' in self.labels:
                new_val = int(self.sliders['rpca_n'].get())
                if app_state.robust_pca_params.get('n_components') != new_val:
                    print(f"[DEBUG] Robust PCA n_components changed: {app_state.robust_pca_params.get('n_components')} -> {new_val}", flush=True)
                    rpca_changed = True
                    app_state.robust_pca_params['n_components'] = new_val
                    self.labels['rpca_n'].config(text=f"{new_val}")

            if 'rpca_r' in self.sliders and 'rpca_r' in self.labels:
                new_val = int(self.sliders['rpca_r'].get())
                if app_state.robust_pca_params.get('random_state') != new_val:
                    print(f"[DEBUG] Robust PCA random_state changed: {app_state.robust_pca_params.get('random_state')} -> {new_val}", flush=True)
                    rpca_changed = True
                    app_state.robust_pca_params['random_state'] = new_val
                    self.labels['rpca_r'].config(text=f"{new_val}")

            if 'rpca_sf' in self.sliders and 'rpca_sf' in self.labels:
                new_val = float(self.sliders['rpca_sf'].get())
                current_val = app_state.robust_pca_params.get('support_fraction')
                if current_val is None or abs(current_val - new_val) > 1e-6:
                    rpca_changed = True
                    print(f"[DEBUG] Robust PCA support_fraction changed: {current_val} -> {new_val}", flush=True)
                    app_state.robust_pca_params['support_fraction'] = new_val
                    self.labels['rpca_sf'].config(text=f"{new_val:.2f}")

            if rpca_changed:
                print(f"[DEBUG] Robust PCA parameters changed, clearing cache", flush=True)
                keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'robust_pca']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update V1V2 parameters
            v1v2_changed = False
            if 'v1v2_scale' in self.sliders and 'v1v2_scale' in self.labels:
                new_val = float(self.sliders['v1v2_scale'].get())
                if app_state.v1v2_params.get('scale') != new_val:
                    print(f"[DEBUG] V1V2 scale changed: {app_state.v1v2_params.get('scale')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['scale'] = new_val
                    self.labels['v1v2_scale'].config(text=f"{new_val:.1f}")

            if 'v1v2_a' in self.sliders and 'v1v2_a' in self.labels:
                new_val = float(self.sliders['v1v2_a'].get())
                if app_state.v1v2_params.get('a') != new_val:
                    print(f"[DEBUG] V1V2 a changed: {app_state.v1v2_params.get('a')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['a'] = new_val
                    self.labels['v1v2_a'].config(text=f"{new_val:.2f}")

            if 'v1v2_b' in self.sliders and 'v1v2_b' in self.labels:
                new_val = float(self.sliders['v1v2_b'].get())
                if app_state.v1v2_params.get('b') != new_val:
                    print(f"[DEBUG] V1V2 b changed: {app_state.v1v2_params.get('b')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['b'] = new_val
                    self.labels['v1v2_b'].config(text=f"{new_val:.4f}")

            if 'v1v2_c' in self.sliders and 'v1v2_c' in self.labels:
                new_val = float(self.sliders['v1v2_c'].get())
                if app_state.v1v2_params.get('c') != new_val:
                    print(f"[DEBUG] V1V2 c changed: {app_state.v1v2_params.get('c')} -> {new_val}", flush=True)
                    v1v2_changed = True
                    app_state.v1v2_params['c'] = new_val
                    self.labels['v1v2_c'].config(text=f"{new_val:.3f}")

            if v1v2_changed:
                print(f"[DEBUG] V1V2 parameters changed, clearing cache", flush=True)
                keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'v1v2']
                for k in keys_to_remove:
                    del app_state.embedding_cache[k]
            
            # Update common parameters
            if 'size' in self.sliders and 'size' in self.labels:
                app_state.point_size = int(self.sliders['size'].get())
                self.labels['size'].config(text=f"{int(self.sliders['size'].get())}")
            
            # Update Legend Columns
            if 'legend_cols' in self.sliders and 'legend_cols' in self.labels:
                val = int(self.sliders['legend_cols'].get())
                app_state.legend_columns = val
                txt = "Auto" if val == 0 else str(val)
                self.labels['legend_cols'].config(text=txt)

            # Update group column if available
            if 'group' in self.radio_vars:
                old_group = app_state.last_group_col
                new_group = self.radio_vars['group'].get()
                if old_group != new_group:
                    app_state.last_group_col = new_group
                    app_state.visible_groups = None  # Reset visibility filter when group changes
                    print(f"[DEBUG] Group column changed: {old_group} -> {new_group}. Reset visible_groups.", flush=True)
            
            # Call the callback
            print(f"[DEBUG] Calling callback", flush=True)
            if self.callback:
                self.callback()
            print(f"[DEBUG] Callback completed", flush=True)
        
        except KeyError as e:
            print(f"[DEBUG] KeyError in _on_change (expected during init): {e}", flush=True)
        except Exception as e:
            print(f"[ERROR] _on_change: {e}", flush=True)

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

    def _on_toggle_selection(self):
        """Toggle export selection mode from the control panel."""
        from events import toggle_selection_mode
        
        if app_state.render_mode == '3D':
            messagebox.showinfo(
                self._translate("Selection Mode"),
                self._translate("Selection mode is only available in 2D views"),
                parent=self.root
            )
            return

        toggle_selection_mode('export')
        self.update_selection_controls()

    def _on_toggle_ellipse_selection(self):
        """Toggle ellipse selection mode from the control panel."""
        from events import toggle_selection_mode
        
        if app_state.render_mode == '3D':
            messagebox.showinfo(
                self._translate("Selection Mode"),
                self._translate("Selection mode is only available in 2D views"),
                parent=self.root
            )
            return

        toggle_selection_mode('ellipse')
        self.update_selection_controls()

    def _reset_v1v2_defaults(self):
        """Reset V1V2 parameters to their default values."""
        defaults = {
            'v1v2_scale': 1.0,
            'v1v2_a': 0.0,
            'v1v2_b': 2.0367,
            'v1v2_c': -6.143
        }
        
        for key, value in defaults.items():
            if key in self.sliders:
                self.sliders[key].set(value)
        
        # Update state directly
        app_state.v1v2_params['scale'] = defaults['v1v2_scale']
        app_state.v1v2_params['a'] = defaults['v1v2_a']
        app_state.v1v2_params['b'] = defaults['v1v2_b']
        app_state.v1v2_params['c'] = defaults['v1v2_c']
        
        # Update labels
        if 'v1v2_scale' in self.labels:
            self.labels['v1v2_scale'].config(text=f"{defaults['v1v2_scale']:.1f}")
        if 'v1v2_a' in self.labels:
            self.labels['v1v2_a'].config(text=f"{defaults['v1v2_a']:.2f}")
        if 'v1v2_b' in self.labels:
            self.labels['v1v2_b'].config(text=f"{defaults['v1v2_b']:.4f}")
        if 'v1v2_c' in self.labels:
            self.labels['v1v2_c'].config(text=f"{defaults['v1v2_c']:.3f}")

        # Clear cache
        keys_to_remove = [k for k in list(app_state.embedding_cache.keys()) if isinstance(k, tuple) and len(k) > 0 and k[0] == 'v1v2']
        for k in keys_to_remove:
            del app_state.embedding_cache[k]

        # Trigger callback
        if self.callback:
            self.callback()
