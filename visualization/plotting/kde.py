"""KDE helpers for plotting."""
import logging

import numpy as np
from scipy.stats import gaussian_kde

from core import app_state, state_gateway
from visualization.line_styles import ensure_line_style

logger = logging.getLogger(__name__)

# Default maximum number of points per group for KDE sampling
_KDE_MAX_POINTS_DEFAULT = 5000
_KDE_GRID_SIZE_DEFAULT = 256
_KDE_BW_ADJUST_DEFAULT = 1.0
_KDE_CUT_DEFAULT = 1.0


def _to_float_array(values) -> np.ndarray:
    """Return finite float array for KDE calculation."""
    arr = np.asarray(values, dtype=float)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    return arr[np.isfinite(arr)]


def _estimate_density_curve(
    values,
    *,
    bw_adjust: float,
    gridsize: int,
    cut: float,
    log_transform: bool,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Estimate 1D density curve with optional log transform on density."""
    data = _to_float_array(values)
    if data.size < 2:
        return None
    if np.nanstd(data) <= 1e-12:
        return None

    try:
        kde = gaussian_kde(data)
        kde.set_bandwidth(bw_method=max(0.05, kde.factor * float(max(0.05, bw_adjust))))

        std = float(np.nanstd(data))
        left = float(np.nanmin(data) - max(0.0, float(cut)) * std)
        right = float(np.nanmax(data) + max(0.0, float(cut)) * std)
        if not np.isfinite(left) or not np.isfinite(right) or right <= left:
            return None

        grid = np.linspace(left, right, int(max(32, gridsize)))
        density = kde(grid)
        density = np.clip(density, 0.0, None)
        if log_transform:
            # Log + per-curve normalization prevents narrow spikes from dominating.
            density = np.log1p(density)
            peak = float(np.nanmax(density))
            if np.isfinite(peak) and peak > 0.0:
                density = density / peak
        return grid, density
    except Exception:
        return None


def clear_marginal_axes():
    axes = getattr(app_state, 'marginal_axes', None)
    if axes:
        for ax in axes:
            try:
                ax.remove()
            except Exception:
                pass
    state_gateway.set_marginal_axes(None)


def draw_marginal_kde(ax, df_plot, group_col, palette, unique_cats, x_col='_emb_x', y_col='_emb_y'):
    """Draw marginal KDEs on top/right axes for 2D plots."""
    try:
        from mpl_toolkits.axes_grid1 import make_axes_locatable
    except Exception as import_err:
        logger.warning("Failed to import KDE dependencies: %s", import_err)
        return

    max_points = int(getattr(app_state, 'marginal_kde_max_points', _KDE_MAX_POINTS_DEFAULT))

    rng = np.random.default_rng(42)

    divider = make_axes_locatable(ax)
    top_size = float(getattr(app_state, 'marginal_kde_top_size', 15.0))
    right_size = float(getattr(app_state, 'marginal_kde_right_size', 15.0))
    top_size = max(5.0, min(top_size, 40.0))
    right_size = max(5.0, min(right_size, 40.0))

    ax_top = divider.append_axes("top", size=f"{top_size:.0f}%", pad=0.06, sharex=ax)
    ax_right = divider.append_axes("right", size=f"{right_size:.0f}%", pad=0.06, sharey=ax)

    legacy_style = getattr(app_state, 'marginal_kde_style', {}) or {}
    style = ensure_line_style(
        app_state,
        'marginal_kde_curve',
        {
            'color': None,
            'linewidth': float(legacy_style.get('linewidth', 1.0)),
            'linestyle': '-',
            'alpha': float(legacy_style.get('alpha', 0.25)),
            'fill': bool(legacy_style.get('fill', True)),
            'bw_adjust': float(getattr(app_state, 'marginal_kde_bw_adjust', legacy_style.get('bw_adjust', _KDE_BW_ADJUST_DEFAULT))),
            'gridsize': int(getattr(app_state, 'marginal_kde_gridsize', legacy_style.get('gridsize', _KDE_GRID_SIZE_DEFAULT))),
            'cut': float(getattr(app_state, 'marginal_kde_cut', legacy_style.get('cut', _KDE_CUT_DEFAULT))),
            'log_transform': bool(getattr(app_state, 'marginal_kde_log_transform', legacy_style.get('log_transform', False))),
        }
    )
    kde_alpha = float(style.get('alpha', 0.25))
    kde_linewidth = float(style.get('linewidth', 1.0))
    kde_fill = bool(style.get('fill', True))
    gridsize = max(32, min(int(style.get('gridsize', _KDE_GRID_SIZE_DEFAULT)), 1024))
    bw_adjust = max(0.05, min(float(style.get('bw_adjust', _KDE_BW_ADJUST_DEFAULT)), 5.0))
    cut = max(0.0, min(float(style.get('cut', _KDE_CUT_DEFAULT)), 5.0))
    log_transform = bool(style.get('log_transform', False))
    max_points = max(200, min(max_points, 50000))

    for cat in unique_cats:
        subset = df_plot[df_plot[group_col] == cat]
        if subset.empty:
            continue
        if x_col not in subset.columns or y_col not in subset.columns:
            continue
        xs = subset[x_col].to_numpy(dtype=float, copy=False)
        ys = subset[y_col].to_numpy(dtype=float, copy=False)

        if max_points > 0 and len(xs) > max_points:
            sample_idx = rng.choice(len(xs), size=max_points, replace=False)
            xs = xs[sample_idx]
            ys = ys[sample_idx]

        if len(xs) > 1:
            curve_x = _estimate_density_curve(
                xs,
                bw_adjust=bw_adjust,
                gridsize=gridsize,
                cut=cut,
                log_transform=log_transform,
            )
            if curve_x is not None:
                grid_x, density_x = curve_x
                try:
                    ax_top.plot(
                        grid_x,
                        density_x,
                        color=palette[cat],
                        linewidth=kde_linewidth,
                        alpha=kde_alpha,
                        linestyle='-'
                    )
                    if kde_fill:
                        ax_top.fill_between(
                            grid_x,
                            0.0,
                            density_x,
                            color=palette[cat],
                            alpha=min(kde_alpha * 0.75, 0.85),
                        )
                except Exception as kde_err:
                    logger.warning("Marginal KDE X failed for %s: %s", cat, kde_err)
        if len(ys) > 1:
            curve_y = _estimate_density_curve(
                ys,
                bw_adjust=bw_adjust,
                gridsize=gridsize,
                cut=cut,
                log_transform=log_transform,
            )
            if curve_y is not None:
                grid_y, density_y = curve_y
                try:
                    ax_right.plot(
                        density_y,
                        grid_y,
                        color=palette[cat],
                        linewidth=kde_linewidth,
                        alpha=kde_alpha,
                        linestyle='-'
                    )
                    if kde_fill:
                        ax_right.fill_betweenx(
                            grid_y,
                            0.0,
                            density_y,
                            color=palette[cat],
                            alpha=min(kde_alpha * 0.75, 0.85),
                        )
                except Exception as kde_err:
                    logger.warning("Marginal KDE Y failed for %s: %s", cat, kde_err)

    # Keep marginal panels visually clean: no ticks or tick marks.
    # NOTE: marginal axes share x/y with the main axes. Do not call
    # set_xticks/set_yticks here, or shared main-axis ticks will be cleared.
    ax_top.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False, labelbottom=False, labeltop=False, labelleft=False, labelright=False, length=0)
    ax_right.tick_params(axis='both', which='both', bottom=False, top=False, left=False, right=False, labelbottom=False, labeltop=False, labelleft=False, labelright=False, length=0)
    ax_top.grid(False)
    ax_right.grid(False)
    ax_top.set_xlabel("")
    ax_top.set_ylabel("")
    ax_right.set_xlabel("")
    ax_right.set_ylabel("")
    ax_top.set_facecolor("none")
    ax_right.set_facecolor("none")
    ax_top.set_frame_on(False)
    ax_right.set_frame_on(False)
    try:
        ax_top.patch.set_visible(False)
        ax_right.patch.set_visible(False)
    except Exception:
        pass
    for spine in ax_top.spines.values():
        spine.set_visible(False)
    for spine in ax_right.spines.values():
        spine.set_visible(False)

    state_gateway.set_marginal_axes((ax_top, ax_right))
    try:
        ax.figure.set_constrained_layout(True)
        ax.figure.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)
    except Exception:
        pass

