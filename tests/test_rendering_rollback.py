"""Rendering exception rollback tests — verify state consistency after errors."""
from __future__ import annotations

import numpy as np


def test_async_render_stale_token_ignored():
    """Stale embedding task token should not modify worker state."""
    from core import app_state

    app_state.embedding_task_token = 999
    app_state.embedding_task_running = True
    app_state.embedding_worker = "mock_worker"

    from visualization.events import _on_embedding_task_finished

    _on_embedding_task_finished(
        task_token=1,
        payload={"algorithm": "UMAP", "embedding": np.zeros((3, 2))},
        group_col="Group",
    )

    assert app_state.embedding_task_token == 999
    assert app_state.embedding_task_running is True
    assert app_state.embedding_worker == "mock_worker"


def test_embedding_task_failed_clears_worker():
    """Matching token failure should clear worker state."""
    from core import app_state

    app_state.embedding_task_token = 42
    app_state.embedding_task_running = True
    app_state.embedding_worker = "mock_worker"

    from visualization.events import _on_embedding_task_failed

    _on_embedding_task_failed(task_token=42, error_message="Test failure")

    assert app_state.embedding_worker is None
    assert not app_state.embedding_task_running


def test_failed_stale_token_ignored():
    """Failed embedding with stale token should not modify state."""
    from core import app_state

    app_state.embedding_task_token = 999
    app_state.embedding_task_running = True
    app_state.embedding_worker = "mock_worker"

    from visualization.events import _on_embedding_task_failed

    _on_embedding_task_failed(task_token=1, error_message="Old failure")

    assert app_state.embedding_task_token == 999
    assert app_state.embedding_task_running is True
