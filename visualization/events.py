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
from .plotting.rendering.common.state_access import (
    _data_cols,
    _df_global,
    _group_cols,
)

logger = logging.getLogger(__name__)

_ASYNC_EMBEDDING_ALGORITHMS = {'UMAP', 'tSNE', 'PCA', 'RobustPCA'}

# Retired embedding workers kept alive until their threads actually stop.
# Replacing app_state.embedding_worker drops the only strong reference; a
# running QThread that gets garbage-collected aborts the process with
# "QThread: Destroyed while thread is still running".
_retired_workers: list[Any] = []


def _sweep_retired_workers() -> None:
    """Reap retired workers whose threads have finished."""
    remaining: list[Any] = []
    for worker in _retired_workers:
        try:
            if worker is not None and worker.isRunning():
                remaining.append(worker)
                continue
            if worker is not None:
                worker.wait(5000)
                worker.deleteLater()
        except Exception as err:
            logger.warning('Failed to retire embedding worker: %s', err)
    _retired_workers[:] = remaining


def shutdown_embedding_worker() -> None:
    """Cancel, wait for, and dispose of all embedding workers (app exit).

    Workers that do not stop within the wait window are KEPT ALIVE with a
    warning: dropping the last reference would let GC destroy a running
    QThread ("QThread: Destroyed while thread is still running").
    """
    try:
        _cancel_embedding_task(reason='app_shutdown')
    except Exception:
        pass
    current = getattr(app_state, 'embedding_worker', None)
    if current is not None:
        _retired_workers.append(current)
        state_gateway.set_embedding_worker(None, running=False)
    _sweep_retired_workers()
    still_running = []
    for worker in list(_retired_workers):
        try:
            stopped = worker.wait(5000)
            if stopped:
                worker.deleteLater()
            else:
                still_running.append(worker)
                logger.error(
                    "Embedding worker still running after shutdown wait; "
                    "keeping it alive to avoid destroying a running thread"
                )
        except Exception:
            pass
    _retired_workers[:] = still_running


def _sync_render_mode(render_mode: str) -> None:
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


_CACHE_ALGORITHM_NAMES = {
    'UMAP': 'umap',
    'tSNE': 'tsne',
    'PCA': 'pca',
    'RobustPCA': 'robust_pca',
}


def _embedding_cache_key(algorithm: str, params: dict) -> Any:
    """Build the LRU cache key used by the sync embedding getters."""
    from core.cache import build_embedding_cache_key
    from .plotting.core import _build_subset_key

    cache_name = _CACHE_ALGORITHM_NAMES.get(algorithm, str(algorithm).lower())
    return build_embedding_cache_key(app_state, cache_name, params, _build_subset_key())


def _render_embedding_result(group_col: str, algorithm: str, payload: dict) -> bool:
    """Render a computed embedding and finish the render cycle.

    Shared by the async worker completion path and the cache-hit fast path.
    """
    from .plotting import plot_embedding

    # Use the worker's original params for the computed algorithm so the
    # title / labels match the embedding that was actually produced.
    worker_params = payload.get('params', {}) or {}
    umap_p = dict(app_state.umap_params)
    tsne_p = dict(app_state.tsne_params)
    pca_p = dict(app_state.pca_params)
    robust_pca_p = dict(app_state.robust_pca_params)
    if algorithm == 'UMAP':
        umap_p.update(worker_params)
    elif algorithm == 'tSNE':
        tsne_p.update(worker_params)
    elif algorithm == 'PCA':
        pca_p.update(worker_params)
    elif algorithm == 'RobustPCA':
        robust_pca_p.update(worker_params)

    render_ok = plot_embedding(
        group_col,
        algorithm,
        umap_params=umap_p,
        tsne_params=tsne_p,
        pca_params=pca_p,
        robust_pca_params=robust_pca_p,
        size=app_state.point_size,
        precomputed_embedding=payload.get('embedding'),
        precomputed_meta=payload.get('meta', {}),
    )

    if render_ok:
        # Populate the LRU cache so subsequent renders (including style-only
        # slider changes) short-circuit instead of recomputing.
        embedding = payload.get('embedding')
        if embedding is not None:
            try:
                app_state.embedding_cache.set(
                    _embedding_cache_key(algorithm, worker_params),
                    embedding,
                )
            except Exception as cache_err:
                logger.warning('Failed to cache embedding: %s', cache_err)
        refresh_selection_overlay()
        sync_selection_tools()
        _notify_selection_ui()
        try:
            app_state.fig.canvas.draw_idle()
            app_state.fig.canvas.flush_events()
        except Exception:
            pass
        state_gateway.set_initial_render_done(True)
        logger.debug('Embedding render completed for %s', algorithm)
    else:
        logger.warning('Embedding render failed for %s', algorithm)
    return render_ok


