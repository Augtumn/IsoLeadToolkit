"""Localization utilities for handling multi-language support."""
import json
from pathlib import Path
from typing import Dict

from config import CONFIG

_TRANSLATIONS: Dict[str, Dict[str, str]] = {}
_FALLBACK_LANGUAGE = CONFIG.get('default_language', 'en')
_LOCALES_DIR = Path(CONFIG.get('locales_dir', 'locales'))


def available_languages() -> Dict[str, str]:
    """Return mapping of language codes to human-readable labels."""
    return CONFIG.get('languages', {})


def _load_language(language: str, force: bool = False) -> None:
    """Load translation file for the given language into cache."""
    if not force and language in _TRANSLATIONS:
        if _TRANSLATIONS[language]:
            return

    locale_path = _LOCALES_DIR / f"{language}.json"
    
    if not locale_path.exists():
        _TRANSLATIONS[language] = {}
        return

    try:
        # Try utf-8-sig first (handles BOM), then utf-8
        try:
            with open(locale_path, 'r', encoding='utf-8-sig') as handle:
                data = json.load(handle)
        except UnicodeDecodeError:
            with open(locale_path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
    except Exception as e:
        print(f"[ERROR] Failed to load locale file {locale_path}: {e}")
        data = {}
    
    _TRANSLATIONS[language] = data or {}


def ensure_language(language: str) -> None:
    """Ensure translations for the given language are loaded."""
    _load_language(language)


def translate(text: str, language: str = None, **kwargs) -> str:
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
            from state import app_state  # Lazy import to avoid circular import
        except Exception:
            app_state = None
        if app_state is not None:
            language = getattr(app_state, 'language', _FALLBACK_LANGUAGE)
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
        try:
            translation = translation.format(**kwargs)
        except Exception:
            pass

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
        from state import app_state  # Lazy import to avoid circular import
    except Exception:
        return False

    app_state.language = language
    notify = getattr(app_state, 'notify_language_change', None)
    if callable(notify):
        notify()
    return True