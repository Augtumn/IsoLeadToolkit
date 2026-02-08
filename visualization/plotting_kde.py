"""KDE helpers for plotting."""
import pandas as pd
import numpy as np
from core.state import app_state

sns = None


def lazy_import_seaborn():
    """Lazy import seaborn and return module."""
    global sns
    if sns is None:
        import seaborn as _sns
        sns = _sns
    return sns


def clear_marginal_axes():
    axes = getattr(app_state, 'marginal_axes', None)
    if axes:
        for ax in axes:
            try:
                ax.remove()
            except Exception:
                pass
    app_state.marginal_axes = None


def draw_marginal_kde(ax, df_plot, group_col, palette, unique_cats, x_col='_emb_x', y_col='_emb_y'):
    """Draw marginal KDEs on top/right axes for 2D plots."""
    try:
        lazy_import_seaborn()
        from mpl_toolkits.axes_grid1 import make_axes_locatable
    except Exception as import_err:
        print(f"[WARN] Failed to import KDE dependencies: {import_err}", flush=True)
        return

    divider = make_axes_locatable(ax)
    ax_top = divider.append_axes("top", size="15%", pad=0.06, sharex=ax)
    ax_right = divider.append_axes("right", size="15%", pad=0.06, sharey=ax)

    style = getattr(app_state, 'marginal_kde_style', {})
    kde_alpha = float(style.get('alpha', 0.25))
    kde_linewidth = float(style.get('linewidth', 1.0))
    kde_fill = bool(style.get('fill', True))

    for cat in unique_cats:
        subset = df_plot[df_plot[group_col] == cat]
        if subset.empty:
            continue
        if x_col not in subset.columns or y_col not in subset.columns:
            continue
        xs = subset[x_col].to_numpy(dtype=float, copy=False)
        ys = subset[y_col].to_numpy(dtype=float, copy=False)

        if len(xs) > 1:
            sns.kdeplot(
                x=xs,
                ax=ax_top,
                color=palette[cat],
                fill=kde_fill,
                alpha=kde_alpha,
                linewidth=kde_linewidth,
                warn_singular=False
            )
        if len(ys) > 1:
            sns.kdeplot(
                y=ys,
                ax=ax_right,
                color=palette[cat],
                fill=kde_fill,
                alpha=kde_alpha,
                linewidth=kde_linewidth,
                warn_singular=False
            )

    ax_top.tick_params(axis='x', labelbottom=False)
    ax_top.tick_params(axis='y', left=False, labelleft=False)
    ax_right.tick_params(axis='y', labelleft=False)
    ax_right.tick_params(axis='x', bottom=False, labelbottom=False)
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

    app_state.marginal_axes = (ax_top, ax_right)
    try:
        ax.figure.set_constrained_layout(True)
        ax.figure.set_constrained_layout_pads(w_pad=0.02, h_pad=0.02, wspace=0.02, hspace=0.02)
    except Exception:
        pass
