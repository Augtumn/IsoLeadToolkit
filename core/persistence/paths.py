"""Persistence file paths and crash markers."""

from __future__ import annotations

from pathlib import Path

from ..config import CONFIG, TEMP_DIR

#: Session parameters (existing file, extended).
SESSION_FILE = Path(CONFIG.get("params_temp_file", TEMP_DIR / "params.json"))
#: User configuration state (styles, legend, presets, recent files, ...).
UI_STATE_FILE = TEMP_DIR / "ui_state.json"
#: Display themes (legacy file, kept as-is for compatibility).
THEMES_FILE = TEMP_DIR / "user_themes.json"
#: Marker written on a clean exit; missing on startup implies a crash.
EXIT_OK_FILE = TEMP_DIR / "last_exit_ok"
#: Optional persistent embedding cache.
CACHE_FILE = TEMP_DIR / "embedding_cache.npz"
