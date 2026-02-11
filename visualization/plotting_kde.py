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

    max_points = int(getattr(app_state, 'marginal_kde_max_points', 5000))
    rng = np.random.default_rng(42)

    divider = make_axes_locatable(ax)
    top_size = float(getattr(app_state, 'marginal_kde_top_size', 15.0))
    right_size = float(getattr(app_state, 'marginal_kde_right_size', 15.0))
    top_size = max(5.0, min(top_size, 40.0))
    right_size = max(5.0, min(right_size, 40.0))

    ax_top = divider.append_axes("top", size=f"{top_size:.0f}%", pad=0.06, sharex=ax)
    ax_right = divider.append_axes("right", size=f"{right_size:.0f}%", pad=0.06, sharey=ax)

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

        if max_points > 0 and len(xs) > max_points:
            sample_idx = rng.choice(len(xs), size=max_points, replace=False)
            xs = xs[sample_idx]
            ys = ys[sample_idx]

        if len(xs) > 1:
            try:
                sns.kdeplot(
                    x=xs,
                    ax=ax_top,
                    color=palette[cat],
                    fill=kde_fill,
                    alpha=kde_alpha,
                    linewidth=kde_linewidth,
                    warn_singular=False
                )
            except Exception as kde_err:
                print(f"[WARN] Marginal KDE X failed for {cat}: {kde_err}", flush=True)
        if len(ys) > 1:
            try:
                sns.kdeplot(
                    y=ys,
                    ax=ax_right,
                    color=palette[cat],
                    fill=kde_fill,
                    alpha=kde_alpha,
                    linewidth=kde_linewidth,
                    warn_singular=False
                )
            except Exception as kde_err:
                print(f"[WARN] Marginal KDE Y failed for {cat}: {kde_err}", flush=True)

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
