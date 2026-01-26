"""
Logger setup for Isotopes Analysis application
"""
import sys
import os
import logging
from logging.handlers import RotatingFileHandler


class LoggerWriter:
    """
    Custom writer that writes to both a logger (file) and the original stream (console).
    """
    def __init__(self, logger, level, original_stream):
        self.logger = logger
        self.level = level
        self.original_stream = original_stream
        self.linebuf = ''

    def write(self, buf):
        # Write to original stream (console)
        try:
            self.original_stream.write(buf)
            self.original_stream.flush()
        except Exception:
            pass

        # Buffer and write to logger
        self.linebuf += buf
        if '\n' in self.linebuf:
            lines = self.linebuf.split('\n')
            # Process all complete lines
            for line in lines[:-1]:
                line = line.rstrip()
                if line:
                    self.logger.log(self.level, line)
            # Keep the last partial line
            self.linebuf = lines[-1]

    def flush(self):
        try:
            self.original_stream.flush()
        except Exception:
            pass


def setup_logging(log_filename='isotopes_analyse.log', max_bytes=50*1024*1024, backup_count=1):
    """
    Sets up logging to a rotating file and redirects stdout/stderr to it.
    
    Args:
        log_filename (str): Path to the log file.
        max_bytes (int): Maximum size of the log file in bytes before rotation.
        backup_count (int): Number of backup files to keep.
    """
    # Create a logger specific for stdout/stderr capture
    logger = logging.getLogger('AppLogger')
    logger.setLevel(logging.DEBUG)
    
    # Prevent propagation to root logger to avoid double printing if root has console handler
    logger.propagate = False

    # Create Rotating File Handler
    try:
        handler = RotatingFileHandler(
            log_filename, 
            maxBytes=max_bytes, 
            backupCount=backup_count, 
            encoding='utf-8'
        )
        
        # Format: Time - Message
        formatter = logging.Formatter('%(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        
        logger.addHandler(handler)

        # Redirect stdout and stderr
        # We use INFO for stdout and ERROR for stderr
        sys.stdout = LoggerWriter(logger, logging.INFO, sys.__stdout__)
        sys.stderr = LoggerWriter(logger, logging.ERROR, sys.__stderr__)
        
        print(f"[INFO] Logging initialized. Log file: {os.path.abspath(log_filename)}")
        
    except Exception as e:
        print(f"[ERROR] Failed to setup logging: {e}")
