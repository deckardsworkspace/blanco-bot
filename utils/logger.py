from typing import Optional
import logging


# Log line format
LOG_FMT_STR = '%(asctime)s [%(levelname)s] %(message)s (%(filename)s:%(lineno)d)'

# ANSI terminal colors (for logging)
ANSI_BLUE = '\x1b[36;20m'
ANSI_GREEN = '\x1b[32;20m'
ANSI_GREY = '\x1b[38;20m'
ANSI_RED = '\x1b[31;20m'
ANSI_RED_BOLD = '\x1b[31;1m'
ANSI_YELLOW = '\x1b[33;20m'
ANSI_RESET = '\x1b[0m'
LOG_FMT_COLOR = {
    logging.DEBUG: ANSI_GREY + LOG_FMT_STR + ANSI_RESET,
    logging.INFO: ANSI_BLUE + LOG_FMT_STR + ANSI_RESET,
    logging.WARNING: ANSI_YELLOW + LOG_FMT_STR + ANSI_RESET,
    logging.ERROR: ANSI_RED + LOG_FMT_STR + ANSI_RESET,
    logging.CRITICAL: ANSI_RED_BOLD + LOG_FMT_STR + ANSI_RESET
}


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


def create_logger(name: str, debug: bool = False) -> logging.Logger:
    """
    Creates a logger with the given name and returns it.

    :param name: Name of the logger
    :return: Logger object
    """
    logger = logging.getLogger(name)
    if (logger.hasHandlers()):
        logger.handlers.clear()

    # Set level
    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    # Add color formatter
    color_handler = logging.StreamHandler()
    color_handler.setFormatter(ColorFormatter())
    logger.addHandler(color_handler)
    
    return logger
