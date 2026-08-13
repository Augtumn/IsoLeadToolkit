"""Application use cases for session export/import.

Wraps the pure IO in ``core.persistence`` (``export_session``/``import_session``)
with the state application logic: importing restores configuration through the
StateStore whitelist and, when the archive carries data, hydrates the global
DataFrame through the same path the import wizard uses.
"""
from __future__ import annotations

import io
import logging
from typing import Any

import pandas as pd

from core import (
    set_language,
    state_gateway,
)

logger = logging.getLogger(__name__)

#: Session payload keys that must be restored BEFORE data hydration (the
#: hydrator validates the loaded columns against them).
_DATA_CONTRACT_KEYS = (
    "group_cols",
    "data_cols",
    "file_path",
    "sheet_name",
    "last_group_col",
)


def export_session(path: str) -> bool:
    """Export the current session (config + loaded data) to *path*."""
    from core.persistence import export_session as _export

    return _export(state_gateway, path)


def import_session(path: str) -> tuple[bool, str | None]:
    """Import a session archive and apply it to the live state.

    Returns ``(ok, flag)`` where *flag* is one of:
    - ``None``        — everything applied
    - ``"invalid"``   — file missing/unreadable/unsupported
    - ``"data_failed"`` — configuration restored but the saved data could not
      be hydrated (e.g. columns are no longer numeric after CSV round-trip)
    """
    from core.persistence import import_session as _import

    payloads = _import(path)
    if payloads is None:
        return False, "invalid"

    session_payload: dict[str, Any] = payloads.get("session") or {}
    ui_payload: dict[str, Any] = payloads.get("ui_state") or {}

    data_ok = True
    if payloads.get("has_data") and payloads.get("data_csv") is not None:
        # 1) Restore the data contract first so hydration validates against
        #    the imported column selection.
        contract = {
            key: value for key, value in session_payload.items() if key in _DATA_CONTRACT_KEYS
        }
        if contract:
            state_gateway.restore_snapshot(contract)
        # 2) Hydrate the saved DataFrame (resets transient column selection).
        try:
            df = pd.read_csv(io.BytesIO(payloads["data_csv"].encode("utf-8")))
            from .load_dataset import hydrate_state_from_dataframe

            data_ok = hydrate_state_from_dataframe(
                df,
                file_path=session_payload.get("file_path") or "",
                sheet_name=session_payload.get("sheet_name"),
            )
        except Exception as exc:
            logger.exception("Failed to hydrate session data: %s", exc)
            data_ok = False

    # 3) Restore the full session + UI state (covers visible groups, column
    #    selections and styles wiped by the hydration reset).
    if session_payload:
        state_gateway.restore_snapshot(session_payload)
    if ui_payload:
        state_gateway.restore_snapshot(ui_payload)

    # 4) Language lives in the session payload; refresh translations.
    language = session_payload.get("language")
    if language:
        try:
            set_language(str(language))
        except Exception:
            logger.exception("Failed to apply imported language %s", language)

    if not data_ok and payloads.get("has_data"):
        return True, "data_failed"
    return True, None
