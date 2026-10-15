"""Localization utilities for handling multi-language support."""
from __future__ import annotations

import json
import logging
from typing import Any

from .config import CONFIG, LOCALES_DIR

logger = logging.getLogger(__name__)

_TRANSLATIONS: dict[str, dict[str, str]] = {}
_FALLBACK_LANGUAGE = CONFIG.get('default_language', 'en')
_LOCALES_DIR = LOCALES_DIR


def available_languages() -> dict[str, str]:
    """Return mapping of language codes to human-readable labels."""
    return CONFIG.get('languages', {})


def _load_language(language: str) -> None:
    """Load translation file for the given language into cache.

    Raises:
        FileNotFoundError: the locale file is missing - a broken installation is reported,
            never papered over with an empty translation table.
        json.JSONDecodeError: the locale file is corrupt.
    """
    if language in _TRANSLATIONS:
        return

    locale_path = _LOCALES_DIR / f"{language}.json"
    # utf-8-sig decodes both plain UTF-8 and a BOM-prefixed file, so one read is enough.
    with open(locale_path, 'r', encoding='utf-8-sig') as handle:
        _TRANSLATIONS[language] = json.load(handle)


def ensure_language(language: str) -> None:
    """Ensure translations for the given language are loaded."""
    _load_language(language)


def translate(text: str, language: str | None = None, **kwargs: Any) -> str:
    """Translate the provided text into the requested language.

    Args:
        text: Source text (English canonical form) used as the lookup key.
        language: Optional language code. When omitted, uses the current
            application language from state.
        **kwargs: Optional formatting arguments.

    Returns:
        Translated text with formatting applied when possible.
    """
    if not isinstance(text, str):
        return text

    if language is None:
        try:
            from .state import app_state  # Lazy import to avoid circular import
        except Exception:
            # Reached only while core.state is still initializing (translate can be
            # called from module-level code); a broken install raises elsewhere.
            logger.warning(
                'core.state unavailable while translating %r, using %s',
                text, _FALLBACK_LANGUAGE,
            )
            app_state = None
        if app_state is not None:
            language = app_state.language
        else:
            language = _FALLBACK_LANGUAGE

    ensure_language(language)
    translation = _TRANSLATIONS.get(language, {}).get(text)

    if translation is None and language != _FALLBACK_LANGUAGE:
        ensure_language(_FALLBACK_LANGUAGE)
        translation = _TRANSLATIONS.get(_FALLBACK_LANGUAGE, {}).get(text, text)

    if translation is None:
        translation = text

    if kwargs:
        # No fallback: a placeholder that does not match its arguments is a bug in the call
        # site (or in the locale file), and hiding it shipped messages with literal ``{name}``
        # in them. Every placeholder key in the code is formatted at its call site.
        translation = translation.format(**kwargs)

    return translation


def validate_language(language: str) -> bool:
    """Return True if the language is supported."""
    return language in available_languages()


def set_language(language: str) -> bool:
    """Set the active application language.

    Returns True when language updated successfully.
    """
    if not validate_language(language):
        return False

    ensure_language(language)
    try:
        from .state import app_state, state_gateway  # Lazy import to avoid circular import
    except Exception:
        logger.warning('core.state unavailable, language left unchanged (requested %s)', language)
        return False

    state_gateway.set_language_code(language)
    notify = getattr(app_state, 'notify_language_change', None)
    if callable(notify):
        notify()
    return True


def translation_table(language: str) -> dict[str, str]:
    """Read-only view of the loaded table for *language*.

    The UI layer needs the table itself to translate a widget tree in place by matching the
    text it already shows, which is how the panels pick up a language switch without being
    rebuilt or tagged one widget at a time.
    """
    ensure_language(language)
    return dict(_TRANSLATIONS.get(language, {}))


def default_language() -> str:
    """The language whose texts are the lookup keys."""
    return _FALLBACK_LANGUAGE
