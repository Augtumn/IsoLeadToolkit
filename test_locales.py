
import sys
import os
from pathlib import Path
import json

# Add current directory to path
sys.path.append(os.getcwd())

from localization import _load_language, translate, _TRANSLATIONS, set_language
from config import CONFIG

print(f"Current working directory: {os.getcwd()}")
print(f"Config locales_dir: {CONFIG['locales_dir']}")
print(f"Locales dir exists: {CONFIG['locales_dir'].exists()}")

print("\n--- Testing 'zh' loading ---")
_load_language('zh', force=True)
print(f"Translations loaded for 'zh': {len(_TRANSLATIONS.get('zh', {}))}")
if 'zh' in _TRANSLATIONS:
    print(f"Sample key 'Select Data File': {_TRANSLATIONS['zh'].get('Select Data File', 'NOT FOUND')}")

print("\n--- Testing Translation Function ---")
# Mock app_state if needed, but translate handles it
try:
    from state import app_state
    app_state.language = 'zh'
    print("Set app_state.language = 'zh'")
except ImportError:
    print("Could not import app_state")

result = translate("Select Data File", language='zh')
print(f"translate('Select Data File', language='zh') -> '{result}'")

result_default = translate("Select Data File")
print(f"translate('Select Data File') [default] -> '{result_default}'")

print("\n--- Testing 'en' loading ---")
_load_language('en', force=True)
print(f"Translations loaded for 'en': {len(_TRANSLATIONS.get('en', {}))}")
