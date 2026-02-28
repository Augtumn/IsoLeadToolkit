"""
Isotopes Analysis - PyQt5 entry point
"""
import os
import sys
import logging
import traceback
import faulthandler

from utils.logger import setup_logging

logger = logging.getLogger(__name__)


def _configure_qt_debug_mode(argv):
    """Enable verbose Qt diagnostics when requested."""
    enabled = os.environ.get('ISOTOPES_QT_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}
    if '--qt-debug' in argv:
        enabled = True
        try:
            argv.remove('--qt-debug')
        except ValueError:
            pass

    if not enabled:
        return

    os.environ['ISOTOPES_QT_DEBUG'] = '1'
    os.environ.setdefault('ISOTOPES_LOG_LEVEL', 'DEBUG')
    os.environ.setdefault('QT_DEBUG_PLUGINS', '1')
    os.environ.setdefault(
        'QT_LOGGING_RULES',
        ';'.join([
            '*.debug=true',
            'qt.qpa.*=true',
            'qt.widgets.*=true',
            'qt.gui.*=true',
            'qt.core.qobject.*=true',
        ])
    )


if __name__ == "__main__":
    try:
        _configure_qt_debug_mode(sys.argv)

        # Initialize logging (50MB limit)
        setup_logging(max_bytes=50 * 1024 * 1024)

        from ui.app import Qt5Application

        try:
            faulthandler.enable(file=sys.stderr, all_threads=True)
            logger.info("Crash handler enabled")
        except Exception as fh_err:
            logger.warning("Failed to enable crash handler: %s", fh_err)

        if os.environ.get('ISOTOPES_QT_DEBUG', '').strip() == '1':
            logger.info("Qt debug mode enabled (--qt-debug)")

        logger.info("Application launching...")
        app = Qt5Application()
        success = app.run()
        logger.info("Application exit code: %s", 0 if success else 1)
        sys.exit(0 if success else 1)
    except Exception as final_err:
        logger.critical("Uncaught exception: %s", final_err)
        traceback.print_exc()
        sys.exit(1)
