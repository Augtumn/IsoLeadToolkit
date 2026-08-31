"""KDE helpers for plotting."""
import logging
from typing import Any

import numpy as np
from scipy.stats import gaussian_kde

from core import app_state, state_gateway
from visualization.line_styles import ensure_line_style
from .style import configure_constrained_layout

logger = logging.getLogger(__name__)

# constrained_layout cannot coexist with axes_grid1 divider axes; it is
# disabled while marginal KDE axes are attached and restored on clear.
_constrained_layout_disabled = False

# Default maximum number of points per group for KDE sampling
_KDE_MAX_POINTS_DEFAULT = 5000
_KDE_GRID_SIZE_DEFAULT = 256
_KDE_BW_ADJUST_DEFAULT = 1.0
_KDE_BANDWIDTH_DEFAULT = 0.0
_KDE_CUT_DEFAULT = 1.0
_KDE_MIN_STD = 1e-12
_KDE_BW_ADJUST_MIN = 0.05
_KDE_BW_ADJUST_MAX = 5.0
_KDE_BW_MIN = 0.01
_KDE_KERNEL_DEFAULT = "gaussian"
_KDE_AUTO_BW_METHOD_DEFAULT = "scott"
_KDE_ALLOWED_KERNELS = (
    "gaussian",
    "tophat",
    "epanechnikov",
    "exponential",
    "linear",
    "cosine",
)
_KDE_ALLOWED_AUTO_BW_METHODS = ("scott", "silverman")

KernelDensity = None
_kernel_density_import_checked = False

sns = None
_seaborn_import_checked = False


def lazy_import_seaborn():
    """Lazy import seaborn for KDE overlay rendering.

    Exposed on the ``kde_utils`` module so callers (rendering/kde.py,
    rendering/raw/plot2d.py) can do ``kde_utils.lazy_import_seaborn()`` and
    then use ``kde_utils.sns``. Without this the KDE overlays fail
    silently with an AttributeError swallowed by their try/except blocks.
    """
    global sns, _seaborn_import_checked
    if sns is None and not _seaborn_import_checked:
        _seaborn_import_checked = True
        try:
            import seaborn as _sns
            sns = _sns
        except Exception as exc:
            logger.warning("Failed to import seaborn for KDE overlays: %s", exc)
    return sns


def _lazy_import_kernel_density():
    """Lazy import sklearn KernelDensity for optional non-Gaussian kernels."""
    global KernelDensity, _kernel_density_import_checked
    if KernelDensity is None and not _kernel_density_import_checked:
        _kernel_density_import_checked = True
        try:
            from sklearn.neighbors import KernelDensity as _KernelDensity

            KernelDensity = _KernelDensity
        except Exception as exc:
            logger.warning("Failed to import sklearn KernelDensity: %s", exc)
    return KernelDensity


def _resolve_kernel_name(value: Any) -> str:
    kernel = str(value or _KDE_KERNEL_DEFAULT).strip().lower()
    return kernel if kernel in _KDE_ALLOWED_KERNELS else _KDE_KERNEL_DEFAULT


def _resolve_auto_bandwidth_method(value: Any) -> str:
    method = str(value or _KDE_AUTO_BW_METHOD_DEFAULT).strip().lower()
    return method if method in _KDE_ALLOWED_AUTO_BW_METHODS else _KDE_AUTO_BW_METHOD_DEFAULT


