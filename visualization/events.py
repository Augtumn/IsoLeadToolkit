"""Event orchestration entrypoints for plotting updates and interactions."""
from __future__ import annotations

import logging
from typing import Any

from application import RenderPlotUseCase
from core import app_state, state_gateway
from visualization.event_handlers import (
    _disable_rectangle_selector,
    _notify_selection_ui,
    calculate_selected_isochron,
    on_click,
    on_hover,
    on_legend_click,
    refresh_selection_overlay,
    sync_selection_tools,
    toggle_selection_mode,
)

logger = logging.getLogger(__name__)

_ASYNC_EMBEDDING_ALGORITHMS = {'UMAP', 'tSNE', 'PCA', 'RobustPCA'}


def _data_state() -> Any:
    """Return layered data state when available, otherwise fallback to app_state."""
    return getattr(app_state, 'data', app_state)


def _df_global() -> Any:
    return getattr(_data_state(), 'df_global', app_state.df_global)


def _data_cols() -> list[str]:
    return getattr(_data_state(), 'data_cols', app_state.data_cols)


def _group_cols() -> list[str]:
    return getattr(_data_state(), 'group_cols', app_state.group_cols)


def _sync_render_mode(render_mode):
    """Update app_state and control panel if render_mode changed."""
    if render_mode == app_state.render_mode:
        return
    logger.debug('Adjusted render mode: %s -> %s', app_state.render_mode, render_mode)
    state_gateway.set_render_mode(render_mode)
    try:
        panel = getattr(app_state, 'control_panel_ref', None)
        if panel is not None and 'render_mode' in panel.radio_vars:
            panel.radio_vars['render_mode'].set(render_mode)
    except Exception as sync_err:
        logger.warning('Unable to sync control panel render mode: %s', sync_err)


def _cancel_embedding_task(reason: str = '') -> None:
    """Request cancellation for any running embedding task."""
    worker = getattr(app_state, 'embedding_worker', None)
    if worker is None:
        return

    try:
        if worker.isRunning():
            worker.request_cancel()
            logger.debug('Requested cancellation of embedding task. reason=%s', reason)
    except Exception as err:
        logger.warning('Failed to cancel embedding task: %s', err)


def _on_embedding_task_progress(task_token: int, percent: int, stage: str) -> None:
    if task_token != getattr(app_state, 'embedding_task_token', -1):
        return
    callback = getattr(app_state, 'embedding_progress_callback', None)
    if callable(callback):
        try:
            callback(percent, stage)
        except Exception:
            pass


def _on_embedding_task_finished(task_token: int, payload: dict, group_col: str) -> None:
    if task_token != getattr(app_state, 'embedding_task_token', -1):
        logger.debug('Ignore stale embedding result token=%s', task_token)
        return

    state_gateway.set_embedding_worker(None, running=False)

    algorithm = payload.get('algorithm', app_state.render_mode)
    if app_state.render_mode != algorithm:
        logger.debug('Ignore embedding result due to render mode change: %s -> %s', algorithm, app_state.render_mode)
        return

    from .plotting import plot_embedding

    render_ok = plot_embedding(
        group_col,
        algorithm,
        umap_params=app_state.umap_params,
        tsne_params=app_state.tsne_params,
        pca_params=app_state.pca_params,
        robust_pca_params=app_state.robust_pca_params,
        size=app_state.point_size,
        precomputed_embedding=payload.get('embedding'),
        precomputed_meta=payload.get('meta', {}),
    )

    if render_ok:
        refresh_selection_overlay()
        sync_selection_tools()
        _notify_selection_ui()
        try:
            app_state.fig.canvas.draw_idle()
        except Exception:
            pass
        state_gateway.set_initial_render_done(True)
        logger.debug('Async embedding render completed for %s', algorithm)
    else:
        logger.warning('Async embedding render failed for %s', algorithm)


def _on_embedding_task_failed(task_token: int, error_message: str) -> None:
    if task_token != getattr(app_state, 'embedding_task_token', -1):
        return

    state_gateway.set_embedding_worker(None, running=False)
    logger.warning('Embedding task failed: %s', error_message)


def _on_embedding_task_cancelled(task_token: int) -> None:
    if task_token != getattr(app_state, 'embedding_task_token', -1):
        return

    state_gateway.set_embedding_worker(None, running=False)
    logger.debug('Embedding task cancelled: token=%s', task_token)


def _start_async_embedding_render(group_col: str) -> bool:
    """Start background embedding computation for heavy algorithms."""
    from .embedding_worker import EmbeddingWorker
    from .plotting.data import _get_analysis_data

    algorithm = app_state.render_mode
    if algorithm not in _ASYNC_EMBEDDING_ALGORITHMS:
        return False

    x_data, _ = _get_analysis_data()
    if x_data is None:
        return False

    params_map = {
        'UMAP': app_state.umap_params,
        'tSNE': app_state.tsne_params,
        'PCA': app_state.pca_params,
        'RobustPCA': app_state.robust_pca_params,
    }
    params = dict(params_map.get(algorithm, {}))

    _cancel_embedding_task(reason='start_new_task')

    task_token = int(getattr(app_state, 'embedding_task_token', 0)) + 1

    worker = EmbeddingWorker(
        task_token=task_token,
        algorithm=algorithm,
        x_data=x_data,
        params=params,
        feature_names=list(_data_cols()),
    )

    worker.progress.connect(_on_embedding_task_progress)
    worker.finished_signal.connect(lambda token, payload: _on_embedding_task_finished(token, payload, group_col))
    worker.failed.connect(_on_embedding_task_failed)
    worker.cancelled.connect(_on_embedding_task_cancelled)

    state_gateway.set_embedding_worker(worker, running=True, task_token=task_token)
    worker.start()
    logger.debug('Started async embedding task token=%s, algorithm=%s', task_token, algorithm)
    return True


def _build_render_use_case() -> RenderPlotUseCase:
    from .plotting import plot_2d_data, plot_3d_data, plot_embedding

    return RenderPlotUseCase(
        state=app_state,
        get_df_global=_df_global,
        get_data_cols=_data_cols,
        get_group_cols=_group_cols,
        sync_render_mode=_sync_render_mode,
        cancel_embedding_task=_cancel_embedding_task,
        start_async_embedding_render=_start_async_embedding_render,
        plot_embedding=plot_embedding,
        plot_2d_data=plot_2d_data,
        plot_3d_data=plot_3d_data,
        refresh_selection_overlay=refresh_selection_overlay,
        sync_selection_tools=sync_selection_tools,
        notify_selection_ui=_notify_selection_ui,
        disable_rectangle_selector=_disable_rectangle_selector,
    )


def on_slider_change(val=None) -> None:
    """Handle slider and radio button changes from the control panel."""
    try:
        logger.debug('on_slider_change called, val=%s', val)
        _build_render_use_case().execute()
    except Exception as err:
        logger.error('on_slider_change error: %s', err)
        import traceback
        traceback.print_exc()
