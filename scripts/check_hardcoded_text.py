"""Guard wrapper: the hardcoded-text check lives with the other locale scripts.

``locales/check_hardcoded_text.py`` needs the application's source tree, not the package, so it sits next
to ``check_untranslated.py``. This wrapper puts it in the same loop as ``scripts/check_*.py`` so a guard run
covers it too.
"""
from __future__ import annotations

import pathlib
import runpy
import sys

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "locales" / "check_hardcoded_text.py"

if __name__ == "__main__":
    sys.argv[0] = str(SCRIPT)
    runpy.run_path(str(SCRIPT), run_name="__main__")
