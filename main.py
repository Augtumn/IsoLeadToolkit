"""
Isotopes Analysis - PyQt5 entry point
"""
import sys
import logging
import traceback
import faulthandler

from ui.app import Qt5Application
from utils.logger import setup_logging

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        # Initialize logging (50MB limit)
        setup_logging(max_bytes=50 * 1024 * 1024)

        try:
            faulthandler.enable(file=sys.stderr, all_threads=True)
            logger.info("Crash handler enabled")
        except Exception as fh_err:
            logger.warning("Failed to enable crash handler: %s", fh_err)

        logger.info("Application launching...")
        app = Qt5Application()
        success = app.run()
        logger.info("Application exit code: %s", 0 if success else 1)
        sys.exit(0 if success else 1)
    except Exception as final_err:
        logger.critical("Uncaught exception: %s", final_err)
        traceback.print_exc()
        sys.exit(1)
