"""Atomic file writes with corruption isolation.

All persistence files are written via tmp + fsync + rename so a crash mid
write can never corrupt the previous snapshot. Unreadable files are renamed
to ``<name>.corrupt-<ts>`` instead of failing startup.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Write *data* as JSON atomically (temp file + fsync + rename)."""
    tmp_path = Path(str(path) + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def read_json_isolated(path: Path) -> dict[str, Any] | None:
    """Read JSON; on failure isolate the file and return None.

    A corrupt file is renamed to ``<stem>.corrupt-<timestamp><suffix>`` so
    user data is never silently destroyed and the problem stays visible.
    """
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("persisted payload is not a JSON object")
        return data
    except Exception as exc:
        logger.warning("Unreadable persistence file %s: %s", path, exc)
        try:
            stamp = time.strftime("%Y%m%d-%H%M%S")
            corrupt = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
            path.replace(corrupt)
            logger.warning("Isolated corrupt file as %s", corrupt)
        except OSError:
            pass
        return None
