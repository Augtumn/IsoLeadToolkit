"""
Isotopes Analysis - PyQt5 entry point
"""
import sys
import traceback
import faulthandler

from ui.app import Qt5Application
from utils.logger import setup_logging


if __name__ == "__main__":
    try:
        # Initialize logging (50MB limit)
        setup_logging(max_bytes=50 * 1024 * 1024)

        try:
            crash_log = open("isotopes_crash.log", "a", buffering=1)
            faulthandler.enable(file=crash_log, all_threads=True)
            faulthandler.dump_traceback_later(5, repeat=True, file=crash_log)
            print("[INFO] Crash handler enabled (isotopes_crash.log)", flush=True)
        except Exception as fh_err:
            print(f"[WARN] Failed to enable crash handler: {fh_err}", flush=True)

        print("[START] Application launching...", flush=True)
        app = Qt5Application()
        success = app.run()
        print(f"[END] Application exit code: {0 if success else 1}", flush=True)
        sys.exit(0 if success else 1)
    except Exception as final_err:
        print(f"[FATAL] Uncaught exception: {final_err}", flush=True)
        traceback.print_exc()
        sys.exit(1)