def _on_embedding_task_finished(task_token: int, payload: dict, group_col: str) -> None:
    _sweep_retired_workers()
    if task_token != getattr(app_state, 'embedding_task_token', -1):
        logger.debug('Ignore stale embedding result token=%s', task_token)
        return

    finished_worker = getattr(app_state, 'embedding_worker', None)
    state_gateway.set_embedding_worker(None, running=False)
    if finished_worker is not None:
        _retired_workers.append(finished_worker)

    algorithm = payload.get('algorithm', app_state.render_mode)
    if app_state.render_mode != algorithm:
        logger.debug('Ignore embedding result due to render mode change: %s -> %s', algorithm, app_state.render_mode)
        return

    _render_embedding_result(group_col, algorithm, payload)


def _on_embedding_task_failed(task_token: int, error_message: str) -> None:
    _sweep_retired_workers()
    if task_token != getattr(app_state, 'embedding_task_token', -1):
        return

    failed_worker = getattr(app_state, 'embedding_worker', None)
    state_gateway.set_embedding_worker(None, running=False)
    if failed_worker is not None:
        _retired_workers.append(failed_worker)
    logger.warning('Embedding task failed: %s', error_message)

    # Notify user with a visible error dialog so silent failures don't
    # leave the user wondering why the plot didn't refresh.
    try:
        from PyQt5.QtWidgets import QApplication, QMessageBox
        from core import translate as _t

        parent = QApplication.activeWindow()
        algorithm = getattr(app_state, 'render_mode', 'Unknown')
        QMessageBox.warning(
            parent,
            _t("Embedding Error"),
            _t("Failed to compute {algorithm} embedding: {error}").format(
                algorithm=algorithm,
                error=error_message,
            ),
        )
    except Exception as notify_err:
        logger.warning('Failed to show embedding error dialog: %s', notify_err)


def _on_embedding_task_cancelled(task_token: int) -> None:
    _sweep_retired_workers()
    if task_token != getattr(app_state, 'embedding_task_token', -1):
        return

    cancelled_worker = getattr(app_state, 'embedding_worker', None)
    state_gateway.set_embedding_worker(None, running=False)
    if cancelled_worker is not None:
        _retired_workers.append(cancelled_worker)
    logger.debug('Embedding task cancelled: token=%s', task_token)


def _start_async_embedding_render(group_col: str) -> tuple[bool, bool]:
    """Start background embedding computation for heavy algorithms.

    Returns ``(rendered_ok, pending_async)``:
    - ``(True, False)`` — a cached embedding was rendered synchronously;
    - ``(True, True)`` — the background worker was started;
    - ``(False, False)`` — nothing could be started.
    """
    from .embedding_worker import EmbeddingWorker
    from .plotting.data import _get_analysis_data

    algorithm = app_state.render_mode
    if algorithm not in _ASYNC_EMBEDDING_ALGORITHMS:
        return False, False

    params_map = {
        'UMAP': app_state.umap_params,
        'tSNE': app_state.tsne_params,
        'PCA': app_state.pca_params,
        'RobustPCA': app_state.robust_pca_params,
    }
    params = dict(params_map.get(algorithm, {}))

    # Cache fast path: identical algorithm + params + data was already
    # computed; render it synchronously and skip the worker entirely.
    try:
        cached = app_state.embedding_cache.get(_embedding_cache_key(algorithm, params))
    except Exception:
        cached = None
    if cached is not None:
        logger.debug('Embedding cache hit for %s; rendering synchronously', algorithm)
        _cancel_embedding_task(reason='cache_hit')
        ok = _render_embedding_result(
            group_col,
            algorithm,
            {'algorithm': algorithm, 'embedding': cached, 'meta': {}, 'params': params},
        )
        return ok, False

    x_data, _ = _get_analysis_data()
    if x_data is None:
        return False, False

    _cancel_embedding_task(reason='start_new_task')

    # Keep the old worker referenced until its thread actually stops;
    # dropping the last reference while it is still running aborts Qt.
    old_worker = getattr(app_state, 'embedding_worker', None)
    if old_worker is not None:
        _retired_workers.append(old_worker)

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
    return True, True


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
        logger.exception('on_slider_change error: %s', err)
