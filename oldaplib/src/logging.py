# Module-level logger (default fallback)

import logging

_logger = logging.getLogger("oldaplib")
_logger.addHandler(logging.NullHandler())

def set_logger(external_logger: logging.Logger):
    """Inject an external logger (e.g. Flask's app.logger)"""
    global _logger
    _logger = external_logger

def get_logger() -> logging.Logger:
    return _logger