"""
Style Manager for Matplotlib visualization
Handles themes, fonts, and color schemes
"""
import matplotlib.pyplot as plt
from matplotlib import rcParams, font_manager
import matplotlib as mpl
from core.config import CONFIG

# --- Color Cycles ---
# Defined to match common scienceplots schemes
class StyleManager:
    """
    Centralized manager for Matplotlib styles, fonts, and color schemes.
    Supports dynamic theme application and CJK font handling.
    """
    
    DEFAULT_PALETTES = {
        'vibrant': ['#EE7733', '#0077BB', '#33BBEE', '#EE3377', '#CC3311', '#009988', '#BBBBBB'],
        'bright': ['#4477AA', '#66CCEE', '#228833', '#CCBB44', '#EE6677', '#AA3377', '#BBBBBB'],
        'high-vis': ['#0d49fb', '#e6091c', '#26eb47', '#8936df', '#fec32d', '#25d7fd'],
        'light': ['#77AADD', '#EE8866', '#EEDD88', '#FFAABB', '#99DDFF', '#44BB99', '#BBCC33', '#AAAA00', '#DDDDDD'],
        'muted': ['#CC6677', '#332288', '#DDCC77', '#117733', '#88CCEE', '#882255', '#44AA99', '#999933', '#AA4499'],
        'retro': ['#4165c0', '#e770a2', '#5ac600', '#696969', '#f2d40f'],
        'std-colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
        'dark_background': ['#8dd3c7', '#feffb3', '#bfbbd9', '#fa8174', '#81b1d2', '#fdb462', '#b3de69', '#bc80bd', '#ccebc5', '#ffed6f'],
    }

    GRID_STYLE = {
        'axes.grid': True,
        'grid.linestyle': '--',
        'grid.linewidth': 0.5,
        'grid.alpha': 0.7,
    }

    # --- UI Themes ---
    UI_THEMES = {
        'Modern Light': {
            'bg': '#ffffff', 'fg': '#1f2937', 'select_bg': '#3b82f6', 
            'panel_bg': '#f3f4f6', 'header_bg': '#e5e7eb',
            'accent': '#2563eb', 'secondary': '#4b5563',
            'plot_bg': '#ffffff', 'plot_fg': '#000000',
            'mpl_style': 'default'
        },
        'Modern Dark': {
            'bg': '#111827', 'fg': '#f9fafb', 'select_bg': '#3b82f6', 
            'panel_bg': '#1f2937', 'header_bg': '#374151',
            'accent': '#60a5fa', 'secondary': '#9ca3af',
            'plot_bg': '#111827', 'plot_fg': '#f3f4f6',
            'mpl_style': 'dark_background'
        },
        'Scientific Blue': {
            'bg': '#f0f9ff', 'fg': '#0c4a6e', 'select_bg': '#0ea5e9', 
            'panel_bg': '#e0f2fe', 'header_bg': '#bae6fd',
            'accent': '#0284c7', 'secondary': '#64748b',
            'plot_bg': '#f0f9ff', 'plot_fg': '#0c4a6e',
            'mpl_style': 'default' 
        },
        'Retro Lab': {
            'bg': '#fef3c7', 'fg': '#78350f', 'select_bg': '#d97706', 
            'panel_bg': '#fffbeb', 'header_bg': '#fde68a',
            'accent': '#b45309', 'secondary': '#92400e',
            'plot_bg': '#fffbeb', 'plot_fg': '#78350f',
            'mpl_style': 'bmh'
        }
    }

    def __init__(self):
        self.palettes = self.DEFAULT_PALETTES.copy()
        self._available_fonts = None

    def get_available_fonts(self):
        """Lazy load available system fonts"""
        if self._available_fonts is None:
            self._available_fonts = {f.name for f in font_manager.fontManager.ttflist}
        return self._available_fonts

    def get_palette_names(self):
        return sorted(list(self.palettes.keys()))

    def get_ui_theme_names(self):
        return list(self.UI_THEMES.keys())

    def get_ui_theme(self, name):
        return self.UI_THEMES.get(name, self.UI_THEMES['Modern Light'])

    def apply_style(self, show_grid=False, color_scheme=None, primary_font=None, cjk_font=None, font_sizes=None):
        """
        Apply global matplotlib settings.
        
        Args:
            show_grid (bool): Enable grid.
            color_scheme (str): Name of the palette to use.
            primary_font (str): Preferred English/Main font family.
            cjk_font (str): Preferred Chinese/CJK font family.
            font_sizes (dict): Dictionary of font sizes used for 'title', 'label', 'tick', 'legend'.
        """
        # 1. Reset to defaults to clear previous state
        plt.style.use('default')
        
        # 2. Apply Grid if requested
        if show_grid:
            rcParams.update(self.GRID_STYLE)
        
        # 3. Apply Color Scheme
        if color_scheme and color_scheme in self.palettes:
            rcParams['axes.prop_cycle'] = mpl.cycler(color=self.palettes[color_scheme])
            # Optional: Handle dark background specific settings if needed
            if color_scheme == 'dark_background':
                # Simplified dark mode tweaks if desired, or rely on plt.style.use('dark_background')
                # But 'dark_background' is just a palette name here.
                pass
        
        # 4. Apply Font Sizes
        if font_sizes:
            self._apply_font_sizes(font_sizes)
            
        # 5. Apply Fonts (Priority: User Primary -> User CJK -> Config CJK -> Generic)
        self._apply_fonts(primary_font, cjk_font)

        # 6. Fix Unicode Minus
        rcParams['axes.unicode_minus'] = False
        
    def _apply_font_sizes(self, font_sizes):
        """Safe apply font sizes"""
        mapping = {
            'title': 'axes.titlesize',
            'label': 'axes.labelsize',
            'tick': ['xtick.labelsize', 'ytick.labelsize'],
            'legend': 'legend.fontsize'
        }
        
        for key, rc_keys in mapping.items():
            val = font_sizes.get(key)
            if val:
                if isinstance(rc_keys, list):
                    for k in rc_keys: rcParams[k] = val
                else:
                    rcParams[rc_keys] = val

    def _apply_fonts(self, primary_font, cjk_font):
        """Construct and apply font stack"""
        final_fonts = []
        
        # 4a. User Primary Font (Highest Priority)
        if primary_font and primary_font.strip():
            final_fonts.append(primary_font)
        else:
            final_fonts.append('Arial')
            
        # 4b. User CJK Font (High Priority Fallback)
        if cjk_font and cjk_font.strip():
            if cjk_font not in final_fonts:
                final_fonts.append(cjk_font)
        
        # 4c. Config CJK Fonts (General Fallback)
        available = self.get_available_fonts()
        config_cjk = CONFIG.get('preferred_plot_fonts', ['Microsoft YaHei', 'SimHei', 'SimSun'])
        
        for f in config_cjk:
            if f in available and f not in final_fonts:
                final_fonts.append(f)
                
        # 4d. Generic Fallback
        final_fonts.append('sans-serif')
                
        # Apply to font.family directly as a list
        rcParams['font.family'] = final_fonts
        rcParams['font.sans-serif'] = final_fonts
        rcParams['font.serif'] = ['Times New Roman'] + [f for f in final_fonts if f != 'Times New Roman']

style_manager_instance = StyleManager()

# --- Backward Compatibility Exports ---
COLORS = style_manager_instance.palettes
STYLES = {'grid': style_manager_instance.GRID_STYLE}

def apply_custom_style(show_grid=False, color_scheme=None, primary_font=None, cjk_font=None, font_sizes=None):
    """
    Apply custom styles and color schemes to Matplotlib using the global StyleManager.
    """
    style_manager_instance.apply_style(show_grid, color_scheme, primary_font, cjk_font, font_sizes)
