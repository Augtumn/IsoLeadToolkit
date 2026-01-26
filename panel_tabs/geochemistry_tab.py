"""
Geochemistry Tab - Geochemical parameters and model settings
"""
import tkinter as tk
from tkinter import ttk, messagebox

from state import app_state

try:
    import geochemistry
    from geochemistry import calculate_all_parameters
except ImportError:
    geochemistry = None
    calculate_all_parameters = None


class GeochemistryTabMixin:
    """Mixin providing the Geochemistry tab builder"""

    def _build_geo_tab(self, parent):
        """Build the Geochemistry Parameters tab with optimized layout (Grid)"""
        frame = self._build_scrollable_frame(parent)
        
        if geochemistry is None:
            lbl = ttk.Label(frame, text=self._translate("Geochemical module not loaded."), style='BodyMuted.TLabel')
            lbl.pack(anchor=tk.W, pady=20, padx=20)
            self._register_translation(lbl, "Geochemical module not loaded.")
            return

        # Helper to add entry in Grid Layout
        def add_entry_grid(parent_frame, label_key, default_val, var_key, row, col):
            # Container for label+entry
            cell = ttk.Frame(parent_frame, style='ControlPanel.TFrame')
            cell.grid(row=row, column=col, padx=8, pady=4, sticky=tk.EW)
            
            lbl = ttk.Label(cell, text=self._translate(label_key), style='Body.TLabel')
            lbl.pack(anchor=tk.W)
            self._register_translation(lbl, label_key)
            
            var = tk.StringVar(value=str(default_val))
            self.geo_vars[var_key] = var
            entry = ttk.Entry(cell, textvariable=var)
            entry.pack(fill=tk.X, expand=True)
            return var

        # Load current params from module
        try:
            current_params = geochemistry.engine.get_parameters()
        except AttributeError:
            lbl = ttk.Label(frame, text="Module Outdated. Missing get_parameters().")
            lbl.pack()
            return

        # 0. Model Selection
        sect_model = self._create_section(frame, "Model Selection", "Choose a standard parameter set.")
        model_frame = ttk.Frame(sect_model, style='CardBody.TFrame')
        model_frame.pack(fill=tk.X, expand=True)
        
        lbl_mod = ttk.Label(model_frame, text=self._translate("Preset Model:"), style='Body.TLabel')
        lbl_mod.pack(side=tk.LEFT, padx=(0, 5))
        self._register_translation(lbl_mod, "Preset Model:")
        
        try:
            models = geochemistry.engine.get_available_models()
            current_model = getattr(geochemistry.engine, 'current_model_name', models[0] if models else "")
        except:
            models = []
            current_model = ""
        
        self.geo_model_var = tk.StringVar(value=current_model)
        model_combo = ttk.Combobox(model_frame, textvariable=self.geo_model_var, values=models, state="readonly")
        model_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

        # 1. Time Constants
        sect_time = self._create_section(frame, "Time Parameters (Ma)", "Ages and time constants.")
        
        grid_time = ttk.Frame(sect_time, style='CardBody.TFrame')
        grid_time.pack(fill=tk.X, expand=True)
        grid_time.columnconfigure(0, weight=1)
        grid_time.columnconfigure(1, weight=1)
        
        add_entry_grid(grid_time, "T1 (1st Stage)", current_params.get('T1', '')/1e6, 'T1', 0, 0)
        add_entry_grid(grid_time, "T2 (Earth Age)", current_params.get('T2', '')/1e6, 'T2', 0, 1)
        add_entry_grid(grid_time, "Tsec (2nd Stage)", current_params.get('Tsec', '')/1e6, 'Tsec', 1, 0)

        # 2. Decay Constants
        sect_decay = self._create_section(frame, "Decay Constants (a^-1)", "Radioactive decay constants.")
        
        grid_decay = ttk.Frame(sect_decay, style='CardBody.TFrame')
        grid_decay.pack(fill=tk.X, expand=True)
        grid_decay.columnconfigure(0, weight=1)
        grid_decay.columnconfigure(1, weight=1)
        
        add_entry_grid(grid_decay, "λ (238U)", current_params.get('lambda_238', ''), 'lambda_238', 0, 0)
        add_entry_grid(grid_decay, "λ (235U)", current_params.get('lambda_235', ''), 'lambda_235', 0, 1)
        add_entry_grid(grid_decay, "λ (232Th)", current_params.get('lambda_232', ''), 'lambda_232', 1, 0)

        # 3. Initial Lead
        sect_init = self._create_section(frame, "Initial Lead Compositions", "Primordial and Two-Stage initial ratios.")
        
        grid_init = ttk.Frame(sect_init, style='CardBody.TFrame')
        grid_init.pack(fill=tk.X, expand=True)
        grid_init.columnconfigure(0, weight=1)
        grid_init.columnconfigure(1, weight=1)
        
        # Subheaders
        sub_p = ttk.Label(grid_init, text=self._translate("Primordial (T1/T2)"), style='Body.TLabel', font="-weight bold")
        sub_p.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(5,0), padx=5)
        self._register_translation(sub_p, "Primordial (T1/T2)")
        
        add_entry_grid(grid_init, "a0 (206/204)", current_params.get('a0', ''), 'a0', 1, 0)
        add_entry_grid(grid_init, "b0 (207/204)", current_params.get('b0', ''), 'b0', 1, 1)
        add_entry_grid(grid_init, "c0 (208/204)", current_params.get('c0', ''), 'c0', 2, 0)

        sub_s = ttk.Label(grid_init, text=self._translate("Stacy-Kramers 2nd Stage"), style='Body.TLabel', font="-weight bold")
        sub_s.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10,0), padx=5)
        self._register_translation(sub_s, "Stacy-Kramers 2nd Stage")
        
        add_entry_grid(grid_init, "a1 (206/204)", current_params.get('a1', ''), 'a1', 4, 0)
        add_entry_grid(grid_init, "b1 (207/204)", current_params.get('b1', ''), 'b1', 4, 1)
        add_entry_grid(grid_init, "c1 (208/204)", current_params.get('c1', ''), 'c1', 5, 0)

        # 4. Mantle & Ratios
        sect_mantle = self._create_section(frame, "Mantle & Production", "Mantle reservoir parameters.")
        
        grid_mantle = ttk.Frame(sect_mantle, style='CardBody.TFrame')
        grid_mantle.pack(fill=tk.X, expand=True)
        grid_mantle.columnconfigure(0, weight=1)
        grid_mantle.columnconfigure(1, weight=1)
        
        add_entry_grid(grid_mantle, "μ (Mantle)", current_params.get('mu_M', ''), 'mu_M', 0, 0)
        add_entry_grid(grid_mantle, "ω (Mantle)", current_params.get('omega_M', ''), 'omega_M', 0, 1)
        add_entry_grid(grid_mantle, "U Ratio (235/238)", current_params.get('U_ratio', ''), 'U_ratio', 1, 0)

        # Actions
        btn_frame = ttk.Frame(frame, style='ControlPanel.TFrame')
        btn_frame.pack(fill=tk.X, pady=20)
        
        def apply_changes():
            new_params = {}
            try:
                # Handle Time explicitly (Ma -> years)
                if 'T1' in self.geo_vars:
                    new_params['T1'] = float(self.geo_vars['T1'].get()) * 1e6
                if 'T2' in self.geo_vars:
                    new_params['T2'] = float(self.geo_vars['T2'].get()) * 1e6
                new_params['Tsec'] = float(self.geo_vars['Tsec'].get()) * 1e6
                
                # Others direct float conversion
                direct_keys = ['lambda_238', 'lambda_235', 'lambda_232', 
                               'a0', 'b0', 'c0', 'a1', 'b1', 'c1',
                               'mu_M', 'omega_M', 'U_ratio']
                               
                for k in direct_keys:
                    new_params[k] = float(self.geo_vars[k].get())
                    
                geochemistry.engine.update_parameters(new_params)
                
                # Trigger Data Recalculation if data exists
                if app_state.df_global is not None:
                    if app_state.render_mode == 'V1V2':
                        self._on_change()
                
                messagebox.showinfo(self._translate("Success"), self._translate("Parameters updated successfully."))

            except ValueError:
                messagebox.showerror(self._translate("Error"), self._translate("Invalid numeric input."))

        apply_btn = ttk.Button(btn_frame, text=self._translate("Apply Changes"), style='Accent.TButton', command=apply_changes)
        apply_btn.pack(side=tk.RIGHT, padx=5)
        self._register_translation(apply_btn, "Apply Changes")

        def reset_defaults():
            defaults = {
                'Tsec': 3700,
                'lambda_238': 1.55125e-10, 'lambda_235': 9.8485e-10, 'lambda_232': 4.94752e-11,
                'a0': 9.307, 'b0': 10.294, 'c0': 29.476,
                'a1': 11.152, 'b1': 12.998, 'c1': 31.23,
                'mu_M': 7.8, 'omega_M': 4.04 * 7.8, 'U_ratio': 1/137.88
            }
            
            for k, v in defaults.items():
                if k in self.geo_vars:
                    self.geo_vars[k].set(str(v))
            
            apply_changes()

        reset_btn = ttk.Button(btn_frame, text=self._translate("Reset Defaults"), style='Secondary.TButton', command=reset_defaults)
        reset_btn.pack(side=tk.RIGHT)
        self._register_translation(reset_btn, "Reset Defaults")

    def _on_model_selected(self, event=None):
        """Handle Geochemistry Model Selection Change"""
        model_name = self.geo_model_var.get()
        if not model_name or geochemistry is None:
            return
        
        # Load preset into engine
        if geochemistry.engine.load_preset(model_name):
            # Refresh UI variables
            current_params = geochemistry.engine.get_parameters()
            
            # Helper to safely update StringVar
            def safe_set(key, val):
                if key in self.geo_vars:
                    self.geo_vars[key].set(str(val))

            # Updates
            safe_set('T1', current_params['T1'] / 1e6)
            safe_set('T2', current_params['T2'] / 1e6)
            safe_set('Tsec', current_params['Tsec'] / 1e6)
            
            safe_set('lambda_238', current_params['lambda_238'])
            safe_set('lambda_235', current_params['lambda_235'])
            safe_set('lambda_232', current_params['lambda_232'])
            
            safe_set('a0', current_params['a0'])
            safe_set('b0', current_params['b0'])
            safe_set('c0', current_params['c0'])
            
            safe_set('a1', current_params['a1'])
            safe_set('b1', current_params['b1'])
            safe_set('c1', current_params['c1'])
            
            safe_set('mu_M', current_params['mu_M'])
            safe_set('omega_M', current_params['omega_M'])
            safe_set('U_ratio', current_params['U_ratio'])
            
            print(f"[INFO] Loaded Geochemistry Model: {model_name}")
