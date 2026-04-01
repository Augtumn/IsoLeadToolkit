"""Equation overlay evaluation and rendering helpers for geochemistry plotting."""
from __future__ import annotations

import ast
import logging
import operator

import numpy as np

from core import app_state
from visualization.line_styles import ensure_line_style
from ..label_layout import position_curve_label
from .overlay_helpers import (
    _format_label_text,
    _label_bbox,
    _register_overlay_artist,
    _register_overlay_curve_label,
    _resolve_label_options,
)

logger = logging.getLogger(__name__)

def _safe_eval_expression(expression, x_vals):
    """Safely evaluate a mathematical expression over *x_vals*.

    Uses AST parsing to restrict allowed operations to arithmetic,
    comparisons, and a whitelist of numpy functions. No arbitrary
    code execution is possible.
    """
    _ALLOWED_NUMPY = {
        'sin', 'cos', 'tan', 'arcsin', 'arccos', 'arctan', 'arctan2',
        'exp', 'log', 'log2', 'log10', 'sqrt', 'abs', 'power', 'pi', 'e',
        'maximum', 'minimum', 'clip', 'where', 'sign', 'floor', 'ceil',
    }

    _BINOP_MAP = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
    }

    _UNARYOP_MAP = {
        ast.UAdd: operator.pos,
        ast.USub: operator.neg,
    }

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, (int, float)):
                raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")
            return node.value
        if isinstance(node, ast.Name):
            if node.id == 'x':
                return x_vals
            if node.id == 'pi':
                return np.pi
            if node.id == 'e':
                return np.e
            raise ValueError(f"Unknown variable: {node.id}")
        if isinstance(node, ast.BinOp):
            op_fn = _BINOP_MAP.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op_fn(_eval_node(node.left), _eval_node(node.right))
        if isinstance(node, ast.UnaryOp):
            op_fn = _UNARYOP_MAP.get(type(node.op))
            if op_fn is None:
                raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
            return op_fn(_eval_node(node.operand))
        if isinstance(node, ast.Call):
            if not isinstance(node.func, (ast.Name, ast.Attribute)):
                raise ValueError("Only direct function calls are allowed")
            if isinstance(node.func, ast.Attribute):
                if not (isinstance(node.func.value, ast.Name) and node.func.value.id == 'np'):
                    raise ValueError(f"Only np.* calls are allowed")
                func_name = node.func.attr
            else:
                func_name = node.func.id
            if func_name not in _ALLOWED_NUMPY:
                raise ValueError(f"Function not allowed: {func_name}")
            np_func = getattr(np, func_name)
            args = [_eval_node(a) for a in node.args]
            return np_func(*args)
        if isinstance(node, ast.IfExp):
            test = _eval_node(node.test)
            body = _eval_node(node.body)
            orelse = _eval_node(node.orelse)
            return np.where(test, body, orelse)
        if isinstance(node, ast.Compare):
            left = _eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = _eval_node(comparator)
                if isinstance(op, ast.Lt):
                    left = left < right
                elif isinstance(op, ast.LtE):
                    left = left <= right
                elif isinstance(op, ast.Gt):
                    left = left > right
                elif isinstance(op, ast.GtE):
                    left = left >= right
                else:
                    raise ValueError(f"Unsupported comparison: {type(op).__name__}")
            return left
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    tree = ast.parse(expression, mode='eval')
    return _eval_node(tree)


def _draw_equation_overlays(ax):
    """Draw configured equation overlays on the current axes."""
    if not getattr(app_state, 'show_equation_overlays', False):
        return

    overlays = getattr(app_state, 'equation_overlays', []) or []
    if not overlays:
        return

    x_min, x_max = ax.get_xlim()
    x_vals = np.linspace(x_min, x_max, 200)

    for overlay in overlays:
        if not overlay.get('enabled', True):
            continue

        expression = overlay.get('expression')
        slope = overlay.get('slope')
        intercept = overlay.get('intercept', 0.0)
        y_vals = None

        if expression:
            try:
                y_vals = _safe_eval_expression(expression, x_vals)
            except Exception as err:
                logger.warning("Failed to evaluate equation '%s': %s", expression, err)
                continue
        elif slope is not None:
            y_vals = slope * x_vals + intercept

        if y_vals is None:
            continue

        style_key = overlay.get('style_key')
        if not style_key:
            overlay_id = overlay.get('id') or overlay.get('expression') or overlay.get('label') or 'equation'
            style_key = f"equation:{overlay_id}"
            overlay['style_key'] = style_key

        existing_style = getattr(app_state, 'line_styles', {}).get(style_key, {}) or {}
        fallback_color = None if existing_style.get('color', '__missing__') in (None, '') else overlay.get('color', '#ef4444')
        style = ensure_line_style(
            app_state,
            style_key,
            {
                'color': fallback_color,
                'linewidth': overlay.get('linewidth', 1.0),
                'linestyle': overlay.get('linestyle', '--'),
                'alpha': overlay.get('alpha', 0.85),
            }
        )

        line_color = style.get('color') or overlay.get('color', '#ef4444')
        line_artists = ax.plot(
            x_vals,
            y_vals,
            color=line_color,
            linewidth=style['linewidth'],
            linestyle=style['linestyle'],
            alpha=style['alpha'],
            zorder=1,
            label='_nolegend_'
        )
        for artist in line_artists:
            _register_overlay_artist(style_key, artist)

        label_opts = _resolve_label_options(
            style_key,
            {
                'label_text': '',
                'label_fontsize': 8,
                'label_background': False,
                'label_bg_color': '#ffffff',
                'label_bg_alpha': 0.85,
                'label_position': 'auto',
            }
        )
        label_text = _format_label_text(label_opts.get('label_text'), label=overlay.get('label'))
        if label_text:
            text_artist = ax.text(
                x_vals[0],
                y_vals[0],
                label_text,
                color=line_color,
                fontsize=label_opts['label_fontsize'],
                va='center',
                ha='center',
                alpha=style['alpha'],
                bbox=_label_bbox(label_opts, edgecolor=line_color)
            )
            _register_overlay_curve_label(
                text_artist,
                x_vals,
                y_vals,
                label_text,
                label_opts.get('label_position', 'auto'),
                style_key=style_key
            )
            position_curve_label(
                ax,
                text_artist,
                mode='isoage',
                x_line=x_vals,
                y_line=y_vals,
                label_text=label_text,
                position_mode=label_opts.get('label_position', 'auto'),
            )


