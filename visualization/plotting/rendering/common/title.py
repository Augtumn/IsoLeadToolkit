"""Plot title and axis label helpers for embedding rendering."""
from __future__ import annotations

from typing import Any

from matplotlib import font_manager

from core import CONFIG, app_state, state_gateway

from ...style import _apply_axis_text_style
from .state_access import _active_subset_indices


def _render_title_labels(
    actual_algorithm: str,
    group_col: str,
    umap_params: dict[str, Any],
    tsne_params: dict[str, Any],
    pca_params: dict[str, Any],
    robust_pca_params: dict[str, Any],
) -> None:
    subset_info = ' (Subset)' if _active_subset_indices() is not None else ''

    if actual_algorithm == 'UMAP':
        title = (
            f'Embedding - UMAP{subset_info} (n_neighbors={umap_params["n_neighbors"]}, min_dist={umap_params["min_dist"]})\n'
            f'Colored by {group_col}'
        )
    elif actual_algorithm == 'TSNE':
        title = (
            f'Embedding - t-SNE{subset_info} (perplexity={tsne_params["perplexity"]}, lr={tsne_params["learning_rate"]})\n'
            f'Colored by {group_col}'
        )
    elif actual_algorithm == 'PCA':
        title = f'Embedding - PCA{subset_info} (n_components={pca_params["n_components"]})\nColored by {group_col}'
    elif actual_algorithm == 'RobustPCA':
        title = (
            f'Embedding - Robust PCA{subset_info} (n_components={robust_pca_params["n_components"]})\n'
            f'Colored by {group_col}'
        )
    elif actual_algorithm == 'V1V2':
        title = f'Geochem - V1-V2 Diagram{subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'TERNARY':
        title = f'Raw - Ternary Plot{subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_EVOL_76':
        title = f'Geochem - Pb Evolution / Model Curves (206-207){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_EVOL_86':
        title = f'Geochem - Pb Evolution / Model Curves (206-208){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PLUMBOTECTONICS_76':
        title = f'Geochem - Plumbotectonics (206-207){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PLUMBOTECTONICS_86':
        title = f'Geochem - Plumbotectonics (206-208){subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_MU_AGE':
        title = f'Geochem - Mu vs Age{subset_info}\nColored by {group_col}'
    elif actual_algorithm == 'PB_KAPPA_AGE':
        title = f'Geochem - Kappa vs Age{subset_info}\nColored by {group_col}'
    else:
        title = f'{actual_algorithm}{subset_info}\nColored by {group_col}'

    title_font_dict = {}
    has_cjk = any('\u4e00' <= char <= '\u9fff' for char in title)
    if has_cjk:
        cjk_font = getattr(app_state, 'custom_cjk_font', '')
        if cjk_font:
            title_font_dict['fontname'] = cjk_font
        else:
            try:
                available = {f.name for f in font_manager.fontManager.ttflist}
                for font_name in CONFIG.get('preferred_plot_fonts', []):
                    if font_name in available:
                        title_font_dict['fontname'] = font_name
                        break
            except Exception:
                pass

    state_gateway.set_current_plot_title(title)
    if getattr(app_state, 'show_plot_title', True):
        app_state.ax.set_title(title, pad=getattr(app_state, 'title_pad', 20.0), **title_font_dict)
    else:
        app_state.ax.set_title('')

    if actual_algorithm == 'V1V2':
        app_state.ax.set_xlabel('V1')
        app_state.ax.set_ylabel('V2')
    elif actual_algorithm in ('PB_EVOL_76', 'PLUMBOTECTONICS_76'):
        app_state.ax.set_xlabel('206Pb/204Pb')
        app_state.ax.set_ylabel('207Pb/204Pb')
    elif actual_algorithm in ('PB_EVOL_86', 'PLUMBOTECTONICS_86'):
        app_state.ax.set_xlabel('206Pb/204Pb')
        app_state.ax.set_ylabel('208Pb/204Pb')
    elif actual_algorithm == 'PB_MU_AGE':
        app_state.ax.set_xlabel('Age (Ma)')
        app_state.ax.set_ylabel('Mu (238U/204Pb)')
    elif actual_algorithm == 'PB_KAPPA_AGE':
        app_state.ax.set_xlabel('Age (Ma)')
        app_state.ax.set_ylabel('Kappa (232Th/238U)')
    elif actual_algorithm == 'TERNARY':
        app_state.ax.set_aspect('equal')
    elif actual_algorithm in ('PCA', 'RobustPCA') and hasattr(app_state, 'pca_component_indices'):
        idx_x = app_state.pca_component_indices[0] + 1
        idx_y = app_state.pca_component_indices[1] + 1
        app_state.ax.set_xlabel(f'PC{idx_x}')
        app_state.ax.set_ylabel(f'PC{idx_y}')
    else:
        app_state.ax.set_xlabel(f'{actual_algorithm} Dimension 1')
        app_state.ax.set_ylabel(f'{actual_algorithm} Dimension 2')

    _apply_axis_text_style(app_state.ax)
