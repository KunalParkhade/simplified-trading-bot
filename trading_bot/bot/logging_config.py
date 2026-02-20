"""
Logging configuration for the trading bot.

Provides a :func:`setup_logging` function that configures:

* A ``StreamHandler`` (console) at ``INFO`` level.
* A ``RotatingFileHandler`` (file) at ``DEBUG`` level, writing to
  ``logs/trading_bot.log``.

Call :func:`setup_logging` once at application start-up before using any
other module that obtains a logger.
"""

import logging
import logging.handlers
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Rotate at 5 MB, keep 5 backup files
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5


def setup_logging(log_level_console: int = logging.INFO) -> None:
    """
    Configure root logger with console and rotating-file handlers.

    Args:
        log_level_console: Logging level for the console handler.
            Defaults to :data:`logging.INFO`.  The file handler always
            uses :data:`logging.DEBUG`.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level_console)
    console_handler.setFormatter(formatter)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Avoid adding duplicate handlers if called more than once
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    else:
        root_logger.handlers.clear()
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
