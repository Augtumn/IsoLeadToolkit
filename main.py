"""
Isotopes Analysis - UMAP Visualization Tool
A robust interactive visualization for lead isotope data analysis

Application entry point - simplified initialization
"""
import sys
import traceback

from core import Application
from utils.logger import setup_logging


if __name__ == "__main__":
    try:
        # Initialize logging (50MB limit)
        setup_logging(max_bytes=50*1024*1024)
        
        print("[START] Application launching...", flush=True)
        app = Application()
        success = app.run()
        print(f"[END] Application exit code: {0 if success else 1}", flush=True)
        sys.exit(0 if success else 1)
    except Exception as final_err:
        print(f"[FATAL] Uncaught exception: {final_err}", flush=True)
        traceback.print_exc()
        sys.exit(1)
