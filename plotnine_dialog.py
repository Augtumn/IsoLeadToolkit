import tkinter as tk
from tkinter import ttk, messagebox
import plotnine as p9
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from core.state import app_state
from core.localization import translate

class PlotnineDialog:
    def __init__(self, parent):
        self.top = tk.Toplevel(parent)
        self.top.title(translate("Plotnine Visualization"))
        self.top.geometry("900x700")
        
        # Make modal-like but non-blocking (or just a regular window)
        try:
            self.top.focus_force()
        except:
            pass

        self.df = app_state.df_global
        
        if self.df is None or self.df.empty:
            label = ttk.Label(self.top, text=translate("No data available. Please load data first."), style='Body.TLabel')
            label.pack(expand=True)
            return

        # Prepare columns
        self.columns = sorted(list(self.df.columns))
        
        # Styles
        style_frame = ttk.Frame(self.top, padding=10)
        style_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Controls
        controls_frame = ttk.Frame(style_frame)
        controls_frame.pack(fill=tk.X)
        
        # X Axis
        ttk.Label(controls_frame, text=translate("X Axis:")).pack(side=tk.LEFT, padx=(0, 5))
        self.x_var = tk.StringVar()
        self.x_combo = ttk.Combobox(controls_frame, textvariable=self.x_var, values=self.columns, state="readonly", width=15)
        self.x_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # Y Axis
        ttk.Label(controls_frame, text=translate("Y Axis:")).pack(side=tk.LEFT, padx=(0, 5))
        self.y_var = tk.StringVar()
        self.y_combo = ttk.Combobox(controls_frame, textvariable=self.y_var, values=self.columns, state="readonly", width=15)
        self.y_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # Color
        ttk.Label(controls_frame, text=translate("Color:")).pack(side=tk.LEFT, padx=(0, 5))
        self.color_var = tk.StringVar(value="None")
        self.color_combo = ttk.Combobox(controls_frame, textvariable=self.color_var, values=["None"] + self.columns, state="readonly", width=15)
        self.color_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # Size
        ttk.Label(controls_frame, text=translate("Size:")).pack(side=tk.LEFT, padx=(0, 5))
        self.size_var = tk.StringVar(value="None")
        self.size_combo = ttk.Combobox(controls_frame, textvariable=self.size_var, values=["None"] + self.columns, state="readonly", width=15)
        self.size_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # Plot Button
        btn_plot = ttk.Button(controls_frame, text=translate("Generate Plot"), command=self.plot, style='Accent.TButton')
        btn_plot.pack(side=tk.LEFT, padx=(10, 0))
        
        # Canvas Area
        self.plot_container = ttk.Frame(self.top)
        self.plot_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = None
        
        # Set default selections if possible
        if len(self.columns) > 0:
            self.x_combo.current(0)
        if len(self.columns) > 1:
            self.y_combo.current(1)

    def plot(self):
        x_col = self.x_var.get()
        y_col = self.y_var.get()
        color_col = self.color_var.get()
        size_col = self.size_var.get()
        
        if not x_col or not y_col:
            messagebox.showwarning(translate("Warning"), translate("Please select both X and Y axes."))
            return

        try:
            # Construct mapping
            mapping = p9.aes(x=x_col, y=y_col)
            if color_col != "None":
                mapping = p9.aes(x=x_col, y=y_col, color=color_col)
            if size_col != "None":
                if color_col != "None":
                    mapping = p9.aes(x=x_col, y=y_col, color=color_col, size=size_col)
                else:
                    mapping = p9.aes(x=x_col, y=y_col, size=size_col)
                
            # Create plot
            # Using theme_matplotlib to respect some matplotlib settings or theme_bw for clean look
            # Also using custom font if set
            font_family = 'sans-serif'
            
            p = (p9.ggplot(self.df, mapping)
                 + p9.geom_point()
                 + p9.theme_bw()
                 + p9.theme(text=p9.element_text(family=font_family))
                 + p9.labs(x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
                )
            
            # Render to Matplotlib Figure
            fig = p.draw()

            # Update sample coordinates for tooltips in this dialog if needed
            # (Though events.py uses app_state.sample_coordinates which might be overwritten by main plot)

            # Clear previous
            if self.canvas:
                self.canvas.get_tk_widget().destroy()
                # Close the previous figure to free memory
                if hasattr(self, 'current_fig') and self.current_fig:
                    plt.close(self.current_fig)

            self.current_fig = fig

            # Show on Tkinter
            self.canvas = FigureCanvasTkAgg(fig, master=self.plot_container)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        except Exception as e:
            messagebox.showerror(translate("Error"), f"Plotting failed: {str(e)}")
            import traceback
            traceback.print_exc()

def show_plotnine_dialog(parent):
    PlotnineDialog(parent)
