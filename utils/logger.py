"""
Custom logger module that supports ANSI color codes.
"""

import logging
from typing import Optional

import sentry_sdk
from sentry_sdk.integrations.logging import EventHandler

from .config import DEBUG_ENABLED, SENTRY_DSN, SENTRY_ENV
from .constants import RELEASE

# Log line format
LOG_FMT_STR = '{0}%(asctime)s.%(msecs)03d {1}[%(levelname)s]{2} %(message)s (%(filename)s:%(lineno)d)' # pylint: disable=line-too-long

# ANSI terminal colors (for logging)
ANSI_BLUE = '\x1b[36;20m'
ANSI_GREEN = '\x1b[32;20m'
ANSI_GREY = '\x1b[37;1m'
ANSI_RED = '\x1b[31;20m'
ANSI_RED_BOLD = '\x1b[41;1m'
ANSI_YELLOW = '\x1b[33;20m'
ANSI_RESET = '\x1b[0m'
LOG_FMT_COLOR = {
    logging.DEBUG: LOG_FMT_STR.format(ANSI_GREY, ANSI_GREEN, ANSI_RESET),
    logging.INFO: LOG_FMT_STR.format(ANSI_GREY, ANSI_BLUE, ANSI_RESET),
    logging.WARNING: LOG_FMT_STR.format(ANSI_GREY, ANSI_YELLOW, ANSI_RESET),
    logging.ERROR: LOG_FMT_STR.format(ANSI_GREY, ANSI_RED, ANSI_RESET),
    logging.CRITICAL: LOG_FMT_STR.format(ANSI_RED_BOLD, ANSI_RED_BOLD, ANSI_RESET),
}


# Initialize sentry
if SENTRY_DSN is not None and SENTRY_ENV is not None:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=SENTRY_ENV,
        release=RELEASE,
        traces_sample_rate=1.0
    )

class ColorFormatter(logging.Formatter):
    """
    Custom logging formatter that supports ANSI color codes.

    Adapted from https://stackoverflow.com/a/384125
    """
    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        logging.Formatter.__init__(self, fmt, datefmt)

    def format(self, record: logging.LogRecord):
        log_fmt = LOG_FMT_COLOR.get(record.levelno)
        formatter = logging.Formatter(fmt=log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
        return formatter.format(record)


def create_logger(name: str) -> logging.Logger:
    """
    Creates a logger with the given name and returns it.

    :param name: Name of the logger
    :return: Logger object
    """
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()

    # Set level
    level = logging.DEBUG if DEBUG_ENABLED else logging.INFO
    logger.setLevel(level)

    # Set level names
    logging.addLevelName(logging.DEBUG, 'DBUG')
    logging.addLevelName(logging.INFO, 'INFO')
    logging.addLevelName(logging.WARNING, 'WARN')
    logging.addLevelName(logging.ERROR, 'ERR!')
    logging.addLevelName(logging.CRITICAL, 'CRIT')

    # Add color formatter
    color_handler = logging.StreamHandler()
    color_handler.setFormatter(ColorFormatter())
    logger.addHandler(color_handler)

    # Add Sentry handler
    if SENTRY_DSN is not None and SENTRY_ENV is not None:
        sentry_handler = EventHandler()
        sentry_handler.setLevel(logging.ERROR)
        logger.addHandler(sentry_handler)

    return logger