def _resolve_kernel_bandwidth(
    data: np.ndarray,
    *,
    bw_adjust: float,
    bandwidth: float,
    auto_bandwidth_method: str,
) -> float:
    bw_adjust_safe = max(_KDE_BW_ADJUST_MIN, float(bw_adjust))
    if bandwidth > 0.0:
        return max(_KDE_BW_MIN, float(bandwidth) * bw_adjust_safe)

    std = float(np.nanstd(data))
    if not np.isfinite(std) or std <= _KDE_MIN_STD:
        std = 1.0

    n_samples = max(int(data.size), 2)
    method = _resolve_auto_bandwidth_method(auto_bandwidth_method)
    if method == "silverman":
        factor = float((n_samples * 3.0 / 4.0) ** (-1.0 / 5.0))
    else:
        factor = float(n_samples ** (-1.0 / 5.0))
    return max(_KDE_BW_MIN, std * factor * bw_adjust_safe)


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
    bandwidth: float,
    kernel: str,
    auto_bandwidth_method: str,
    gridsize: int,
    cut: float,
    log_transform: bool,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Estimate 1D density curve with optional log transform on density."""
    data = _to_float_array(values)
    if data.size < 2:
        return None
    if np.nanstd(data) <= _KDE_MIN_STD:
        return None

    kernel_name = _resolve_kernel_name(kernel)
    auto_bw_method = _resolve_auto_bandwidth_method(auto_bandwidth_method)
    bandwidth_value = max(0.0, float(bandwidth))

    try:
        std = float(np.nanstd(data))
        left = float(np.nanmin(data) - max(0.0, float(cut)) * std)
        right = float(np.nanmax(data) + max(0.0, float(cut)) * std)
        if not np.isfinite(left) or not np.isfinite(right) or right <= left:
            return None

        grid = np.linspace(left, right, int(max(32, gridsize)))
        density = None

        if kernel_name == _KDE_KERNEL_DEFAULT and bandwidth_value <= 0.0:
            kde = gaussian_kde(data)
            kde.set_bandwidth(bw_method=auto_bw_method)
            kde.set_bandwidth(bw_method=max(0.05, kde.factor * float(max(0.05, bw_adjust))))
            density = kde(grid)
        else:
            kernel_density_cls = _lazy_import_kernel_density()
            if kernel_density_cls is None:
                return None

            kde = kernel_density_cls(
                bandwidth=_resolve_kernel_bandwidth(
                    data,
                    bw_adjust=bw_adjust,
                    bandwidth=bandwidth_value,
                    auto_bandwidth_method=auto_bw_method,
                ),
                kernel=kernel_name,
            )
            kde.fit(data.reshape(-1, 1))
            density = np.exp(kde.score_samples(grid.reshape(-1, 1)))

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


def _normalize_density_curve(density: np.ndarray) -> np.ndarray:
    """Scale a density curve to a peak of 1.0 (per-curve normalization).

    Marginal KDE axes share one y-scale; without normalization a group whose
    data is extremely concentrated produces a huge density spike that flattens
    every other group's curve against the axis bottom. Normalizing each curve
    to its own peak keeps all shapes comparable. Idempotent when the curve is
    already peak-normalized (e.g. after the log-transform path).
    """
    if density is None or density.size == 0:
        return density
    peak = float(np.nanmax(density))
    if not np.isfinite(peak) or peak <= 0.0:
        return density
    return density / peak


def clear_marginal_axes() -> None:
    global _constrained_layout_disabled
    axes = getattr(app_state, 'marginal_axes', None)
    fig = None
    if axes:
        for ax in axes:
            if fig is None:
                fig = getattr(ax, 'figure', None)
            try:
                ax.remove()
            except Exception:
                pass
    state_gateway.set_marginal_axes(None)
    # Re-enable constrained layout now that the divider axes are gone
    # (constrained_layout cannot coexist with axes_grid1 divider axes).
    if _constrained_layout_disabled:
        _constrained_layout_disabled = False
        if fig is not None:
            try:
                configure_constrained_layout(fig)
            except Exception:
                pass


def _figure_uses_constrained_layout(fig: Any) -> bool:
    """Detect whether a figure has constrained layout enabled."""
    if fig is None:
        return False
    try:
        engine = fig.get_layout_engine()
        if engine is not None:
            return True
    except Exception:
        pass
    try:
        return bool(fig.get_constrained_layout())
    except Exception:
        return False


def _set_figure_constrained_layout(fig: Any, enabled: bool) -> None:
    """Enable/disable constrained layout (both API generations)."""
    try:
        if hasattr(fig, 'set_layout_engine'):
            fig.set_layout_engine('constrained' if enabled else 'none')
            return
    except Exception:
        pass
    try:
        fig.set_constrained_layout(enabled)
    except Exception:
        pass


def draw_marginal_kde(
    ax: Any,
    df_plot: Any,
    group_col: str,
    palette: dict[str, str],
    unique_cats: list[str],
    x_col: str = '_emb_x',
    y_col: str = '_emb_y',
) -> None:
    """Draw marginal KDEs on top/right axes for 2D plots."""
    global _constrained_layout_disabled
    try:
        from mpl_toolkits.axes_grid1 import make_axes_locatable
    except Exception as import_err:
        logger.warning("Failed to import KDE dependencies: %s", import_err)
        return

    # Divider axes are incompatible with constrained layout (axes collapse
    # to zero and matplotlib warns on every draw). Disable it for as long as
    # the marginal axes are attached; clear_marginal_axes restores it.
    fig = getattr(ax, 'figure', None) if ax is not None else None
    if _figure_uses_constrained_layout(fig):
        _set_figure_constrained_layout(fig, False)
        _constrained_layout_disabled = True

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
            'bandwidth': float(getattr(app_state, 'marginal_kde_bandwidth', legacy_style.get('bandwidth', _KDE_BANDWIDTH_DEFAULT)) or 0.0),
            'kernel': _resolve_kernel_name(
                getattr(
                    app_state,
                    'marginal_kde_kernel',
                    legacy_style.get('kernel', _KDE_KERNEL_DEFAULT),
                )
            ),
            'auto_bandwidth_method': _resolve_auto_bandwidth_method(
                getattr(
                    app_state,
                    'marginal_kde_auto_bandwidth_method',
                    legacy_style.get('auto_bandwidth_method', _KDE_AUTO_BW_METHOD_DEFAULT),
                )
            ),
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
    bandwidth = max(0.0, min(float(style.get('bandwidth', _KDE_BANDWIDTH_DEFAULT) or 0.0), 10.0))
    kernel = _resolve_kernel_name(style.get('kernel', _KDE_KERNEL_DEFAULT))
    auto_bandwidth_method = _resolve_auto_bandwidth_method(
        style.get('auto_bandwidth_method', _KDE_AUTO_BW_METHOD_DEFAULT)
    )
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
                bandwidth=bandwidth,
                kernel=kernel,
                auto_bandwidth_method=auto_bandwidth_method,
                gridsize=gridsize,
                cut=cut,
                log_transform=log_transform,
            )
            if curve_x is not None:
                grid_x, density_x = curve_x
                # Per-curve normalization so one tightly-spiked group cannot
                # flatten the other curves on the shared marginal axis.
                density_x = _normalize_density_curve(density_x)
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
                bandwidth=bandwidth,
                kernel=kernel,
                auto_bandwidth_method=auto_bandwidth_method,
                gridsize=gridsize,
                cut=cut,
                log_transform=log_transform,
            )
            if curve_y is not None:
                grid_y, density_y = curve_y
                # Per-curve normalization (see X-side comment above).
                density_y = _normalize_density_curve(density_y)
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
    # NOTE: constrained layout stays OFF while the divider axes exist (see
    # the disable block at the top of this function); clear_marginal_axes
    # re-enables it. Re-enabling here would warn on every draw.

