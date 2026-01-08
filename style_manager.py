import matplotlib.pyplot as plt
from matplotlib import rcParams, font_manager
import matplotlib as mpl
from config import CONFIG

# --- Color Cycles ---
# Defined to match common scienceplots schemes
COLORS = {
    'vibrant': ['#EE7733', '#0077BB', '#33BBEE', '#EE3377', '#CC3311', '#009988', '#BBBBBB'],
    'bright': ['#4477AA', '#66CCEE', '#228833', '#CCBB44', '#EE6677', '#AA3377', '#BBBBBB'],
    'high-vis': ['#0d49fb', '#e6091c', '#26eb47', '#8936df', '#fec32d', '#25d7fd'],
    'light': ['#77AADD', '#EE8866', '#EEDD88', '#FFAABB', '#99DDFF', '#44BB99', '#BBCC33', '#AAAA00', '#DDDDDD'],
    'muted': ['#CC6677', '#332288', '#DDCC77', '#117733', '#88CCEE', '#882255', '#44AA99', '#999933', '#AA4499'],
    'retro': ['#4165c0', '#e770a2', '#5ac600', '#696969', '#f2d40f'],
    'std-colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'],
    'dark_background': ['#8dd3c7', '#feffb3', '#bfbbd9', '#fa8174', '#81b1d2', '#fdb462', '#b3de69', '#bc80bd', '#ccebc5', '#ffed6f'],
}

# --- Base Styles ---
# Simplified to just grid settings
STYLES = {
    'grid': {
        'axes.grid': True,
        'grid.linestyle': '--',
        'grid.linewidth': 0.5,
        'grid.alpha': 0.7,
    }
}

def apply_custom_style(show_grid=False, color_scheme=None, primary_font=None, cjk_font=None, font_sizes=None):
    """
    Apply custom styles and color schemes to Matplotlib.
    Simplified version without complex themes.
    """
    # 1. Reset to defaults to clear previous state
    plt.style.use('default')
    
    # 2. Apply Grid if requested
    if show_grid:
        rcParams.update(STYLES['grid'])
    
    # 3. Apply Color Scheme
    if color_scheme and color_scheme in COLORS:
        rcParams['axes.prop_cycle'] = mpl.cycler(color=COLORS[color_scheme])
        
    # 4. Apply Font Sizes
    if font_sizes:
        rcParams['axes.titlesize'] = font_sizes.get('title', 14)
        rcParams['axes.labelsize'] = font_sizes.get('label', 12)
        rcParams['xtick.labelsize'] = font_sizes.get('tick', 10)
        rcParams['ytick.labelsize'] = font_sizes.get('tick', 10)
        rcParams['legend.fontsize'] = font_sizes.get('legend', 10)
        
    # 5. Apply Fonts (Priority: User Primary -> User CJK -> Config CJK -> Generic)
    
    final_fonts = []
    
    # 4a. User Primary Font (Highest Priority)
    if primary_font and primary_font.strip():
        final_fonts.append(primary_font)
    else:
        # Default English font if none selected
        final_fonts.append('Arial')
        
    # 4b. User CJK Font (High Priority Fallback)
    if cjk_font and cjk_font.strip():
        if cjk_font not in final_fonts:
            final_fonts.append(cjk_font)
    
    # 4c. Config CJK Fonts (General Fallback)
    # Filter to only include installed fonts to avoid "findfont" warnings
    available_fonts = {f.name for f in font_manager.fontManager.ttflist}
    config_cjk = CONFIG.get('preferred_plot_fonts', ['Microsoft YaHei', 'SimHei', 'SimSun'])
    
    for f in config_cjk:
        if f in available_fonts and f not in final_fonts:
            final_fonts.append(f)
            
    # 4d. Generic Fallback
    final_fonts.append('sans-serif')
            
    # Apply to font.family directly as a list
    # This ensures Matplotlib tries them in order
    rcParams['font.family'] = final_fonts
    rcParams['font.sans-serif'] = final_fonts
    
    # Also update serif just in case
    rcParams['font.serif'] = ['Times New Roman'] + [f for f in final_fonts if f != 'Times New Roman']

    # 5. Fix Unicode Minus
    rcParams['axes.unicode_minus'] = False
    
    # Debug output
    print(f"[DEBUG] Applied Fonts: {final_fonts[:3]}...", flush=True)
