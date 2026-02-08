"""KDE style utilities."""
import tkinter as tk
from tkinter import ttk


def open_kde_style_dialog(parent, translate, app_state, target='kde', swatch=None, on_apply=None):
    """Open dialog to edit KDE style settings."""
    dialog = tk.Toplevel(parent)
    title_key = "KDE Style" if target == 'kde' else "Marginal KDE Style"
    dialog.title(translate(title_key))
    dialog.geometry("420x240")
    dialog.transient(parent)
    dialog.grab_set()

    body = ttk.Frame(dialog, padding=12)
    body.pack(fill=tk.BOTH, expand=True)

    style = getattr(app_state, 'kde_style' if target == 'kde' else 'marginal_kde_style', {})
    alpha_var = tk.DoubleVar(value=float(style.get('alpha', 0.6 if target == 'kde' else 0.25)))
    linewidth_var = tk.DoubleVar(value=float(style.get('linewidth', 1.0)))
    fill_var = tk.BooleanVar(value=bool(style.get('fill', True)))
    levels_var = tk.IntVar(value=int(style.get('levels', 10)))

    form = ttk.Frame(body, style='CardBody.TFrame')
    form.pack(fill=tk.X)

    alpha_row = ttk.Frame(form, style='CardBody.TFrame')
    alpha_row.pack(fill=tk.X, pady=4)
    ttk.Label(alpha_row, text=translate("Opacity"), style='Body.TLabel').pack(side=tk.LEFT)
    ttk.Spinbox(alpha_row, from_=0.05, to=1.0, increment=0.05, textvariable=alpha_var, width=6).pack(side=tk.LEFT, padx=(8, 0))

    width_row = ttk.Frame(form, style='CardBody.TFrame')
    width_row.pack(fill=tk.X, pady=4)
    ttk.Label(width_row, text=translate("Line Width"), style='Body.TLabel').pack(side=tk.LEFT)
    ttk.Spinbox(width_row, from_=0.0, to=4.0, increment=0.1, textvariable=linewidth_var, width=6).pack(side=tk.LEFT, padx=(8, 0))

    fill_row = ttk.Frame(form, style='CardBody.TFrame')
    fill_row.pack(fill=tk.X, pady=4)
    ttk.Label(fill_row, text=translate("Fill"), style='Body.TLabel').pack(side=tk.LEFT)
    ttk.Checkbutton(fill_row, variable=fill_var, style='Option.TCheckbutton').pack(side=tk.LEFT, padx=(8, 0))

    if target == 'kde':
        levels_row = ttk.Frame(form, style='CardBody.TFrame')
        levels_row.pack(fill=tk.X, pady=4)
        ttk.Label(levels_row, text=translate("KDE Levels"), style='Body.TLabel').pack(side=tk.LEFT)
        ttk.Spinbox(levels_row, from_=3, to=30, increment=1, textvariable=levels_var, width=6).pack(side=tk.LEFT, padx=(8, 0))

    btn_row = ttk.Frame(body)
    btn_row.pack(fill=tk.X, pady=(12, 0))
    btn_row.columnconfigure(0, weight=1)

    def _apply():
        target_key = 'kde_style' if target == 'kde' else 'marginal_kde_style'
        style_ref = getattr(app_state, target_key, {})
        style_ref['alpha'] = float(alpha_var.get())
        style_ref['linewidth'] = float(linewidth_var.get())
        style_ref['fill'] = bool(fill_var.get())
        if target == 'kde':
            style_ref['levels'] = int(levels_var.get())
        setattr(app_state, target_key, style_ref)

        if swatch is not None:
            swatch.configure(bg='#e2e8f0')
        dialog.destroy()
        if callable(on_apply):
            on_apply()

    ttk.Button(btn_row, text=translate("Cancel"), style='Secondary.TButton', command=dialog.destroy).pack(side=tk.RIGHT)
    ttk.Button(btn_row, text=translate("Save"), style='Accent.TButton', command=_apply).pack(side=tk.RIGHT, padx=(0, 8))
